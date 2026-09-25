# Changelog

## 1.0.1 (unreleased)

- Fix Linux Sleep and Hibernate becoming unavailable because of the plugin's own sleep inhibitor.
- Preserve the selected action during monitoring, including when reopening preferences. Release the inhibitor after the final torrent check and before checking action availability again.
- Keep refusing genuinely unavailable actions after the inhibitor is released; no fallback action or interactive authentication is used.
- Add regression coverage for the full countdown, dry-run, real-action dispatch with a mocked backend, and loss of action availability.
- Record user-confirmed shutdown after downloads on an Ubuntu desktop. Real Linux Sleep and Hibernate remain **NOT TESTED**.

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
