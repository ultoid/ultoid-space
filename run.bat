@echo off
chcp 65001 > nul
echo Menyalakan Ultoid Space versi Lokal...
echo.
echo [1/2] Installing required packages...
python -m pip install -r requirements.txt -q
echo ✅ Packages installed!
echo.
echo [2/2] Starting application...
start http://127.0.0.1:8080
python app.py
pause
