@echo off
python --version >nul 2>&1
if errorlevel 1 (
    echo Erreur: Python n'est pas installe
    pause
    exit /b 1
)

python -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances...
    python -m pip install pygame>=2.5.0
    if errorlevel 1 (
        echo Erreur lors de l'installation de pygame.
        echo Essayez d'installer manuellement :
        echo   pip install pygame
        pause
        exit /b 1
    )
)

python ato.py
pause

