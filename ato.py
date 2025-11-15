import sys
import subprocess
import time

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

pygame.init()

info = pygame.display.Info()
DESKTOP_W = info.current_w
DESKTOP_H = info.current_h

SCREEN_W = 320
SCREEN_H = 240
TS = 28
CHUNK_SIZE = 560
CHUNK_TILES = CHUNK_SIZE // TS
W = SCREEN_W // TS
H = SCREEN_H // TS
PS = 28
SPD = 8
BORDER_SIZE = 10
MAX_CHUNKS_LOADED = 100
HALF_W = SCREEN_W // 2
HALF_H = SCREEN_H // 2

chunks_loaded = {}
chunks_order = []
smoke_particles = []
grass_tiles = []
field_38_tile = None

P = {
    'G': (60, 120, 40), 'GL': (100, 180, 70), 'GD': (40, 90, 30),
    'P': (222, 184, 135), 'TT': (34, 139, 34), 'TR': (101, 67, 33),
    'R': (178, 34, 34), 'RD': (139, 0, 0), 'RL': (220, 50, 50),
    'W': (160, 82, 45), 'WL': (180, 100, 60), 'WD': (140, 70, 35),
    'D': (101, 67, 33), 'DD': (70, 45, 20), 'WIN': (135, 206, 250),
    'WID': (70, 130, 180), 'C': (80, 80, 80), 'CD': (50, 50, 50),
    'F': (138, 43, 226), 'ROCK': (105, 105, 105), 'ROD': (64, 64, 64),
    'B': (0, 100, 0), 'BL': (0, 0, 0), 'WH': (255, 255, 255),
    'BR': (139, 69, 19),
    'BLUE': (0, 100, 255),
    'SLIME': (50, 100, 200),
    'SLIME_D': (30, 60, 150),
    'SLIME_L': (100, 150, 255)
}

T_GRASS, T_PATH, T_TREE, T_ROCK, T_BUSH, T_FLOWER, T_HOUSE, T_BORDER = 0, 1, 2, 3, 4, 5, 6, 7

GAME_STATE_MENU = 0
GAME_STATE_PLAYING = 1
GAME_STATE_PAUSED = 2

COLORS = P.copy()

fullscreen = False
screen = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.RESIZABLE)
pygame.display.set_caption("A.T.O")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)

def load_grass_tiles():
    global grass_tiles, field_38_tile
    grass_tiles = []
    field_38_tile = None
    import os
    base_paths = [
        "desktop/assets/fields",
        "assets/fields",
        os.path.join(os.path.dirname(__file__), "assets", "fields"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "desktop", "assets", "fields")
    ]
    for base_path in base_paths:
        if os.path.exists(base_path):
            for i in range(1, 65):
                field_path = os.path.join(base_path, f"FieldsTile_{i:02d}.png")
                if os.path.exists(field_path):
                    try:
                        field = pygame.image.load(field_path)
                        field = pygame.transform.scale(field, (TS, TS))
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
    return (cx, cy)

def get_chunk_coords(wx, wy):
    return (wx // CHUNK_SIZE, wy // CHUNK_SIZE)

def get_tile_in_chunk(chunk, tx, ty):
    if chunk is None:
        return None
    if 0 <= tx < CHUNK_TILES and 0 <= ty < CHUNK_TILES:
        return chunk[ty * CHUNK_TILES + tx]
    return None

def is_village_chunk(cx, cy):
    seed = (cx * 73856093) ^ (cy * 19349663)
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return (seed % 50) == 0

def generate_village(chunk, cx, cy):
    import math
    village_seed = (cx * 73856093) ^ (cy * 19349663)
    village_seed = (village_seed * 1103515245 + 12345) & 0x7FFFFFFF
    center_x = CHUNK_TILES // 2
    center_y = CHUNK_TILES // 2
    num_houses = 3 + (village_seed % 3)
    for h in range(num_houses):
        angle = (h / num_houses) * 6.28318
        dist = 3 + (village_seed % 3)
        hx = int(center_x + math.cos(angle) * dist)
        hy = int(center_y + math.sin(angle) * dist)
        if 0 <= hx < CHUNK_TILES and 0 <= hy < CHUNK_TILES:
            chunk[hy * CHUNK_TILES + hx] = T_HOUSE
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    px = hx + dx
                    py = hy + dy
                    if 0 <= px < CHUNK_TILES and 0 <= py < CHUNK_TILES:
                        if chunk[py * CHUNK_TILES + px] == T_GRASS:
                            chunk[py * CHUNK_TILES + px] = T_PATH
    for ty in range(CHUNK_TILES):
        for tx in range(CHUNK_TILES):
            if chunk[ty * CHUNK_TILES + tx] == T_GRASS:
                dist_to_center = math.sqrt((tx - center_x)**2 + (ty - center_y)**2)
                if dist_to_center < 5 and (tx - center_x) % 2 == 0 and (ty - center_y) % 2 == 0:
                    if chunk[ty * CHUNK_TILES + tx] == T_GRASS:
                        chunk[ty * CHUNK_TILES + tx] = T_PATH

def generate_chunk(cx, cy):
    chunk = [T_GRASS] * (CHUNK_TILES * CHUNK_TILES)
    return chunk

def load_chunk(cx, cy):
    key = get_chunk_key(cx, cy)
    if key not in chunks_loaded:
        if len(chunks_loaded) >= MAX_CHUNKS_LOADED:
            old_key = chunks_order.pop(0)
            del chunks_loaded[old_key]
        chunk = generate_chunk(cx, cy)
        chunks_loaded[key] = chunk
        chunks_order.append(key)
    return chunks_loaded[key]

def unload_distant_chunks(cam_x, cam_y):
    cam_cx = cam_x // CHUNK_SIZE
    cam_cy = cam_y // CHUNK_SIZE
    view_range = 3
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
    cx, cy = get_chunk_coords(wx, wy)
    chunk = load_chunk(cx, cy)
    local_x = ((wx % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE // TS
    local_y = ((wy % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE // TS
    return get_tile_in_chunk(chunk, local_x, local_y)

def draw_tile_screen(sx, sy, tile_type, wx=0, wy=0):
    if tile_type == T_GRASS:
        if field_38_tile is not None or len(grass_tiles) > 0:
            tx = wx // TS
            ty = wy // TS
            seed = (tx * 73856093) ^ (ty * 19349663)
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            rand = seed % 100
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
        pygame.draw.rect(screen, COLORS['P'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['DD'], (sx, sy, TS, 4))
    elif tile_type == T_TREE:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['TT'], (sx + 6, sy, 16, 16))
        pygame.draw.rect(screen, COLORS['TR'], (sx + 12, sy + 16, 4, 8))
    elif tile_type == T_ROCK:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['ROCK'], (sx + 6, sy + 6, 16, 12))
        pygame.draw.rect(screen, COLORS['ROD'], (sx + 16, sy + 10, 4, 6))
    elif tile_type == T_BUSH:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['B'], (sx + 5, sy + 8, 18, 12))
        pygame.draw.rect(screen, COLORS['B'], (sx + 3, sy + 10, 22, 10))
    elif tile_type == T_FLOWER:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['F'], (sx + 11, sy + 11, 6, 6))
    elif tile_type == T_HOUSE:
        pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))
        pygame.draw.rect(screen, COLORS['W'], (sx + 3, sy + 10, 22, 16))
        for i in range(0, 22, 7):
            pygame.draw.rect(screen, COLORS['WD'], (sx + 3 + i, sy + 10, 2, 16))
        pygame.draw.rect(screen, COLORS['R'], (sx, sy + 6, 28, 6))
        pygame.draw.rect(screen, COLORS['D'], (sx + 11, sy + 20, 6, 6))
    elif tile_type == T_BORDER:
        cx, cy = get_chunk_coords(wx, wy)
        if cx == 0 or cy == 0:
            color_idx = (wx + wy) % (BORDER_SIZE * 2)
            color = COLORS['BLUE'] if color_idx < BORDER_SIZE else COLORS['WH']
            pygame.draw.rect(screen, color, (sx, sy, TS, TS))
        else:
            pygame.draw.rect(screen, COLORS['G'], (sx, sy, TS, TS))

def draw_world(cam_x, cam_y):
    screen.fill(COLORS['BL'])
    cam_cx = cam_x // CHUNK_SIZE
    cam_cy = cam_y // CHUNK_SIZE
    for cy in range(cam_cy - 2, cam_cy + 3):
        for cx in range(cam_cx - 2, cam_cx + 3):
            load_chunk(cx, cy)
    unload_distant_chunks(cam_x, cam_y)
    start_tx = (cam_x - HALF_W) // TS - 1
    start_ty = (cam_y - HALF_H) // TS - 1
    end_tx = (cam_x + HALF_W) // TS + 2
    end_ty = (cam_y + HALF_H) // TS + 2
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
    sx = HALF_W - PS // 2
    sy = HALF_H - PS // 2
    progress = frame / 20.0
    squash = int(3 * abs(0.5 - progress) * 2)
    wave_x = int(2 * abs(0.5 - progress))
    eye_y_offset = int(1 * abs(0.5 - progress))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 4, sy + 4 + squash, 20, 16 - squash * 2))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 5, sy + 5 + squash, 18, 14 - squash * 2))
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 6, sy + 6 + squash, 16, 12 - squash * 2))
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 6, sy + 5 + squash, 8, 7))
    pygame.draw.rect(screen, COLORS['SLIME_L'], (sx + 8, sy + 6 + squash, 6, 6))
    pygame.draw.rect(screen, COLORS['WH'], (sx + 11 + wave_x, sy + 8 + squash + eye_y_offset, 2, 3))
    pygame.draw.rect(screen, COLORS['SLIME_D'], (sx + 5, sy + 18 - squash, 18, 3))
    pygame.draw.rect(screen, COLORS['SLIME_D'], (sx + 6, sy + 20 - squash, 16, 2))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 2, sy + 6 + squash, 2, 3))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 24, sy + 6 + squash, 2, 3))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 4, sy + 5 + squash, 2, 2))
    pygame.draw.rect(screen, COLORS['SLIME'], (sx + 22, sy + 5 + squash, 2, 2))

def handle_input(wx, wy, keys):
    nwx, nwy, m = wx, wy, False
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        nwy -= SPD
        m = True
    elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
        nwy += SPD
        m = True
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        nwx -= SPD
        m = True
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        nwx += SPD
        m = True
    return nwx, nwy, m

def loading_screen():
    screen.fill(COLORS['BL'])
    text = font.render("Chargement...", True, COLORS['WH'])
    text_rect = text.get_rect(center=(HALF_W, HALF_H - 10))
    screen.blit(text, text_rect)
    pygame.display.flip()
    for i in range(3):
        pygame.draw.rect(screen, COLORS['BLUE'], (HALF_W - 30 + i * 20, HALF_H + 10, 15, 15))
        pygame.display.flip()
        time.sleep(0.1)
    time.sleep(0.2)

def create_smoke(x, y):
    if len(smoke_particles) >= 4:
        return
    import math
    target_x = x + 8
    target_y = y + 36
    for i in range(4):
        if len(smoke_particles) >= 4:
            break
        start_x = x - 1 + (i - 1.5) * 2
        start_y = y + 28 - 1
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.sqrt(dx * dx + dy * dy)
        max_dist = 4.0
        speed = max_dist / 60.0
        if dist > 0:
            smoke_particles.append({
                'x': start_x,
                'y': start_y,
                'target_x': target_x,
                'target_y': target_y,
                'vx': (dx / dist) * speed,
                'vy': (dy / dist) * speed,
                'life': 1.0
            })

def update_smoke(dt):
    global smoke_particles
    new_particles = []
    for p in smoke_particles:
        p['x'] += p['vx'] * dt * 60
        p['y'] += p['vy'] * dt * 60
        p['life'] -= dt * 2.0
        p['vx'] *= 0.9
        p['vy'] *= 0.9
        if p['life'] > 0:
            new_particles.append(p)
    smoke_particles = new_particles

def draw_smoke():
    for p in smoke_particles:
        if p['life'] > 0:
            brown = int(139 * p['life'])
            color = (brown, brown // 2, brown // 3)
            x = int(p['x'])
            y = int(p['y'])
            pygame.draw.rect(screen, color, (x, y, 2, 2))

def draw_fps(fps):
    fps_text = font.render(f"FPS: {fps}", True, COLORS['WH'])
    text_rect = fps_text.get_rect(topright=(SCREEN_W - 5, 5))
    pygame.draw.rect(screen, COLORS['BL'], (text_rect.x - 2, text_rect.y - 2, text_rect.width + 4, text_rect.height + 4))
    screen.blit(fps_text, text_rect)

def draw_menu():
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
    global screen, fullscreen, SCREEN_W, SCREEN_H, HALF_W, HALF_H
    load_grass_tiles()
    game_state = GAME_STATE_MENU
    world_x = 0
    world_y = 0
    anim_frame = 0
    last_frame = -1
    fps_counter = 0
    fps = 0
    fps_timer = time.time()
    anim_timer = time.time()
    anim_speed = 0.05
    last_time = time.time()
    running = True
    needs_redraw = True
    draw_menu()
    pygame.display.flip()
    
    while running:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
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
                elif event.key == pygame.K_ESCAPE:
                    if game_state == GAME_STATE_PLAYING:
                        game_state = GAME_STATE_PAUSED
                        needs_redraw = True
                    elif game_state == GAME_STATE_PAUSED:
                        game_state = GAME_STATE_PLAYING
                        needs_redraw = True
                elif event.key == pygame.K_SPACE:
                    if game_state == GAME_STATE_MENU:
                        game_state = GAME_STATE_PLAYING
                        needs_redraw = True
                elif event.key == pygame.K_q:
                    if game_state == GAME_STATE_PAUSED:
                        running = False
            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    SCREEN_W = event.w
                    SCREEN_H = event.h
                    HALF_W = SCREEN_W // 2
                    HALF_H = SCREEN_H // 2
                    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
                    needs_redraw = True
        
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
            keys = pygame.key.get_pressed()
            nwx, nwy, moved = handle_input(world_x, world_y, keys)
            
            if moved:
                world_x, world_y = nwx, nwy
                needs_redraw = True
            
            current_anim_time = time.time()
            if current_anim_time - anim_timer >= anim_speed:
                anim_frame = (anim_frame + 1) % 20
                anim_timer = current_anim_time
                needs_redraw = True
            
            if needs_redraw:
                draw_world(world_x, world_y)
                draw_player(anim_frame)
                draw_fps(fps)
                pygame.display.flip()
                needs_redraw = False
            
            fps_counter += 1
            if current_time - fps_timer >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_timer = current_time
                needs_redraw = True
        
        clock.tick(50)
    
    pygame.quit()

if __name__ == "__main__":
    game_engine()

