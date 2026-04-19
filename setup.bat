@echo off
chcp 65001 >nul
echo ============================================
echo   FUN like HEL — Instalacja na nowym komputerze
echo ============================================
echo.

:: Sprawdz Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Python nie jest zainstalowany!
    echo Pobierz z: https://www.python.org/downloads/
    echo Zaznacz "Add Python to PATH" podczas instalacji!
    pause
    exit /b 1
)

echo [1/4] Instaluje wymagane biblioteki...
pip install -r requirements.txt
if errorlevel 1 (
    echo [BLAD] Nie udalo sie zainstalowac bibliotek!
    pause
    exit /b 1
)

echo.
echo [2/4] Sprawdzam pliki konfiguracyjne...

if not exist "api.env" (
    echo.
    echo [!] BRAK PLIKU api.env
    echo     Skopiuj plik api.env z glownego komputera do tego folderu.
    echo     Albo skopiuj .env.example jako api.env i uzupelnij klucze.
    echo.
    copy .env.example api.env >nul 2>&1
    echo     Utworzylem api.env z szablonu — uzupelnij go prawdziwymi kluczami!
    echo.
) else (
    echo     api.env — OK
)

if not exist "credentials.json" (
    echo [!] BRAK credentials.json — skopiuj z glownego komputera
    echo     (potrzebny do Gmail, Drive, YouTube, Google Business)
) else (
    echo     credentials.json — OK
)

if not exist "token.json" (
    echo.
    echo [!] BRAK token.json — uruchamiam autoryzacje Google...
    if exist "credentials.json" (
        python google_auth.py
    ) else (
        echo     Najpierw skopiuj credentials.json, potem uruchom: python google_auth.py
    )
) else (
    echo     token.json — OK
)

echo.
echo [3/4] Sprawdzam baze danych...
if not exist "memory.db" (
    echo     memory.db zostanie utworzona automatycznie przy starcie.
) else (
    echo     memory.db — OK
)

echo.
echo [4/4] Wszystko gotowe!
echo.
echo ============================================
echo   URUCHOMIENIE SERWERA:
echo   uvicorn main:app --reload
echo ============================================
echo.
echo   Albo po prostu uruchom: start.bat
echo.
pause
