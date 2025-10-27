@echo off
echo 🎲 Setting up D&D 5e Combat Simulator Backend...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Install requirements
echo 🔄 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Run migrations
echo 🔄 Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ❌ Failed to run migrations
    pause
    exit /b 1
)

REM Populate base data
echo 🔄 Populating D&D data...
python manage.py populate_dnd_data

echo 🔄 Populating conditions and environments...
python manage.py populate_conditions_environments

echo.
echo 🎉 Setup completed successfully!
echo.
echo 📋 Next steps:
echo 1. Start the development server: python manage.py runserver
echo 2. Visit the API: http://127.0.0.1:8000/api/
echo 3. Visit the admin: http://127.0.0.1:8000/admin/
echo 4. Visit the import interface: http://127.0.0.1:8000/api/enemies/import/
echo.
echo 🎲 Happy gaming!
pause
