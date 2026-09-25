"""Native GTK3 preferences page, local desktop monitoring and countdown."""
from .i18n import _, select_language
import logging
import time

from gi.repository import GLib, Gtk
from twisted.internet import reactor, threads
import deluge.component as component
from deluge.configmanager import ConfigManager
from deluge.plugins.pluginbase import Gtk3PluginBase
from deluge.ui.client import client

from .model import ACTIONS, KEYS, Monitor
from . import power

log = logging.getLogger(__name__)
PAGE = 'AfterDownloads'


class GtkUI(Gtk3PluginBase):
    def enable(self):
        select_language(ConfigManager('gtk3ui.conf')['language'])
        self.enabled = True
        self.armed = False
        self.generation = 0
        self.inflight = False
        self.guard = None
        self.dialog = None
        self.timer = None
        self.next_poll = 0
        self.monitor = Monitor(time.monotonic)
        self.config = ConfigManager('afterdownloads-gtk.conf', {'action': '', 'dry_run': False})
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.set_border_width(12)
        self.box.pack_start(self._label(_('После завершения загрузок'), bold=True), False, False, 0)
        self.box.pack_start(self._label(_('Во время ожидания автоматический переход в сон заблокирован. '
                                        'Экран при этом может гаснуть.\n'
                                        'Когда все активные загрузки завершатся, начнётся отсчёт 60 секунд, '
                                        'затем выполнится выбранное действие. Торренты на паузе не учитываются. '
                                        'До конца отсчёта действие можно отменить.')), False, False, 0)
        row = Gtk.Box(spacing=14)
        self.buttons = {}
        # Hidden group member allows "no selection" without selecting a dangerous fallback.
        self.none_button = Gtk.RadioButton.new_with_label_from_widget(None, '')
        for action, title in ACTIONS.items():
            button = Gtk.RadioButton.new_with_label_from_widget(self.none_button, _(title))
            self.buttons[action] = button
            row.pack_start(button, False, False, 0)
        self.box.pack_start(row, False, False, 0)
        self.dry = Gtk.CheckButton(label=_('Только проверка (dry-run)'))
        self.dry.set_active(bool(self.config['dry_run']))
        self.box.pack_start(self.dry, False, False, 0)
        row = Gtk.Box(spacing=10)
        self.start_button = Gtk.Button(label=_('Начать ожидание'))
        self.cancel_button = Gtk.Button(label=_('Отменить'))
        self.cancel_button.set_sensitive(False)
        self.start_button.connect('clicked', self._start)
        self.cancel_button.connect('clicked', lambda *unused: self._stop(_('Действие отменено. Ожидание остановлено.')))
        row.pack_start(self.start_button, False, False, 0)
        row.pack_start(self.cancel_button, False, False, 0)
        self.box.pack_start(row, False, False, 0)
        self.status = self._label(_('Не запущено. Выбери действие и нажми «Начать ожидание».'))
        self.support = self._label('')
        self.box.pack_start(self.status, False, False, 0)
        self.box.pack_start(self.support, False, False, 0)
        self._refresh_support()
        saved = self.config['action']
        if saved in self.buttons and self.caps[saved]:
            self.buttons[saved].set_active(True)
        self.box.show_all()
        component.get('Preferences').add_page(PAGE, self.box)
        manager = component.get('PluginManager')
        manager.register_hook('on_show_prefs', self._refresh_support)
        manager.register_hook('on_apply_prefs', self._save)
        self.timer = GLib.timeout_add_seconds(1, self._tick)
        self._report()
        log.info('AfterDownloads GTK loaded; unarmed; capabilities=%s', self.caps)

    @staticmethod
    def _label(text, bold=False):
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_line_wrap(True)
        if bold:
            label.set_markup('<b>{}</b>'.format(GLib.markup_escape_text(text)))
        else:
            label.set_text(text)
        return label

    def _report(self):
        if client.connected():
            client.afterdownloads.report_ui(self.enabled, self.armed, self.caps['sleep'],
                                           self.caps['hibernate']).addErrback(lambda _: None)

    def _refresh_support(self):
        # logind can reject CanSuspend/CanHibernate because of our own inhibitor.
        # Keep the pre-monitoring result until that inhibitor has been released.
        if self.guard is None:
            self.caps = power.capabilities()
        self.support.set_text(self.caps['reason'])
        for action, button in self.buttons.items():
            button.set_sensitive(self.caps[action] and not self.armed)
            if not self.caps[action] and button.get_active():
                self.none_button.set_active(True)

    def _save(self):
        self.config['action'] = next((a for a, b in self.buttons.items() if b.get_active()), '')
        self.config['dry_run'] = self.dry.get_active()
        self.config.save()

    def _start(self, *unused):
        if self.armed:
            return
        self._refresh_support()
        action = next((a for a, b in self.buttons.items() if b.get_active()), '')
        if not action or not self.caps[action]:
            self.status.set_text(_('Выбери доступное действие.'))
            return
        if not client.connected() or not client.is_localhost():
            self.status.set_text(_('Нужно подключение к Deluge на этом компьютере.'))
            return
        try:
            self.guard = power.AwakeGuard()
        except Exception as error:
            self.status.set_text(_('Не удалось запретить сон: {}').format(error))
            return
        self.action = action
        self.dry_run = self.dry.get_active()
        self._save()
        self.armed = True
        self.generation += 1
        self.inflight = False
        self.monitor = Monitor(time.monotonic)
        self.next_poll = 0
        self.start_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.dry.set_sensitive(False)
        self._refresh_support()
        self.status.set_text(_('Ожидание загрузок. Экран может гаснуть.'))
        self._report()
        self._poll()

    def _close_dialog(self):
        if self.dialog is not None:
            dialog, self.dialog = self.dialog, None
            dialog.destroy()

    def _stop(self, message):
        self.armed = False
        self.generation += 1
        self.inflight = False
        self.monitor.deadline = None
        self._close_dialog()
        self._release_guard()
        self.start_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.dry.set_sensitive(True)
        self._refresh_support()
        self.status.set_text(message)
        self._report()
        log.info('AfterDownloads: %s', message)

    def _release_guard(self):
        if self.guard:
            self.guard.close()
            self.guard = None

    def _tick(self):
        if not self.enabled:
            return False
        if not self.armed:
            return True
        if not client.connected() or not client.is_localhost():
            self._stop(_('Соединение потеряно. Действие отменено.'))
        elif not self.guard or not self.guard.active:
            self._stop(_('Запрет сна больше не действует. Ожидание остановлено.'))
        elif self.monitor.deadline is not None:
            remaining = self.monitor.remaining()
            if self.dialog:
                self.countdown_label.set_text(_('{} через {} сек.\nТорренты на паузе не учитываются.{}').format(
                    _(ACTIONS[self.action]), remaining, _('\nDry-run: действие не будет выполнено.') if self.dry_run else ''))
            if remaining == 0:
                self._poll(final=True)
            elif time.monotonic() >= self.next_poll:
                self._poll()
        elif time.monotonic() >= self.next_poll:
            self._poll()
        return True

    def _poll(self, final=False):
        if not self.armed or self.inflight:
            return
        self.inflight = True
        token = self.generation
        try:
            request = client.core.get_torrents_status({}, KEYS)
            request.addTimeout(15, reactor)
            request.addCallback(self._received, token, final)
            request.addErrback(self._failed, token)
        except Exception as error:
            self._stop(_('Ошибка запроса: {}').format(error))

    def _failed(self, failure, token):
        if self.armed and token == self.generation:
            self._stop(_('Ошибка связи с Deluge. Действие отменено: {}').format(failure.getErrorMessage()))
        return None

    def _received(self, torrents, token, final):
        if not self.armed or token != self.generation:
            return
        self.inflight = False
        outcome, summary = self.monitor.observe(torrents, final)
        self.status.set_text(_('Всего: {total} · На паузе: {paused} · Осталось: {pending}').format(**summary))
        self.next_poll = time.monotonic() + (5 if self.monitor.deadline is not None else 30)
        if outcome == 'wait':
            self._close_dialog()
        elif outcome == 'countdown' and self.dialog is None:
            self.dialog = Gtk.Dialog(title=_('После загрузок — ') + _(ACTIONS[self.action]),
                                     transient_for=component.get('MainWindow').window, modal=False)
            self.dialog.add_button(_('Отменить'), Gtk.ResponseType.CANCEL)
            self.dialog.set_default_size(440, 170)
            self.dialog.set_keep_above(True)
            self.countdown_label = self._label(_('{} через 60 сек.').format(_(ACTIONS[self.action])))
            self.countdown_label.set_margin_top(20)
            self.countdown_label.set_margin_start(20)
            self.countdown_label.set_margin_end(20)
            self.dialog.get_content_area().pack_start(self.countdown_label, True, True, 10)
            self.dialog.connect('response', self._cancel_dialog)
            self.dialog.connect('delete-event', self._delete_dialog)
            self.dialog.show_all()
            self.dialog.present()
        elif outcome == 'execute':
            # A fresh final torrent response has confirmed completion. Release
            # our inhibitor before checking permissions; other blockers still apply.
            self._release_guard()
            self._refresh_support()
            if not self.caps[self.action]:
                self._stop(_('Выбранное действие больше недоступно в системе.'))
                return
            action, dry = self.action, self.dry_run
            self._stop((_('Dry-run завершён: ') if dry else _('Выполняется: ')) + _(ACTIONS[action]))
            if not dry:
                self.start_button.set_sensitive(False)
                token = self.generation
                threads.deferToThread(power.execute, action).addCallbacks(
                    lambda _: self._action_done(token), lambda failure: self._action_done(token, failure))

    def _action_done(self, token, failure=None):
        if self.enabled and token == self.generation:
            self.start_button.set_sensitive(True)
            self.status.set_text(_('Ошибка: ') + failure.getErrorMessage() if failure else _('Действие выполнено. Ожидание остановлено.'))
        return None

    def _cancel_dialog(self, dialog, response):
        if dialog is self.dialog:
            self._stop(_('Действие отменено. Ожидание остановлено.'))

    def _delete_dialog(self, dialog, event):
        self._cancel_dialog(dialog, Gtk.ResponseType.CANCEL)
        return True

    def disable(self):
        self.enabled = False
        self._stop(_('Плагин отключён.'))
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None
        manager = component.get('PluginManager')
        manager.deregister_hook('on_show_prefs', self._refresh_support)
        manager.deregister_hook('on_apply_prefs', self._save)
        component.get('Preferences').remove_page(PAGE)

    def update(self):
        pass
