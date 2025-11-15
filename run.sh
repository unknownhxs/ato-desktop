#!/bin/bash

if ! command -v python3 &> /dev/null; then
    echo "Erreur: Python 3 n'est pas installé"
    exit 1
fi

if ! python3 -c "import pygame" 2>/dev/null; then
    echo "Installation des dépendances..."
    if ! python3 -m pip install --user pygame>=2.5.0 2>&1 | tee /tmp/pygame_install.log; then
        echo ""
        echo "Erreur lors de l'installation automatique."
        echo ""
        echo "Solutions possibles :"
        echo ""
        echo "1. Installer via le gestionnaire de paquets système :"
        if command -v apt-get &> /dev/null; then
            echo "   sudo apt-get install python3-pygame"
        elif command -v dnf &> /dev/null; then
            echo "   sudo dnf install python3-pygame"
        elif command -v pacman &> /dev/null; then
            echo "   sudo pacman -S python-pygame"
        elif command -v yum &> /dev/null; then
            echo "   sudo yum install python3-pygame"
        fi
        echo ""
        echo "2. Installer les dépendances de compilation d'abord :"
        if command -v apt-get &> /dev/null; then
            echo "   sudo apt-get install python3-dev python3-pip libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev"
        elif command -v dnf &> /dev/null; then
            echo "   sudo dnf install python3-devel SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel"
        fi
        echo "   puis : python3 -m pip install pygame"
        echo ""
        echo "3. Utiliser une version précompilée :"
        echo "   python3 -m pip install --only-binary :all: pygame"
        echo ""
        echo "Détails de l'erreur dans /tmp/pygame_install.log"
        exit 1
    fi
fi

python3 ato.py

