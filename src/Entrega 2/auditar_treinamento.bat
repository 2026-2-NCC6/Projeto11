@echo off
title TenniSync - Modulo de Auditoria Guiada e Treinamento
color 0b
echo ==============================================================================
echo                 TENNISYNC - AUDITORIA E QUALIFICACAO DE GOLPES
echo ==============================================================================
echo.
echo  Iniciando modulo de visao computacional, avaliacao continua e hardware IoT...
echo.
echo  - Monitoramento continuo do arco de preparacao, aceleracao e terminacao
echo  - Acendimento em tempo real dos LEDs no Arduino Uno (COM4)
echo  - Pausa obrigatoria com Replay de 5 segundos em loop para cada movimento
echo  - Teclas de Auditoria:
echo      [ENTER] Confirmar golpe previsto pela IA
echo      [1]     Corrigir para Forehand
echo      [2]     Corrigir para Backhand
echo      [3]     Corrigir para Saque
echo      [4 / F] MARCAR COMO FALSO POSITIVO (Envia para pasta repouso/)
echo      [D]     Descartar clipe
echo      [Q]     Sair e Retreinar a IA automaticamente
echo ==============================================================================
echo.

cd /d "%~dp0"

:: Notifica o servidor FastAPI em segundo plano para liberar o acesso exclusivo da camera
curl -s -X POST http://localhost:8000/api/camera/pause >nul 2>&1

:: Executa a sessao de auditoria com camera nativa
py -3.11 Backend\audit_camera_session.py %*

:: Devolve a camera ao servidor web ao finalizar
curl -s -X POST http://localhost:8000/api/camera/resume >nul 2>&1

echo.
echo Sessao finalizada. Pressione qualquer tecla para sair...
pause >nul
