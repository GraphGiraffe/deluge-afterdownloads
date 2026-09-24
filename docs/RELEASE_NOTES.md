# AfterDownloads 1.0.0

A native Deluge GTK3 plugin for Windows and Linux with systemd/logind. Prevent automatic sleep while active downloads finish, then Sleep, Hibernate, or Shut down after a cancellable 60-second countdown. Paused torrents are ignored, and the display can still turn off.

Windows operation and dry-run were confirmed by the user in Deluge 2.2.0. Linux desktop integration and real power actions are **NOT TESTED**; automated tests pass in Ubuntu 26.04 WSL. macOS and FreeBSD are not implemented or advertised as supported.

Install the `.egg` matching Deluge's Python version. Packages are provided for Python 3.9â€“3.14. The tested official Windows Deluge 2.2.0 build uses `py3.9`. Verify the download using the attached `SHA256SUMS.txt`.

English and Russian UI follow the Deluge language setting; other languages fall back to English. Technical names such as Modern Standby, S0, and dry-run remain unchanged.

Unavailable Sleep and Hibernate options are disabled automatically. Sleep is disabled on Modern Standby S0-only devices because of the behavior of the Windows API used here. Remote connections and headless/Web UI sessions without GTK do not perform power actions. No Web UI password is required.

Enabling the plugin does not start monitoring. Open its preferences page and click **Start waiting**. Use **Test only (dry-run)** for the first run.
