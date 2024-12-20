# libraries
import pyglet
import random
import numpy as np
import copy

# configurations

WINDOW_HEIGHT : int = 800
WINDOW_WIDTH : int = 800

WIND_VECTOR : list[int] = [4] # supposed to be a n-dimensional vector but for now its 1d

NUMBER_OF_TILES : int = 100

GERMINATION_MIN_WATER : int = 40
GERMINATION_MIN_NUTRIENT : int = 40 
GERMINATION_MIN_SUCCESS : float = 0.02

WATER_CONSUMPTION_RATE : int = 10 # litres of water in soil used per year
NUTRIENT_CONSUMPTION_RATE : int = 10 # kgs of nutrient in soil used per year

# rate of returning water and nutrients to the soil once dead
WATER_RETURN_RATE : int = 10 
NUTRIENT_RETURN_RATE : int = 10

# tree stages are quite simple:
# [0, 1, 2, 3, 4, 5, 6] = [no tree, seed, seedling, sapling, mature, old, dead]

STAGE_TO_YEAR : dict[int, int] = {

    0 : 1,
    1 : 2, 
    5 : 3,
    20 : 4, 
    100 : 5,
    400 : 6

}
SORTED_YEARS = sorted(STAGE_TO_YEAR.keys())

TIME_BASE : int = 2 # number of seconds per year
GLOBAL_TIME : int = 0 # current time in the simulation

# general utility functions

def calculate_tree_stage(age : int) -> int:
    """ returns the current stage of the tree """
    return max(stage for stage, year in STAGE_TO_YEAR.items() if age >= year)

# X ~ B(N, P). N = number of seeds

# we'll have a random number from 0 to 1
# 


def binomial_dist() -> dict[int : float]:
    """ Returns a distribution based on different factors """

    y = {}
    std_dev = 4
    tolerance = 2
    mean = WIND_VECTOR[0]
    min_bound = -std_dev * tolerance + mean
    max_bound = std_dev * tolerance + mean
    for x in range(min_bound, max_bound):
        prev = y[x-1] if x > min_bound else 0
        y[x] = float(1 / (std_dev * np.sqrt(2 * np.pi))) * np.exp(-((x - mean)**2) / (2 * std_dev**2)) + prev

    return y

distribution = binomial_dist()
print(distribution)

def get_random_position(distribution : dict[int : float]) -> int:
    """ Given a distribution, determines a random distance"""
    sorted_distribution_keys = sorted(distribution.keys())
    sorted_distribution_values = sorted(distribution.values())
    n = sorted_distribution_values[-1]
    random_n = random.uniform(0, n)
    print(f"random_n = {random_n}")
    for key in sorted_distribution_keys:
        if random_n < distribution[key] : print(f"key = {key}"); return key
    return n



class soil_tile:

    def __init__(self) -> None:
        """ create a soil tile """
        self.hasTree = False
        
    def get_seed_position(self, debug : str) -> int:
        print(debug)
        return get_random_position(distribution)
    

   
soil_plane = []

for x in range(NUMBER_OF_TILES):
    soil_plane.append(soil_tile())

soil_plane[30].hasTree = True # append tree
soil_plane[90].hasTree = True

# Create a Pyglet window
window = pyglet.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Xylonomial")

# Create a batch for efficient drawing
batch = pyglet.graphics.Batch()

# Line height calculation
line_width = WINDOW_WIDTH / NUMBER_OF_TILES
line_height = 20
render_plane = []

# Generate lines
for i in range(NUMBER_OF_TILES):
    x_start = i * line_width
    x_end = x_start + line_width - 2  # Add a small gap between segments
    y_center = WINDOW_HEIGHT // 2  # Vertically center the lines
    line = pyglet.shapes.Line(x_start, y_center, x_end, y_center, line_width, color = (255, 255, 255), batch = batch)
    render_plane.append(line)

def render():
    for e, line in enumerate(render_plane):
        if soil_plane[e].hasTree:
            line.color = (0, 0, 255)
        else:
            line.color = (255, 255, 255)

def update_line_colors(dt):

    global soil_plane
    new_soil_plane = copy.deepcopy(soil_plane)

    for e, soil in enumerate(soil_plane):
        if soil.hasTree:
            print("soil on", e)
            x1 = e+soil.get_seed_position("x1") 
            x2 = e+soil.get_seed_position("x2") 
            if 0 <= x1 < NUMBER_OF_TILES:
                new_soil_plane[x1].hasTree = True
            if 0 <= x2 < NUMBER_OF_TILES:
                new_soil_plane[x2].hasTree = True
            
    soil_plane = new_soil_plane

    render()

render()

@window.event
def on_draw():
    window.clear()
    batch.draw()

pyglet.clock.schedule_interval(update_line_colors, TIME_BASE)

# Run the application
pyglet.app.run()
