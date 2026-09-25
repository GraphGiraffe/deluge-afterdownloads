# AfterDownloads for Deluge

A native Deluge 2.x GTK3 plugin that prevents automatic sleep while downloads are active, then performs a selected power action after a cancellable 60-second countdown. The display can still turn off.

## Platform support

| Platform | Implementation | Validation |
| --- | --- | --- |
| Windows 10/11, Deluge 2.x GTK3 | Win32 power APIs and a dedicated awake thread | Automated tests; operation and dry-run confirmed in Deluge 2.2.0 |
| Ubuntu and other Linux distributions with systemd/logind | systemd-inhibit and logind D-Bus via busctl | Automated tests in Ubuntu 26.04 WSL; preferences, countdown, and shutdown after downloads confirmed by a user on an Ubuntu desktop. Real Sleep and Hibernate **NOT TESTED** |
| Linux without systemd/logind | Not implemented | Actions disabled |
| macOS, FreeBSD | Not implemented | Actions disabled |

## Features

- Choose Sleep, Hibernate, or Shut down using radio buttons in Deluge preferences.
- Sleep and hibernation availability is checked when the plugin is enabled, idle preferences are opened, and monitoring starts. During monitoring the selection is locked and the previous result is kept, so the plugin's own sleep inhibitor does not make the action appear unavailable. At the end, the inhibitor is released before checking availability again. Unavailable actions are disabled with an explanation.
- Paused torrents are ignored. Unfinished queued downloads, file checks, and errors prevent the action.
- Automatic sleep is blocked while waiting. Windows uses `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` on a dedicated thread, following the PowerToys Awake approach. Linux uses `systemd-inhibit`.
- A separate dialog provides a 60-second countdown and a Cancel button. Closing the dialog also cancels monitoring.
- Torrent status is checked again before the action. New unfinished downloads return the plugin to waiting.
- Dry-run follows the same flow without sleeping, hibernating, or shutting down.
- The action and dry-run preference are saved. Monitoring **never starts automatically** after a restart.
- No Web UI or password is needed: the plugin uses Deluge's current local connection.
- English and Russian UI follow the Deluge language setting; other languages fall back to English. Restart Deluge after changing its language. Technical names such as Modern Standby, S0, S1â€“S3, dry-run, and systemd/logind remain unchanged.

## Installation

1. Download an `.egg` from [Releases](https://github.com/GraphGiraffe/deluge-afterdownloads/releases) matching the Python version used by your Deluge installation. The tested official Deluge 2.2.0 Windows build uses `AfterDownloads-1.0.0-py3.9.egg`.
2. Open **Preferences â†’ Plugins â†’ Install**, select the `.egg`, and enable **AfterDownloads**. Fully restart Deluge if its preferences page does not appear.
3. Open **AfterDownloads** in preferences, select an available action, and click **Start waiting**. Use **Test only (dry-run)** for the first run.

Deluge must remain running; minimizing it to the tray is supported. Disabling the plugin, closing Deluge, or losing the connection cancels monitoring and releases the sleep inhibitor. Closing preferences does not stop monitoring. Avoid running another automatic shutdown utility at the same time.

## Limitations

The plugin controls the computer running the Deluge GTK client. Remote daemon connections are rejected. Headless daemons and Web UI sessions without the GTK client do not perform power actions.

Linux requires systemd/logind, `busctl`, `systemd-inhibit`, and a regular Python interpreter at `sys.executable`. Availability is queried using `CanSuspend`, `CanHibernate`, and `CanPowerOff`. Only `yes` enables an action; `no`, `na`, and `challenge` disable it. No interactive privilege elevation is requested. Linux hibernation also requires working kernel and swap/resume configuration. The inhibitor is released before the action. Frozen/AppImage builds with an unusual `sys.executable` may not support the helper and are **NOT TESTED**.

On Windows, Sleep is enabled only when S1â€“S3 is available. On Modern Standby S0-only systems, the API used here can enter hibernation, so Sleep is disabled in the plugin. This does not disable Modern Standby in Windows. Firmware and drivers can still affect behavior; test your device. Hibernation availability is checked with `IsPwrHibernateAllowed`.

Manual sleep, session locking, lid actions, and critical-battery protection can override the plugin's attempt to keep the system awake. An empty torrent list does not trigger an action; a list containing only paused torrents starts the countdown. Windows shutdown does not use `/f`, so applications with unsaved work may prevent shutdown.

## Development and building

Building and unit tests require only the Python standard library. Deluge provides GTK3, Twisted, and its own APIs at runtime.

```sh
python -m unittest discover -s tests -v
python build.py --python-version 3.9
```

Output from the current development version: `dist/AfterDownloads-1.0.1-py3.9.egg`. This ZIP contains Python source and Deluge metadata, without an EXE, DLL, or bundled third-party dependencies.

Releases include tags for Python 3.9â€“3.14 and `SHA256SUMS.txt`. Package contents are identical; select the filename matching Deluge's Python version. A filename tag alone does not establish compatibility with every Deluge build. See [Testing](docs/TESTING.md) for the configurations actually checked.

Publication instructions: [Releasing](docs/RELEASING.md). License: [MIT](LICENSE).
