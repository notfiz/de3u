@echo off

SET VENV_NAME=de3u

if not exist "%VENV_NAME%\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv %VENV_NAME%
) else (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call %VENV_NAME%\Scripts\activate

if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
) else (
    echo No requirements.txt found. Skipping dependency installation.
)

if exist "main.py" (
    echo Running main.py...
    python main.py
) else (
    echo No main.py found. Please make sure it is in the current directory.
)

echo Done.
pause