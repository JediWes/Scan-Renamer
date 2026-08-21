@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title Instalador - Cartorio Santa Cruz

echo.
echo  ====================================================
echo   INSTALADOR - Renomeador de Declaracoes
echo   Cartorio Santa Cruz - 2 Subdistrito
echo  ====================================================
echo.
echo  Este processo pode levar alguns minutos.
echo  Nao feche esta janela.
echo.
pause

:: ----------------------------------------------------
:: ETAPA 1 - Verificar internet
:: ----------------------------------------------------
echo.
echo [1/5] Verificando conexao com a internet...
ping -n 1 8.8.8.8 >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERRO: Sem conexao com a internet.
    echo  Conecte o computador e tente novamente.
    echo.
    pause
    exit /b 1
)
echo        OK.

:: ----------------------------------------------------
:: ETAPA 2 - Verificar / Instalar Python 3.11
:: ----------------------------------------------------
echo.
echo [2/5] Verificando Python...

python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PY_VER=%%V
    echo        Python !PY_VER! ja instalado. Pulando instalacao.
    goto :python_ok
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
    echo        Python 3.11 encontrado em AppData.
    goto :python_ok
)

echo        Python nao encontrado. Baixando instalador...
echo        (aguarde, arquivo ~25 MB)
echo.

set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PY_INST=%TEMP%\py3119.exe"

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; (New-Object Net.WebClient).DownloadFile('%PY_URL%','%PY_INST%')" 2>nul

if not exist "%PY_INST%" (
    echo        Tentando com curl...
    curl -L --output "%PY_INST%" "%PY_URL%" 2>nul
)

if not exist "%PY_INST%" (
    echo.
    echo  ERRO: Nao foi possivel baixar o Python.
    echo  Baixe manualmente:
    echo  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo  Instale com opcoes padrao e rode este script novamente.
    echo.
    pause
    exit /b 1
)

echo        Instalando Python 3.11.9...
"%PY_INST%" /quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1 Include_pip=1

if errorlevel 1 (
    echo.
    echo  ERRO: Falha na instalacao do Python.
    echo  Tente executar manualmente: %PY_INST%
    echo.
    pause
    exit /b 1
)

set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
echo        Python 3.11.9 instalado com sucesso.

:python_ok

:: ----------------------------------------------------
:: ETAPA 3 - Atualizar pip
:: ----------------------------------------------------
echo.
echo [3/5] Atualizando pip...
python -m pip install --upgrade pip --quiet --no-warn-script-location
echo        OK.

:: ----------------------------------------------------
:: ETAPA 4 - Instalar dependencias
:: ----------------------------------------------------
echo.
echo [4/5] Instalando dependencias...
echo.

echo   [4a] Pillow (imagens)...
python -m pip install Pillow --quiet --no-warn-script-location
if errorlevel 1 (
    python -m pip install Pillow
)
echo         OK.

echo   [4b] watchdog (monitoramento de pasta)...
python -m pip install watchdog --quiet --no-warn-script-location
if errorlevel 1 (
    python -m pip install watchdog
)
echo         OK.

echo   [4c] pypdfium2 (leitura de PDF)...
python -m pip install pypdfium2 --quiet --no-warn-script-location
if errorlevel 1 (
    python -m pip install pypdfium2
)
echo         OK.

echo.
echo        Dependencias instaladas.

:: ----------------------------------------------------
:: ETAPA 5 - Criar atalho na Area de Trabalho
:: ----------------------------------------------------
echo.
echo [5/5] Criando atalho na Area de Trabalho...

set "BAT_DIR=%~dp0"
if "%BAT_DIR:~-1%"=="\" set "BAT_DIR=%BAT_DIR:~0,-1%"
set "MAIN_PY=%BAT_DIR%\main.py"

set "PYTHONW=%LocalAppData%\Programs\Python\Python311\pythonw.exe"
if not exist "%PYTHONW%" (
    for /f "usebackq delims=" %%P in (`where pythonw 2^>nul`) do (
        set "PYTHONW=%%P"
        goto :found_pw
    )
    for /f "usebackq delims=" %%P in (`where python 2^>nul`) do (
        set "PYTHONW=%%P"
        goto :found_pw
    )
)
:found_pw

set "LNK=%USERPROFILE%\Desktop\Renomeador Cartorio.lnk"

powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%LNK%'); $s.TargetPath='%PYTHONW%'; $s.Arguments='\"%MAIN_PY%\"'; $s.WorkingDirectory='%BAT_DIR%'; $s.Description='Renomeador - Cartorio Santa Cruz'; $s.Save()" 2>nul

if exist "%LNK%" (
    echo        Atalho criado na Area de Trabalho.
) else (
    echo        Nao foi possivel criar o atalho automaticamente.
    echo        Crie manualmente: clique direito em main.py
    echo        e escolha Enviar para / Area de Trabalho.
)

:: ----------------------------------------------------
:: Verificacao final
:: ----------------------------------------------------
echo.
echo  ====================================================
echo   Verificando instalacao...
echo  ====================================================
echo.
python -c "import PIL; print('  Pillow:    ' + PIL.__version__)"
python -c "import watchdog; print('  watchdog:  OK')"
python -c "import pypdfium2; print('  pypdfium2: OK')"
python -c "import tkinter; print('  tkinter:   OK')"
echo.
echo  ====================================================
echo   INSTALACAO CONCLUIDA!
echo.
echo   Para abrir o programa:
echo     - Clique no atalho "Renomeador Cartorio"
echo       na Area de Trabalho, OU
echo     - Clique duplo em main.py
echo  ====================================================
echo.
pause
exit /b 0
