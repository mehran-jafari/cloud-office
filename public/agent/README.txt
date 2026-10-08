Cloud Office Desk Agent
=======================

Install (recommended: one command, no file download needed)
-----------------------------------------------------------
The install dialog inside the app shows the exact command for your system.

Windows (PowerShell):
  powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb 'https://YOUR-SERVER/api/desk/agent/windows/?app=https://YOUR-SERVER' | iex"

macOS (Terminal):
  curl -fsSL 'https://YOUR-SERVER/api/desk/agent/macos/?app=https://YOUR-SERVER' | bash

Linux (terminal):
  curl -fsSL 'https://YOUR-SERVER/api/desk/agent/linux/?app=https://YOUR-SERVER' | bash

What it does: creates a "Cloud Office Desk" shortcut/app (Desktop + Start Menu / Launchpad /
applications menu) that opens the remote-support page of YOUR server in a standalone window
(Edge/Chrome/Brave when available, otherwise the default browser). Nothing runs in the
background and no admin rights are needed.

Uninstall
---------
  Windows: set CLOUD_OFFICE_UNINSTALL=1 and run the same command
  macOS/Linux: same command with   | bash -s -- --uninstall

Notes
-----
- Open the app and sign in once; the sign-in is shared with your normal browser profile.
- Production: set PUBLIC_APP_URL in backend/.env so scripts always contain the public address.
- This version is a secure web launcher + WebRTC screen share. Full OS-level mouse/keyboard
  control needs a signed native agent (future).
