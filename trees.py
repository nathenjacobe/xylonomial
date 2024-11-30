# libraries

import pyglet
from random import random



# configurations

WIND_VECTOR : list[int] = [1] # supposed to be a n-dimensional vector but for now its 1d

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



# probably going to have just 1 primary class: a soil tile
# stores all the important information for a tile. This is pretty scalable too
# since we'll store the soil tiles in an n-dimensional array; we can just scale n

# following the principle of abstraction, we don't need to send meta data to the class parameters
# namely, the soil tile doesn't need to know where it is relative to other tiles
# all it needs to know is its own parameters:
# nutrient density, water content, tree stage

class soil_tile:

    def __init__(self, water_content : float, nutrient_density : float) -> None:
        """ create a soil tile """
        self.water_content : int = water_content
        self.nutrient_density : int = nutrient_density
        self.tree_stage : int = 0
        self.tree_age : int = 0
        self.accumulated_water : int = 0
        self.accumulated_nutrients : int = 0

    def __str__(self) -> str:
        return f"Water: {self.water_content}; Nutrient: {self.nutrient_density}; Tree (St)age: {self.tree_stage, self.tree_age}"
    
    def attempt_seed_plant(self) -> None:
        """ attempt to plant a seed """
        if self.tree_stage > 0: return # already has a tree
        if self.nutrient_density < GERMINATION_MIN_NUTRIENT or self.water_content < GERMINATION_MIN_WATER: return
        if random.random() < GERMINATION_MIN_SUCCESS: return # random chance of failure
        self.tree_stage = 1
        self.tree_age = 0

        # sanity check; should be 0 anyway lol
        self.accumulated_nutrients = 0
        self.accumulated_water = 0
    
    def kill_tree(self) -> None:
        self.tree_age = 0
        self.tree_stage = 6

    def on_increment_time(self) -> None:
        """ age the tree and expend soil resources """
        if self.tree_stage == 0: return

        if self.tree_stage == 6:

            if self.accumulated_nutrients < NUTRIENT_RETURN_RATE: 
                self.accumulated_nutrients = 0; self.nutrient_density += self.accumulated_nutrients; return
            if self.accumulated_water < WATER_RETURN_RATE: 
                self.accumulated_water = 0; self.water_content += self.accumulated_water; return
            
            self.nutrient_density += NUTRIENT_RETURN_RATE
            self.water_content += WATER_RETURN_RATE
            self.accumulated_nutrients -= NUTRIENT_RETURN_RATE
            self.accumulated_water -= WATER_RETURN_RATE

            return

        self.tree_age += 1
        self.tree_stage = calculate_tree_stage(self.tree_age)

        self.nutrient_density -= NUTRIENT_CONSUMPTION_RATE
        self.water_content -= WATER_CONSUMPTION_RATE
        if self.nutrient_density < 0 or self.water_content < 0: self.kill_tree()
  




# when we increment the time, the order of operation matters:
# 1. disperse seeds
# 2. run increment time on all soils
# 3. update graphics

    


    



# core logic

window = pyglet.window.Window()
label = pyglet.text.Label('Trees',
                          font_name='Times New Roman',
                          font_size=36,
                          x=window.width//2, y=window.height//2,
                          anchor_x='center', anchor_y='center')


@window.event
def on_draw():
    window.clear()
    label.draw()

pyglet.app.run()


