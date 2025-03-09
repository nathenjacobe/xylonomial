import pyglet as pg
import math
from random import randint

WINDOW_HEIGHT: int = 1000
WINDOW_WIDTH: int = 1000
TILE_DIMENSION: int = 2  # metres
HEIGHT_TILES: int = 100
WIDTH_TILES: int = 100
BORDER_THICKNESS: int = 1 

WIND_VECTOR: int = [0, 0];

window = pg.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="XYLONOMIAL")
batch = pg.graphics.Batch()
sq_width: int = WINDOW_WIDTH / WIDTH_TILES
sq_height: int = WINDOW_HEIGHT / HEIGHT_TILES

rendered_grid_squares = []

def get_direction(xpos, ypos):
    return randint(0, 360)

def get_magnitude(xpos, ypos):
    return randint(2, 5)

def get_coordinates(dir, mag):
    rad = math.radians(dir)
    return(mag * math.cos(rad), mag * math.sin(rad))

def get_seed_displacement():
    pass

def get_cluster_displacement():
    pass

class Tile:
    def __init__(self):
        self.has_tree = False
        self.tree_age = 0

    def lifecycle(self):
        if self.has_tree: self.tree_age += 1;

grid = []

for x in range(WIDTH_TILES):
    grid.append([])
    for y in range(HEIGHT_TILES):
        grid[x].append(Tile())

# bottom left is 0, 0

grid[0][2].has_tree = True;
grid[28][28].has_tree = True;
        

def draw_grid():
    for square in rendered_grid_squares:
        square.delete()
    rendered_grid_squares.clear()

    for i in range(WIDTH_TILES):
        for j in range(HEIGHT_TILES):
            x = i * sq_width
            y = j * sq_height

            border_rect = pg.shapes.Rectangle(
                x, y, sq_width, sq_height, 
                color=(100, 100, 100), 
                batch=batch
            )

            fill_rect = None

            if grid[i][j].has_tree:
                fill_rect = pg.shapes.Rectangle(
                    x + BORDER_THICKNESS, 
                    y + BORDER_THICKNESS, 
                    sq_width - 2 * BORDER_THICKNESS, 
                    sq_height - 2 * BORDER_THICKNESS, 
                    color=(255, 255, 255), 
                    batch=batch
                )
                fill_rect.opacity = 150  
            else:
                fill_rect = pg.shapes.Rectangle(
                    x + BORDER_THICKNESS, 
                    y + BORDER_THICKNESS, 
                    sq_width - 2 * BORDER_THICKNESS, 
                    sq_height - 2 * BORDER_THICKNESS, 
                    color=(255, 75, 75), 
                    batch=batch
                )
                fill_rect.opacity = 150 

            rendered_grid_squares.append(border_rect)
            rendered_grid_squares.append(fill_rect)




@window.event
def on_draw():
    window.clear()
    draw_grid()

    batch.draw()


if __name__ == "__main__":
    draw_grid()
    pg.app.run()
