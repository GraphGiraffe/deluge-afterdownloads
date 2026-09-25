# AfterDownloads 1.0.1

Unreleased: prepared for testing from the integration branch.

Fix Sleep and Hibernate becoming unavailable on Linux after starting monitoring. The plugin previously queried logind while holding its own sleep inhibitor, which could cause an available action to be rejected.

The plugin now preserves the availability result while waiting. After the countdown and a fresh torrent-status check, it releases its inhibitor before querying availability again. Actions that are still unavailable are rejected. The action selectors remain locked during monitoring, and dry-run never requests a power transition.

A native Deluge GTK3 plugin for Windows and Linux with systemd/logind. Prevent automatic sleep while active downloads finish, then Sleep, Hibernate, or Shut down after a cancellable 60-second countdown. Paused torrents are ignored, and the display can still turn off.

Windows operation and dry-run were confirmed by the user in Deluge 2.2.0. The user also confirmed shutdown after downloads on an Ubuntu desktop. Actual Linux Sleep and Hibernate, including physical-device verification of this fix, remain **NOT TESTED**. Automated regression coverage simulates the inhibitor affecting logind responses; the suite passes on Windows and Ubuntu WSL. macOS and FreeBSD are not implemented or advertised as supported.

Install the `.egg` matching Deluge's Python version. Packages are provided for Python 3.9â€“3.14. The tested official Windows Deluge 2.2.0 build uses `py3.9`. Verify the download using the attached `SHA256SUMS.txt`.

English and Russian UI follow the Deluge language setting; other languages fall back to English. Technical names such as Modern Standby, S0, and dry-run remain unchanged.

Unavailable Sleep and Hibernate options are disabled automatically. Sleep is disabled on Modern Standby S0-only devices because of the behavior of the Windows API used here. Remote connections and headless/Web UI sessions without GTK do not perform power actions. No Web UI password is required.

Fully restart Deluge after installing an updated package. Enabling the plugin does not start monitoring. Open its preferences page and click **Start waiting**. Use **Test only (dry-run)** for the first run.
