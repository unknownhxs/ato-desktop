# ATO - Version Desktop (Linux/Windows)
By hxs - alpha 1

Version adaptée du jeu ATO pour Linux et Windows utilisant pygame.

## Installation

### Prérequis
- Python 3.7 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation automatique

Les dépendances s'installent automatiquement au premier lancement ! Vous pouvez simplement lancer le jeu :

**Linux/Mac :**
```bash
./run.sh
```

**Windows :**
```batch
run.bat
```

**Ou directement :**
```bash
python ato.py
```

Le script détectera automatiquement si pygame est manquant et l'installera.

### Dépannage

Si l'installation automatique échoue, voici les solutions :

**Linux (Debian/Ubuntu) :**
```bash
sudo apt-get install python3-pygame
```

**Linux (Fedora/RHEL) :**
```bash
sudo dnf install python3-pygame
```

**Linux (Arch) :**
```bash
sudo pacman -S python-pygame
```

**Si vous devez compiler pygame vous-même :**

Installez d'abord les dépendances de compilation :

*Debian/Ubuntu :*
```bash
sudo apt-get install python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
pip install pygame
```

*Fedora/RHEL :*
```bash
sudo dnf install python3-devel SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel
pip install pygame
```

**Alternative : utiliser une version précompilée :**
```bash
pip install --only-binary :all: pygame
```

## Contrôles

- **Flèches directionnelles** ou **WASD** : Déplacer le personnage
- **Échap** : Quitter le jeu

## Caractéristiques

- Carte procédurale de 500x500 pixels
- Génération aléatoire d'arbres et de rochers
- Bordure bleue et blanche aux limites de la carte
- Animation du personnage (slime bleu)
- Affichage FPS dans la console

## Notes

Cette version est adaptée depuis la version NumWorks (MicroPython) pour fonctionner sur desktop avec pygame. La logique de jeu reste identique.

