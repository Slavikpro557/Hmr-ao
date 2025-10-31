@echo off
REM HRM Gradio installer for Windows (batch)
REM Требуется: git, Python 3.8+ (python или py)
setlocal enabledelayedexpansion

echo ===============================
echo HRM Gradio installer (Windows)
echo ===============================

REM Проверка git
git --version >nul 2>&1
if errorlevel 1 (
  echo Git не найден в PATH.
  echo Установите Git: https://git-scm.com/download/win
  pause
  exit /b 1
)

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
  py -3 --version >nul 2>&1
  if errorlevel 1 (
    echo Python не найден. Установите Python 3.8+ и повторите.
    echo Рекомендуется: https://www.python.org/downloads/
    pause
    exit /b 1
  ) else (
    set "PYEXEC=py -3"
  )
) else (
  set "PYEXEC=python"
)

echo Using Python: %PYEXEC%
echo.

REM Параметры
set "REPO_URL=https://github.com/Slavikpro557/Hmr-ao.git"
set "REPO_DIR=Hmr-ao"

REM Клонирование репозитория (если ещё нет)
if not exist "%REPO_DIR%\" (
  echo Cloning repository...
  git clone %REPO_URL%
  if errorlevel 1 (
    echo Ошибка клонирования репозитория.
    pause
    exit /b 1
  )
) else (
  echo Репозиторий %REPO_DIR% уже существует — пропускаю клонирование.
)

REM Создание виртуального окружения внутри репо
pushd "%REPO_DIR%"
if not exist ".venv\" (
  echo Создаю виртуальное окружение .venv...
  %PYEXEC% -m venv .venv
) else (
  echo Виртуальное окружение .venv уже существует.
)

echo Активирую виртуальное окружение...
call .venv\Scripts\activate.bat

echo Обновляю pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel

REM Установка зависимостей из репо (если есть)
if exist requirements.txt (
  echo Устанавливаю зависимости из requirements.txt...
  pip install -r requirements.txt
) else (
  echo requirements.txt не найден в репо — пропускаю.
)

echo Устанавливаю gradio и torch (если нужно)...
pip install --no-deps gradio
REM Попробуем установить torch — если не сработает, подскажем ссылку
pip install --no-deps torch || (
  echo Не удалось установить torch автоматически. Установите подходящую версию вручную: https://pytorch.org/get-started/locally/
)

popd

REM Копирование локальных файлов ui.py и dataset (ожидаются рядом с этим install.bat)
echo Копирование ui.py и dataset в папку %REPO_DIR% (если они найдены рядом с инсталлятором)...
if exist "ui.py" (
  xcopy /Y "ui.py" "%REPO_DIR%\ui.py" >nul
  echo ui.py -> %REPO_DIR%\ui.py
) else (
  echo WARNING: ui.py не найден рядом с install.bat. Положите ui.py рядом и запустите снова, или отредактируйте %REPO_DIR%\ui.py вручную.
)

if exist "dataset\build_code_dataset.py" (
  if not exist "%REPO_DIR%\dataset" mkdir "%REPO_DIR%\dataset"
  xcopy /Y "dataset\build_code_dataset.py" "%REPO_DIR%\dataset\build_code_dataset.py" >nul
  echo dataset\build_code_dataset.py -> %REPO_DIR%\dataset\build_code_dataset.py
) else (
  echo WARNING: dataset\build_code_dataset.py не найден в подпапке dataset рядом с install.bat.
)

REM Создание checkpoints
if not exist "%REPO_DIR%\checkpoints" (
  mkdir "%REPO_DIR%\checkpoints"
)

echo.
echo Установка завершена (локально). Чтобы запустить UI:
echo 1) Откройте CMD/PowerShell
echo 2) Перейдите в папку репозитория: cd %REPO_DIR%
echo 3) Активируйте виртуальное окружение: call .venv\Scripts\activate.bat
echo 4) Запустите UI: python ui.py
echo
 echo Примечание: Если pretrain.py / evaluate.py в вашем репо имеют другие CLI/аргументы, откройте ui.py и подправьте вызовы subprocess или прямые импорты.
pause
endlocal