@echo off
setlocal
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
echo.
echo VerdantCare is ready.
echo Admin dashboard: http://127.0.0.1:8001/dashboard/
echo Django admin:      http://127.0.0.1:8001/admin/
echo Login: admin / admin12345
python manage.py runserver 127.0.0.1:8001
