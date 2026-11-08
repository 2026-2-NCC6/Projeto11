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
py -3.11 Backend\record_batch_repouso.py
echo.
echo Sessao finalizada.
pause
