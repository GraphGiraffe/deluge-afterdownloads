# Publishing a release

This directory is the standalone [AfterDownloads repository](https://github.com/GraphGiraffe/deluge-afterdownloads). The neighboring DelugeSleep desktop application, passwords, user settings, and backups do not belong here. EXE/DLL files and private runtime data are also excluded by `.gitignore`.

The integration branch is `dev`; the stable branch is `main`. Normal changes use a task branch and a PR into `dev`. Releases use a separate PR from `dev` into `main`. Use **Squash and merge**.

1. Create a task branch from current `dev`, make changes, update documentation, and run local tests.
2. Push the task branch and open a PR into `dev`. Commits and publishing actions use the owner's GitHub account. A GitHub noreply address avoids exposing a personal email.
3. Wait for **Test and build**. It runs Python 3.9, 3.13, and 3.14 on Windows and Ubuntu and uploads packages. CI does not replace physical-device power testing.
4. Check the plugin in real Deluge, including dry-run and cancellation. Review [Testing](TESTING.md) for known limitations.
5. Update `VERSION` in `build.py`, the diagnostic version in `core.py`, `CHANGELOG.md`, and `RELEASE_NOTES.md`. All versions must match.
6. After the tested release commit reaches `main`, create and push an annotated tag on that commit. For 1.0.0: `git tag -a v1.0.0 -m "AfterDownloads 1.0.0"`, then `git push origin v1.0.0`.
7. **Build release** runs the same Windows/Ubuntu test matrix, verifies that the tag matches the source version, builds eggs for Python 3.9â€“3.14, and uploads them with `SHA256SUMS.txt` as `AfterDownloads-v1.0.0-release`.
8. Download the artifact, verify SHA-256, install the appropriate `.egg`, and check dry-run in Deluge. Create a GitHub Release for the existing tag using the owner's account. Attach all six eggs and `SHA256SUMS.txt`; use `docs/RELEASE_NOTES.md` as the description. Review the files, then publish.

Tests never run real sleep, hibernation, or shutdown commands. Routing and cancellation tests cannot guarantee actual power behavior on other computers.

The workflow has only `contents: read` and does not publish as `github-actions[bot]`. The local build script also makes no GitHub writes.
