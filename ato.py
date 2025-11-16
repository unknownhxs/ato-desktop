"""
A.T.O - Jeu de type exploration avec génération procédurale de monde
"""

import sys
import subprocess
import time

# Installation automatique de pygame si nécessaire
try:
    import pygame
except ImportError:
    print("pygame n'est pas installé. Tentative d'installation...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "pygame>=2.5.0"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("Installation réussie !")
            import pygame
        else:
            print("Erreur lors de l'installation de pygame.")
            print("\nSolutions possibles :")
            print("1. Installer les dépendances système (Linux) :")
            print("   sudo apt-get install python3-pygame")
            print("   ou")
            print("   sudo dnf install python3-pygame")
            print("\n2. Installer via pip avec les dépendances :")
            print("   pip install --upgrade pip")
            print("   pip install pygame")
            print("\n3. Utiliser une version plus ancienne :")
            print("   pip install pygame==2.0.0")
            print("\nDétails de l'erreur :")
            if result.stderr:
                print(result.stderr[-500:])
            sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        print("\nVeuillez installer pygame manuellement.")
        print("Sur Linux, essayez : sudo apt-get install python3-pygame")
        print("Ou : pip install pygame")
        sys.exit(1)

# Initialisation de pygame
pygame.init()

# Configuration de l'écran
info = pygame.display.Info()
DESKTOP_W = info.current_w  # Largeur de l'écran du bureau
DESKTOP_H = info.current_h  # Hauteur de l'écran du bureau

# Constantes du jeu
SCREEN_W = 320  # Largeur de la fenêtre de jeu
SCREEN_H = 240  # Hauteur de la fenêtre de jeu
TS = 28  # Taille d'une tuile (Tile Size) - logique interne
DISPLAY_SCALE = 2  # Facteur d'échelle d'affichage (2x plus grand)
DISPLAY_TS = TS * DISPLAY_SCALE  # Taille d'affichage d'une tuile (56 pixels)
CHUNK_SIZE = 560  # Taille d'un chunk en pixels
CHUNK_TILES = CHUNK_SIZE // TS  # Nombre de tuiles par chunk
PS = 28  # Taille du joueur (Player Size)
SPD = 8  # Vitesse de déplacement du joueur (en pixels logiques)
BORDER_SIZE = 10  # Taille de la bordure
MAX_CHUNKS_LOADED = 100  # Nombre maximum de chunks chargés en mémoire
HALF_W = SCREEN_W // 2  # Moitié de la largeur (pour centrer)
HALF_H = SCREEN_H // 2  # Moitié de la hauteur (pour centrer)

# Structures de données globales
chunks_loaded = {}  # Dictionnaire des chunks chargés en mémoire
chunks_order = []  # Ordre de chargement des chunks (pour LRU)
grass_tiles = []  # Liste des images d'herbe chargées
field_38_tile = None  # Tuile spéciale FieldsTile_38.png
tree_tiles = []  # Liste des images d'arbres chargées

# Palette de couleurs RGB
COLORS = {
    'G': (60, 120, 40),      # Herbe
    'P': (222, 184, 135),    # Chemin
    'TT': (34, 139, 34),     # Feuille d'arbre
    'TR': (101, 67, 33),     # Tronc d'arbre
    'R': (178, 34, 34),      # Toit rouge
    'W': (160, 82, 45),      # Mur de maison
    'WD': (140, 70, 35),     # Mur de maison (sombre)
    'D': (101, 67, 33),      # Porte
    'DD': (70, 45, 20),      # Bordure de chemin
    'BL': (0, 0, 0),         # Noir
    'WH': (255, 255, 255),   # Blanc
    'BLUE': (0, 100, 255),   # Bleu (bordure)
    'SLIME': (50, 100, 200),      # Slime (joueur)
    'SLIME_D': (30, 60, 150),     # Slime sombre
    'SLIME_L': (100, 150, 255)    # Slime clair
}

# Types de tuiles
T_GRASS = 0   # Herbe
T_PATH = 1   # Chemin
T_TREE = 2   # Arbre
T_HOUSE = 6  # Maison
T_BORDER = 7 # Bordure

# États du jeu
GAME_STATE_MENU = 0
GAME_STATE_PLAYING = 1
GAME_STATE_PAUSED = 2
GAME_STATE_CONSOLE = 3

# Initialisation de la fenêtre
fullscreen = False
screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.RESIZABLE)
pygame.display.set_caption("A.T.O")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)

def load_grass_tiles():
    """
    Charge les images d'herbe depuis le dossier assets/fields.
    Cherche dans plusieurs emplacements possibles et redimensionne les images à la taille des tuiles.
    """
    global grass_tiles, field_38_tile
    grass_tiles = []
    field_38_tile = None
    import os
    # Chemins possibles pour trouver les assets
    base_paths = [
        "desktop/assets/fields",
        "assets/fields",
        os.path.join(os.path.dirname(__file__), "assets", "fields"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "desktop", "assets", "fields")
    ]
    for base_path in base_paths:
        if os.path.exists(base_path):
            # Charge les images FieldsTile_01.png à FieldsTile_64.png
            for i in range(1, 65):
                field_path = os.path.join(base_path, f"FieldsTile_{i:02d}.png")
                if os.path.exists(field_path):
                    try:
                        field = pygame.image.load(field_path)
                        field = pygame.transform.scale(field, (DISPLAY_TS, DISPLAY_TS))
                        # La tuile 38 est traitée séparément (plus fréquente)
                        if i == 38:
                            field_38_tile = field
                        else:
                            grass_tiles.append(field)
                    except Exception as e:
                        print(f"Erreur chargement {field_path}: {e}")
            if len(grass_tiles) > 0 or field_38_tile is not None:
                break
    print(f"Chargé {len(grass_tiles)} images de fields + field_38 depuis {base_path if 'base_path' in locals() else 'aucun chemin trouvé'}")

def load_tree_tiles():
    """
    Charge uniquement les images Tree1.png, Tree2.png, Tree3.png depuis le dossier assets/Trees.
    Cherche dans plusieurs emplacements possibles et redimensionne les images à la taille des tuiles.
    """
    global tree_tiles
    tree_tiles = []
    import os
    # Chemins possibles pour trouver les assets
    base_paths = [
        "desktop/assets/Trees",
        "assets/Trees",
        os.path.join(os.path.dirname(__file__), "assets", "Trees"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "desktop", "assets", "Trees")
    ]
    # Liste des fichiers d'arbres à charger
    tree_names = ["Tree1.png", "Tree2.png", "Tree3.png"]
    for base_path in base_paths:
        if os.path.exists(base_path):
            # Charge uniquement Tree1, Tree2, Tree3
            for tree_name in tree_names:
                tree_path = os.path.join(base_path, tree_name)
                if os.path.exists(tree_path):
                    try:
                        tree = pygame.image.load(tree_path)
                        tree = pygame.transform.scale(tree, (DISPLAY_TS, DISPLAY_TS))
                        tree_tiles.append(tree)
                    except Exception as e:
                        print(f"Erreur chargement {tree_path}: {e}")
            if len(tree_tiles) > 0:
                break
    print(f"Chargé {len(tree_tiles)} images d'arbres (Tree1-3) depuis {base_path if 'base_path' in locals() else 'aucun chemin trouvé'}")

def get_chunk_key(cx, cy):
    """
    Retourne la clé unique d'un chunk à partir de ses coordonnées.
    """
    return (cx, cy)

def get_chunk_coords(wx, wy):
    """
    Convertit des coordonnées monde en coordonnées de chunk.
    """
    return (wx // CHUNK_SIZE, wy // CHUNK_SIZE)

def get_tile_in_chunk(chunk, tx, ty):
    """
    Récupère le type de tuile à une position (tx, ty) dans un chunk.
    Retourne None si la position est invalide.
    """
    if chunk is None:
        return None
    if 0 <= tx < CHUNK_TILES and 0 <= ty < CHUNK_TILES:
        return chunk[ty * CHUNK_TILES + tx]
    return None

def get_seed(x, y, cx=0, cy=0):
    """
    Génère un seed pseudo-aléatoire déterministe basé sur les coordonnées.
    Utile pour la génération procédurale.
    
    Args:
        x, y: Coordonnées locales dans le chunk (tx, ty)
        cx, cy: Coordonnées du chunk (optionnel, pour plus de variété)
    
    Returns:
        Un entier seed déterministe
    """
    seed = (x * 73856093) ^ (y * 19349663) ^ (cx * 83492791) ^ (cy * 19283746)
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return seed

def random_chance(x, y, probability, cx=0, cy=0):
    """
    Retourne True avec une probabilité donnée, de manière déterministe.
    
    Args:
        x, y: Coordonnées locales dans le chunk
        probability: Probabilité entre 0.0 et 1.0 (ex: 0.1 = 10%)
        cx, cy: Coordonnées du chunk (optionnel)
    
    Returns:
        True si la condition est remplie, False sinon
    """
    seed = get_seed(x, y, cx, cy)
    return (seed % 10000) < int(probability * 10000)

def set_tile(chunk, tx, ty, tile_type):
    """
    Définit le type de tuile à une position dans le chunk.
    
    Args:
        chunk: Le chunk à modifier
        tx, ty: Coordonnées locales dans le chunk
        tile_type: Type de tuile à placer
    """
    if 0 <= tx < CHUNK_TILES and 0 <= ty < CHUNK_TILES:
        chunk[ty * CHUNK_TILES + tx] = tile_type

def get_tile(chunk, tx, ty):
    """
    Récupère le type de tuile à une position dans le chunk.
    
    Args:
        chunk: Le chunk à lire
        tx, ty: Coordonnées locales dans le chunk
    
    Returns:
        Le type de tuile ou None si hors limites
    """
    return get_tile_in_chunk(chunk, tx, ty)

def check_neighbors(chunk, tx, ty, tile_type):
    """
    Vérifie combien de voisins d'une tuile sont d'un type donné.
    Utile pour créer des structures cohérentes (ex: chemins, forêts).
    
    Args:
        chunk: Le chunk à vérifier
        tx, ty: Coordonnées locales dans le chunk
        tile_type: Type de tuile à chercher
    
    Returns:
        Le nombre de voisins (0-8) du type spécifié
    """
    count = 0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            nx, ny = tx + dx, ty + dy
            if get_tile(chunk, nx, ny) == tile_type:
                count += 1
    return count

def is_forest_biome(cx, cy):
    """
    Détermine si un chunk doit être un biome forêt.
    Utilise les coordonnées du chunk pour une génération déterministe.
    """
    seed = get_seed(0, 0, cx, cy)
    # 30% de chance qu'un chunk soit une forêt
    return (seed % 100) < 30

def generate_forest_biome(chunk, cx, cy):
    """
    Génère un biome forêt avec des arbres groupés de manière naturelle.
    Les arbres ont tendance à se regrouper pour créer des zones forestières.
    """
    # Première passe : place des "graines" d'arbres (points de départ)
    for ty in range(CHUNK_TILES):
        for tx in range(CHUNK_TILES):
            # 3% de chance de placer une graine d'arbre
            if random_chance(tx, ty, 0.03, cx, cy):
                set_tile(chunk, tx, ty, T_TREE)
    
    # Deuxième passe : fait pousser les arbres autour des graines
    # Plusieurs itérations pour créer des groupes plus denses
    for iteration in range(2):
        for ty in range(CHUNK_TILES):
            for tx in range(CHUNK_TILES):
                if get_tile(chunk, tx, ty) == T_GRASS:
                    neighbors = check_neighbors(chunk, tx, ty, T_TREE)
                    # Si un arbre a au moins 2 voisins arbres, il a 40% de chance de pousser
                    if neighbors >= 2:
                        if random_chance(tx, ty, 0.4, cx, cy):
                            set_tile(chunk, tx, ty, T_TREE)
                    # Si un arbre a 1 voisin, 15% de chance
                    elif neighbors == 1:
                        if random_chance(tx, ty, 0.15, cx, cy):
                            set_tile(chunk, tx, ty, T_TREE)
                    # Sinon, 2% de chance isolée
                    elif random_chance(tx, ty, 0.02, cx, cy):
                        set_tile(chunk, tx, ty, T_TREE)

def generate_chunk(cx, cy):
    """
    Génère un nouveau chunk avec génération procédurale.
    Utilise les fonctions utilitaires pour faciliter l'ajout de conditions.
    
    Fonctions disponibles :
    - random_chance(tx, ty, probabilité, cx, cy) : Teste une probabilité
    - set_tile(chunk, tx, ty, tile_type) : Place une tuile
    - get_tile(chunk, tx, ty) : Lit une tuile
    - check_neighbors(chunk, tx, ty, tile_type) : Compte les voisins d'un type
    - is_forest_biome(cx, cy) : Vérifie si le chunk est une forêt
    - generate_forest_biome(chunk, cx, cy) : Génère un biome forêt
    
    Exemples d'utilisation :
    - random_chance(tx, ty, 0.05, cx, cy) : 5% de chance
    - check_neighbors(chunk, tx, ty, T_TREE) >= 3 : Au moins 3 arbres voisins
    """
    chunk = [T_GRASS] * (CHUNK_TILES * CHUNK_TILES)
    
    # Génération de biome forêt
    if is_forest_biome(cx, cy):
        generate_forest_biome(chunk, cx, cy)
    
    # Vous pouvez ajouter d'autres biomes ici :
    # elif is_desert_biome(cx, cy):
    #     generate_desert_biome(chunk, cx, cy)
    
    return chunk

def load_chunk(cx, cy):
    """
    Charge un chunk en mémoire. Utilise un système LRU (Least Recently Used)
    pour limiter le nombre de chunks chargés.
    """
    key = get_chunk_key(cx, cy)
    if key not in chunks_loaded:
        # Si on atteint la limite, supprime le chunk le plus ancien
        if len(chunks_loaded) >= MAX_CHUNKS_LOADED:
            old_key = chunks_order.pop(0)
            del chunks_loaded[old_key]
        chunk = generate_chunk(cx, cy)
        chunks_loaded[key] = chunk
        chunks_order.append(key)
    return chunks_loaded[key]

def unload_distant_chunks(cam_x, cam_y):
    """
    Décharge les chunks trop éloignés de la caméra pour économiser la mémoire.
    """
    cam_cx = cam_x // CHUNK_SIZE
    cam_cy = cam_y // CHUNK_SIZE
    view_range = 3  # Rayon de chunks à garder chargés
    keys_to_remove = []
    for key in list(chunks_loaded.keys()):
        cx, cy = key
        if abs(cx - cam_cx) > view_range or abs(cy - cam_cy) > view_range:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del chunks_loaded[key]
        if key in chunks_order:
            chunks_order.remove(key)

def get_tile_at_world(wx, wy):
    """
    Récupère le type de tuile aux coordonnées monde (wx, wy).
    """
    cx, cy = get_chunk_coords(wx, wy)
    chunk = load_chunk(cx, cy)
    # Conversion en coordonnées locales dans le chunk
    local_x = ((wx % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE // TS
    local_y = ((wy % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE // TS
    return get_tile_in_chunk(chunk, local_x, local_y)

def draw_grass_tile(sx, sy, wx, wy):
    """
    Dessine une tuile d'herbe à l'écran.
    Utilisé pour T_GRASS et comme fond pour T_TREE.
    """
    if field_38_tile is not None or len(grass_tiles) > 0:
        tx = wx // TS
        ty = wy // TS
        # Générateur pseudo-aléatoire déterministe basé sur la position
        seed = (tx * 73856093) ^ (ty * 19349663)
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        rand = seed % 100
        # 80% de chance d'afficher la tuile 38 (plus fréquente)
        if rand < 80 and field_38_tile is not None:
            screen.blit(field_38_tile, (sx, sy))
        elif len(grass_tiles) > 0:
            grass_index = seed % len(grass_tiles)
            screen.blit(grass_tiles[grass_index], (sx, sy))
        else:
            pygame.draw.rect(screen, COLORS['G'], (sx, sy, DISPLAY_TS, DISPLAY_TS))
    else:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, DISPLAY_TS, DISPLAY_TS))

def draw_tile_screen(sx, sy, tile_type, wx=0, wy=0):
    """
    Dessine une tuile à l'écran aux coordonnées écran (sx, sy).
    Utilise un générateur pseudo-aléatoire basé sur les coordonnées monde pour la variété.
    """
    if tile_type == T_GRASS:
        # Affiche une image d'herbe aléatoire ou un rectangle coloré
        draw_grass_tile(sx, sy, wx, wy)
    elif tile_type == T_PATH:
        # Chemin avec bordure supérieure
        pygame.draw.rect(screen, COLORS['P'], (sx, sy, DISPLAY_TS, DISPLAY_TS))
        pygame.draw.rect(screen, COLORS['DD'], (sx, sy, DISPLAY_TS, 4 * DISPLAY_SCALE))
    elif tile_type == T_TREE:
        # Dessine d'abord l'herbe, puis l'arbre par-dessus (superposition)
        draw_grass_tile(sx, sy, wx, wy)
        if len(tree_tiles) > 0:
            tx = wx // TS
            ty = wy // TS
            # Générateur pseudo-aléatoire déterministe basé sur la position
            seed = (tx * 73856093) ^ (ty * 19349663)
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            tree_index = seed % len(tree_tiles)
            screen.blit(tree_tiles[tree_index], (sx, sy))
        else:
            # Fallback : dessin simple si pas d'images chargées
            pygame.draw.rect(screen, COLORS['TT'], (sx + 6 * DISPLAY_SCALE, sy, 16 * DISPLAY_SCALE, 16 * DISPLAY_SCALE))
            pygame.draw.rect(screen, COLORS['TR'], (sx + 12 * DISPLAY_SCALE, sy + 16 * DISPLAY_SCALE, 4 * DISPLAY_SCALE, 8 * DISPLAY_SCALE))
    elif tile_type == T_HOUSE:
        # Maison : murs, toit rouge et porte
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, DISPLAY_TS, DISPLAY_TS))
        pygame.draw.rect(screen, COLORS['W'], (sx + 3 * DISPLAY_SCALE, sy + 10 * DISPLAY_SCALE, 22 * DISPLAY_SCALE, 16 * DISPLAY_SCALE))
        # Planches verticales sur les murs
        for i in range(0, 22, 7):
            pygame.draw.rect(screen, COLORS['WD'], (sx + (3 + i) * DISPLAY_SCALE, sy + 10 * DISPLAY_SCALE, 2 * DISPLAY_SCALE, 16 * DISPLAY_SCALE))
        pygame.draw.rect(screen, COLORS['R'], (sx, sy + 6 * DISPLAY_SCALE, 28 * DISPLAY_SCALE, 6 * DISPLAY_SCALE))
        pygame.draw.rect(screen, COLORS['D'], (sx + 11 * DISPLAY_SCALE, sy + 20 * DISPLAY_SCALE, 6 * DISPLAY_SCALE, 6 * DISPLAY_SCALE))
    elif tile_type == T_BORDER:
        # Bordure avec motif alterné bleu/blanc
        cx, cy = get_chunk_coords(wx, wy)
        if cx == 0 or cy == 0:
            color_idx = (wx + wy) % (BORDER_SIZE * 2)
            color = COLORS['BLUE'] if color_idx < BORDER_SIZE else COLORS['WH']
            pygame.draw.rect(screen, color, (sx, sy, DISPLAY_TS, DISPLAY_TS))
        else:
            pygame.draw.rect(screen, COLORS['G'], (sx, sy, DISPLAY_TS, DISPLAY_TS))

def draw_world(cam_x, cam_y):
    """
    Dessine le monde visible autour de la caméra.
    Charge les chunks nécessaires et décharge ceux trop éloignés.
    """
    screen.fill(COLORS['BL'])
    cam_cx = cam_x // CHUNK_SIZE
    cam_cy = cam_y // CHUNK_SIZE
    # Charge les chunks dans un rayon de 2 autour de la caméra
    for cy in range(cam_cy - 2, cam_cy + 3):
        for cx in range(cam_cx - 2, cam_cx + 3):
            load_chunk(cx, cy)
    unload_distant_chunks(cam_x, cam_y)
    # Calcule la zone visible en tuiles
    start_tx = (cam_x - HALF_W) // TS - 1
    start_ty = (cam_y - HALF_H) // TS - 1
    end_tx = (cam_x + HALF_W) // TS + 2
    end_ty = (cam_y + HALF_H) // TS + 2
    # Dessine toutes les tuiles visibles
    for ty in range(start_ty, end_ty):
        wy = ty * TS
        sy = (wy - cam_y + HALF_H) * DISPLAY_SCALE
        if -DISPLAY_TS <= sy < SCREEN_H + DISPLAY_TS:
            for tx in range(start_tx, end_tx):
                wx = tx * TS
                sx = (wx - cam_x + HALF_W) * DISPLAY_SCALE
                if -DISPLAY_TS <= sx < SCREEN_W + DISPLAY_TS:
                    tile = get_tile_at_world(wx, wy)
                    if tile is not None:
                        draw_tile_screen(sx, sy, tile, wx, wy)
                    else:
                        pygame.draw.rect(screen, COLORS['BL'], (sx, sy, DISPLAY_TS, DISPLAY_TS))

def draw_player(frame=0):
    """
    Dessine le joueur (slime) au centre de l'écran avec animation de saut.
    Le paramètre frame contrôle l'animation (0-19).
    Le joueur garde sa taille initiale (28 pixels) même si les tuiles sont agrandies.
    """
    sx = HALF_W - PS // 2
    sy = HALF_H - PS // 2
    # Calcul de l'animation de saut (effet de squash/stretch)
    progress = frame / 20.0
    squash = int(3 * abs(0.5 - progress) * 2)  # Compression verticale
    wave_x = int(2 * abs(0.5 - progress))  # Déplacement horizontal de l'œil
    eye_y_offset = int(1 * abs(0.5 - progress))  # Déplacement vertical de l'œil
    # Corps principal du slime
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 4, sy + 4 + squash, 20, 16 - squash * 2))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 5, sy + 5 + squash, 18, 14 - squash * 2))
    # Reflets clairs
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 6, sy + 6 + squash, 16, 12 - squash * 2))
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 6, sy + 5 + squash, 8, 7))
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 8, sy + 6 + squash, 6, 6))
    # Œil
    pygame.draw.rect(screen, COLORS['WH'], (sx + 11 + wave_x, sy + 8 + squash + eye_y_offset, 2, 3))
    # Ombre en bas
    pygame.draw.rect(screen, COLORS['SLIME_D'], (sx + 5, sy + 18 - squash, 18, 3))
    pygame.draw.rect(screen, COLORS['SLIME_D'], (sx + 6, sy + 20 - squash, 16, 2))
    # Petites bulles sur les côtés
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 2, sy + 6 + squash, 2, 3))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 24, sy + 6 + squash, 2, 3))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 4, sy + 5 + squash, 2, 2))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 22, sy + 5 + squash, 2, 2))

def handle_input(wx, wy, keys):
    """
    Gère les entrées clavier pour déplacer le joueur.
    Retourne les nouvelles coordonnées monde et un booléen indiquant si le joueur a bougé.
    """
    nwx, nwy, m = wx, wy, False
    # Déplacement vertical
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        nwy -= SPD
        m = True
    elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
        nwy += SPD
        m = True
    # Déplacement horizontal
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        nwx -= SPD
        m = True
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        nwx += SPD
        m = True
    return nwx, nwy, m

def draw_fps(fps):
    """
    Affiche le nombre de FPS dans le coin supérieur droit.
    """
    fps_text = font.render(f"FPS: {fps}", True, COLORS['WH'])
    text_rect = fps_text.get_rect(topright=(SCREEN_W - 5, 5))
    # Fond noir pour la lisibilité
    pygame.draw.rect(screen, COLORS['BL'], (text_rect.x - 2, text_rect.y - 2, text_rect.width + 4, text_rect.height + 4))
    screen.blit(fps_text, text_rect)

def draw_menu():
    """
    Dessine l'écran de menu principal.
    """
    screen.fill(COLORS['BL'])
    title = font.render("A.T.O", True, COLORS['WH'])
    title_rect = title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 40))
    screen.blit(title, title_rect)
    start_text = font.render("Appuyez sur ESPACE pour commencer", True, COLORS['WH'])
    start_rect = start_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 20))
    screen.blit(start_text, start_rect)
    controls_text = font.render("Fleches/WASD: Deplacer | ESC: Pause", True, COLORS['WH'])
    controls_rect = controls_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 50))
    screen.blit(controls_text, controls_rect)

def draw_pause_menu():
    """
    Dessine le menu de pause avec un overlay semi-transparent.
    """
    overlay = pygame.Surface((SCREEN_W, SCREEN_H))
    overlay.set_alpha(128)
    overlay.fill(COLORS['BL'])
    screen.blit(overlay, (0, 0))
    pause_text = font.render("PAUSE", True, COLORS['WH'])
    pause_rect = pause_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30))
    screen.blit(pause_text, pause_rect)
    resume_text = font.render("Appuyez sur ESC pour reprendre", True, COLORS['WH'])
    resume_rect = resume_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 10))
    screen.blit(resume_text, resume_rect)
    quit_text = font.render("Appuyez sur Q pour quitter", True, COLORS['WH'])
    quit_rect = quit_text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 40))
    screen.blit(quit_text, quit_rect)

def set_game_variable(var_name, value_str, anim_speed_ref=None):
    """
    Modifie une variable du jeu.
    Retourne un message de succès ou d'erreur.
    anim_speed_ref est une référence à la variable anim_speed locale.
    """
    global SCREEN_W, SCREEN_H, HALF_W, HALF_H, TS, DISPLAY_SCALE, DISPLAY_TS
    global CHUNK_SIZE, CHUNK_TILES, PS, SPD, BORDER_SIZE, MAX_CHUNKS_LOADED
    
    # Dictionnaire des variables modifiables
    variables = {
        'SCREEN_W': SCREEN_W,
        'SCREEN_H': SCREEN_H,
        'TS': TS,
        'DISPLAY_SCALE': DISPLAY_SCALE,
        'CHUNK_SIZE': CHUNK_SIZE,
        'PS': PS,
        'SPD': SPD,
        'BORDER_SIZE': BORDER_SIZE,
        'MAX_CHUNKS_LOADED': MAX_CHUNKS_LOADED,
    }
    if anim_speed_ref is not None:
        variables['anim_speed'] = anim_speed_ref[0]
    
    if var_name not in variables:
        return f"Erreur: Variable '{var_name}' introuvable"
    
    # Conversion de la valeur
    try:
        if '.' in value_str:
            value = float(value_str)
        else:
            value = int(value_str)
    except ValueError:
        return f"Erreur: '{value_str}' n'est pas un nombre valide"
    
    # Modification de la variable
    if var_name == 'SCREEN_W':
        SCREEN_W = int(value)
        HALF_W = SCREEN_W // 2
    elif var_name == 'SCREEN_H':
        SCREEN_H = int(value)
        HALF_H = SCREEN_H // 2
    elif var_name == 'TS':
        TS = int(value)
        DISPLAY_TS = TS * DISPLAY_SCALE
        CHUNK_TILES = CHUNK_SIZE // TS
    elif var_name == 'DISPLAY_SCALE':
        DISPLAY_SCALE = int(value)
        DISPLAY_TS = TS * DISPLAY_SCALE
    elif var_name == 'CHUNK_SIZE':
        CHUNK_SIZE = int(value)
        CHUNK_TILES = CHUNK_SIZE // TS
    elif var_name == 'PS':
        PS = int(value)
    elif var_name == 'SPD':
        SPD = int(value)
    elif var_name == 'BORDER_SIZE':
        BORDER_SIZE = int(value)
    elif var_name == 'MAX_CHUNKS_LOADED':
        MAX_CHUNKS_LOADED = int(value)
    elif var_name == 'anim_speed':
        if anim_speed_ref is not None:
            anim_speed_ref[0] = float(value)
            return f"Variable '{var_name}' modifiée: {variables[var_name]} -> {value}"
        else:
            return f"Erreur: Variable '{var_name}' ne peut pas être modifiée"
    
    return f"Variable '{var_name}' modifiée: {variables[var_name]} -> {value}"

def get_variables_list(anim_speed_ref=None):
    """
    Retourne la liste des variables avec leurs valeurs actuelles.
    """
    global SCREEN_W, SCREEN_H, TS, DISPLAY_SCALE, DISPLAY_TS
    global CHUNK_SIZE, CHUNK_TILES, PS, SPD, BORDER_SIZE, MAX_CHUNKS_LOADED
    
    anim_speed_val = anim_speed_ref[0] if anim_speed_ref is not None else "N/A"
    
    return (f"Variables actuelles:\n"
            f"  SCREEN_W = {SCREEN_W}\n"
            f"  SCREEN_H = {SCREEN_H}\n"
            f"  TS = {TS}\n"
            f"  DISPLAY_SCALE = {DISPLAY_SCALE}\n"
            f"  DISPLAY_TS = {DISPLAY_TS}\n"
            f"  CHUNK_SIZE = {CHUNK_SIZE}\n"
            f"  CHUNK_TILES = {CHUNK_TILES}\n"
            f"  PS = {PS}\n"
            f"  SPD = {SPD}\n"
            f"  BORDER_SIZE = {BORDER_SIZE}\n"
            f"  MAX_CHUNKS_LOADED = {MAX_CHUNKS_LOADED}\n"
            f"  anim_speed = {anim_speed_val}")

def execute_command(command, console_history, anim_speed_ref=None):
    """
    Exécute une commande de la console.
    Retourne un message de résultat.
    anim_speed_ref est une référence à la variable anim_speed locale.
    """
    command = command.strip()
    if not command:
        return ""
    
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == "var":
        if len(parts) >= 2 and parts[1] == "-h":
            # Afficher l'aide pour var
            return "Variables modifiables:\n  SCREEN_W - Largeur de l'écran\n  SCREEN_H - Hauteur de l'écran\n  TS - Taille des tuiles\n  DISPLAY_SCALE - Facteur d'échelle (2x, 3x, etc.)\n  CHUNK_SIZE - Taille des chunks\n  PS - Taille du joueur\n  SPD - Vitesse de déplacement\n  BORDER_SIZE - Taille de la bordure\n  MAX_CHUNKS_LOADED - Nombre max de chunks\n  anim_speed - Vitesse d'animation\n\nUsage: var [nom_variable] [valeur]\nExemple: var SPD 10"
        elif len(parts) >= 2 and parts[1].lower() == "list":
            # Afficher la liste des variables avec leurs valeurs
            return get_variables_list(anim_speed_ref)
        elif len(parts) >= 3:
            var_name = parts[1]
            value = parts[2]
            return set_game_variable(var_name, value, anim_speed_ref)
        else:
            return "Usage: var [nom_variable] [valeur]\nTapez 'var -h' pour voir la liste des variables\nTapez 'var list' pour voir les valeurs actuelles"
    elif cmd == "help":
        return "Commandes disponibles:\n  var [nom] [valeur] - Modifie une variable\n  help - Affiche cette aide\n  clear - Efface l'historique"
    elif cmd == "clear":
        console_history.clear()
        return "Historique effacé"
    else:
        return f"Commande inconnue: '{cmd}'. Tapez 'help' pour l'aide"

def draw_console(console_text, console_history):
    """
    Dessine la console de commandes.
    """
    # Overlay semi-transparent
    overlay = pygame.Surface((SCREEN_W, SCREEN_H))
    overlay.set_alpha(200)
    overlay.fill(COLORS['BL'])
    screen.blit(overlay, (0, 0))
    
    # Titre
    title = font.render("CONSOLE DE COMMANDES (ESC pour fermer)", True, COLORS['WH'])
    screen.blit(title, (10, 10))
    
    # Historique des commandes (dernières 15 lignes)
    y_offset = 40
    line_count = 0
    max_lines = 15
    for line in reversed(console_history[-max_lines:]):
        if line_count >= max_lines:
            break
        if line.startswith("Erreur:"):
            color = (255, 100, 100)  # Rouge pour les erreurs
        elif line.startswith("Variable") or line.startswith("Historique"):
            color = (100, 255, 100)  # Vert pour les succès
        else:
            color = COLORS['WH']
        # Limiter la longueur de la ligne pour éviter le débordement
        display_line = line[:50] if len(line) > 50 else line
        text = font.render(display_line, True, color)
        screen.blit(text, (10, SCREEN_H - 50 - (line_count * 20)))
        line_count += 1
    
    # Ligne de commande actuelle
    prompt_text = "> " + console_text + "_"
    if len(prompt_text) > 50:
        prompt_text = prompt_text[-50:]
    prompt = font.render(prompt_text, True, COLORS['WH'])
    screen.blit(prompt, (10, SCREEN_H - 30))

def game_engine():
    """
    Boucle principale du jeu. Gère les états (menu, jeu, pause), les entrées,
    l'animation et le rendu.
    """
    global screen, fullscreen, SCREEN_W, SCREEN_H, HALF_W, HALF_H
    load_grass_tiles()
    load_tree_tiles()
    game_state = GAME_STATE_MENU
    world_x = 0  # Position X du joueur dans le monde
    world_y = 0  # Position Y du joueur dans le monde
    anim_frame = 0  # Frame actuelle de l'animation du joueur
    anim_timer = time.time()  # Timer pour l'animation
    anim_speed = 0.05  # Vitesse de l'animation (secondes par frame)
    running = True
    needs_redraw = True  # Indique si un redessin est nécessaire
    # Variables pour la console
    console_text = ""
    console_history = []
    previous_state = GAME_STATE_PLAYING  # État avant d'ouvrir la console
    draw_menu()
    pygame.display.flip()
    
    while running:
        
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                # Basculer en plein écran
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.RESIZABLE)
                    SCREEN_W = DESKTOP_W
                    SCREEN_H = DESKTOP_H
                    HALF_W = SCREEN_W // 2
                    HALF_H = SCREEN_H // 2
                    needs_redraw = True
                # Gestion de la pause et fermeture de la console
                elif event.key == pygame.K_ESCAPE:
                    if game_state == GAME_STATE_CONSOLE:
                        # Fermer la console avec ESC
                        game_state = previous_state
                        console_text = ""
                        needs_redraw = True
                    elif game_state == GAME_STATE_PLAYING:
                        game_state = GAME_STATE_PAUSED
                        needs_redraw = True
                    elif game_state == GAME_STATE_PAUSED:
                        game_state = GAME_STATE_PLAYING
                        needs_redraw = True
                # Démarrer le jeu depuis le menu
                elif event.key == pygame.K_SPACE:
                    if game_state == GAME_STATE_MENU:
                        game_state = GAME_STATE_PLAYING
                        needs_redraw = True
                # Quitter depuis le menu pause
                elif event.key == pygame.K_q:
                    if game_state == GAME_STATE_PAUSED:
                        running = False
                # Ouvrir la console avec T
                elif event.key == pygame.K_t:
                    if game_state == GAME_STATE_PLAYING or game_state == GAME_STATE_PAUSED:
                        previous_state = game_state
                        game_state = GAME_STATE_CONSOLE
                        console_text = ""
                        needs_redraw = True
                # Gestion de la console
                elif game_state == GAME_STATE_CONSOLE:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        # Exécuter la commande
                        if console_text.strip():
                            console_history.append("> " + console_text)
                            # Passer une référence à anim_speed pour pouvoir la modifier
                            anim_speed_ref = [anim_speed]
                            result = execute_command(console_text, console_history, anim_speed_ref)
                            anim_speed = anim_speed_ref[0]  # Récupérer la valeur modifiée
                            if result:
                                # Gérer les retours à la ligne dans le résultat
                                for line in result.split('\n'):
                                    console_history.append(line)
                        console_text = ""
                        needs_redraw = True
                    elif event.key == pygame.K_BACKSPACE:
                        # Backspace
                        console_text = console_text[:-1]
                        needs_redraw = True
            # Gestion de la saisie de texte dans la console
            elif event.type == pygame.TEXTINPUT and game_state == GAME_STATE_CONSOLE:
                console_text += event.text
                needs_redraw = True
            # Gestion du redimensionnement de la fenêtre
            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    SCREEN_W = event.w
                    SCREEN_H = event.h
                    HALF_W = SCREEN_W // 2
                    HALF_H = SCREEN_H // 2
                    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
                    needs_redraw = True
        
        # Gestion des différents états du jeu
        if game_state == GAME_STATE_MENU:
            if needs_redraw:
                draw_menu()
                pygame.display.flip()
                needs_redraw = False
        elif game_state == GAME_STATE_PAUSED:
            if needs_redraw:
                draw_world(world_x, world_y)
                draw_player(anim_frame)
                draw_pause_menu()
                pygame.display.flip()
                needs_redraw = False
        elif game_state == GAME_STATE_CONSOLE:
            # Afficher la console
            if needs_redraw:
                draw_world(world_x, world_y)
                draw_player(anim_frame)
                draw_console(console_text, console_history)
                pygame.display.flip()
                needs_redraw = False
        elif game_state == GAME_STATE_PLAYING:
            # Gestion des entrées et du déplacement
            keys = pygame.key.get_pressed()
            nwx, nwy, moved = handle_input(world_x, world_y, keys)
            
            if moved:
                world_x, world_y = nwx, nwy
                needs_redraw = True
            
            # Animation du joueur
            current_anim_time = time.time()
            if current_anim_time - anim_timer >= anim_speed:
                anim_frame = (anim_frame + 1) % 20
                anim_timer = current_anim_time
                needs_redraw = True
            
            # Rendu
            if needs_redraw:
                draw_world(world_x, world_y)
                draw_player(anim_frame)
                # Récupère les FPS directement depuis clock
                fps = int(clock.get_fps())
                draw_fps(fps)
                pygame.display.flip()
                needs_redraw = False
        
        clock.tick(50)  # Limite à 50 FPS
    
    pygame.quit()

if __name__ == "__main__":
    game_engine()

