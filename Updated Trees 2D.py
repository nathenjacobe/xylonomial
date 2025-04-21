import pygame
import math
import random
import numpy as np
import sys

pygame.init()
pygame.font.init()

# --- Constants ---
WINDOW_HEIGHT: int = 800
WINDOW_WIDTH: int = 1000
TILE_DIMENSIONS: int = 5
HEIGHT_TILES: int = 160
WIDTH_TILES: int = 200
BORDER_THICKNESS: int = 1
WIND_VECTOR = [random.random() * 2 - 1, random.random() * 2 - 1] # Random initial wind vector
GROWTH_PROBABILITY = 0.1
GERMINATION_AGE = 40
UPDATE_FREQUENCY = 0.02
YEARS_PER_UPDATE = 0.5
MAST_FREQUENCY_MIN = 2
MAST_FREQUENCY_MAX = 7
MAST_YEAR_MULTIPLIER = 5
BIRD_MIGRATION_FACTOR = 30

# --- Dispersal Constants ---
ANIMAL_DISPERSAL_PROPORTION = 0.95

# -- Animal Dispersal (Pareto Distribution) --
PARETO_ALPHA = 2.5
PARETO_SCALE = 8.0

# -- Wind Dispersal --
WIND_DIRECTION_STD_DEV = 45
SEED_WIND_MAGNITUDE_FACTOR = 0.8
WIND_BASE_DISTANCE_MULT = 2.0
WIND_DISTANCE_VARIATION = 1.5

# --- Tree Mortality Constants ---
YEARS_PER_UPDATE = 0.5

# Young trees have a simplified flat mortality rate
YOUNG_AGE_THRESHOLD = 10.0
YOUNG_MORTALITY_ANNUAL = 0.008  # 0.8% chance of death per year for young trees
BASE_MATURE_MORTALITY_ANNUAL = 0.001  # 0.1% base chance for mature trees

# Logistic function parameters for age-related mortality
SENESCENCE_MIDPOINT = 350.0  # Age at which mortality increase is 50% of maximum
SENESCENCE_STEEPNESS = 0.015  # Controls how quickly mortality increases with age
MAX_SENESCENCE_MORTALITY_ANNUAL = 0.05  # Maximum 5% additional death chance from age

# Convert annual probabilities to per-step probabilities using:
# P(death per step) = 1 - (1 - P(death per year))^(years per step)
YOUNG_MORTALITY_STEP = 1.0 - (1.0 - YOUNG_MORTALITY_ANNUAL) ** YEARS_PER_UPDATE
BASE_MATURE_MORTALITY_STEP = 1.0 - (1.0 - BASE_MATURE_MORTALITY_ANNUAL) ** YEARS_PER_UPDATE
MAX_SENESCENCE_MORTALITY_STEP = 1.0 - (1.0 - MAX_SENESCENCE_MORTALITY_ANNUAL) ** YEARS_PER_UPDATE

# Maximum possible distance in the grid (diagonal) used to clamp dispersal
MAX_GRID_DIST = math.sqrt(WIDTH_TILES**2 + HEIGHT_TILES**2)

# --- Pygame Setup ---
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("xylonomial")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 24)
small_font = pygame.font.SysFont('Arial', 16)

sq_width: int = WINDOW_WIDTH / WIDTH_TILES
sq_height: int = WINDOW_HEIGHT / HEIGHT_TILES

# --- Simulation State ---
soil_moisture = np.zeros((WIDTH_TILES, HEIGHT_TILES))
soil_nutrients = np.zeros((WIDTH_TILES, HEIGHT_TILES))
grid_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
current_year = 0.0
current_half_year = 0
tree_count = 0
death_num = 0
tree_percentage = 0.0
selected_tile = None
simulation_active = False

# --- Soil Initialization ---
def initialize_soil_conditions():
    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            base_moisture = 1.0 - (y / HEIGHT_TILES) * 0.7
            variation = random.uniform(-0.15, 0.15)
            soil_moisture[x][y] = max(0, min(1, base_moisture + variation))

            distance_from_center = abs((y / HEIGHT_TILES) - 0.5) * 2
            base_nutrients = 1.0 - distance_from_center * 0.8
            variation = random.uniform(-0.15, 0.15)
            soil_nutrients[x][y] = max(0, min(1, base_nutrients + variation))

    num_streams = random.randint(1, 3)
    for _ in range(num_streams):
        start_x = random.randint(0, WIDTH_TILES - 1)
        x, y = start_x, 0
        while y < HEIGHT_TILES - 1:
            radius = random.randint(2, 4)
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < WIDTH_TILES and 0 <= ny < HEIGHT_TILES:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance <= radius:
                            intensity = 1.0 - (distance / radius)
                            soil_moisture[nx][ny] = min(1.0, soil_moisture[nx][ny] + intensity * 0.6)
                            soil_nutrients[nx][ny] = min(1.0, soil_nutrients[nx][ny] + intensity * 0.1)

            x += random.randint(-1, 1)
            x = max(0, min(WIDTH_TILES - 1, x))
            y += random.randint(1, 2)

# --- Dispersal Helper Functions ---
def get_coordinates(direction_degrees, magnitude):
    # Convert polar coordinates (angle in degrees, magnitude) to Cartesian (dx, dy)
    rad = math.radians(direction_degrees)
    return (magnitude * math.cos(rad), magnitude * math.sin(rad))

def get_animal_displacement(x, y):
    # Animal dispersal direction is biased by migration season (north/south)
    migration_bias = BIRD_MIGRATION_FACTOR if current_half_year == 0 else -BIRD_MIGRATION_FACTOR
    direction = (random.uniform(0, 360) + migration_bias) % 360

    # Pareto distribution models rare long-distance dispersal events
    pareto_variate = random.paretovariate(PARETO_ALPHA)
    scaled_distance = pareto_variate * PARETO_SCALE
    # Clamp to grid diagonal to avoid out-of-bounds
    magnitude = min(scaled_distance, MAX_GRID_DIST)

    return get_coordinates(direction, magnitude)

def get_wind_displacement(x, y):
    # Wind dispersal: direction is centered on wind vector, with random spread
    base_wind_angle = math.degrees(math.atan2(WIND_VECTOR[1], WIND_VECTOR[0]))
    direction = random.normalvariate(base_wind_angle, WIND_DIRECTION_STD_DEV) % 360

    # Magnitude is based on wind strength, with random variation
    base_magnitude = math.sqrt(WIND_VECTOR[0]**2 + WIND_VECTOR[1]**2)
    magnitude_variation = random.uniform(1.0 - WIND_DISTANCE_VARIATION/2 , 1.0 + WIND_DISTANCE_VARIATION/2)
    magnitude = (base_magnitude * SEED_WIND_MAGNITUDE_FACTOR *
                 WIND_BASE_DISTANCE_MULT * magnitude_variation)
    magnitude = max(0.5, magnitude)  # Ensure minimum dispersal

    return get_coordinates(direction, magnitude)

# --- Soil Color Helper ---
def color_by_soil(moisture, nutrients):
    red = 150 - int(moisture * 60) - int(nutrients * 20)
    green = 80 + int(nutrients * 100) - int(moisture * 20)
    blue = 40 + int(moisture * 60) - int(nutrients * 20)
    return (max(0, min(255, red)), max(0, min(255, green)), max(0, min(255, blue)))

# --- Tile Class ---
class Tile:
    def __init__(self):
        self.has_tree = False
        self.tree_age = 0.0
        self.has_seed = False
        self.seed_timer = 0.0
        self.next_mast_year = random.uniform(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
        self.years_since_last_mast = 0.0
        self.is_mast_year = False

    def lifecycle(self, x, y):
        if self.has_tree:
            self.tree_age += YEARS_PER_UPDATE

            prob_death_step = 0.0
            if self.tree_age < YOUNG_AGE_THRESHOLD:
                # Young trees: flat mortality rate
                prob_death_step = YOUNG_MORTALITY_STEP
            else:
                # Mature trees: logistic increase in mortality with age (senescence)
                # The logistic function smoothly increases mortality after a midpoint
                senescence_increase = (MAX_SENESCENCE_MORTALITY_STEP - BASE_MATURE_MORTALITY_STEP) / \
                                      (1 + math.exp(-SENESCENCE_STEEPNESS * (self.tree_age - SENESCENCE_MIDPOINT)))
                senescence_increase = max(0, senescence_increase)
                prob_death_step = BASE_MATURE_MORTALITY_STEP + senescence_increase

            if random.random() < prob_death_step:
                global death_num
                self.has_tree = False
                self.tree_age = 0.0
                self.has_seed = False
                self.seed_timer = 0.0
                self.years_since_last_mast = 0.0
                self.is_mast_year = False
                death_num += 1
                return

            self.years_since_last_mast += YEARS_PER_UPDATE

            if self.years_since_last_mast >= self.next_mast_year:
                # Mast years: tree produces many seeds at irregular intervals
                self.is_mast_year = True
                self.years_since_last_mast = 0.0
                self.next_mast_year = random.uniform(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
            else:
                self.is_mast_year = False

            if self.tree_age >= GERMINATION_AGE:    
                # Mature trees produce seeds, more in mast years
                seed_count = random.randint(1, 2)
                if self.is_mast_year:
                    seed_count = random.randint(5, 10)
                self.disperse_seeds(x, y, seed_count)

        elif self.has_seed:
            self.seed_timer += YEARS_PER_UPDATE

            moisture = soil_moisture[x][y]
            nutrients = soil_nutrients[x][y]
            MAX_MOISTURE_FOR_GERMINATION = 0.85
            if moisture <= MAX_MOISTURE_FOR_GERMINATION:
                # Germination chance increases with soil moisture and nutrients
                growth_chance = GROWTH_PROBABILITY * math.sqrt(moisture) * math.sqrt(nutrients)

                if self.seed_timer >= 5 and random.random() < growth_chance:
                    # Competition: more neighbors = lower chance to establish
                    neighbor_trees = 0
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < WIDTH_TILES and 0 <= ny < HEIGHT_TILES:
                                if grid[nx][ny].has_tree:
                                    neighbor_trees += 1
                    competition_factor = 1.0 - (neighbor_trees / 8.0) * 0.5

                    if random.random() < competition_factor:
                        self.has_tree = True
                        self.has_seed = False
                        self.tree_age = 0.0
                        self.seed_timer = 0.0
                        self.next_mast_year = random.uniform(MAST_FREQUENCY_MIN, MAST_FREQUENCY_MAX)
                        self.years_since_last_mast = 0.0
                        self.is_mast_year = False

            if self.seed_timer > 30:
                # Seeds expire after 30 years if not germinated
                self.has_seed = False
                self.seed_timer = 0.0

    def disperse_seeds(self, x, y, seed_count):
        for _ in range(seed_count):
            # Most seeds dispersed by animals, some by wind
            if random.random() < ANIMAL_DISPERSAL_PROPORTION:
                dx, dy = get_animal_displacement(x, y)
            else:
                dx, dy = get_wind_displacement(x, y)

            # Round to nearest tile
            new_x = int(round(x + dx))
            new_y = int(round(y + dy))

            if 0 <= new_x < WIDTH_TILES and 0 <= new_y < HEIGHT_TILES:
                target_tile = grid[new_x][new_y]
                if not target_tile.has_tree and not target_tile.has_seed:
                    target_tile.has_seed = True
                    target_tile.seed_timer = 0.0

# --- Grid Initialization ---
grid = [[Tile() for y in range(HEIGHT_TILES)] for x in range(WIDTH_TILES)]

# --- Helper Functions ---
def place_initial_seed(x, y):
    if 0 <= x < WIDTH_TILES and 0 <= y < HEIGHT_TILES:
        tile = grid[x][y]
        if not tile.has_tree and not tile.has_seed:
            tile.has_seed = True
            tile.seed_timer = 0.0
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
    total_tiles = WIDTH_TILES * HEIGHT_TILES
    tree_percentage = (count / total_tiles) * 100 if total_tiles > 0 else 0.0

def update_simulation():
    global current_year, current_half_year
    current_year += YEARS_PER_UPDATE

    current_half_year = 1 - current_half_year

    tile_indices = [(x, y) for x in range(WIDTH_TILES) for y in range(HEIGHT_TILES)]
    random.shuffle(tile_indices)

    for x, y in tile_indices:
        grid[x][y].lifecycle(x, y)

    count_trees()

# --- Drawing Functions ---
def draw_stats_panel():
    panel_width = 280
    panel_height = 110
    panel_x = WINDOW_WIDTH - panel_width - 20
    panel_y = 20

    panel = pygame.Surface((panel_width, panel_height))
    panel.fill((20, 20, 20))
    panel.set_alpha(200)
    pygame.draw.rect(panel, (100, 100, 100), panel.get_rect(), 1)

    title_text = small_font.render("Forest Statistics", True, (220, 220, 220))
    panel.blit(title_text, (10, 5))

    tree_text = small_font.render(f"Living Trees: {tree_count}", True, (200, 255, 200))
    panel.blit(tree_text, (10, 25))

    percentage_text = small_font.render(f"Forest Coverage: {tree_percentage:.2f}%", True, (200, 255, 200))
    panel.blit(percentage_text, (10, 45))

    migration_label = "Animal Migration:"
    migration_dir = "Northward (Spring)" if current_half_year == 0 else "Southward (Autumn)"
    migration_text = small_font.render(f"{migration_label} {migration_dir}", True, (200, 200, 255))
    panel.blit(migration_text, (10, 65))

    death_text = small_font.render(f"Deaths: {death_num}", True, (200, 255, 200))
    panel.blit(death_text, (10, 85))

    window.blit(panel, (panel_x, panel_y))

def draw_grid():
    grid_surface.fill((0, 0, 0))

    tree_circle_radius = int(min(sq_width, sq_height) / 2 * 0.8)
    seed_circle_radius = max(1, int(tree_circle_radius * 0.4))

    normal_tree_color = (100, 255, 100)
    seed_color = (200, 200, 0)
    highlight_color = (255, 255, 255)

    for x in range(WIDTH_TILES):
        for y in range(HEIGHT_TILES):
            px = int(x * sq_width)
            py = int(y * sq_height)
            tile_rect = pygame.Rect(px, py, int(sq_width) + 1, int(sq_height) + 1)
            center_x = int(px + sq_width / 2)
            center_y = int(py + sq_height / 2)

            tile_state = grid[x][y]

            soil_color = color_by_soil(soil_moisture[x][y], soil_nutrients[x][y])
            pygame.draw.rect(grid_surface, soil_color, tile_rect)

            if tile_state.has_tree:
                tree_color = normal_tree_color
                pygame.draw.circle(grid_surface, tree_color, (center_x, center_y), tree_circle_radius)

            elif tile_state.has_seed:
                pygame.draw.circle(grid_surface, seed_color, (center_x, center_y), seed_circle_radius)

            if selected_tile == (x, y):
                highlight_rect = pygame.Rect(px, py, int(sq_width), int(sq_height))
                pygame.draw.rect(grid_surface, highlight_color, highlight_rect, 2)

    window.blit(grid_surface, (0, 0))

    year_str = f"Year: {current_year:.1f}"
    migration_season = "Spring/Summer" if current_half_year == 0 else "Autumn/Winter"
    year_text = font.render(f"{year_str} ({migration_season})", True, (255, 255, 255))
    window.blit(year_text, (20, 20))

    draw_stats_panel()

    if not simulation_active:
        instruction_text = font.render("Click to place seeds. SPACE to start/pause. R to reset.", True, (255, 255, 255))
        text_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30))
        window.blit(instruction_text, text_rect)
    else:
        instruction_text = font.render("Simulation Running. SPACE to pause. R to reset.", True, (255, 255, 255))
        text_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30))
        window.blit(instruction_text, text_rect)

    if selected_tile:
        x, y = selected_tile
        tile = grid[x][y]
        info_box_width = 300
        info_box_height = 120
        info_box = pygame.Surface((info_box_width, info_box_height))
        info_box.fill((20, 20, 20))
        info_box.set_alpha(220)
        pygame.draw.rect(info_box, (100, 100, 100), info_box.get_rect(), 1)

        title_text = small_font.render(f"Tile Info ({x}, {y})", True, (220, 220, 220))
        info_box.blit(title_text, (10, 5))

        line_y = 25
        line_spacing = 18

        soil_text = small_font.render(f"Soil M: {soil_moisture[x][y]:.2f} N: {soil_nutrients[x][y]:.2f}", True, (180, 180, 255))
        info_box.blit(soil_text, (10, line_y)); line_y += line_spacing

        if tile.has_tree:
            tree_text = small_font.render(f"Tree Age: {tile.tree_age:.1f} years", True, (180, 255, 180))
            info_box.blit(tree_text, (10, line_y)); line_y += line_spacing
            mature_text = small_font.render(f"Mature: {'Yes' if tile.tree_age >= GERMINATION_AGE else 'No'}", True, (200, 200, 200))
            info_box.blit(mature_text, (10, line_y)); line_y += line_spacing
            mast_text = small_font.render(f"Mast Year: {'Yes' if tile.is_mast_year else 'No'}", True, (255, 255, 100))
            info_box.blit(mast_text, (10, line_y))
            next_mast_rem = max(0, tile.next_mast_year - tile.years_since_last_mast)
            next_mast_text = small_font.render(f"(Next in ~{next_mast_rem:.1f} yrs)", True, (150, 150, 150))
            info_box.blit(next_mast_text, (10 + mast_text.get_width() + 5 , line_y)); line_y += line_spacing

        elif tile.has_seed:
            seed_text = small_font.render(f"Seed Age: {tile.seed_timer:.1f} years", True, (255, 255, 150))
            info_box.blit(seed_text, (10, line_y)); line_y += line_spacing

            germ_time_rem = max(0, 5 - tile.seed_timer)
            expiry_time_rem = max(0, 30 - tile.seed_timer)
            germ_text = small_font.render(f"Germ. check in: {germ_time_rem:.1f} yrs", True, (200, 200, 200))
            info_box.blit(germ_text, (10, line_y)); line_y += line_spacing
            expiry_text = small_font.render(f"Expires in: {expiry_time_rem:.1f} yrs", True, (200, 150, 150))
            info_box.blit(expiry_text, (10, line_y)); line_y += line_spacing

        else:
            moisture = soil_moisture[x][y]
            nutrients = soil_nutrients[x][y]
            growth_chance = GROWTH_PROBABILITY * math.sqrt(moisture) * math.sqrt(nutrients) * 100
            growth_text = small_font.render(f"Est. Growth Chance: {growth_chance:.1f}%", True, (150, 200, 150))
            info_box.blit(growth_text, (10, line_y)); line_y += line_spacing
            empty_text = small_font.render("Tile is empty", True, (150, 150, 150))
            info_box.blit(empty_text, (10, line_y)); line_y += line_spacing

        info_box_x = WINDOW_WIDTH - info_box_width - 20
        info_box_y = WINDOW_HEIGHT - info_box_height - 20
        window.blit(info_box, (info_box_x, info_box_y))

# --- Wind Control ---
def change_wind_direction(dx, dy):
    global WIND_VECTOR
    norm = math.sqrt(dx**2 + dy**2)
    if norm > 0:
       scale = 1.0
       WIND_VECTOR = [dx / norm * scale, dy / norm * scale]
    else:
       WIND_VECTOR = [0, 0]
    print(f"Wind vector changed to: [{WIND_VECTOR[0]:.2f}, {WIND_VECTOR[1]:.2f}]")

# --- Simulation ---
def initialize_simulation():
    global current_year, current_half_year, selected_tile, simulation_active, tree_count, tree_percentage, grid
    current_year = 0.0
    current_half_year = 0
    selected_tile = None
    simulation_active = False
    tree_count = 0
    tree_percentage = 0.0

    grid = [[Tile() for _ in range(HEIGHT_TILES)] for _ in range(WIDTH_TILES)]

    initialize_soil_conditions()
    print("Simulation reset.")

# --- Core ---
def main():
    global selected_tile, simulation_active

    seed = 2025
    random.seed(seed)
    np.random.seed(seed)

    initialize_simulation()

    last_update_time = pygame.time.get_ticks()
    update_interval_ms = UPDATE_FREQUENCY * 1000

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    simulation_active = not simulation_active
                    print(f"Simulation {'started' if simulation_active else 'paused'}.")
                elif event.key == pygame.K_r:
                    initialize_simulation()
                elif event.key == pygame.K_UP:
                    change_wind_direction(0, -1)
                elif event.key == pygame.K_DOWN:
                    change_wind_direction(0, 1)
                elif event.key == pygame.K_LEFT:
                    change_wind_direction(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    change_wind_direction(1, 0)
                elif event.key == pygame.K_w:
                    change_wind_direction(1,-1)
                elif event.key == pygame.K_s:
                    change_wind_direction(1, 1)
                elif event.key == pygame.K_a:
                     change_wind_direction(-1,-1) # NW diagonal = (-1,-1) normalized
                elif event.key == pygame.K_d:
                     change_wind_direction(-1, 1)  # SW diagonal = (-1,1) normalized

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                # Convert pixel coordinates to grid coordinates using floor division
                # This maps continuous mouse position to discrete grid tiles
                tile_x = int(mouse_x // sq_width)
                tile_y = int(mouse_y // sq_height)

                if 0 <= tile_x < WIDTH_TILES and 0 <= tile_y < HEIGHT_TILES:
                    if event.button == 1:
                        selected_tile = (tile_x, tile_y)
                        if not simulation_active:
                            placed = place_initial_seed(tile_x, tile_y)
                            if placed:
                                print(f"Placed seed at ({tile_x}, {tile_y})")
                        else:
                             print(f"Selected tile ({tile_x}, {tile_y}) for info.")
                    elif event.button == 3:
                        selected_tile = None

        if simulation_active:
            current_time = pygame.time.get_ticks()
            # Convert update frequency from seconds to milliseconds
            # and check if enough time has passed since last update
            if current_time - last_update_time >= update_interval_ms:
                update_simulation()
                last_update_time = current_time  # Reset timer for next interval

        window.fill((30, 30, 30))
        draw_grid()
        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
