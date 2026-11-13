@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

set "PY_CMD="

rem 1. Штатный лаунчер Python для Windows.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY_CMD=py -3"
)
if defined PY_CMD goto :check_version

rem 2. python.exe в PATH, кроме заглушки Microsoft Store.
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | findstr /I /C:"\WindowsApps\" >nul
    if errorlevel 1 (
        "%%P" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD="%%P""
            goto :check_version
        )
    )
)

rem 3. python3.exe в PATH, тоже без заглушки Store.
for /f "delims=" %%P in ('where python3 2^>nul') do (
    echo %%P | findstr /I /C:"\WindowsApps\" >nul
    if errorlevel 1 (
        "%%P" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD="%%P""
            goto :check_version
        )
    )
)

rem 4. Типовые каталоги установки.
for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~fD\python.exe" (
        "%%~fD\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD="%%~fD\python.exe""
            goto :check_version
        )
    )
)
for /d %%D in ("%ProgramFiles%\Python*") do (
    if exist "%%~fD\python.exe" (
        "%%~fD\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD="%%~fD\python.exe""
            goto :check_version
        )
    )
)
for /d %%D in ("C:\Python*") do (
    if exist "%%~fD\python.exe" (
        "%%~fD\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD="%%~fD\python.exe""
            goto :check_version
        )
    )
)
if exist "%UserProfile%\anaconda3\python.exe" set "PY_CMD="%UserProfile%\anaconda3\python.exe""
if exist "%LocalAppData%\Continuum\anaconda3\python.exe" set "PY_CMD="%LocalAppData%\Continuum\anaconda3\python.exe""
if exist "%ProgramData%\Anaconda3\python.exe" set "PY_CMD="%ProgramData%\Anaconda3\python.exe""
if defined PY_CMD goto :check_version

:missing_python
echo.
echo ============================================================
echo  Python не найден.
echo ============================================================
echo.
echo  Для работы Link Audit нужен Python 3.10 или новее.
echo.
echo  1. Скачайте установщик:
echo     https://www.python.org/downloads/windows/
echo  2. При установке обязательно включите:
echo     "Add python.exe to PATH"
echo  3. Закройте это окно и снова запустите
echo     Запустить_аудит.bat.
echo.
if not defined LINK_AUDIT_NO_BROWSER (
    echo  Открываю страницу загрузки Python...
    start "" "https://www.python.org/downloads/windows/"
)
echo.
pause
exit /b 1

:check_version
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Найден Python, но его версия старше 3.10:
    %PY_CMD% --version
    echo.
    echo Установите Python 3.10+ с https://www.python.org/downloads/windows/
    echo и включите "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

%PY_CMD% link_audit.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
