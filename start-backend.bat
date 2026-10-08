@echo off
cd /d %~dp0backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
