#!/usr/bin/env bash
set -euo pipefail
TARGET="${XDG_DATA_HOME:-$HOME/.local/share}"
for name in player encoder exporter; do rm -f "$TARGET/applications/scv-$name.desktop"; done
rm -f "$TARGET/mime/packages/scv.xml" "$TARGET/icons/hicolor/scalable/apps/scv.svg"
command -v update-mime-database >/dev/null && update-mime-database "$TARGET/mime" || true
command -v update-desktop-database >/dev/null && update-desktop-database "$TARGET/applications" || true
echo 'Removed user-level SCV integration; your lecture files are untouched.'
