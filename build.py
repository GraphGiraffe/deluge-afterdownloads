"""Build a deterministic, source-only Deluge egg without installed Deluge."""
import argparse
import pathlib
import zipfile

VERSION = '1.0.0'
ROOT = pathlib.Path(__file__).resolve().parent


def source_bytes(path):
    # A checkout with CRLF must produce the same artifact as a checkout with LF.
    return path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')


def build(python_version='3.9'):
    output = ROOT / 'dist' / ('AfterDownloads-{}-py{}.egg'.format(VERSION, python_version))
    output.parent.mkdir(exist_ok=True)
    entries = {
        'EGG-INFO/PKG-INFO': ('Metadata-Version: 1.2\nName: AfterDownloads\nVersion: {}\n'
                            'Summary: Power actions after Deluge downloads finish on Windows and Linux\n'
                            'License: MIT\n\nNative GTK3 plugin for Deluge 2.x.\n').format(VERSION).encode(),
        'EGG-INFO/entry_points.txt': ( '[deluge.plugin.core]\nAfterDownloads = deluge_afterdownloads:CorePlugin\n\n'
                                     '[deluge.plugin.gtk3ui]\nAfterDownloads = deluge_afterdownloads:GtkUIPlugin\n').encode(),
        'EGG-INFO/top_level.txt': b'deluge_afterdownloads\n',
        'EGG-INFO/zip-safe': b'',
        'EGG-INFO/LICENSE': source_bytes(ROOT / 'LICENSE'),
    }
    for source in sorted((ROOT / 'deluge_afterdownloads').glob('*.py')):
        entries['deluge_afterdownloads/' + source.name] = source_bytes(source)
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            # Source eggs are small. Storing avoids zlib-version-dependent output.
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--python-version', choices=['3.9', '3.10', '3.11', '3.12', '3.13', '3.14'], default='3.9')
    print(build(parser.parse_args().python_version))
