@echo off
chcp 65001 >nul
echo ============================================
echo   Kopiowanie sekretow na pendrive/dysk
echo ============================================
echo.
echo Ten skrypt kopiuje pliki z kluczami API
echo na pendrive lub folder sieciowy.
echo.

set /p DEST="Podaj sciezke docelowa (np. E:\funlikehel-secrets): "

if not exist "%DEST%" mkdir "%DEST%"

echo.
echo Kopiuje pliki...
copy /y "api.env" "%DEST%\api.env"
copy /y "credentials.json" "%DEST%\credentials.json"
copy /y "token.json" "%DEST%\token.json"
if exist "memory.db" copy /y "memory.db" "%DEST%\memory.db"
if exist "ekipa.db" copy /y "ekipa.db" "%DEST%\ekipa.db"

echo.
echo ============================================
echo   Gotowe! Skopiowane pliki:
echo   - api.env (klucze API)
echo   - credentials.json (Google OAuth)
echo   - token.json (token Google)
echo   - memory.db (pamiec rozmow)
echo   - ekipa.db (baza ekipy)
echo.
echo   Na drugim komputerze:
echo   1. git clone https://github.com/funlikehelbrand-crypto/funlikehel-bot.git
echo   2. Wklej te pliki do folderu funlikehel-bot/
echo   3. Uruchom setup.bat
echo ============================================
echo.
pause
