#!/usr/bin/env python3
import curses
import time
import random
from collections import namedtuple

Point = namedtuple('Point', ['y', 'x'])

class GameObject:
    def __init__(self, y, x, char):
        self.y = y
        self.x = x
        self.char = char
        self.dy = 0
        self.dx = 0

class Ghost(GameObject):
    def __init__(self, y, x, char='n'):
        super().__init__(y, x, char)
        self.frightened = False
        self.frightened_time = 0
        
class PacMan(GameObject):
    def __init__(self, y, x, char='c'):
        super().__init__(y, x, char)
        self.next_dy = 0
        self.next_dx = 0

class Game:
    def __init__(self, stdscr, map_file):
        self.stdscr = stdscr
        self.load_map(map_file)
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
        self.power_mode_time = 0
        self.pellets_remaining = 0
        self.speed = 0.15
        
        # Level system
        self.level = 1
        self.extra_life_awarded = False
        
        # Fruit mechanics
        self.fruit_spawn_time = 0
        self.fruit_active = False
        self.dots_eaten = 0
        self.fruit_triggered_70 = False
        self.fruit_triggered_170 = False
        
        # Initialize game objects
        self.pacman = None
        self.ghosts = []
        self.fruit = None
        self.pellets = set()
        self.power_pills = set()
        self.initial_pellets = set()
        self.initial_power_pills = set()
        self.initial_fruit = None
        
        # Warp tunnel positions
        self.warp_left = None  # Position of '<'
        self.warp_right = None  # Position of '>'
        
        # Store starting positions
        self.pacman_start = None
        self.ghost_starts = []
        
        self.parse_map()
        
        # Setup colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Pacman
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Walls
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Pellets
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)     # Ghosts
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Frightened ghosts
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Fruit
        curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Power pills
        
    def load_map(self, map_file):
        with open(map_file, 'r') as f:
            lines = f.readlines()
        self.original_map = [list(line.rstrip('\n')) for line in lines]
        self.height = len(self.original_map)
        self.width = max(len(row) for row in self.original_map)
        
        # Pad rows to equal width
        for row in self.original_map:
            while len(row) < self.width:
                row.append(' ')
    
    def parse_map(self):
        for y, row in enumerate(self.original_map):
            for x, char in enumerate(row):
                if char == 'c':
                    self.pacman_start = Point(y, x)
                    self.pacman = PacMan(y, x)
                    self.original_map[y][x] = ' '
                elif char == 'n':
                    self.ghost_starts.append(Point(y, x))
                    self.ghosts.append(Ghost(y, x))
                    self.original_map[y][x] = ' '
                elif char == '@':
                    self.fruit = Point(y, x)
                    self.initial_fruit = Point(y, x)
                    self.original_map[y][x] = ' '  # Remove @ from map so it's not counted elsewhere
                elif char == '<':
                    self.warp_left = Point(y, x)
                    self.original_map[y][x] = ' '
                elif char == '>':
                    self.warp_right = Point(y, x)
                    self.original_map[y][x] = ' '
                elif char == '.':
                    self.pellets.add(Point(y, x))
                    self.initial_pellets.add(Point(y, x))
                elif char == 'o':
                    self.power_pills.add(Point(y, x))
                    self.initial_power_pills.add(Point(y, x))
        
        self.pellets_remaining = len(self.pellets) + len(self.power_pills)
    
    def draw(self):
        self.stdscr.erase()
        
        # Draw map
        for y, row in enumerate(self.original_map):
            for x, char in enumerate(row):
                if char == '#':
                    # Use line drawing characters
                    self.stdscr.addch(y, x, curses.ACS_CKBOARD, curses.color_pair(2))
                elif char == ' ':
                    self.stdscr.addch(y, x, ' ')
        
        # Draw fruit
        if self.fruit and self.fruit_active:
            self.stdscr.addch(self.fruit.y, self.fruit.x, '*', curses.color_pair(6))
        
        # Draw pellets
        for pellet in self.pellets:
            self.stdscr.addch(pellet.y, pellet.x, '.', curses.color_pair(3))
        
        # Draw power pills
        for pill in self.power_pills:
            self.stdscr.addch(pill.y, pill.x, 'O', curses.color_pair(7) | curses.A_BOLD)
        
        # Draw ghosts
        for ghost in self.ghosts:
            if ghost.frightened:
                self.stdscr.addch(ghost.y, ghost.x, 'M', curses.color_pair(5))
            else:
                self.stdscr.addch(ghost.y, ghost.x, 'W', curses.color_pair(4) | curses.A_BOLD)
        
        # Draw pacman
        if self.pacman:
            self.stdscr.addch(self.pacman.y, self.pacman.x, 'C', curses.color_pair(1) | curses.A_BOLD)
        
        # Draw score and lives at top
        score_str = f"Score: {self.score} - Level: {self.level} - Lives: {self.lives}"
        self.stdscr.addstr(0, (self.width - len(score_str)) // 2, score_str, curses.A_BOLD)
        
        if self.game_over:
            msg = "GAME OVER - Hit R to restart, Q to quit"
            self.stdscr.addstr(self.height // 2, (self.width - len(msg)) // 2, msg, curses.A_BOLD)

        if self.won:
            msg = "LEVEL UP - Hit SPACE to continue, Q to quit"
            self.stdscr.addstr(self.height // 2, (self.width - len(msg)) // 2, msg, curses.A_BOLD)
        
        self.stdscr.refresh()
    
    def is_wall(self, y, x):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.original_map[y][x] == '#'
        return True
    
    def is_valid_move(self, y, x):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.original_map[y][x] != '#'
        return False
    
    def move_pacman(self):
        if not self.pacman:
            return
        
        # Try to change direction if new direction pressed
        if self.pacman.next_dy != 0 or self.pacman.next_dx != 0:
            new_y = self.pacman.y + self.pacman.next_dy
            new_x = self.pacman.x + self.pacman.next_dx
            
            if self.is_valid_move(new_y, new_x):
                self.pacman.dy = self.pacman.next_dy
                self.pacman.dx = self.pacman.next_dx
                self.pacman.next_dy = 0
                self.pacman.next_dx = 0
        
        # Continue in current direction
        if self.pacman.dy != 0 or self.pacman.dx != 0:
            new_y = self.pacman.y + self.pacman.dy
            new_x = self.pacman.x + self.pacman.dx
            
            # Check if we're at a warp tunnel entrance
            current_pos = Point(self.pacman.y, self.pacman.x)
            if self.warp_left and self.warp_right:
                if current_pos == self.warp_left and self.pacman.dx < 0:
                    # Warp from left to right
                    self.pacman.y = self.warp_right.y
                    self.pacman.x = self.warp_right.x
                    return
                elif current_pos == self.warp_right and self.pacman.dx > 0:
                    # Warp from right to left
                    self.pacman.y = self.warp_left.y
                    self.pacman.x = self.warp_left.x
                    return
            
            # Normal movement
            if self.is_valid_move(new_y, new_x):
                self.pacman.y = new_y
                self.pacman.x = new_x
            else:
                # Hit a wall, stop
                self.pacman.dy = 0
                self.pacman.dx = 0
        
        # Check for pellet collection
        pos = Point(self.pacman.y, self.pacman.x)
        if pos in self.pellets:
            self.pellets.remove(pos)
            self.score += 10
            self.pellets_remaining -= 1
            self.dots_eaten += 1
            self.check_extra_life()
            
            # Check for fruit spawn triggers
            if self.dots_eaten == 70 and not self.fruit_triggered_70:
                self.spawn_fruit()
                self.fruit_triggered_70 = True
            elif self.dots_eaten == 170 and not self.fruit_triggered_170:
                self.spawn_fruit()
                self.fruit_triggered_170 = True
        
        # Check for power pill
        if pos in self.power_pills:
            self.power_pills.remove(pos)
            self.score += 50
            self.pellets_remaining -= 1
            self.dots_eaten += 1
            self.check_extra_life()
            
            # Check for fruit spawn triggers
            if self.dots_eaten == 70 and not self.fruit_triggered_70:
                self.spawn_fruit()
                self.fruit_triggered_70 = True
            elif self.dots_eaten == 170 and not self.fruit_triggered_170:
                self.spawn_fruit()
                self.fruit_triggered_170 = True
            
            self.power_mode_time = time.time()
            for ghost in self.ghosts:
                ghost.frightened = True
        
        # Check for fruit
        if self.fruit and self.fruit_active and pos.y == self.fruit.y and pos.x == self.fruit.x:
            self.score += 100
            self.fruit_active = False
            self.check_extra_life()
        
        # Check win condition
        if self.pellets_remaining == 0:
            self.won = True
    
    def check_extra_life(self):
        """Award extra life at 10,000 points"""
        if not self.extra_life_awarded and self.score >= 10000:
            self.lives += 1
            self.extra_life_awarded = True
    
    def next_level(self):
        """Advance to the next level"""
        self.level += 1
        self.won = False
        self.power_mode_time = 0
        
        # Reset fruit mechanics for new level
        self.fruit_spawn_time = 0
        self.fruit_active = False
        self.dots_eaten = 0
        self.fruit_triggered_70 = False
        self.fruit_triggered_170 = False
        
        # Reset pellets and power pills to initial state
        self.pellets = self.initial_pellets.copy()
        self.power_pills = self.initial_power_pills.copy()
        self.pellets_remaining = len(self.pellets) + len(self.power_pills)
        
        # Reset fruit to initial position (but not active)
        if hasattr(self, 'initial_fruit') and self.initial_fruit:
            self.fruit = self.initial_fruit
        
        # Reset positions
        self.reset_positions()
        
        # Increase difficulty slightly (make ghosts a bit faster)
        self.speed = max(0.08, self.speed - 0.01)
    
    def spawn_fruit(self):
        """Spawn the fruit and start the 10-second timer"""
        if self.initial_fruit:
            self.fruit_active = True
            self.fruit_spawn_time = time.time()
    
    def update_fruit(self):
        """Check if fruit timer has expired"""
        if self.fruit_active and time.time() - self.fruit_spawn_time > 10:
            self.fruit_active = False
    
    def get_valid_directions(self, y, x):
        directions = []
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_y, new_x = y + dy, x + dx
            if self.is_valid_move(new_y, new_x):
                directions.append((dy, dx))
        return directions
    
    def is_junction(self, y, x):
        return len(self.get_valid_directions(y, x)) > 2
    
    def move_ghosts(self):
        current_time = time.time()
        
        # Check if power mode expired
        if self.power_mode_time > 0 and current_time - self.power_mode_time > 6:
            self.power_mode_time = 0
            for ghost in self.ghosts:
                ghost.frightened = False
        
        # Update fruit timer
        self.update_fruit()
        
        for ghost in self.ghosts:
            # Store old position for crossing detection
            old_ghost_y = ghost.y
            old_ghost_x = ghost.x
            
            # Initialize ghost movement if not moving
            if ghost.dy == 0 and ghost.dx == 0:
                directions = self.get_valid_directions(ghost.y, ghost.x)
                if directions:
                    ghost.dy, ghost.dx = random.choice(directions)
            
            # Random chance to change direction at junction
            if self.is_junction(ghost.y, ghost.x) and random.random() < 0.3:
                directions = self.get_valid_directions(ghost.y, ghost.x)
                # Remove opposite direction
                if directions:
                    opposite = (-ghost.dy, -ghost.dx)
                    directions = [d for d in directions if d != opposite]
                    if directions:
                        ghost.dy, ghost.dx = random.choice(directions)
            
            # Try to move
            new_y = ghost.y + ghost.dy
            new_x = ghost.x + ghost.dx
            
            # Check if we're at a warp tunnel entrance
            current_pos = Point(ghost.y, ghost.x)
            if self.warp_left and self.warp_right:
                if current_pos == self.warp_left and ghost.dx < 0:
                    # Warp from left to right
                    ghost.y = self.warp_right.y
                    ghost.x = self.warp_right.x
                    # Check collision after warp
                    if self.check_ghost_collision_with_crossing(ghost, old_ghost_y, old_ghost_x):
                        self.handle_collision(ghost)
                        if self.game_over:
                            return
                    continue
                elif current_pos == self.warp_right and ghost.dx > 0:
                    # Warp from right to left
                    ghost.y = self.warp_left.y
                    ghost.x = self.warp_left.x
                    # Check collision after warp
                    if self.check_ghost_collision_with_crossing(ghost, old_ghost_y, old_ghost_x):
                        self.handle_collision(ghost)
                        if self.game_over:
                            return
                    continue
            
            # Normal movement
            if self.is_valid_move(new_y, new_x):
                ghost.y = new_y
                ghost.x = new_x
                
                # Check for collision after each ghost moves (including crossing detection)
                if self.check_ghost_collision_with_crossing(ghost, old_ghost_y, old_ghost_x):
                    self.handle_collision(ghost)
                    if self.game_over:
                        return
            else:
                # Hit a wall, choose new random direction
                directions = self.get_valid_directions(ghost.y, ghost.x)
                if directions:
                    ghost.dy, ghost.dx = random.choice(directions)
    
    def check_collisions(self):
        if not self.pacman:
            return
        
        for ghost in self.ghosts[:]:
            # Check if they occupy the same position
            if ghost.y == self.pacman.y and ghost.x == self.pacman.x:
                self.handle_collision(ghost)
                return
    
    def check_ghost_collision_with_crossing(self, ghost, old_ghost_y, old_ghost_x):
        """Check if pacman and ghost crossed paths (edge case detection)"""
        if not self.pacman:
            return False
        
        # Check if they're now at the same position
        if ghost.y == self.pacman.y and ghost.x == self.pacman.x:
            return True
        
        # Check if they crossed paths (swapped positions)
        # This happens when they move towards each other and pass through
        pacman_old_y = self.pacman.y - self.pacman.dy
        pacman_old_x = self.pacman.x - self.pacman.dx
        
        # Did pacman move from where ghost is now, and ghost move from where pacman is now?
        if (pacman_old_y == ghost.y and pacman_old_x == ghost.x and
            old_ghost_y == self.pacman.y and old_ghost_x == self.pacman.x):
            return True
        
        return False
    
    def handle_collision(self, ghost):
        """Handle collision between pacman and a ghost"""
        if ghost.frightened:
            # Eat ghost
            self.score += 200
            # Respawn ghost at its starting position
            ghost_index = self.ghosts.index(ghost)
            if ghost_index < len(self.ghost_starts):
                ghost.y = self.ghost_starts[ghost_index].y
                ghost.x = self.ghost_starts[ghost_index].x
            ghost.frightened = False
            ghost.dy = 0
            ghost.dx = 0
        else:
            # Lose a life
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                # Reset positions
                self.reset_positions()
    
    def reset_positions(self):
        # Reset pacman to starting position
        if self.pacman_start:
            self.pacman.y = self.pacman_start.y
            self.pacman.x = self.pacman_start.x
        
        self.pacman.dy = 0
        self.pacman.dx = 0
        self.pacman.next_dy = 0
        self.pacman.next_dx = 0
        
        # Reset ghosts to their starting positions
        for i, ghost in enumerate(self.ghosts):
            if i < len(self.ghost_starts):
                ghost.y = self.ghost_starts[i].y
                ghost.x = self.ghost_starts[i].x
            ghost.dy = 0
            ghost.dx = 0
            ghost.frightened = False
        
        self.power_mode_time = 0
    
    def reset_game(self):
        # Reset game state
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
        self.power_mode_time = 0
        
        # Reset pellets and power pills to initial state
        self.pellets = self.initial_pellets.copy()
        self.power_pills = self.initial_power_pills.copy()
        self.pellets_remaining = len(self.pellets) + len(self.power_pills)
        
        # Reset fruit to initial position
        # Find it from the stored initial position
        if hasattr(self, 'initial_fruit') and self.initial_fruit:
            self.fruit = self.initial_fruit
        
        # Reset positions
        self.reset_positions()
    
    def run(self):
        self.stdscr.nodelay(1)
        self.stdscr.keypad(1)
        curses.curs_set(0)
        
        last_move_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Handle input
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                if self.game_over or self.won:
                    self.reset_game()
                    last_move_time = time.time()
            elif key == ord(' '):
                if self.won:
                    self.next_level()
                    last_move_time = time.time()
            elif not self.game_over and not self.won:
                if key == curses.KEY_UP:
                    self.pacman.next_dy = -1
                    self.pacman.next_dx = 0
                elif key == curses.KEY_DOWN:
                    self.pacman.next_dy = 1
                    self.pacman.next_dx = 0
                elif key == curses.KEY_LEFT:
                    self.pacman.next_dy = 0
                    self.pacman.next_dx = -1
                elif key == curses.KEY_RIGHT:
                    self.pacman.next_dy = 0
                    self.pacman.next_dx = 1
            
            # Update game state
            if not self.game_over and not self.won:
                if current_time - last_move_time >= self.speed:
                    self.move_pacman()
                    self.move_ghosts()
                    # Final collision check after all movements
                    self.check_collisions()
                    last_move_time = current_time
            
            self.draw()
            time.sleep(0.01)

def main(stdscr):
    game = Game(stdscr, 'pacman-map.txt')
    game.run()

if __name__ == '__main__':
    curses.wrapper(main)
