#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$TARGET/applications" "$TARGET/mime/packages" "$TARGET/icons/hicolor/scalable/apps"
cp "$ROOT/integration/linux/scv.xml" "$TARGET/mime/packages/scv.xml"
cp "$ROOT/assets/scv.svg" "$TARGET/icons/hicolor/scalable/apps/scv.svg"
# Portable binary: prefer dist/SCV-Player, fallback to module launcher (must be installed).
for name in Studio Player Encoder Exporter; do
  lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
  exe="$ROOT/dist/SCV-$name/SCV-$name"
  if [[ -x "$exe" ]]; then cmd="$exe"; else cmd="python3 -m scv.$([[ "$name" == 'Exporter' ]] && echo export_gui || echo "$lower")"; fi
  cat > "$TARGET/applications/scv-$lower.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SCV $name
Exec=$cmd %f
Icon=scv
Terminal=false
Categories=AudioVideo;
$( [[ "$name" == 'Player' || "$name" == 'Studio' ]] && echo 'MimeType=application/x-scv;' || true )
EOF
done
command -v update-mime-database >/dev/null && update-mime-database "$TARGET/mime" || true
command -v update-desktop-database >/dev/null && update-desktop-database "$TARGET/applications" || true
command -v xdg-mime >/dev/null && xdg-mime default scv-player.desktop application/x-scv || true
echo 'Installed user-level SCV desktop entries. Uninstall: integration/linux/uninstall.sh'
