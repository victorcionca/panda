import sys
import pygame
import random
import math
from pygame.math import Vector2
from pygame.locals import *

HEIGHT = 800
WIDTH = 800
ACC = 0.5
FRIC = -0.12
FPS = 30

class FloatingSprite(pygame.sprite.Sprite):
    def __init__(self, mass, pos):
        super().__init__()
        self.pos = pos
        self.mass = mass
        self.fixed = False
        self.falling = False
        self.vertical_veloc = Vector2((0,0))
        self.rect = None

    def jump(self, delta_x, delta_y):
        self.falling = True
        self.vertical_veloc -= Vector2((delta_x, delta_y))

    def move_vertically(self):
        if self.falling:
            self.vertical_veloc += Vector2((0, self.mass))
        return self.vertical_veloc 

    def stop_falling(self, bottom):
        self.falling = False
        self.vertical_veloc = Vector2((0,0))
        self.pos.y = bottom-self.rect.height/2+5
        self.rect.center = self.pos

class FixedSprite(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.pos = pos
        self.fixed = True

class Player(FloatingSprite):

    PLAYER_MOVE_DIST = 10

    def __init__(self, pos):
        super().__init__(10, pos)
        self.image = pygame.image.load("panda.png")
        self.rect = self.image.get_rect()
        self.rect.center = self.pos
        self.prev_pos = Vector2(self.pos)

    def move(self):
        pressed_keys = pygame.key.get_pressed()
        update = None
        pos_change = Vector2((0,0))
        if pressed_keys[K_LEFT]:
            update = True
            pos_change -= ((Player.PLAYER_MOVE_DIST, 0))
        if pressed_keys[K_RIGHT]:
            update = True
            pos_change += ((Player.PLAYER_MOVE_DIST, 0))
        if pressed_keys[K_UP] and not self.falling:
            update = True
            self.jump(0,50)
        if pressed_keys[K_DOWN]:
            update = True
            pos_change += ((0, Player.PLAYER_MOVE_DIST))

        vertical_disp = self.move_vertically()
        if vertical_disp:
            update = True
            pos_change += vertical_disp
        if update:
            print(f"Moving {self.pos} + {pos_change}")
            self.prev_pos = self.pos
            self.pos += pos_change
            self.rect.center = self.pos
        del pos_change

    def undo_move(self):
        print(f"Undo move {self.pos} --> {self.prev_pos}")
        self.pos = self.prev_pos
        self.rect.midbottom = self.pos

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Tiger(pygame.sprite.Sprite):
    def __init__(self, speed_divider):
        super().__init__()
        self.image = pygame.image.load("tiger.png")
        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(40, WIDTH-40), 0)
        self.width = self.rect.width
        self.height = self.rect.height
        self.crt_pos = 0    # Represents current index in loop
        self.loop = list()
        self.speed_divider = speed_divider
        self.speed_idx = 0

    def deploy(self, obstacles, loop_radius):
        """
        The tiger moves in a loop on the map.
        We have to compute the loop when the tiger is instantiated on the
        environment.
        """
        # Select an initial position
        self.start_pos = Vector2((random.randint(self.width, WIDTH-self.width),
                                random.randint(self.height, HEIGHT-self.height)))
        # The loop is a circle where the initial position is the W-most point
        # TODO: ensure that the loop is entirely on the board
        # The tiger will move on the loop horizontally at width,height resolution
        x = -loop_radius
        delta_x = self.width
        while x < loop_radius:
            print(f"x={x}")
            y = math.sqrt(loop_radius**2 - x**2)
            print(f"y={y}")
            self.loop.append(Vector2((x, y)))
            x += delta_x
        x = loop_radius
        while x > -loop_radius:
            print(f"x={x}")
            y = -math.sqrt(loop_radius**2 - x**2)
            print(f"y={y}")
            self.loop.append(Vector2((x, y)))
            x -= delta_x

    def move(self):
        self.speed_idx += 1
        if self.speed_idx < self.speed_divider: return
        self.speed_idx = 0
        next_pos = self.loop[self.crt_pos]
        self.rect.midbottom = self.start_pos + next_pos
        self.crt_pos  = (self.crt_pos+1)%len(self.loop)
        print(f"Tiger pos: {self.crt_pos} --> {self.loop[self.crt_pos]}")

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Platform(FixedSprite):
    def __init__(self, pos, width, height):
        super().__init__(pos)
        self.surf = pygame.Surface((width, height))
        self.surf.fill((255, 0, 0))
        self.rect = self.surf.get_rect(center = pos, width=width, height=height)

    def draw(self, surface):
        surface.blit(self.surf, self.rect)

class EnvSprite(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def move(self, position):
        self.rect.midbottom = position

rock = pygame.image.load("rock.png") # 35x24 pixels
tree = pygame.image.load("tree.png") # 24x47 pixels
bush = pygame.image.load("bush.png")  # 42x21 pixels
env_comps = [rock, tree, bush]
env_comp_width = max([comp.get_rect().width for comp in [rock, tree, bush]])
env_comp_height = max([comp.get_rect().height for comp in [rock, tree, bush]])
MAX_COMPS_PER_SQUARE = 9
env_comp_sq_size = MAX_COMPS_PER_SQUARE * max(env_comp_width, env_comp_height)

def init_environment(surface):
    # Environment components are clustered.
    # At most 9 components per cluster.
    # We compute the maximum cluster size as a square.
    # The environment is divided into such squares, and each square
    # has an exponentially distributed number of components, where the mean
    # ensures that at most 40% of squares are occuppied by components.
    env_rect = surface.get_rect()
    horiz_squares = int(math.ceil(env_rect.width / env_comp_sq_size))
    vert_squares = int(math.ceil(env_rect.height / env_comp_sq_size))
    total_squares = horiz_squares * vert_squares
    print(f"Init environment: total squares = {total_squares}")
    mean_comp_per_sq = MAX_COMPS_PER_SQUARE
    print(f"Init environment: mean components per square = {mean_comp_per_sq}")
    env_clusters = []
    for vsq in range(vert_squares):
        for hsq in range(horiz_squares):
            num_comps = int(min(MAX_COMPS_PER_SQUARE, random.expovariate(1/mean_comp_per_sq)))
            print(f"Init environment: square {vsq}x{hsq} components={num_comps}")
            # deploy the components with equal probability
            cluster = pygame.sprite.Group()
            for i in range(num_comps):
                compx = random.randint(hsq*env_comp_sq_size, (hsq+1)*env_comp_sq_size)
                compy = random.randint(vsq*env_comp_sq_size, (vsq+1)*env_comp_sq_size)
                print(f"Init environment: component at {compx},{compy}")
                if compx > env_rect.width or compy > env_rect.height:
                    continue
                comp = EnvSprite(random.choice(env_comps))
                comp.move((compx, compy))
                #comp.draw(surface)
                cluster.add(comp)
            env_clusters.append(cluster)
    return env_clusters


pygame.init()

FramePerSec = pygame.time.Clock()
displaysurface = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Game")

P1 = Player(Vector2((200,200)))

all_sprites = pygame.sprite.Group()
all_sprites.add(P1)
#all_sprites.add(P1)

# Fixed sprites
fixed_sprites = pygame.sprite.Group()
fixed_sprites.add(Platform(Vector2((WIDTH/2,HEIGHT-100)), WIDTH, 50))
fixed_sprites.add(Platform(Vector2((WIDTH/2,HEIGHT-250)), 100, 10))

# Game loop
#env_clusters = pygame.sprite.RenderUpdates()
#env_clusters.draw(displaysurface)

while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

        if event.type == KEYDOWN:
            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[K_q]:
                pygame.quit()
                sys.exit()

    P1.move()
    # Implement falling
    coll_sprite = pygame.sprite.spritecollideany(P1, fixed_sprites)
    if coll_sprite:
        P1.stop_falling(coll_sprite.rect.top)
    else:
        P1.falling = True
        print("Falling")

    # Gravity implementation
    # --- any sprite that is not fixed will fall until it meets 

    displaysurface.fill((0,100,0))
    for entity in all_sprites:
        entity.draw(displaysurface)
    for entity in fixed_sprites:
        entity.draw(displaysurface)

    pygame.display.flip()
    FramePerSec.tick(FPS)
