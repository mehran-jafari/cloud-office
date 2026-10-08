#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || true
fi
python manage.py migrate
# در production:
# export DJANGO_DEBUG=0
# python manage.py check --deploy
echo ""
echo "==> اگر سوپریوزر ندارید: python manage.py createsuperuser"
echo "==> Backend: http://127.0.0.1:8000"
python manage.py runserver 0.0.0.0:8000
