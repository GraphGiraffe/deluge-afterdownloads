# Changelog

## 1.0.0

- Initial native GTK3 plugin for Deluge 2.x on Windows.
- Linux systemd/logind adapter; real desktop and power transitions **NOT TESTED**.
- Sleep, Hibernate, and Shut down with runtime capability checks.
- Automatic sleep inhibition while allowing the display to turn off.
- Paused-torrent filtering, a cancellable 60-second countdown, a fresh final status check, and dry-run.
- Monitoring stops on connection failure or plugin disable and never resumes automatically.
- English and Russian UI follow the Deluge language setting, with English fallback and unchanged technical names.
- A short explanation at the top describes sleep inhibition and the action after active downloads finish.
- Reproducible source-only `.egg` packages for Python 3.9â€“3.14, Windows/Ubuntu CI, and verified release artifacts published by the repository owner.
