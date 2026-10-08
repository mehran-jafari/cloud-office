#!/usr/bin/env bash
# Cloud Office Desk - macOS installer
# Usage: curl -fsSL "__APP_URL__/api/desk/agent/macos/?app=__APP_URL__" | bash
set -eu

APP_URL="__APP_URL__"
APP_NAME="Cloud Office Desk"
APP_DIR="$HOME/Applications/$APP_NAME.app"
DATA_DIR="$HOME/Library/Application Support/CloudOfficeDesk"

if [ "${1:-}" = "--uninstall" ]; then
  rm -r -f "$APP_DIR" "$DATA_DIR" "$HOME/Desktop/$APP_NAME.app"
  echo "Removed $APP_NAME."
  exit 0
fi

echo "=== Installing $APP_NAME (macOS) ==="
echo "Server: $APP_URL"

mkdir -p "$APP_DIR/Contents/MacOS" "$DATA_DIR"

cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>ir.cloudoffice.desk</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>LSUIElement</key><false/>
</dict>
</plist>
PLIST

# Launcher: opens the remote page as a standalone app window when a
# Chromium-based browser exists, otherwise in the default browser.
cat > "$APP_DIR/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
URL="$APP_URL/remote-support?agent=1"
for B in "Google Chrome" "Microsoft Edge" "Brave Browser" "Chromium"; do
  if [ -d "/Applications/\$B.app" ] || [ -d "\$HOME/Applications/\$B.app" ]; then
    open -na "\$B" --args --app="\$URL" && exit 0
  fi
done
open "\$URL"
LAUNCH
chmod +x "$APP_DIR/Contents/MacOS/launch"

# Files created locally are not quarantined, but clear the flag defensively.
xattr -dr com.apple.quarantine "$APP_DIR" 2>/dev/null || true

# Desktop shortcut (alias via symlink)
ln -sfn "$APP_DIR" "$HOME/Desktop/$APP_NAME.app" 2>/dev/null || true

date -u +%Y-%m-%dT%H:%M:%SZ > "$DATA_DIR/installed.flag"
printf '%s\n' "$APP_URL" > "$DATA_DIR/server.url"

echo "Installed: $APP_DIR"
echo "Open '$APP_NAME' from Launchpad/Spotlight or the Desktop."
"$APP_DIR/Contents/MacOS/launch" || true
