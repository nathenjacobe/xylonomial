import pygame
import math
import numpy as np
from random import randint, random, seed as random_seed
import sys

pygame.init()
pygame.font.init()

WINDOW_HEIGHT: int = 800
WINDOW_WIDTH: int = 1000
TILE_DIMENSION: int = 2
HEIGHT_TILES: int = 80
WIDTH_TILES: int = 100
BORDER_THICKNESS: int = 1 
WIND_VECTOR = [1, 0]
SEED_PROBABILITY = 0.1
GROWTH_PROBABILITY = 0.05
GERMINATION_AGE = 15
UPDATE_FREQUENCY = 0.2
YEARS_PER_UPDATE = 1
MAST_FREQUENCY_MIN = 3
MAST_FREQUENCY_MAX = 7
MAST_YEAR_MULTIPLIER = 5

window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("FOREST ECOSYSTEM SIMULATION")
clock = pygame.time.Clock()

font = pygame.font.SysFont('Arial', 24)
small_font = pygame.font.SysFont('Arial', 16)

sq_width: int = WINDOW_WIDTH / WIDTH_TILES
sq_height: int = WINDOW_HEIGHT / HEIGHT_TILES

soil_moisture = np.zeros((WIDTH_TILES, HEIGHT_TILES))
soil_nutrients = np.zeros((WIDTH_TILES, HEIGHT_TILES))

grid_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

current_year = 0
tree_count = 0
tree_percentage = 0.0
selected_tile = None
simulation_active = False

def initialize_soil_conditions():
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            base_moisture = 1.0 - (y / HEIGHT_TILES) * 0.7
            
            variation = random() * 0.3 - 0.15
            soil_moisture[x][y] = max(0, min(1, base_moisture + variation))
            
            distance_from_center = abs((y / HEIGHT_TILES) - 0.5) * 2
            base_nutrients = 1.0 - distance_from_center * 0.8
            variation = random() * 0.3 - 0.15
            soil_nutrients[x][y] = max(0, min(1, base_nutrients + variation))
            
    num_streams = randint(1, 3)
    for _ in range(num_streams):
        start_x = randint(0, WIDTH_TILES - 1)
        x, y = start_x, 0
        while y < HEIGHT_TILES - 1:
            radius = randint(2, 4)
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < WIDTH_TILES and 0 <= ny < HEIGHT_TILES:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance <= radius:
                            intensity = 1.0 - (distance / radius) * 0.5
                            soil_moisture[nx][ny] = min(1.0, soil_moisture[nx][ny] + intensity * 0.5)
            
            x += randint(-2, 2)
            x = max(0, min(WIDTH_TILES - 1, x))
            y += randint(1, 3)

def get_direction(xpos, ypos):
    base_direction = math.degrees(math.atan2(WIND_VECTOR[1], WIND_VECTOR[0]))
    
    variation = randint(-30, 30)
    
    return (base_direction + variation) % 360

def get_magnitude(xpos, ypos):
    base_magnitude = math.sqrt(WIND_VECTOR[0]**2 + WIND_VECTOR[1]**2)
    
    variation = random() * 2 - 1
    
    height_factor = 1 + (ypos / HEIGHT_TILES) * 1.5
    
    return max(1, min(5, (base_magnitude + variation) * height_factor))

def get_coordinates(direction, magnitude):
    rad = math.radians(direction)
    return (magnitude * math.cos(rad), magnitude * math.sin(rad))

def get_seed_displacement(x, y, is_animal_dispersed=False):
    if is_animal_dispersed:
        direction = randint(0, 360)
        magnitude = randint(5, 15)
    else:
        direction = get_direction(x, y)
        magnitude = get_magnitude(x, y) * (2 + random() * 3)
    
    return get_coordinates(direction, magnitude)

def get_cluster_displacement():
    direction = randint(0, 360)
    magnitude = randint(10, 25)
    return get_coordinates(direction, magnitude)

def color_by_soil(moisture, nutrients):
    red = 139 - int(moisture * 60)
    green = 69 + int(nutrients * 80)
    blue = 19 + int(moisture * 80)
    return (red, green, blue)

class Tile:
    def __init__(self):
        self.has_tree = False
        self.tree_age = 0
        self.has_seed = False
        self.seed_timer = 0
        self.is_animal_dispersed = False
        self.next_mast_year = randint(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
        self.years_since_last_mast = 0
        self.is_mast_year = False
    
    def lifecycle(self, x, y):
        if self.has_tree:
            self.tree_age += 1
            
            self.years_since_last_mast += 1
            
            if self.years_since_last_mast >= self.next_mast_year:
                self.is_mast_year = True
                self.years_since_last_mast = 0
                self.next_mast_year = randint(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
            else:
                self.is_mast_year = False
            
            if self.tree_age >= GERMINATION_AGE:
                seed_chance = SEED_PROBABILITY
                seed_count = randint(1, 2)
                
                if self.is_mast_year:
                    seed_chance *= 2
                    seed_count = randint(3, 7)
                
                if random() < seed_chance:
                    self.disperse_seeds(x, y, seed_count)
        
        elif self.has_seed:
            self.seed_timer += 1
            
            moisture = soil_moisture[x][y]
            nutrients = soil_nutrients[x][y]
            
            growth_chance = GROWTH_PROBABILITY * moisture * nutrients
            
            if self.seed_timer >= 5 and random() < growth_chance:
                self.has_tree = True
                self.has_seed = False
                self.tree_age = 0
                self.next_mast_year = randint(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
                self.years_since_last_mast = 0
            elif self.seed_timer > 30:
                self.has_seed = False
                self.seed_timer = 0
    
    def disperse_seeds(self, x, y, seed_count=1):
        for _ in range(seed_count):
            is_animal = self.is_animal_dispersed or (random() < 0.2)
            
            dx, dy = get_seed_displacement(x, y, is_animal)
            
            new_x = int(x + dx)
            new_y = int(y + dy)
            
            if 0 <= new_x < WIDTH_TILES and 0 <= new_y < HEIGHT_TILES:
                if not grid[new_x][new_y].has_tree and not grid[new_x][new_y].has_seed:
                    grid[new_x][new_y].has_seed = True
                    grid[new_x][new_y].seed_timer = 0
                    grid[new_x][new_y].is_animal_dispersed = is_animal

grid = []
for x in range(WIDTH_TILES):
    grid.append([])
    for y in range(HEIGHT_TILES):
        grid[x].append(Tile())

def place_seed(x, y):
    if 0 <= x < WIDTH_TILES and 0 <= y < HEIGHT_TILES:
        if not grid[x][y].has_tree and not grid[x][y].has_seed:
            grid[x][y].has_seed = True
            grid[x][y].seed_timer = 0
            grid[x][y].is_animal_dispersed = random() < 0.5
            return True
    return False

def count_trees():
    global tree_count, tree_percentage
    count = 0
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            if grid[x][y].has_tree:
                count += 1
    
    tree_count = count
    tree_percentage = (count / (WIDTH_TILES * HEIGHT_TILES)) * 100

def update_simulation():
    global current_year
    current_year += YEARS_PER_UPDATE
    
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            grid[x][y].lifecycle(x, y)
    
    count_trees()

def draw_stats_panel():
    panel_width = 280
    panel_height = 80
    panel_x = WINDOW_WIDTH - panel_width - 20
    panel_y = 20
    
    panel = pygame.Surface((panel_width, panel_height))
    panel.fill((0, 0, 0))
    pygame.draw.rect(panel, (100, 100, 100), pygame.Rect(0, 0, panel_width, panel_height), 2)
    
    title_text = small_font.render("Forest Statistics", True, (255, 255, 255))
    panel.blit(title_text, (10, 10))
    
    tree_text = small_font.render(f"Living Trees: {tree_count}", True, (255, 255, 255))
    panel.blit(tree_text, (10, 30))
    
    percentage_text = small_font.render(f"Forest Coverage: {tree_percentage:.2f}%", True, (255, 255, 255))
    panel.blit(percentage_text, (10, 50))
    
    window.blit(panel, (panel_x, panel_y))

def draw_grid():
    grid_surface.fill((0, 0, 0))
    
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            px = int(x * sq_width)
            py = int(y * sq_height)
            rect = pygame.Rect(px, py, int(sq_width) + 1, int(sq_height) + 1)
            
            if grid[x][y].has_tree:
                if grid[x][y].is_animal_dispersed:
                    color = (80, 150, 80)
                else:
                    color = (50, 160, 50)
                
                if grid[x][y].is_mast_year:
                    color = (70, 200, 70)
            elif grid[x][y].has_seed:
                if grid[x][y].is_animal_dispersed:
                    color = (220, 150, 0)
                else:
                    color = (200, 200, 0)
            else:
                color = color_by_soil(soil_moisture[x][y], soil_nutrients[x][y])
            
            pygame.draw.rect(grid_surface, color, rect, 0)
            
            if selected_tile == (x, y):
                highlight_rect = pygame.Rect(px, py, int(sq_width) + 1, int(sq_height) + 1)
                pygame.draw.rect(grid_surface, (255, 255, 255), highlight_rect, 2)
    
    window.blit(grid_surface, (0, 0))
    
    year_text = font.render(f"Year: {current_year}", True, (255, 255, 255))
    window.blit(year_text, (20, 20))
    
    draw_stats_panel()
    
    if not simulation_active:
        instruction_text = font.render("Click to place seeds, press SPACE to start simulation", True, (255, 255, 255))
        window.blit(instruction_text, (WINDOW_WIDTH // 2 - 220, WINDOW_HEIGHT - 40))
    else:
        instruction_text = font.render("Simulation running (SPACE to pause, R to reset)", True, (255, 255, 255))
        window.blit(instruction_text, (WINDOW_WIDTH // 2 - 180, WINDOW_HEIGHT - 40))
    
    if selected_tile:
        x, y = selected_tile
        tile = grid[x][y]
        info_box = pygame.Surface((300, 100))
        info_box.fill((0, 0, 0))
        pygame.draw.rect(info_box, (100, 100, 100), pygame.Rect(0, 0, 300, 100), 2)
        
        title_text = small_font.render("Tile Information", True, (255, 255, 255))
        info_box.blit(title_text, (10, 10))
        
        if tile.has_tree:
            tree_text = small_font.render(f"Tree Age: {tile.tree_age} years", True, (255, 255, 255))
            info_box.blit(tree_text, (10, 30))
            
            mature_text = small_font.render(f"Mature: {'Yes' if tile.tree_age >= GERMINATION_AGE else 'No'}", True, (255, 255, 255))
            info_box.blit(mature_text, (10, 50))
            
            mast_text = small_font.render(f"Mast Year: {'Yes' if tile.is_mast_year else 'No'}", True, (255, 255, 255))
            info_box.blit(mast_text, (10, 70))
            
            next_mast_text = small_font.render(f"Next Mast: {tile.next_mast_year - tile.years_since_last_mast} years", True, (255, 255, 255))
            info_box.blit(next_mast_text, (160, 30))
            
            type_text = small_font.render(f"Dispersal: {'Animal' if tile.is_animal_dispersed else 'Wind'}", True, (255, 255, 255))
            info_box.blit(type_text, (160, 50))
        elif tile.has_seed:
            seed_text = small_font.render(f"Seed Age: {tile.seed_timer} years", True, (255, 255, 255))
            info_box.blit(seed_text, (10, 30))
            
            type_text = small_font.render(f"Dispersal: {'Animal' if tile.is_animal_dispersed else 'Wind'}", True, (255, 255, 255))
            info_box.blit(type_text, (10, 50))
            
            germ_text = small_font.render(f"Will Germinate at: {GERMINATION_AGE} years", True, (255, 255, 255))
            info_box.blit(germ_text, (10, 70))
        else:
            soil_text = small_font.render(f"Soil Moisture: {soil_moisture[x][y]:.2f}", True, (255, 255, 255))
            info_box.blit(soil_text, (10, 30))
            
            nutrients_text = small_font.render(f"Soil Nutrients: {soil_nutrients[x][y]:.2f}", True, (255, 255, 255))
            info_box.blit(nutrients_text, (10, 50))
            
            growth_chance = GROWTH_PROBABILITY * soil_moisture[x][y] * soil_nutrients[x][y]
            growth_text = small_font.render(f"Growth Chance: {growth_chance:.3f}", True, (255, 255, 255))
            info_box.blit(growth_text, (10, 70))
        
        window.blit(info_box, (WINDOW_WIDTH - 320, WINDOW_HEIGHT - 120))

def change_wind_direction(dx, dy):
    global WIND_VECTOR
    WIND_VECTOR = [dx, dy]
    print(f"Wind direction changed to: {WIND_VECTOR}")

def initialize_simulation():
    global current_year, selected_tile, simulation_active, tree_count, tree_percentage
    current_year = 0
    selected_tile = None
    simulation_active = False
    tree_count = 0
    tree_percentage = 0.0
    
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            grid[x][y].has_tree = False
            grid[x][y].tree_age = 0
            grid[x][y].has_seed = False
            grid[x][y].is_animal_dispersed = False
            grid[x][y].next_mast_year = randint(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
            grid[x][y].years_since_last_mast = 0
            grid[x][y].is_mast_year = False
    
    initialize_soil_conditions()

def main():
    global selected_tile, simulation_active
    
    random_seed(42)
    
    initialize_simulation()
    
    last_update_time = pygame.time.get_ticks()
    update_interval = UPDATE_FREQUENCY * 1000
    
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    change_wind_direction(0, 1)
                elif event.key == pygame.K_DOWN:
                    change_wind_direction(0, -1)
                elif event.key == pygame.K_LEFT:
                    change_wind_direction(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    change_wind_direction(1, 0)
                elif event.key == pygame.K_r:
                    initialize_simulation()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    simulation_active = not simulation_active
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not simulation_active:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    tile_x = int(mouse_x / sq_width)
                    tile_y = int(mouse_y / sq_height)
                    
                    if 0 <= tile_x < WIDTH_TILES and 0 <= tile_y < HEIGHT_TILES:
                        selected_tile = (tile_x, tile_y)
                        place_seed(tile_x, tile_y)
                elif event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    tile_x = int(mouse_x / sq_width)
                    tile_y = int(mouse_y / sq_height)
                    
                    if 0 <= tile_x < WIDTH_TILES and 0 <= tile_y < HEIGHT_TILES:
                        selected_tile = (tile_x, tile_y)
        
        if simulation_active:
            current_time = pygame.time.get_ticks()
            if current_time - last_update_time >= update_interval:
                update_simulation()
                last_update_time = current_time
        
        window.fill((0, 0, 0))
        draw_grid()
        pygame.display.flip()
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()