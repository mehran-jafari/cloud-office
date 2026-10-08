#!/usr/bin/env bash
# اجرای همزمان Backend + Frontend
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> راه‌اندازی Backend و Frontend..."

# Backend در پس‌زمینه همین شل
(
  cd backend
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  [ -f .env ] || cp .env.example .env 2>/dev/null || true
  python manage.py migrate --noinput
  echo "Backend آماده — http://127.0.0.1:8000"
  python manage.py runserver 0.0.0.0:8000
) &
BACKEND_PID=$!

# Frontend
sleep 2
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
  echo "Frontend آماده — http://127.0.0.1:3000"
  pnpm dev &
  FRONT_PID=$!
else
  npm install
  npm run dev &
  FRONT_PID=$!
fi

# اگر روی macOS هستیم ترمینال جدا برای frontend هم پیشنهاد می‌شود
if [[ "$OSTYPE" == darwin* ]] && command -v osascript >/dev/null 2>&1; then
  osascript <<APPLESCRIPT
tell application "Terminal"
  do script "cd '$ROOT' && bash start-frontend.sh"
end tell
APPLESCRIPT
  echo "==> ترمینال جدا برای Frontend باز شد (macOS)."
fi

trap 'kill $BACKEND_PID $FRONT_PID 2>/dev/null; exit' INT TERM
wait
