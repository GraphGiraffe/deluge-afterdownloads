# Testing and limitations

## Local Windows validation, September 2026

- Python 3.13.13: `python -m unittest discover -s tests -v` passes all 31 tests.
- Translation tests cover Deluge language precedence, active gettext detection, English fallback, catalog completeness, matching format placeholders, and unchanged technical names.
- The English preferences page was visually checked in the real Deluge GTK client. The user confirmed the plugin works and separately confirmed a successful dry-run.
- Tests cover completion rules, a full minute before execution, a fresh final response, new downloads during the countdown, cancellation, connection loss, stale callbacks, and dry-run without power actions.
- Windows capability queries and sleep-inhibitor creation/release were exercised with the real APIs. The tested device has no S1â€“S3 support and does support hibernation.
- Deluge 2.2.0 Windows with its bundled Python 3.9 loaded both the core and GTK components. Diagnostics reported `loaded=true`, `armed=false`, and the expected action availability.
- Build, core, changelog, and release-note versions are checked for consistency. Plugin modules are also parsed using Python 3.9 syntax rules.
- Release bytes match across Windows and Ubuntu WSL, including checkouts with different line endings. Packages contain no EXE, DLL, credentials, or user configuration.
- Automated controller tests use GTK/Deluge stubs. Each real power transition has not been independently verified by the agent.

## CI and other environments

- GitHub Actions runs the suite on Windows and Ubuntu with Python 3.9, 3.13, and 3.14. Check the [Actions page](https://github.com/GraphGiraffe/deluge-afterdownloads/actions) for the result associated with a particular commit or tag.
- Ubuntu 26.04 WSL with Python 3.14.4: 30 tests passed and the Windows API test was skipped. Mock tests check logind availability responses and D-Bus method selection without interactive authentication.
- A controller regression test simulates `CanSuspend` and `CanHibernate` returning `challenge` while the plugin's inhibitor is held. It covers starting monitoring, reopening preferences, retaining the selection, the full 60-second countdown, inhibitor release before the final availability query, and both dry-run and dispatch with a mocked power backend. The test failed on 1.0.0 and passes with the fix. A separate negative test checks that actions still unavailable after release are refused.
- Real Linux Sleep and Hibernate and physical-device verification of the inhibitor fix remain **NOT TESTED**. WSL does not replace physical-device validation.
- Python 3.10â€“3.14 inside real Deluge installations is **NOT TESTED**. Matching the `.egg` filename tag does not prove compatibility with a particular Deluge distribution.
- macOS, FreeBSD, and Linux without systemd/logind are not implemented; actions are disabled.

## Ubuntu desktop report, September 25, 2026

- The user confirmed that Shut down ran successfully after downloads finished.
- The supplied screenshot confirms that the preferences page and Sleep countdown opened in the real GTK client with dry-run enabled.
- Sleep was available before starting monitoring but was then incorrectly reported as unavailable. The plugin queried logind with its own `idle:sleep` inhibitor active; this ordering is corrected in 1.0.1.
- The grey action selectors during monitoring are intentional: they lock the selected action until completion or cancellation. The incorrect availability message is a separate bug.
- Ubuntu, desktop environment, Deluge, and Python versions were not provided. This report does not establish compatibility with every Ubuntu or Deluge build.
- Actual Sleep and Hibernate transitions and a repeat test with 1.0.1 have not yet been confirmed.

## Manual release checks

1. Install the `.egg`, enable the plugin, and fully restart Deluge if needed. Open AfterDownloads in preferences.
2. Check that unavailable actions are disabled and explained. Capabilities must be detected again on another computer.
3. Enable **Test only (dry-run)**, select an available action, and start waiting. Check unfinished, paused, and completed torrents.
4. Check the countdown, Cancel button, and closing the countdown window. On Linux, select Sleep or Hibernate if available, start waiting, then reopen preferences during the countdown: the selected action must remain selected without a new unavailable message. The selectors are intentionally locked. Wait for the dry-run completion message; power state must not change. Repeat with cancellation and confirm the available selectors become usable again.
5. Add or resume an unfinished download during the countdown: monitoring must return to waiting. Disconnecting or disabling the plugin must cancel monitoring.
6. Confirm that the display can turn off, automatic sleep is blocked during monitoring, and the inhibitor is released after cancellation.
7. Test real power actions separately after saving work. On Linux, first verify that OS hibernation itself is configured. Record the OS, Deluge/Python versions, and observed results in this document.
