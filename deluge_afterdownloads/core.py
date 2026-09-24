"""Registration and read-only diagnostics; power actions never run on the daemon."""
from deluge.plugins.pluginbase import CorePluginBase
from deluge.core.rpcserver import export


class Core(CorePluginBase):
    def enable(self):
        self.ui_status = {'loaded': False, 'armed': False}

    def disable(self):
        pass

    def update(self):
        pass

    @export
    def report_ui(self, loaded, armed, sleep_available, hibernate_available):
        self.ui_status = dict(loaded=bool(loaded), armed=bool(armed),
                              sleep_available=bool(sleep_available),
                              hibernate_available=bool(hibernate_available))

    @export
    def get_status(self):
        return dict(version='1.0.0', **self.ui_status)
