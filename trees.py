# libraries
import pyglet
import random
import numpy as np
from scipy.stats import pareto

# configurations

WINDOW_HEIGHT : int = 1000
WINDOW_WIDTH : int = 1000

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

TIME_BASE : int = 1 # number of seconds per year
GLOBAL_TIME : int = 0 # current time in the simulation

NUM_CALLS : int = 0

# general utility functions

def calculate_tree_stage(age : int) -> int:
    """ returns the current stage of the tree """
    return max(stage for stage, year in STAGE_TO_YEAR.items() if age >= year)

# X ~ B(N, P). N = number of seeds

# we'll have a random number from 0 to 1
# 

def lerp(a, b, t):
    return a + t * (b-a);


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

# def animal_distribution(tVal):
#     y = {}

#     alpha = 0 #shape of distribution
#     scale = 0 #minimum value
#     distance = 0 #how far the distribution considers values for where the acorns can fall (should be large because pareto has long tail)

#     positions = np.arange(-distance, distance +, 1)
    

    

distribution = binomial_dist()

def get_random_position(distribution : dict[int : float]) -> int:
    """ Given a distribution, determines a random distance"""
    global NUM_CALLS
    sorted_distribution_keys = sorted(distribution.keys())
    sorted_distribution_values = sorted(distribution.values())

    n = sorted_distribution_values[-1]
    random_n = random.uniform(0, n)
    NUM_CALLS += 1
    for key in sorted_distribution_keys:
        #[0 : 0.1, 1:0.2, 2:0.4, 3:0.6, 4:0.9] 0.7 sums to 0.9/
        if random_n < distribution[key] : 
            final = distribution.get(key - 1, 0)
            distance = distribution[key] - final
            return lerp(key-1, key, (random_n - final) / distance)

    return n

trees = {
    3 * WINDOW_WIDTH // 4 : 1,
    WINDOW_WIDTH // 4 : 1
         } 

window = pyglet.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="XYLONOMIAL")

batch = pyglet.graphics.Batch()

line_height = 16;
baseline = pyglet.shapes.Line(0, WINDOW_HEIGHT // 2, WINDOW_WIDTH, WINDOW_HEIGHT // 2, line_height, color=(255, 255, 255), batch=batch)

lines = []

def update_line(dt):
    original_keys = np.array(list(trees.keys())).astype(int)
    for tree_pos in original_keys:
        x1 = get_random_position(distribution)
        x2 = get_random_position(distribution)
        trees[tree_pos+x1] = 1
        trees[tree_pos+x2] = 1
        lines.append(
            pyglet.shapes.Line(
                int(tree_pos+x1), 
                WINDOW_HEIGHT // 2 + 20, 
                int(tree_pos+x1), 
                WINDOW_HEIGHT // 2 - 20, 
                1, 
                color=(255, 20, 20), 
                batch=batch)
            )
        lines.append(
            pyglet.shapes.Line(
                int(tree_pos+x2), 
                WINDOW_HEIGHT // 2 + 20, 
                int(tree_pos+x2), 
                WINDOW_HEIGHT // 2 - 20, 
                1, 
                color=(255, 20, 20), 
                batch=batch)
            )

@window.event
def on_draw():
    window.clear()
    batch.draw()

pyglet.clock.schedule_interval(update_line, TIME_BASE)

pyglet.app.run()

