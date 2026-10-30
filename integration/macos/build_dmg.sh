#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Run on macOS only. PyInstaller creates .app bundles in dist/.
for app in SCV-Encoder SCV-Player SCV-Exporter; do
  test -d "dist/$app.app" || { echo "Missing dist/$app.app. First run python build/build.py on macOS" >&2; exit 1; }
done
mkdir -p build/dmg
for app in SCV-Encoder SCV-Player SCV-Exporter; do cp -R "dist/$app.app" build/dmg/; done
hdiutil create -volname 'SCV Suite 1.0' -srcfolder build/dmg -ov -format UDZO SCV-Suite-1.0.dmg
printf 'To uninstall, drag the 3 SCV apps from Applications to Trash.\n'
