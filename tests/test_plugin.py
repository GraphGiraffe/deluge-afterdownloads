import importlib
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
import zipfile
import hashlib
import ast
import builtins
import gettext
import string
import tempfile
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Import the implementation without requiring the Deluge host for unit tests.
package = types.ModuleType('deluge_afterdownloads')
package.__path__ = [str(ROOT / 'deluge_afterdownloads')]
sys.modules.setdefault('deluge_afterdownloads', package)
model = importlib.import_module('deluge_afterdownloads.model')
power = importlib.import_module('deluge_afterdownloads.power')
i18n = importlib.import_module('deluge_afterdownloads.i18n')
DONE = {'state': 'Seeding', 'progress': 100, 'is_finished': True}
PAUSED = {'state': 'Paused', 'progress': 12, 'is_finished': False}


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        i18n.select_language('en')

    def test_deluge_language_overrides_system_language(self):
        with patch.dict(i18n.os.environ, {'LANGUAGE': 'ru_RU'}):
            self.assertEqual(i18n.select_language('en_US'), 'en')
            self.assertEqual(i18n._('Сон'), 'Sleep')
            self.assertEqual(i18n.select_language('ru-RU'), 'ru')
            self.assertEqual(i18n._('Сон'), 'Сон')

    def test_automatic_uses_active_deluge_translation(self):
        translator = gettext.NullTranslations()
        translator._info = {'language': 'ru'}
        with patch.object(builtins, '_', translator.gettext, create=True):
            self.assertEqual(i18n.select_language(None), 'ru')
        translator._info = {}
        with patch.object(builtins, '_', translator.gettext, create=True), \
                patch.dict(i18n.os.environ, {'LANGUAGE': 'ru'}):
            self.assertEqual(i18n.select_language(None), 'en')

    def test_other_languages_fall_back_to_english(self):
        for language in ('de_DE', 'fr', 'C'):
            self.assertEqual(i18n.select_language(language), 'en')
            self.assertEqual(i18n._('Отменить'), 'Cancel')

    def test_all_messages_have_translation_and_matching_placeholders(self):
        parser = string.Formatter()
        for filename in ('model.py', 'power.py', 'gtkui.py'):
            tree = ast.parse((ROOT / 'deluge_afterdownloads' / filename).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and any('\u0400' <= c <= '\u04ff' for c in node.value):
                    self.assertIn(node.value, i18n.ENGLISH)
        for original, translated in i18n.ENGLISH.items():
            self.assertEqual([field for _, field, _, _ in parser.parse(original) if field is not None],
                             [field for _, field, _, _ in parser.parse(translated) if field is not None])

    def test_technical_names_stay_english(self):
        for language in ('ru', 'en'):
            i18n.select_language(language)
            self.assertIn('Modern Standby (S0)', i18n._('Сон недоступен в плагине: нет S1–S3; вызов при S0 может привести к гибернации.'))
            self.assertIn('dry-run', i18n._('Только проверка (dry-run)'))


class CompletionTests(unittest.TestCase):
    def test_finished_and_paused(self):
        self.assertEqual(model.summarize({'a': DONE, 'b': PAUSED}),
                         dict(total=2, paused=1, pending=0, ready=True))

    def test_all_paused(self):
        self.assertTrue(model.summarize({'a': PAUSED})['ready'])

    def test_incomplete_or_unknown_blocks(self):
        for row in ({}, None, dict(DONE, progress=99.9), dict(DONE, progress=float('nan')),
                    dict(DONE, state='Moving'), dict(DONE, state='Checking'),
                    dict(DONE, state='Error'), dict(DONE, state='Queued', progress=40),
                    dict(DONE, is_finished=False), dict(DONE, progress=None)):
            with self.subTest(row=row):
                self.assertFalse(model.summarize({'a': row})['ready'])

    def test_empty_not_ready(self):
        self.assertFalse(model.summarize({})['ready'])

    def test_bad_response_rejected(self):
        with self.assertRaises(ValueError):
            model.summarize(None)

    def test_countdown_requires_full_minute_and_fresh_final_response(self):
        now = [0]
        monitor = model.Monitor(lambda: now[0])
        self.assertEqual(monitor.observe({'a': DONE})[0], 'countdown')
        now[0] = 59.9
        self.assertEqual(monitor.observe({'a': DONE}, final=True)[0], 'countdown')
        self.assertEqual(monitor.remaining(), 1)
        now[0] = 60
        self.assertEqual(monitor.observe({'a': DONE})[0], 'countdown')
        self.assertEqual(monitor.observe({'a': DONE}, final=True)[0], 'execute')

    def test_new_download_aborts_countdown(self):
        now = [0]
        monitor = model.Monitor(lambda: now[0])
        monitor.observe({'a': DONE})
        now[0] = 60
        self.assertEqual(monitor.observe({'a': dict(DONE, progress=50)}, final=True)[0], 'wait')
        self.assertIsNone(monitor.deadline)
        self.assertEqual(monitor.observe({'a': DONE}, final=True)[0], 'countdown')
        self.assertEqual(monitor.remaining(), 60)


class PowerTests(unittest.TestCase):
    def test_linux_capabilities_require_unattended_permission(self):
        responses = [types.SimpleNamespace(returncode=0, stdout='s "yes"'),
                     types.SimpleNamespace(returncode=0, stdout='s "challenge"'),
                     types.SimpleNamespace(returncode=0, stdout='s "no"')]
        with patch.object(power.shutil, 'which', return_value='/usr/bin/tool'), \
                patch.object(power.subprocess, 'run', side_effect=responses):
            caps = power._linux_capabilities()
        self.assertTrue(caps['sleep'])
        self.assertFalse(caps['hibernate'])
        self.assertFalse(caps['shutdown'])

    def test_linux_missing_tools_disable_actions(self):
        with patch.object(power.shutil, 'which', return_value=None):
            caps = power._linux_capabilities()
        self.assertFalse(any(caps[a] for a in model.ACTIONS))

    def test_linux_actions_use_correct_logind_methods_without_interactive_auth(self):
        with patch.object(power.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run:
            for action, method in power.LINUX_METHODS.items():
                power._execute_linux(action)
                self.assertEqual(run.call_args.args[0][-3:], [method, 'b', 'false'])

    def test_dry_run_never_invokes_power_actions(self):
        with patch.object(power, 'capabilities', return_value=dict(sleep=True, hibernate=True, shutdown=True)), \
                patch.object(power, '_suspend') as sleep, patch.object(power.subprocess, 'run') as shutdown:
            for action in model.ACTIONS:
                power.execute(action, dry_run=True)
            sleep.assert_not_called()
            shutdown.assert_not_called()

    def test_unavailable_hibernate_and_sleep_rechecked(self):
        with patch.object(power, 'capabilities', return_value=dict(sleep=False, hibernate=False, shutdown=True)), \
                patch.object(power, '_suspend') as sleep, patch.object(power.subprocess, 'run') as shutdown:
            for action in ('sleep', 'hibernate'):
                with self.assertRaises(RuntimeError):
                    power.execute(action)
            sleep.assert_not_called()
            shutdown.assert_not_called()

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            power.execute('reboot')

    def test_display_not_held(self):
        self.assertEqual(power.AWAKE_FLAGS, 0x80000001)
        self.assertEqual(power.AWAKE_FLAGS & 2, 0)

    @unittest.skipUnless(sys.platform == 'win32', 'Native Windows API test')
    def test_native_capabilities_and_guard_cleanup(self):
        caps = power.capabilities()
        self.assertIsInstance(caps['sleep'], bool)
        self.assertIsInstance(caps['hibernate'], bool)
        guard = power.AwakeGuard()
        try:
            self.assertTrue(guard.active)
        finally:
            guard.close()
        guard.close()
        self.assertFalse(guard.active)


def load_gtk_with_stubs():
    stubs = {}
    for name in ('gi', 'gi.repository', 'twisted', 'twisted.internet', 'deluge', 'deluge.component',
                 'deluge.configmanager', 'deluge.plugins', 'deluge.plugins.pluginbase', 'deluge.ui', 'deluge.ui.client'):
        stubs[name] = types.ModuleType(name)
    stubs['gi.repository'].GLib = MagicMock()
    stubs['gi.repository'].Gtk = MagicMock()
    stubs['twisted.internet'].reactor = MagicMock()
    stubs['twisted.internet'].threads = MagicMock()
    stubs['deluge.plugins.pluginbase'].Gtk3PluginBase = object
    stubs['deluge.configmanager'].ConfigManager = MagicMock()
    stubs['deluge.ui.client'].client = MagicMock()
    with patch.dict(sys.modules, stubs):
        return importlib.import_module('deluge_afterdownloads.gtkui')


gtkui = load_gtk_with_stubs()


class ControllerTests(unittest.TestCase):
    def test_start_without_selection_displays_translated_message(self):
        ui = self.make_ui()
        ui.armed = False
        ui._refresh_support = MagicMock()
        ui.buttons = {}
        i18n.select_language('en')
        ui._start()
        ui.status.set_text.assert_called_once_with('Select an available action.')

    def make_ui(self):
        ui = gtkui.GtkUI()
        ui.enabled = True
        ui.armed = True
        ui.generation = 1
        ui.inflight = False
        ui.guard = MagicMock(active=True)
        ui.status = MagicMock()
        ui.support = MagicMock()
        ui.start_button = MagicMock()
        ui.cancel_button = MagicMock()
        ui.dry = MagicMock()
        ui.buttons = {a: MagicMock() for a in model.ACTIONS}
        ui.none_button = MagicMock()
        ui.dialog = None
        ui.action = 'hibernate'
        ui.dry_run = True
        ui.monitor = model.Monitor(lambda: 60)
        ui.monitor.deadline = 60
        ui._report = MagicMock()
        return ui

    def test_cancel_releases_guard_and_invalidates_callbacks(self):
        ui = self.make_ui()
        guard = ui.guard
        ui._stop('cancelled')
        guard.close.assert_called_once()
        self.assertFalse(ui.armed)
        self.assertEqual(ui.generation, 2)
        ui.status.reset_mock()
        ui._received({'a': DONE}, 1, True)
        ui.status.set_text.assert_not_called()

    def test_unavailable_actions_remain_disabled_after_stop(self):
        ui = self.make_ui()
        with patch.object(power, 'capabilities', return_value=dict(sleep=False, hibernate=False, shutdown=True, reason='Unavailable')):
            ui._stop('cancel')
        ui.buttons['sleep'].set_sensitive.assert_called_with(False)
        ui.buttons['hibernate'].set_sensitive.assert_called_with(False)
        ui.buttons['shutdown'].set_sensitive.assert_called_with(True)

    def test_final_dry_run_does_not_dispatch_action(self):
        ui = self.make_ui()
        with patch.object(power, 'capabilities', return_value=dict(sleep=False, hibernate=True, shutdown=True, reason='OK')):
            gtkui.threads.deferToThread.reset_mock()
            ui._received({'a': DONE}, 1, True)
        gtkui.threads.deferToThread.assert_not_called()
        self.assertFalse(ui.armed)

    def test_action_becomes_unavailable_at_end(self):
        ui = self.make_ui()
        ui.dry_run = False
        with patch.object(power, 'capabilities', return_value=dict(sleep=False, hibernate=False, shutdown=True, reason='Unavailable')):
            gtkui.threads.deferToThread.reset_mock()
            ui._received({'a': DONE}, 1, True)
        gtkui.threads.deferToThread.assert_not_called()
        self.assertFalse(ui.armed)

    def test_disconnect_cancels(self):
        ui = self.make_ui()
        with patch.object(gtkui.client, 'connected', return_value=False):
            self.assertTrue(ui._tick())
        self.assertFalse(ui.armed)

    def test_rpc_failure_cancels(self):
        ui = self.make_ui()
        ui._failed(MagicMock(), 1)
        self.assertFalse(ui.armed)


class PackageTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('plugin_build', ROOT / 'build.py')
        self.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.build)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.build.ROOT = pathlib.Path(temporary.name)
        shutil.copytree(ROOT / 'deluge_afterdownloads', self.build.ROOT / 'deluge_afterdownloads',
                        ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT / 'LICENSE', self.build.ROOT / 'LICENSE')

    def test_deterministic_egg_no_exe_or_private_data(self):
        path = self.build.build()
        first = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(first, hashlib.sha256(self.build.build().read_bytes()).hexdigest())
        with zipfile.ZipFile(path) as z:
            self.assertIn('EGG-INFO/entry_points.txt', z.namelist())
            for name in z.namelist():
                self.assertFalse(name.endswith(('.exe', '.dll', '.dpapi', '.conf', '.log', '.pyc')))
            self.assertIn('deluge.plugin.gtk3ui', z.read('EGG-INFO/entry_points.txt').decode())

    def test_release_bytes_do_not_depend_on_checkout_line_endings(self):
        first = self.build.build().read_bytes()
        paths = list((self.build.ROOT / 'deluge_afterdownloads').glob('*.py')) + [self.build.ROOT / 'LICENSE']
        for path in paths:
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.assertEqual(first, self.build.build().read_bytes())
        with zipfile.ZipFile(self.build.build()) as archive:
            self.assertTrue(all(info.create_system == 3 and info.compress_type == zipfile.ZIP_STORED
                                for info in archive.infolist()))

    def test_release_version_and_python_39_syntax(self):
        core = ast.parse((ROOT / 'deluge_afterdownloads' / 'core.py').read_text(encoding='utf-8'))
        versions = [kw.value.value for node in ast.walk(core) if isinstance(node, ast.Call)
                    for kw in node.keywords if kw.arg == 'version' and isinstance(kw.value, ast.Constant)]
        self.assertEqual(versions, [self.build.VERSION])
        self.assertIn('# AfterDownloads ' + self.build.VERSION,
                      (ROOT / 'docs' / 'RELEASE_NOTES.md').read_text(encoding='utf-8'))
        self.assertIn('## ' + self.build.VERSION, (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'))
        for path in (ROOT / 'deluge_afterdownloads').glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=path.name, feature_version=(3, 9))


if __name__ == '__main__':
    unittest.main()
