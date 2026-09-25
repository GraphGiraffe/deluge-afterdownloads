"""Windows and systemd power adapters; no changes to system settings."""
from .i18n import _
import ctypes
from ctypes import wintypes
import os
import subprocess
import threading
import sys
import shutil
import shlex
import queue

AWAKE_FLAGS = 0x80000001  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED


def capabilities():
    if sys.platform.startswith('linux'):
        return _linux_capabilities()
    if os.name != 'nt':
        return dict(sleep=False, hibernate=False, shutdown=False,
                    reason=_('Эта платформа не поддерживается: нужны Windows или Linux с systemd/logind.'))
    power = ctypes.WinDLL('powrprof', use_last_error=True)
    query = power.GetPwrCapabilities
    query.argtypes = [ctypes.c_void_p]
    query.restype = ctypes.c_ubyte
    # Stable leading BOOLEAN members: S1/S2/S3 at offsets 3/4/5.
    buffer = ctypes.create_string_buffer(256)
    ok = bool(query(buffer))
    sleep = bool(ok and any(buffer.raw[i] for i in (3, 4, 5)))
    hibernate_query = power.IsPwrHibernateAllowed
    hibernate_query.argtypes = []
    hibernate_query.restype = ctypes.c_ubyte
    hibernate = bool(hibernate_query())
    reason = (_('Сон доступен (S1–S3).') if sleep else
              _('Сон недоступен в плагине: нет S1–S3; вызов при S0 может привести к гибернации.') if ok else
              _('Сон недоступен: Windows не вернула поддерживаемые режимы.'))
    reason += '\n' + (_('Гибернация доступна.') if hibernate else
                       _('Гибернация недоступна: отключена в Windows или не поддерживается.'))
    return dict(sleep=sleep, hibernate=hibernate, shutdown=True, reason=reason)


class WindowsAwakeGuard:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError(_('Требуется Windows.'))
        self._stop = threading.Event()
        self._ready = threading.Event()
        self.active = False
        self._thread = threading.Thread(target=self._run, name='DelugeAfterDownloadsAwake', daemon=True)
        self._thread.start()
        if not self._ready.wait(5) or not self.active:
            self.close()
            raise RuntimeError(_('Windows не приняла запрос запрета сна.'))

    def _run(self):
        call = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
        call.argtypes = [wintypes.DWORD]
        call.restype = wintypes.DWORD
        try:
            self.active = bool(call(AWAKE_FLAGS))
            self._ready.set()
            while self.active and not self._stop.wait(30):
                self.active = bool(call(AWAKE_FLAGS))
        finally:
            call(0x80000000)
            self.active = False
            self._ready.set()

    def close(self):
        self._stop.set()
        self._thread.join()


def _suspend():
    """Enable shutdown privilege only for the duration of SetSuspendState."""
    class Luid(ctypes.Structure):
        _fields_ = [('low', wintypes.DWORD), ('high', wintypes.LONG)]
    class Privileges(ctypes.Structure):
        _fields_ = [('count', wintypes.DWORD), ('luid', Luid), ('attributes', wintypes.DWORD)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(Luid)]
    advapi.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(Privileges), wintypes.DWORD, ctypes.POINTER(Privileges), ctypes.POINTER(wintypes.DWORD)]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x28, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    changed = False
    old = Privileges()
    try:
        desired = Privileges(count=1, attributes=2)
        if not advapi.LookupPrivilegeValueW(None, 'SeShutdownPrivilege', ctypes.byref(desired.luid)):
            raise ctypes.WinError(ctypes.get_last_error())
        length = wintypes.DWORD()
        ctypes.set_last_error(0)
        if not advapi.AdjustTokenPrivileges(token, False, ctypes.byref(desired), ctypes.sizeof(old), ctypes.byref(old), ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 1300:
            raise RuntimeError(_('Нет права перевести Windows в сон.'))
        changed = True
        call = ctypes.WinDLL('powrprof', use_last_error=True).SetSuspendState
        call.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte]
        call.restype = ctypes.c_ubyte
        if not call(False, False, False):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if changed:
            advapi.AdjustTokenPrivileges(token, False, ctypes.byref(old), 0, None, None)
        kernel.CloseHandle(token)


def _execute_windows(action):
    if action == 'sleep':
        _suspend()
    else:
        command = os.path.join(os.environ['SystemRoot'], 'System32', 'shutdown.exe')
        args = ['/h'] if action == 'hibernate' else ['/s', '/t', '0']
        result = subprocess.run([command] + args, creationflags=subprocess.CREATE_NO_WINDOW,
                                capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(_('Windows отклонила действие (код {}).').format(result.returncode))


LOGIN_SERVICE = 'org.freedesktop.login1'
LOGIN_PATH = '/org/freedesktop/login1'
LOGIN_INTERFACE = 'org.freedesktop.login1.Manager'
LINUX_METHODS = dict(sleep='Suspend', hibernate='Hibernate', shutdown='PowerOff')


def _login_command(method, *args):
    return ['busctl', '--system', '--timeout=15', 'call', LOGIN_SERVICE, LOGIN_PATH,
            LOGIN_INTERFACE, method] + list(args)


def _linux_capabilities():
    result = dict(sleep=False, hibernate=False, shutdown=False)
    if not shutil.which('busctl') or not shutil.which('systemd-inhibit'):
        result['reason'] = _('Требуются Linux с systemd/logind, busctl и systemd-inhibit.')
        return result
    reasons = []
    for action, method in LINUX_METHODS.items():
        try:
            response = subprocess.run(_login_command('Can' + method), capture_output=True,
                                      text=True, timeout=3)
            fields = shlex.split(response.stdout.strip())
            allowed = response.returncode == 0 and fields == ['s', 'yes']
            result[action] = allowed
            if not allowed:
                reasons.append(_('{}: недоступно или требует дополнительных прав.').format(action))
        except (OSError, subprocess.TimeoutExpired, ValueError):
            reasons.append(_('{}: logind не ответил.').format(action))
    result['reason'] = '\n'.join([_('Linux/systemd: сон и гибернация на реальном устройстве — NOT TESTED.')] + reasons)
    return result


class LinuxAwakeGuard:
    """Hold a logind inhibitor in a child process; parent pipe closure releases it."""
    def __init__(self):
        self.process = subprocess.Popen([
            'systemd-inhibit', '--what=idle:sleep', '--mode=block',
            '--who=Deluge AfterDownloads', '--why=Waiting for torrent downloads',
            sys.executable, '-c', 'import sys; print("READY", flush=True); sys.stdin.read()'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(self.process.stdout.readline()), daemon=True).start()
        try:
            if ready.get(timeout=5).strip() != 'READY' or not self.active:
                raise RuntimeError(_('systemd-inhibit не предоставил запрет сна.'))
        except Exception:
            self.close()
            raise

    @property
    def active(self):
        return self.process.poll() is None

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        if self.process.stdout and not self.process.stdout.closed:
            self.process.stdout.close()


def AwakeGuard():
    if os.name == 'nt':
        return WindowsAwakeGuard()
    if sys.platform.startswith('linux'):
        return LinuxAwakeGuard()
    raise RuntimeError(_('Платформа не поддерживается.'))


def _execute_linux(action):
    # interactive=false: never leave an unattended authentication prompt.
    result = subprocess.run(_login_command(LINUX_METHODS[action], 'b', 'false'),
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(_('logind отклонил действие (код {}).').format(result.returncode))


def execute(action, dry_run=False):
    if action not in ('sleep', 'hibernate', 'shutdown'):
        raise ValueError(_('Неизвестное действие.'))
    if not capabilities()[action]:
        raise RuntimeError(_('Выбранное действие больше недоступно в системе.'))
    if dry_run:
        return
    if sys.platform.startswith('linux'):
        _execute_linux(action)
    else:
        _execute_windows(action)
