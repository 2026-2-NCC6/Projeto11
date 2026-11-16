@echo off
chcp 65001 >nul
title TenniSync - Gravador Automatico de Firmware Arduino

echo ==================================================================
echo         TENNISSYNC - GRAVAÇÃO DE FIRMWARE NO ARDUINO UNO
echo ==================================================================
echo.

cd /d "%~dp0"

set "CLI=..\..\.tools\arduino-cli\arduino-cli.exe"
set "SKETCH=IoT\firmware_leds"

if not exist "%CLI%" (
    echo [ERRO] Binario arduino-cli nao encontrado em %CLI%
    pause
    exit /b 1
)

echo [1/3] Detectando porta do Arduino...
set "ARDUINO_PORT="

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)

for /f "delims=" %%i in ('%PY_CMD% -c "import sys; sys.path.insert(0, 'Backend'); from serial_manager import arduino_controller; print(arduino_controller._auto_detect_port() or '')"') do set ARDUINO_PORT=%%i

if "%ARDUINO_PORT%"=="" (
    echo [AVISO] Nenhuma porta COM do Arduino foi auto-detectada.
    set /p ARDUINO_PORT="Digite a porta COM do seu Arduino (ex: COM9, COM4, COM3): "
)

echo [OK] Porta selecionada: %ARDUINO_PORT%
echo.

echo [2/3] Compilando firmware (firmware_leds.ino)...
"%CLI%" compile --fqbn arduino:avr:uno "%SKETCH%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha na compilação do firmware.
    pause
    exit /b 1
)

echo.
echo [3/3] Gravando no Arduino na porta %ARDUINO_PORT%...
"%CLI%" upload -p %ARDUINO_PORT% --fqbn arduino:avr:uno "%SKETCH%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao enviar para o Arduino. Verifique se o cabo USB está conectado.
    pause
    exit /b 1
)

echo.
echo ==================================================================
echo  [SUCESSO] FIRMWARE GRAVADO E ATUALIZADO NO ARDUINO UNO!
echo ==================================================================
echo.
pause
