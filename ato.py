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
TS = 28  # Taille d'une tuile (Tile Size)
CHUNK_SIZE = 560  # Taille d'un chunk en pixels
CHUNK_TILES = CHUNK_SIZE // TS  # Nombre de tuiles par chunk
PS = 28  # Taille du joueur (Player Size)
SPD = 8  # Vitesse de déplacement du joueur
BORDER_SIZE = 10  # Taille de la bordure
MAX_CHUNKS_LOADED = 100  # Nombre maximum de chunks chargés en mémoire
HALF_W = SCREEN_W // 2  # Moitié de la largeur (pour centrer)
HALF_H = SCREEN_H // 2  # Moitié de la hauteur (pour centrer)

# Structures de données globales
chunks_loaded = {}  # Dictionnaire des chunks chargés en mémoire
chunks_order = []  # Ordre de chargement des chunks (pour LRU)
grass_tiles = []  # Liste des images d'herbe chargées
field_38_tile = None  # Tuile spéciale FieldsTile_38.png

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
                        field = pygame.transform.scale(field, (TS, TS))
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

def generate_chunk(cx, cy):
    """
    Génère un nouveau chunk avec génération procédurale.
    Utilise les fonctions utilitaires pour faciliter l'ajout de conditions.
    
    Fonctions disponibles :
    - random_chance(tx, ty, probabilité, cx, cy) : Teste une probabilité
    - set_tile(chunk, tx, ty, tile_type) : Place une tuile
    - get_tile(chunk, tx, ty) : Lit une tuile
    - check_neighbors(chunk, tx, ty, tile_type) : Compte les voisins d'un type
    
    Exemples d'utilisation :
    - random_chance(tx, ty, 0.05, cx, cy) : 5% de chance
    - check_neighbors(chunk, tx, ty, T_TREE) >= 3 : Au moins 3 arbres voisins
    """
    chunk = [T_GRASS] * (CHUNK_TILES * CHUNK_TILES)
    
    # Exemples d'utilisation (décommentez et modifiez selon vos besoins) :
    #
    # # Exemple 1 : Arbres aléatoires
    # for ty in range(CHUNK_TILES):
    #     for tx in range(CHUNK_TILES):
    #         if random_chance(tx, ty, 0.05, cx, cy):
    #             set_tile(chunk, tx, ty, T_TREE)
    #
    # # Exemple 2 : Forêts (arbres groupés)
    # for ty in range(CHUNK_TILES):
    #     for tx in range(CHUNK_TILES):
    #         neighbors = check_neighbors(chunk, tx, ty, T_TREE)
    #         if random_chance(tx, ty, 0.02, cx, cy) or neighbors >= 2:
    #             set_tile(chunk, tx, ty, T_TREE)
    #
    # # Exemple 3 : Chemins conditionnels
    # for ty in range(CHUNK_TILES):
    #     for tx in range(CHUNK_TILES):
    #         if random_chance(tx, ty, 0.01, cx, cy) and check_neighbors(chunk, tx, ty, T_PATH) == 0:
    #             set_tile(chunk, tx, ty, T_PATH)
    
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

def draw_tile_screen(sx, sy, tile_type, wx=0, wy=0):
    """
    Dessine une tuile à l'écran aux coordonnées écran (sx, sy).
    Utilise un générateur pseudo-aléatoire basé sur les coordonnées monde pour la variété.
    """
    if tile_type == T_GRASS:
        # Affiche une image d'herbe aléatoire ou un rectangle coloré
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
                pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        else:
            pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
    elif tile_type == T_PATH:
        # Chemin avec bordure supérieure
        pygame.draw.rect(screen, COLORS['P'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['DD'], (sx, sy, TS, 4))
    elif tile_type == T_TREE:
        # Arbre : feuillage vert et tronc marron
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['TT'], (sx + 6, sy, 16, 16))
        pygame.draw.rect(screen, COLORS['TR'], (sx + 12, sy + 16, 4, 8))
    elif tile_type == T_HOUSE:
        # Maison : murs, toit rouge et porte
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['W'], (sx + 3, sy + 10, 22, 16))
        # Planches verticales sur les murs
        for i in range(0, 22, 7):
            pygame.draw.rect(screen, COLORS['WD'], (sx + 3 + i, sy + 10, 2, 16))
        pygame.draw.rect(screen, COLORS['R'], (sx, sy + 6, 28, 6))
        pygame.draw.rect(screen, COLORS['D'], (sx + 11, sy + 20, 6, 6))
    elif tile_type == T_BORDER:
        # Bordure avec motif alterné bleu/blanc
        cx, cy = get_chunk_coords(wx, wy)
        if cx == 0 or cy == 0:
            color_idx = (wx + wy) % (BORDER_SIZE * 2)
            color = COLORS['BLUE'] if color_idx < BORDER_SIZE else COLORS['WH']
            pygame.draw.rect(screen, color, (sx, sy, TS, TS))
        else:
            pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))

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
        sy = wy - cam_y + HALF_H
        if -TS <= sy < SCREEN_H + TS:
            for tx in range(start_tx, end_tx):
                wx = tx * TS
                sx = wx - cam_x + HALF_W
                if -TS <= sx < SCREEN_W + TS:
                    tile = get_tile_at_world(wx, wy)
                    if tile is not None:
                        draw_tile_screen(sx, sy, tile, wx, wy)
                    else:
                        pygame.draw.rect(screen, COLORS['BL'], (sx, sy, TS, TS))

def draw_player(frame=0):
    """
    Dessine le joueur (slime) au centre de l'écran avec animation de saut.
    Le paramètre frame contrôle l'animation (0-19).
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

def game_engine():
    """
    Boucle principale du jeu. Gère les états (menu, jeu, pause), les entrées,
    l'animation et le rendu.
    """
    global screen, fullscreen, SCREEN_W, SCREEN_H, HALF_W, HALF_H
    load_grass_tiles()
    game_state = GAME_STATE_MENU
    world_x = 0  # Position X du joueur dans le monde
    world_y = 0  # Position Y du joueur dans le monde
    anim_frame = 0  # Frame actuelle de l'animation du joueur
    anim_timer = time.time()  # Timer pour l'animation
    anim_speed = 0.05  # Vitesse de l'animation (secondes par frame)
    running = True
    needs_redraw = True  # Indique si un redessin est nécessaire
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
                # Gestion de la pause
                elif event.key == pygame.K_ESCAPE:
                    if game_state == GAME_STATE_PLAYING:
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

