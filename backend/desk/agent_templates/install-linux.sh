#!/usr/bin/env bash
# Cloud Office Desk - Linux installer
# Usage: curl -fsSL "__APP_URL__/api/desk/agent/linux/?app=__APP_URL__" | bash
set -eu

APP_URL="__APP_URL__"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/cloud-office-desk"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/cloud-office-desk.desktop"

if [ "${1:-}" = "--uninstall" ]; then
  rm -rf "$INSTALL_DIR" "$DESKTOP_FILE" "$HOME/Desktop/cloud-office-desk.desktop"
  echo "Removed Cloud Office Desk."
  exit 0
fi

echo "=== Installing Cloud Office Desk (Linux) ==="
echo "Server: $APP_URL"
mkdir -p "$INSTALL_DIR" "$APPS_DIR"

cat > "$INSTALL_DIR/start-desk-agent.sh" <<LAUNCH
#!/usr/bin/env bash
URL="$APP_URL/remote-support?agent=1"
for B in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge brave-browser; do
  if command -v "\$B" >/dev/null 2>&1; then
    nohup "\$B" --app="\$URL" >/dev/null 2>&1 &
    exit 0
  fi
done
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "\$URL" >/dev/null 2>&1 &
elif command -v sensible-browser >/dev/null 2>&1; then
  sensible-browser "\$URL" >/dev/null 2>&1 &
else
  echo "Open this address in your browser: \$URL"
fi
LAUNCH
chmod +x "$INSTALL_DIR/start-desk-agent.sh"

cat > "$DESKTOP_FILE" <<DESK
[Desktop Entry]
Name=Cloud Office Desk
Comment=Secure remote connection
Exec="$INSTALL_DIR/start-desk-agent.sh"
Terminal=false
Type=Application
Categories=Network;
DESK
chmod +x "$DESKTOP_FILE"

if [ -d "$HOME/Desktop" ]; then
  cp "$DESKTOP_FILE" "$HOME/Desktop/cloud-office-desk.desktop" 2>/dev/null || true
  chmod +x "$HOME/Desktop/cloud-office-desk.desktop" 2>/dev/null || true
fi
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

date -u +%Y-%m-%dT%H:%M:%SZ > "$INSTALL_DIR/installed.flag"
printf '%s\n' "$APP_URL" > "$INSTALL_DIR/server.url"
echo "Installed. Launch 'Cloud Office Desk' from your applications menu."
"$INSTALL_DIR/start-desk-agent.sh" || true
