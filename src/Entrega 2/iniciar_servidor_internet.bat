@echo off
title TenniSync - Servidor de Streaming UDP, IA e Hardware IoT
color 0a

echo ==============================================================================
echo        TENNISYNC - SERVIDOR DE PRODUCAO (STREAMING UDP, IA & IOT)
echo ==============================================================================
echo.
echo  Configuracao Ativa de Servico:
echo   - Protocolo de Video:  WebRTC SRTP sobre UDP (Baixa Latencia)
echo   - Fallback de Rede:    WebSocket /ws/video
echo   - Servidor Local:      FastAPI @ http://localhost:8000
echo   - Hardware IoT:        Arduino Uno (COM4 @ 9600 baud - 12 LEDs + Buzzer)
echo   - Autenticacao:        JWT Bearer + Session Cookie
echo.
echo  Credenciais Padrao de Acesso:
echo   [Usuario] admin
echo   [Senha]   tennis2026
echo.
echo ==============================================================================
echo  COMO EXPOR ESTE COMPUTADOR PARA QUALQUER NAVEGADOR NA INTERNET:
echo ==============================================================================
echo.
echo  Opcao 1 (Recomendada - Cloudflare Tunnel Gratuito):
echo    Abra outro terminal e execute:
echo      cloudflared tunnel --url http://localhost:8000
echo.
echo  Opcao 2 (Ngrok):
echo    Abra outro terminal e execute:
echo      ngrok http 8000
echo.
echo  O endereco HTTPS gerado pode ser aberto em qualquer computador ou celular!
echo ==============================================================================
echo.

cd /d "%~dp0"

:: Compila o Frontend se a pasta dist nao existir
if not exist "Frontend\dist" (
    echo [INFO] Compilando Frontend para producao...
    cmd.exe /c "npm --prefix Frontend run build"
    echo.
)

echo [INFO] Iniciando servidor Web backend na porta 8000...
py -3.11 Backend\server.py

pause
