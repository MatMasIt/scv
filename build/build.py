"""Build portable app folders with PyInstaller on the TARGET OS.

Optionally pass --ffmpeg-dir DIRECTORY containing redistributable ffmpeg/ffprobe
binaries *and* a verified third-party notices/source bundle. Never downloads
unverified binaries automatically.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APPS = [
    ('Studio', 'scv.studio'),
    ('Player', 'scv.player'),
    ('Encoder', 'scv.encoder'),
    ('Exporter', 'scv.export_gui'),
]

def main():
    """Build portable application directories for the current platform."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg-dir', type=Path, help='Folder containing licensed ffmpeg and ffprobe executables')
    args = parser.parse_args()
    try: import PyInstaller  # noqa: F401
    except ImportError: parser.error('Install the build dependency: pip install pyinstaller')
    for name, module in APPS:
        entry = ROOT / 'build' / f'entry_{name.lower()}.py'
        entry.write_text(f'from {module} import main\nif __name__ == "__main__": raise SystemExit(main())\n',
                         encoding='utf-8')
        command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
                   '--onedir', '--name', f'SCV-{name}', '--distpath', str(ROOT / 'dist'),
                   '--workpath', str(ROOT / 'build' / 'work'), '--specpath', str(ROOT / 'build' / 'spec'),
                   '--add-data', f'{ROOT / "scv" / "assets"}{os.pathsep}scv/assets', str(entry)]
        print('Building', name, flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
        folder = ROOT / 'dist' / f'SCV-{name}'
        shutil.copy2(ROOT / 'LICENSE', folder / 'LICENSE-SCV.txt')
        shutil.copy2(ROOT / 'third_party' / 'NOTICE.md', folder / 'THIRD-PARTY-NOTICES.txt')
        if args.ffmpeg_dir:
            bin_dir = folder / 'bin'; bin_dir.mkdir(exist_ok=True)
            for executable in ('ffmpeg', 'ffprobe'):
                filename = executable + ('.exe' if os.name == 'nt' else '')
                target = args.ffmpeg_dir / filename
                if not target.is_file(): parser.error(f'Missing {target}')
                shutil.copy2(target, bin_dir / filename)
            required = args.ffmpeg_dir / 'LICENSES-AND-SOURCE.txt'
            if not required.is_file(): parser.error(f'Missing third-party compliance file: {required}')
            shutil.copy2(required, folder / required.name)
    print('Portable folders built under dist/ (on this operating system).')
if __name__ == '__main__': main()
