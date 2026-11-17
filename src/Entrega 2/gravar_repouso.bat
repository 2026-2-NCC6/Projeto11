@echo off
title TenniSync - Gravador Autonomo com MediaPipe Pose 3D
cd /d "%~dp0"
cls
echo ======================================================================
echo  TENNISSYNC: GRAVADOR AUTONOMO DE REPOUSO (50 VIDEOS)
echo ======================================================================
echo  Pressione [ESPACO] para iniciar a gravacao do video exibido na tela.
echo  Pressione [P] para pausar o fluxo.
echo  Pressione [Q] para encerrar e salvar o progresso.
echo ======================================================================
echo.
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)

%PY_CMD% Backend\record_batch_repouso.py
echo.
echo Sessao finalizada.
pause
