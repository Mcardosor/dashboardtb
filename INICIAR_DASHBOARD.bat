@echo off
title Dashboard TB - SINAN
echo.
echo  ============================================
echo   Dashboard TB - SINAN  (Cenarios+)
echo  ============================================
echo.
echo  Iniciando o servidor...
echo  O navegador vai abrir sozinho em alguns segundos.
echo.
echo  Para DESLIGAR o dashboard: feche esta janela
echo  ou pressione Ctrl+C.
echo.

cd /d "%~dp0"

rem Abre o navegador depois de 3 segundos (tempo do servidor subir)
start /b "" cmd /c "timeout /t 3 >nul & start http://localhost:8000"

rem Liga o servidor (API + site juntos na porta 8000)
python -m uvicorn main:app --app-dir backend --port 8000

echo.
echo  O servidor foi encerrado.
pause
