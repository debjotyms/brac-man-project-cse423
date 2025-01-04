from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import time
import random
import math
import os
#Game constants
WIN_WIDTH,WIN_HEIGHT= 800,800
PACMAN_RADIUS =15
ENEMY_RADIUS= 10
POINT_RADIUS=5
BONUS_POINT_RADIUS= 10
PACMAN_SPEED=2 
ENEMY_SPEED= 3
WALL_PADDING =2

#Add power-up constants
POWER_UP_RADIUS= 10
POWER_UP_DURATION =10  #seconds
POWER_UP_SPAWN_CHANCE= 0.002  #0.2% chance per frame

def find_zone(x1, y1,x2,y2):
    dx =x2 -x1
    dy= y2- y1
    if abs(dx)> abs(dy):
        if dx >0 and dy>0:
            return 0
        elif dx<0 and dy >0:
            return 3
        elif dx<0 and dy<0:
            return 4
        elif dx >0 and dy< 0:
            return 7
    else:
        if dx> 0 and dy> 0:
            return 1
        elif dx < 0 and dy >0:
            return 2
        elif dx <0 and dy < 0:
            return 5
        elif dx>0 and dy< 0:
            return 6
    return 0

def convert_to_zone0(x,y,zone):
    
    
    if zone ==0:
        return x,y
    elif zone== 1:
        return y, x
    elif zone== 2:
        return y,-x
    elif zone ==3:
        return -x,y
    elif zone== 4:
        return -x,-y
    elif zone== 5:
        return -y,-x
    elif zone ==6:
        return -y,x
    elif zone== 7:
        return x, -y
    return x,y

def convert_from_zone0(x, y,zone):
    if zone== 0:
        return x,y
    elif zone== 1:
        return y,x
    elif zone ==2:
        return -y,x
    elif zone== 3:
        return -x,y
    elif zone ==4:
        return -x, -y
    elif zone== 5:
        return -y,-x
    elif zone== 6:
        return y,-x
    elif zone== 7:
        return x,-y
    return x,y

def midpoint_line(x1, y1,x2, y2,zone):
    points = []
    dx=x2 -x1
    dy= y2 -y1
    d= 2*dy -dx  #decision variable
    incE =2*dy    #Increment for moving to east pixel
    incNE= 2*(dy -dx)  #increment for moving to north-east pixel
    
    x=x1
    y=y1
    
    #add initial point
    cx, cy = convert_from_zone0(x, y, zone)
    points.append((cx, cy))
    
    while x<x2:
        if d<=0:
            d+=incE
            x += 1
        else:
            d+=incNE
            x +=1
            y+=1
            
        cx,cy =convert_from_zone0(x,y, zone)
        points.append((cx,cy))
    
    return points

def mpl_points(x1,y1, x2,y2):
    #special cases first handle 
    if x1 ==x2:  #vertical line
        y_start,y_end= min(y1,y2),max(y1,y2)
        return [(x1,y) for y in range(y_start,y_end +1)]
    
    if y1==y2:  #horizontal line
        x_start,x_end =min(x1, x2), max(x1, x2)
        return [(x, y1) for x in range(x_start, x_end + 1)]
    
    #find the zone and convert points
    zone =find_zone(x1, y1, x2, y2)
    x1_conv,y1_conv=convert_to_zone0(x1, y1, zone)
    x2_conv, y2_conv =convert_to_zone0(x2, y2, zone)
    
    #ensure points are in correct order (left to right)
    if x1_conv>x2_conv:
        x1_conv,x2_conv= x2_conv,x1_conv
        y1_conv,y2_conv =y2_conv,y1_conv
    
    #draw the line using midpoint algorithm
    return midpoint_line(x1_conv, y1_conv, x2_conv, y2_conv, zone)

def circle_points(x, y, cx, cy, points):
    points.extend([
        (x + cx, y + cy),   # zone 1 (native zone)
        (y + cx, x + cy),   # zone 0
        (y + cx, -x + cy),  # zone 7
        (x + cx, -y + cy),  # zone 6
        (-x + cx, -y + cy), # zone 5
        (-y + cx, -x + cy), # zone 4
        (-y + cx, x + cy),  # zone 3
        (-x + cx, y + cy)   # zone 2
    ])

def mpc_points(cx,cy,radius):
    points =[]
    d=1-radius  #Initial decision variable
    x=0
    y =radius
    
    #plot initial points at (0,r)
    circle_points(x,y,cx, cy,points)
    
    # Continue while x< y
    while x<y:
        if d< 0:
            # Move to east pixel
            d =d+2*x +3
            x=x +1
        else:
            # Move to south-east pixel
            d= d+2*x - 2*y+5
            x = x +1
            y=y -1
        
        circle_points(x,y, cx,cy,points)
    
    return points
    

# Game states
MENU= 0
PLAYING =1
GAME_OVER= 2
GAME_WON =3  
class GameState:
    def __init__(self):
        self.score= 0 
        self.lives =3
        self.start_time =time.time()
        self.last_teleport_time =time.time()
        self.game_over= False
        self.enemies_can_move= False
        self.pacman_x, self.pacman_y =40,40
        self.keys={'w': False, 'a': False, 's': False, 'd': False}
        self.game_state= MENU
        self.speed_multiplier =2.0  # Default easy mode
        self.power_ups =[]
        self.is_powered_up= False
        self.power_up_end_time =0
        self.reset_game()


    def reset_game(self):
        #New game start
        self.score = 0
        self.lives = 3
        self.start_time = time.time()
        self.last_teleport_time = time.time()  # Reset teleport timer
        self.enemies_can_move = False
        self.pacman_x, self.pacman_y = 40, 40
        self.keys = {'w': False, 'a': False, 's': False, 'd': False}
        self.walls = [
            # Outer walls
            (0, 0, WIN_WIDTH, 0),
            (0, WIN_HEIGHT, WIN_WIDTH, WIN_HEIGHT),
            (0, 0, 0, WIN_HEIGHT),
            (WIN_WIDTH, 0, WIN_WIDTH, WIN_HEIGHT),

            #inner vertical walls
            (100,100,100,250),
            (100,350,100,700),
            
            (200, 200,200, 250),
            (200, 350, 200,450),
            (200,550, 200, 700),
            
            (300, 100,300, 150),
            (300,250, 300, 450),
            (300, 550, 300, 650),
            
            (400,100, 400,250),
            (400, 350, 400, 550),
            
            (500, 200,500, 350),
            (500,450, 500,650),
            
            (600,100,600, 150),
            (600, 250, 600,550),
            (600,650,600, 700),
            
            (700,100,700,250),
            (700,350, 700,650),

            #inner horizontal walls
            (100, 100, 250, 100),
            (350, 100, 700, 100),
            
            (200,200, 350,200),
            (450, 200,600,200),
            
            (100, 300, 150,300),
            (250,300, 450,300),
            (550, 300, 700,300),
            
            (200,400,250, 400),
            (350,400, 550,400),
            
            (100, 500,150, 500),
            (250,500, 450, 500),
            (550, 500,650, 500),
            
            (200,600, 350,600),
            (450,600,550, 600),
            
            (100,700, 250,700),
            (350,700,650, 700),
     
        ]
        self.regular_points =[]
        self.bonus_points= []
        self.power_ups= []
        self.is_powered_up=False
        self.power_up_end_time=0
        self.generate_points()
        self.enemies= self.initialize_enemies()
        
    def set_difficulty(self,is_hard_mode):
        self.speed_multiplier=5.0 if is_hard_mode else 2.0
        self.reset_game()


    def draw_pacman(self):
        glColor3f(1.0, 1.0,0.0)  # Yellow color
        
        #Calculate mouth animation (etween 0 and 50 degrees)
        time_factor =math.sin(time.time() * 10)  #Ranges from -1 to 1
        mouth_angle=25 *(1 +time_factor)      #Rangesfrom 0 to 50
        
        #Determine mouth direction with clear conditions
        mouth_direction=0  #Default right direction
        if self.keys['w']:
            if not self.keys['a'] and not self.keys['d']:  # Only if not moving diagonally
                mouth_direction=90
        elif self.keys['s']:
            if not self.keys['a'] and not self.keys['d']:
                mouth_direction =270
        elif self.keys['a']:
            mouth_direction=180
        elif self.keys['d']:
            mouth_direction=0

        #Draw Pac-Man using points
        glBegin(GL_POINTS)
        
        circle_points = mpc_points(self.pacman_x, self.pacman_y, PACMAN_RADIUS)
        
        #Process each point to create mouth effect
        for x,y in circle_points:
            #Calculate angle of current point relative to center
            dx = x -self.pacman_x
            dy = y- self.pacman_y
            angle= math.degrees(math.atan2(dy, dx))
            
            #make sure angle is positive (0 to 360)
            if angle< 0:
                angle+= 360
            
            #adjust angle based on mouth direction
            adjusted_angle = (angle - mouth_direction) % 360
            
            # Determine if point should be drawn (outside mouth opening)
            should_draw= True
            if adjusted_angle <=mouth_angle:  #in lower mouth opening
                should_draw= False
            if adjusted_angle>= (360 -mouth_angle):  # In upper mouth opening
                should_draw =False
                
            if should_draw:
                glVertex2f(x,y)
                
        glEnd()


    def generate_points(self):
        #Generate regular points with smaller grid size
        grid_size =50  #Reduced from 100 to 50 for more points
        for x in range(grid_size,WIN_WIDTH -grid_size,grid_size):
            for y in range(grid_size,WIN_HEIGHT-grid_size,grid_size):
                #add extra check for minimum wall distance
                if not self.is_point_in_wall(x,y) and self.is_point_clear(x,y):
                    self.regular_points.append({"pos": (x,y), "value": 5})

        #Generate bonus points in strategic locations
        bonus_locations=[
            (WIN_WIDTH- 50, WIN_HEIGHT -50),
            (50, WIN_HEIGHT -50),
            (WIN_WIDTH -50,50),
            (50,50),
            (WIN_WIDTH//2, WIN_HEIGHT- 50),
            (WIN_WIDTH//2, 50),
            (50, WIN_HEIGHT //2),
            (WIN_WIDTH -50,WIN_HEIGHT//2)
        ]

        for pos in bonus_locations:
            if not self.is_point_in_wall(pos[0],pos[1]):
                self.bonus_points.append({"pos":pos,"value":20})

    def is_point_in_wall(self,x,y):
        for wall in self.walls:
            x1,y1,x2, y2= wall
            if x1==x2:  #Vertical wall
                if abs(x -x1) <= POINT_RADIUS * 2 and min(y1,y2) <= y<= max(y1,y2):
                    return True
            elif y1== y2:  # Horizontal wall
                if abs(y- y1) <=POINT_RADIUS * 2 and min(x1, x2) <=x <= max(x1, x2):
                    return True
        return False
    
    def is_point_clear(self,x, y):
        #check if point has enough clearance from walls
        MIN_WALL_DISTANCE = 20  # Minimum distance from walls
        
        for wall in self.walls:
            x1,y1,x2, y2 =wall
            if x1== x2:  # Vertical wall
                if abs(x-x1)<= MIN_WALL_DISTANCE:
                    return False
            elif y1==y2:  # Horizontal wall
                if abs(y -y1) <=MIN_WALL_DISTANCE:
                    return False
        return True

    def get_random_valid_position(self):
        while True:
            x =random.randint(ENEMY_RADIUS *2, WIN_WIDTH -ENEMY_RADIUS* 2)
            y= random.randint(ENEMY_RADIUS *2, WIN_HEIGHT- ENEMY_RADIUS *2)
            
            #Check if position is valid (not in wall and not too close to Pacman)
            if not self.check_wall_collision(x, y,ENEMY_RADIUS):
                dist_to_pacman = math.sqrt((x- self.pacman_x)**2 +(y -self.pacman_y)**2)
                if dist_to_pacman >100:  # Minimum distance from Pacman
                    return x,y
    def check_win_condition(self):
        #modified to only check if all enemies are eaten
        if len(self.enemies)== 0:  # All enemies eaten
            self.game_state =GAME_WON
            return True
        return False

    def check_wall_collision(self,x, y,radius):
        for wall in self.walls:
            x1,y1, x2,y2 = wall
            if x1 ==x2:  # Vertical wall
                if abs(x -x1) <= radius +WALL_PADDING and min(y1,y2)<= y<= max(y1, y2):
                    return True
            elif y1== y2:  # Horizontal wall
                if abs(y-y1) <=radius + WALL_PADDING and min(x1,x2)<=x<= max(x1,x2):
                    return True
        return False

    def teleport_enemies(self):
        current_time=time.time()
        if self.speed_multiplier >2.0 and current_time-self.last_teleport_time >= 7:
            self.last_teleport_time = current_time
            
            # Visual effect before teleporting
            glutPostRedisplay()
            
            # Teleport each enemy
            for enemy in self.enemies:
                new_x,new_y =self.get_random_valid_position()
                enemy['x']= new_x
                enemy['y'] =new_y
                enemy['direction'] = random.choice(['up', 'down', 'left', 'right'])


    def move_pacman(self):
        new_x, new_y = self.pacman_x, self.pacman_y
        current_speed = PACMAN_SPEED * self.speed_multiplier
        
        if self.keys['w']:
            new_y+=current_speed
        if self.keys['s']:
            new_y-= current_speed
        if self.keys['a']:
            new_x -=current_speed
        if self.keys['d']:
            new_x+= current_speed

        if not self.check_wall_collision(new_x,new_y,PACMAN_RADIUS):
            self.pacman_x,self.pacman_y = new_x,new_y

    def move_enemies(self):
        # Add teleportation check
        self.teleport_enemies()
        
        for enemy in self.enemies:
            new_x,new_y = enemy['x'],enemy['y']
            current_direction = enemy['direction']
            current_speed= ENEMY_SPEED *self.speed_multiplier
            
            if current_direction =='up':
                new_y +=current_speed
            elif current_direction== 'down':
                new_y-= current_speed
            elif current_direction=='left':
                new_x -= current_speed
            elif current_direction =='right':
                new_x +=current_speed

            if self.check_wall_collision(new_x, new_y,ENEMY_RADIUS) or random.random() <0.02:
                available_directions = []
                for direction in ['up', 'down', 'left', 'right']:
                    test_x, test_y = enemy['x'], enemy['y']
                    if direction =='up':
                        test_y+= current_speed
                    elif direction=='down':
                        test_y -= current_speed
                    elif direction== 'left':
                        test_x-= current_speed
                    elif direction =='right':
                        test_x +=current_speed
                    
                    if not self.check_wall_collision(test_x,test_y,ENEMY_RADIUS):
                        available_directions.append(direction)

                if available_directions:
                    enemy['direction'] =random.choice(available_directions)
                    new_x, new_y=enemy['x'], enemy['y']
            
            if not self.check_wall_collision(new_x, new_y, ENEMY_RADIUS):
                enemy['x'], enemy['y'] = new_x, new_y

    def initialize_enemies(self):
        return [
            {
                'x':WIN_WIDTH-ENEMY_RADIUS * 4,
                'y': WIN_HEIGHT-ENEMY_RADIUS * 4,
                'direction':'left'
            },
            {
                'x':ENEMY_RADIUS* 4,
                'y': WIN_HEIGHT-ENEMY_RADIUS * 4,
                'direction': 'right'
            },
            {
                'x': WIN_WIDTH -ENEMY_RADIUS* 4,
                'y':ENEMY_RADIUS * 4,
                'direction': 'up'
            },
            {
                'x':ENEMY_RADIUS* 4,
                'y':ENEMY_RADIUS *4,
                'direction': 'down'
            }
        ]

    def check_collisions(self):
        #Check all game collisions with clear sections
        #check regular point collisions
        self._check_point_collisions()
        
        #check power-up collisions
        self._check_powerup_collisions()
        
        #check enemy collisions
        self._check_enemy_collisions()

    def _check_point_collisions(self):
        #Check regular points
        for point in self.regular_points[:]:
            x,y =point["pos"]
            # Calculate distance between pacman and point
            distance =math.sqrt((self.pacman_x - x)**2 + (self.pacman_y - y)**2)
            
            # If pacman touches the point
            if distance<=(PACMAN_RADIUS+ POINT_RADIUS):
                self.regular_points.remove(point)
                self.score +=point["value"]

        # Check bonus points
        for point in self.bonus_points[:]:
            x, y =point["pos"]
            # Calculate distance for bonus points
            distance= math.sqrt((self.pacman_x -x)**2 +(self.pacman_y-y)**2)
            
            # If pacman touches the bonus point
            if distance<=(PACMAN_RADIUS + BONUS_POINT_RADIUS):
                self.bonus_points.remove(point)
                self.score+=point["value"]

    def _check_powerup_collisions(self):
        #Handle power-up collision
        for power_up in self.power_ups[:]:
            px,py =power_up['pos']
            distance_squared= (self.pacman_x -px)**2 +(self.pacman_y- py)**2
            collision_distance=(PACMAN_RADIUS +POWER_UP_RADIUS)**2
            
            if distance_squared <=collision_distance:
                self.collect_power_up(power_up)

    def _check_enemy_collisions(self):
        """Handle enemy collisions with power-up state"""
        for enemy in self.enemies[:]:
            distance_squared =(self.pacman_x -enemy['x'])**2+(self.pacman_y-enemy['y'])**2
            collision_distance =(PACMAN_RADIUS + ENEMY_RADIUS)**2
            
            if distance_squared<= collision_distance:
                if self.is_powered_up:
                    #eat enemy
                    self.enemies.remove(enemy)
                    self.score+=100
                    
                    #Check for win condition
                    if len(self.enemies)== 0:
                        self.game_state =GAME_WON
                else:
                    # Enemy kills Pac-Man
                    self.lives-= 1
                    self.pacman_x,self.pacman_y= 60, 60  # Reset position
                    
                    if self.lives <= 0:
                        self.game_state = GAME_OVER

    def update_power_ups(self):
        current_time = time.time()
        
        #Check if power-up effect has expired
        if self.is_powered_up and current_time > self.power_up_end_time:
            self.is_powered_up = False
        
        # Random chance to spawn new power-up
        if random.random()< POWER_UP_SPAWN_CHANCE:
            x,y= self.get_random_valid_position()
            self.power_ups.append({'pos': (x, y)})

    def collect_power_up(self, power_up):
        #Remove the collected power-up
        self.power_ups.remove(power_up)
        
        #Activate power-up effect
        self.is_powered_up = True
        
        #Set expiration time
        current_time = time.time()
        self.power_up_end_time = current_time + POWER_UP_DURATION


def draw_menu():
    #Menu screen 
    glClear(GL_COLOR_BUFFER_BIT)
    glColor3f(1.0, 1.0, 0.0)  #Yellow text
    
    title ="CSE423 Project (Group 9) "
    glRasterPos2f(WIN_WIDTH//2 -70, WIN_HEIGHT//2+100)
    for char in title:
        glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(char))
        
    title = "Welcome to BRAC-MAN"
    glRasterPos2f(WIN_WIDTH//2-60, WIN_HEIGHT//2+50)
    for char in title:
        glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(char))
        
    
    menu_items= [
        "PLAY",
        "EASY MODE" if game_state.speed_multiplier==2.0 else "HARD MODE",
        "EXIT"
    ]
    
    for i, item in enumerate(menu_items):
        y_pos = WIN_HEIGHT//2 -i * 50
        glRasterPos2f(WIN_WIDTH//2- 40,y_pos)
        for char in item:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))


def check_menu_click(x,y):
    # Convert window coordinates to OpenGL coordinates
    y = WIN_HEIGHT- y
    
    # Check each menu item
    for i in range(3):
        item_y = WIN_HEIGHT//2 - i * 50
        if WIN_WIDTH//2-40 <=x<=WIN_WIDTH//2 + 40 and item_y-10 <=y<=item_y +10:
            if i== 0:  # PLAY
                game_state.game_state =PLAYING
            elif i ==1:  # DIFFICULTY
                game_state.set_difficulty(game_state.speed_multiplier == 2.0)
            elif i== 2:  # EXIT
                os._exit(0)

def mouse_click(button, state, x, y):
    if button ==GLUT_LEFT_BUTTON and state== GLUT_DOWN:
        if game_state.game_state ==MENU:
            check_menu_click(x, y)


# Drawing functions
def draw_circle(cx,cy,radius):
    glBegin(GL_POINTS)
    for x, y in mpc_points(cx,cy, radius):
        glVertex2f(x,y)
    glEnd()

def draw_walls():
    glColor3f(0.0,1.0, 0.0)  # Green walls
    glBegin(GL_POINTS)
    for wall in game_state.walls:
        for x, y in mpl_points(wall[0],wall[1], wall[2],wall[3]):
            glVertex2f(x, y)
    glEnd()


def draw_points():
    glColor3f(1.0,0.71, 0.76)  # Pink color (RGB values for pink)
    for point in game_state.regular_points:
        draw_circle(point["pos"][0], point["pos"][1], POINT_RADIUS)

    # Draw bonus points
    glColor3f(1.0, 1.0,1.0)  #White for bonus points
    for point in game_state.bonus_points:
        draw_circle(point["pos"][0], point["pos"][1], BONUS_POINT_RADIUS)

def draw_power_up(cx,cy):
    glColor3f(0.0, 1.0,1.0)  # Cyan color
    
    # Draw outer circle
    glBegin(GL_POINTS)
    for x, y in mpc_points(cx, cy,POWER_UP_RADIUS):
        glVertex2f(x, y)
        
    # Draw inner circle
    for x, y in mpc_points(cx,cy, POWER_UP_RADIUS//2):
        glVertex2f(x, y)
    glEnd()



def draw_enemies():
    for enemy in game_state.enemies:
        if game_state.is_powered_up:
            glColor3f(0.0,0.0, 1.0)  # Blue when vulnerable
        else:
            glColor3f(1.0, 0.0,0.0)  # Red normally
            
        #Draw enemy body using MPC
        glBegin(GL_POINTS)
        for x,y in mpc_points(enemy['x'],enemy['y'], ENEMY_RADIUS):
            glVertex2f(x,y)
            
        #Draw eyes using smaller circles
        eye_radius =ENEMY_RADIUS* 0.2
        eye_offset= ENEMY_RADIUS * 0.3
        
        #Left eye
        for x, y in mpc_points(enemy['x'] -eye_offset, enemy['y'],int(eye_radius)):
            glVertex2f(x, y)
            
        #Right eye
        for x, y in mpc_points(enemy['x']+ eye_offset, enemy['y'],int(eye_radius)):
            glVertex2f(x, y)
        glEnd()
        
        #Visual effect for teleportation in hard mode
        current_time =time.time()
        if game_state.speed_multiplier >2.0:
            time_since_last_teleport =current_time -game_state.last_teleport_time
            if 6.8 <= time_since_last_teleport<= 7.0:
                if int(current_time* 10) % 2 ==0:
                    glColor3f(1.0, 1.0,1.0)  # Flash white
                    draw_circle(enemy['x'], enemy['y'], ENEMY_RADIUS * 1.2)

def draw_score():
    glColor3f(1.0, 1.0,1.0)  # White text
    glRasterPos2f(10, WIN_HEIGHT -20)
    score_text = f"Score: {game_state.score} Lives: {game_state.lives} Enemies: {len(game_state.enemies)}"
    for char in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(char))

def initialize():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WIN_WIDTH,0,WIN_HEIGHT)



def show_screen():
 
    glClear(GL_COLOR_BUFFER_BIT)
    
    if game_state.game_state ==MENU:
        draw_menu()
    elif game_state.game_state== PLAYING:
        game_state.move_pacman()
        game_state.check_collisions()
        game_state.update_power_ups()
        game_state.check_win_condition()
        
        if time.time()- game_state.start_time >5:
            game_state.enemies_can_move = True
        if game_state.enemies_can_move:
            game_state.move_enemies()
        
        draw_walls()
        game_state.draw_pacman()
        draw_points()
        game_state.update_power_ups()
        
        #Draw power-ups
        for power_up in game_state.power_ups:
            draw_power_up(power_up['pos'][0], power_up['pos'][1])
            
        #Change enemy color when powered up
        if game_state.is_powered_up:
            glColor3f(1.0, 0.0, 1.0)  #Blue when vulnerable
            
        draw_enemies()
        draw_score()
        
        if game_state.lives<= 0:
            game_state.game_state = GAME_OVER
    elif game_state.game_state == GAME_OVER:
        glColor3f(1.0, 0.0, 0.0)
        glRasterPos2f(WIN_WIDTH //2 -50, WIN_HEIGHT// 2)
        for char in "GAME OVER":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(char))
        
        glRasterPos2f(WIN_WIDTH // 2-70, WIN_HEIGHT// 2 - 40)
        for char in "Press M for Menu":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    elif game_state.game_state == GAME_WON:  # Add win screen
        glColor3f(0.0, 1.0, 0.0)  # Green color for win message
        
        #Draw congratulations message
        glRasterPos2f(WIN_WIDTH // 2-100,WIN_HEIGHT// 2 +20)
        for char in "CONGRATULATIONS!":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
            
        glRasterPos2f(WIN_WIDTH //2 -80, WIN_HEIGHT //2 - 20)
        for char in f"Final Score: {game_state.score}":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        
        glRasterPos2f(WIN_WIDTH //2- 70, WIN_HEIGHT// 2 - 60)
        for char in "Press M for Menu":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    glutSwapBuffers()


def key_pressed(key,x, y):
    if game_state.game_state== PLAYING:
        if key == b'w':
            game_state.keys['w'] =True
        elif key == b's':
            game_state.keys['s']= True
        elif key == b'a':
            game_state.keys['a']= True
        elif key == b'd':
            game_state.keys['d'] = True
    elif game_state.game_state ==GAME_OVER or game_state.game_state ==GAME_WON:
        if key == b'm':
            game_state.game_state =MENU
            game_state.reset_game()

def key_released(key, x, y):
    if key ==b'w':
        game_state.keys['w'] = False
    elif key == b's':
        game_state.keys['s'] = False
    elif key== b'a':
        game_state.keys['a'] = False
    elif key==b'd':
        game_state.keys['d'] = False

def timer(value):
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)


game_state=GameState()


glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
glutInitWindowSize(WIN_WIDTH, WIN_HEIGHT)
glutCreateWindow(b"BRAC MAN Maze Game")
glutDisplayFunc(show_screen)
glutKeyboardFunc(key_pressed)
glutKeyboardUpFunc(key_released)
glutMouseFunc(mouse_click)
glutTimerFunc(16, timer, 0)
initialize()
glutMainLoop()
