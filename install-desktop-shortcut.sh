#!/usr/bin/env bash
# Write a .desktop launcher with absolute paths onto ~/Desktop and applications menu.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_SRC="$ROOT/redmondhr.desktop"
OUT_NAME="redmondhr.desktop"

if [[ ! -x "$ROOT/start-redmondhr.sh" ]]; then
  chmod +x "$ROOT/start-redmondhr.sh" "$ROOT/stop-redmondhr.sh" 2>/dev/null || true
fi

TMP="$(mktemp)"
sed -e "s|PLACEHOLDER_ROOT|$ROOT|g" "$DESKTOP_SRC" > "$TMP"
chmod +x "$TMP"

mkdir -p "$HOME/.local/share/applications"
cp "$TMP" "$HOME/.local/share/applications/$OUT_NAME"

if [[ -d "$HOME/Desktop" ]]; then
  cp "$TMP" "$HOME/Desktop/$OUT_NAME"
  chmod +x "$HOME/Desktop/$OUT_NAME"
  echo "Installed: $HOME/Desktop/$OUT_NAME"
fi

# Mark trusted on GNOME (ignore failures on other DEs)
if command -v gio >/dev/null 2>&1 && [[ -f "$HOME/Desktop/$OUT_NAME" ]]; then
  gio set "$HOME/Desktop/$OUT_NAME" metadata::trusted true 2>/dev/null || true
fi

rm -f "$TMP"
echo "Installed: $HOME/.local/share/applications/$OUT_NAME"
echo "You can start RedmondHR from the app menu or Desktop icon (double-click)."
echo "A terminal stays open — close it (or Ctrl+C) to stop RedmondHR."
