"""Plugin translations, selected from Deluge's GTK language at enable time."""
import builtins
import locale
import os

LANGUAGE = 'en'
ENGLISH = {
    'Сон': 'Sleep',
    'Гибернация': 'Hibernate',
    'Выключение': 'Shut down',
    'Deluge не вернул список торрентов.': 'Deluge did not return the torrent list.',
    'Эта платформа не поддерживается: нужны Windows или Linux с systemd/logind.': 'Unsupported platform: Windows or Linux with systemd/logind is required.',
    'Сон доступен (S1–S3).': 'Sleep is available (S1–S3).',
    'Сон недоступен в плагине: нет S1–S3; вызов при S0 может привести к гибернации.': 'Sleep is unavailable in this plugin: no S1–S3; the API may hibernate on Modern Standby (S0) systems.',
    'Сон недоступен: Windows не вернула поддерживаемые режимы.': 'Sleep is unavailable: Windows did not report supported states.',
    'Гибернация доступна.': 'Hibernate is available.',
    'Гибернация недоступна: отключена в Windows или не поддерживается.': 'Hibernate is unavailable: disabled in Windows or not supported.',
    'Требуется Windows.': 'Windows is required.',
    'Windows не приняла запрос запрета сна.': 'Windows rejected the request to prevent sleep.',
    'Нет права перевести Windows в сон.': 'Permission to suspend Windows was denied.',
    'Windows отклонила действие (код {}).': 'Windows rejected the action (code {}).',
    'Требуются Linux с systemd/logind, busctl и systemd-inhibit. Linux: NOT TESTED.': 'Linux with systemd/logind, busctl and systemd-inhibit is required. Linux: NOT TESTED.',
    '{}: недоступно или требует дополнительных прав.': '{}: unavailable or requires additional permissions.',
    '{}: logind не ответил.': '{}: logind did not respond.',
    'Linux/systemd: NOT TESTED на реальном устройстве.': 'Linux/systemd: NOT TESTED on a real device.',
    'systemd-inhibit не предоставил запрет сна.': 'systemd-inhibit did not grant a sleep inhibitor.',
    'Платформа не поддерживается.': 'Unsupported platform.',
    'logind отклонил действие (код {}).': 'logind rejected the action (code {}).',
    'Неизвестное действие.': 'Unknown action.',
    'Выбранное действие больше недоступно в системе.': 'The selected action is no longer available on this system.',
    'После завершения загрузок': 'After downloads finish',
    ('Во время ожидания автоматический переход в сон заблокирован. Экран при этом может гаснуть.\n'
     'Когда все активные загрузки завершатся, начнётся отсчёт 60 секунд, затем выполнится выбранное действие. '
     'Торренты на паузе не учитываются. До конца отсчёта действие можно отменить.'):
        ('Automatic sleep is blocked while waiting. The display can still turn off.\n'
         'When all active downloads finish, a 60-second countdown starts, then the selected action is performed. '
         'Paused torrents are ignored. You can cancel the action before the countdown ends.'),
    'Только проверка (dry-run)': 'Test only (dry-run)',
    'Начать ожидание': 'Start waiting',
    'Отменить': 'Cancel',
    'Действие отменено. Ожидание остановлено.': 'Action cancelled. Monitoring stopped.',
    'Не запущено. Выбери действие и нажми «Начать ожидание».': 'Not running. Select an action and click Start waiting.',
    'Выбери доступное действие.': 'Select an available action.',
    'Нужно подключение к Deluge на этом компьютере.': 'A connection to Deluge on this computer is required.',
    'Не удалось запретить сон: {}': 'Could not prevent sleep: {}',
    'Ожидание загрузок. Экран может гаснуть.': 'Waiting for downloads. The display can turn off.',
    'Соединение потеряно. Действие отменено.': 'Connection lost. Action cancelled.',
    'Запрет сна больше не действует. Ожидание остановлено.': 'The sleep inhibitor is no longer active. Monitoring stopped.',
    '{} через {} сек.\nТорренты на паузе не учитываются.{}': '{} in {} seconds.\nPaused torrents are ignored.{}',
    '\nDry-run: действие не будет выполнено.': '\nDry-run: the action will not be performed.',
    'Ошибка запроса: {}': 'Request failed: {}',
    'Ошибка связи с Deluge. Действие отменено: {}': 'Deluge connection error. Action cancelled: {}',
    'Всего: {total} · На паузе: {paused} · Осталось: {pending}': 'Total: {total} · Paused: {paused} · Pending: {pending}',
    'После загрузок — ': 'After downloads — ',
    '{} через 60 сек.': '{} in 60 seconds.',
    'Dry-run завершён: ': 'Dry-run completed: ',
    'Выполняется: ': 'Performing: ',
    'Ошибка: ': 'Error: ',
    'Действие выполнено. Ожидание остановлено.': 'Action completed. Monitoring stopped.',
    'Плагин отключён.': 'Plugin disabled.',
}


def select_language(configured=None):
    """Respect explicit Deluge choice; otherwise use its active gettext locale."""
    global LANGUAGE
    selected = configured if isinstance(configured, str) and configured else None
    if selected is None:
        translator = getattr(getattr(builtins, '_', None), '__self__', None)
        if translator is not None and hasattr(translator, 'info'):
            selected = translator.info().get('language', 'en')
    if selected is None:
        selected = next((os.environ[key] for key in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG')
                         if os.environ.get(key)), None)
    if selected is None:
        try:
            selected = locale.getlocale()[0]
        except (ValueError, TypeError):
            selected = None
    code = (selected or 'en').split(':')[0].replace('-', '_').split('_')[0].split('.')[0].lower()
    LANGUAGE = 'ru' if code == 'ru' else 'en'
    return LANGUAGE


def _(message):
    if LANGUAGE == 'ru':
        # Keep the standard technology name in both locales.
        return message.replace('вызов при S0', 'вызов при Modern Standby (S0)')
    return ENGLISH.get(message, message)
