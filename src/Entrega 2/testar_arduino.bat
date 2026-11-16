@echo off
chcp 65001 >nul
title TenniSync - Teste de Comunicacao Serial Arduino

cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)

%PY_CMD% Backend\test_arduino_com.py --interactive

pause
