@echo off
REM One-click demo script for CPS Growth Copilot (Windows)

echo 🚀 Starting CPS Growth Copilot Demo...
echo.

REM Check dependencies
echo 📋 Checking dependencies...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.11+ first.
    exit /b 1
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ npm is not installed. Please install Node.js 18+ first.
    exit /b 1
)

echo ✅ Dependencies check passed
echo.

REM Step 1: Start PostgreSQL
echo 🐘 Starting PostgreSQL container...
cd app\infra
docker-compose up -d postgres
cd ..\..

echo ⏳ Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak >nul

REM Step 2: Load sample data
echo 📦 Loading sample data...
cd scripts
python load_sample_data.py
cd ..

REM Step 3: Setup backend
echo 🔧 Setting up backend...
cd app\backend
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -q -e . 2>nul || pip install -q fastapi uvicorn sqlalchemy asyncpg pydantic python-dotenv

echo 🚀 Starting backend server...
start "Backend" cmd /k "uvicorn src.main:app --host 0.0.0.0 --port 8000"
cd ..\..

REM Step 4: Setup frontend
echo 🎨 Setting up frontend...
cd app\frontend
if not exist "node_modules" (
    echo Installing npm dependencies...
    call npm install
)

echo 🚀 Starting frontend server...
start "Frontend" cmd /k "npm run dev"
cd ..\..

REM Wait a bit for servers to start
timeout /t 5 /nobreak >nul

echo.
echo ✅ Demo is running!
echo.
echo 📍 Access points:
echo    - Frontend: http://localhost:3000
echo    - Backend API: http://localhost:8000
echo    - API Docs: http://localhost:8000/docs
echo.
echo 🧪 Example API calls:
echo.
echo    curl http://localhost:8000/health
echo    curl http://localhost:8000/metrics/taoke/1?window=7d
echo    curl http://localhost:8000/diagnosis/taoke/1?window=14d
echo.
echo ⚠️  Press any key to stop services...
pause >nul

REM Stop services
taskkill /FI "WINDOWTITLE eq Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /T /F >nul 2>&1
cd app\infra
docker-compose down
cd ..\..

echo.
echo ✅ Services stopped.

