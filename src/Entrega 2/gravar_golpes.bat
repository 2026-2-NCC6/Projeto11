@echo off
title TenniSync - Regravacao de Forehand e Backhand (10 Videos)
cd /d "%~dp0"
cls
echo ======================================================================
echo  TENNISSYNC: REGRAVACAO GUIADA - FOREHAND E BACKHAND (10 VIDEOS)
echo ======================================================================
echo  Os videos de Saque (11 a 15) ja estao preservados e salvos com sucesso!
echo.
echo  Agora serao regravados 10 videos (do 01 ao 10):
echo   - 5 Batidas de Direita (Forehand: braco direito batendo para frente)
echo   - 5 Batidas de Esquerda (Backhand: com 2 maos ou 1 mao)
echo.
echo  Fluxo de Gravacao:
echo   1. Instrucoes na tela (14s) com termos simples do dia a dia
echo   2. Beep continuo de 8 segundos para preparacao e posicionamento a 3.5m
echo   3. Quando o beep parar: GRAVACAO DE 6.5s -> EXECUTE O GOLPE!
echo   4. Chime duplo de confirmacao e avanco automatico
echo.
echo  Controles:
echo   [ESPACO] : Iniciar contagem imediatamente (se ja leu/posicionou)
echo   [P]      : Pausar / Despausar
echo   [R]      : Regravar o golpe anterior
echo   [S]      : Pular este golpe
echo   [Q]      : Sair e salvar o progresso
echo ======================================================================
echo.
py -3.11 Backend\record_batch_golpes.py --start 1 --end 10
echo.
echo Sessao de regravacao concluida!
pause
