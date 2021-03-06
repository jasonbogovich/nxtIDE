from brick import *

from pgu import gui

import env

import os

import math

import imgs
from robothread import *

from dialog import SensorDialog, BackgroundDialog
from console import ConsoleDialog

from sensors import *

import yaml

def p(path):
    """Nasty monkey patch - shall be removed"""
    import os
    from os.path import abspath, dirname
    return dirname(abspath(sys.argv[0])).replace('library.zip', '') + os.sep \
            + path

NXTEMU_ASCII = """
               __                      
   ____  _  __/ /____  ____ ___  __  __
  / __ \| |/_/ __/ _ \/ __ `__ \/ / / /
 / / / />  </ /_/  __/ / / / / / /_/ / 
/_/ /_/_/|_|\__/\___/_/ /_/ /_/\__,_/  
                                       
"""

class Robot(NXTBrick):
    proc = None
    die = False
    inputs = {}
    background = None
    bckg = None
    sensors = {}
    paused = False
    touchPoints = {
        "topleft": [
            [29.0, -133.60281897270363],
            [28.319604517012593, -132.13759477388825],
            [27.65863337187866, -130.6012946450045],
        ],
        "left": [
            [-29, 42.721999467666336],
            [-28.319604517012593, 41.389942632819086],
        ],
        "topright": [
            [27.018512172212592, -51.00900595749453],
            [27.65863337187866, -49.398705354995535],
            [28.319604517012593, -47.862405226111754],
        ],
        "right": [
            [29.698484809834994, -43.97583689433345],
            [29, -42.721999467666336],
            [29, -47.278000532333664],
            [28.319604517012593, -41.389942632819086],
            [28.319604517012593, -48.610057367180914],
        ]
    }

    def __init__(self, wboot = True):
        __builtins__['robot']= self

        self.x = env.w/2
        self.y = env.h/2
        self.angle = 0

        self.mA = 0
        self.mB = 0
        self.mC = 0

        self.p = 0

        self.rotA = self.rotB = self.rotC = 0

        self.radius = 21

        self.dragged = False
        self.dragoffset = []
        #self.image = pygame.image.load("./robot.jpg").convert()
        #path = os.path.dirname(os.path.abspath(sys.argv[0]))
        #self.image = pygame.image.load(path + "/robot.png").convert_alpha() # imgs.robot.convert()
        self.image = imgs.robot.convert_alpha()
        #self.image = pygame.image.load("black_and_blacker.png").convert_alpha()

        self.lock = Lock()
        
        self.root = os.path.abspath(os.path.dirname(sys.argv[0]))
        # directory with programs to the path
        sys.path.append(self.root + os.sep + '__progs__')


        self.lcd = pygame.Surface((204, 130))
        pygame.draw.rect(self.lcd, pygame.Color(0x43, 0x6c, 0x30),
            ((0, 0), (204, 130)))

        if wboot:
            #print "booting"
            RoboThread(target=self.boot).start()
        
        self.sensors = {1: BaseSensor(1),
                        2: BaseSensor(2),
                        3: BaseSensor(3),
                        4: BaseSensor(4)}

        self.ports = {}

        self.bckgDialog = BackgroundDialog(bckg=env.cfg["others"]["background"])

        self.port_1 = SensorDialog(port=1)
        self.port_2 = SensorDialog(port=2)
        self.port_3 = SensorDialog(port=3)
        self.port_4 = SensorDialog(port=4)
        
        self.console = ConsoleDialog(init_code='from api import *', 
                        init_text= 4*'\n' + 
                        NXTEMU_ASCII + 
                        "Welcome to the Robot Live Console." \
                        "Type help if you are lost.", ps1='robot>')

    
    def getDistanceTo(self, point):
        dx = point[0] - self.x
        dy = point[1] - self.y
        return math.sqrt(dx**2 + dy**2)

    def mouseOver(self):
        mpos = pygame.mouse.get_pos()
        if self.getDistanceTo(mpos) < self.radius:
            return True
        else:
            return False

    def drag(self):
        mpos = pygame.mouse.get_pos()
        self.x = mpos[0]
        self.y = mpos[1]
        

        #pygame.image.save(self.image, "robot_.png")

        self.stayIn()
    
    def rot_center(self, image, angle):
        """rotate an image while keeping its center and size"""
        orig_rect = image.get_rect()
        #rot_image = pygame.transform.rotate(image, angle)
        rot_image = pygame.transform.rotozoom(image, angle, 1)
        rot_rect = orig_rect.copy()
        rot_rect.center = rot_image.get_rect().center
        rot_image = rot_image.subsurface(rot_rect).copy()
        return rot_image

    def draw(self):

        env.screen.blit(env.background, (0,0))
        env.screen.blit(self.rot_center(self.image, -self.angle),
                (self.x - 30, self.y - 30))

        env.screen.blit(self.lcd, ((640 + (378/2 - 100)-2, 90), (204, 130)))

        env.app.paint()
        pygame.display.flip()

    def touchesAt(self, positions):
        
        for pos in positions:
            dx = cos(radians(pos[1] + robot.angle)) * pos[0]
            dy = sin(radians(pos[1] + robot.angle)) * pos[0]
            
            #print 30 + round(dx), 30 + round(dy)

            x = int(self.x + round(dx))
            y = int(self.y + round(dy))

            #env.background.set_at((x, y), (0, 0, 255, 0))

            try:
                o = env.background.get_at((x, y))
            except IndexError:
                return True

            if o == (190, 190, 190, 255):
                return True

        return False

    def touches(self):
        out = {}
        for p in self.touchPoints:
            out[p] = self.touchesAt(p)

        return out

    def stayIn(self):
        if self.x > 623:
            self.x = 623

        if self.x < 23:
            self.x = 23

        if self.y > 463:
            self.y = 463

        if self.y < 23:
            self.y = 23


    def tick(self):
        # self.stayIn()
        angle = 0
        rotA = rotB = 0
        touchedA = touchedB = False
       
        if not robot.paused:

            if not self.touchesAt(self.touchPoints["topleft"]):
                rotA = self.mA / 30.0
            else:
                touchedA = True
                rotA -= self.mA / 40.0 

            if not self.touchesAt(self.touchPoints["topright"]):
                rotB = self.mB / 30.0
            else:
                touchedB = True
                rotB -= self.mB / 40.0

            rotC = self.mC / 30.0
                   
            angle += (rotA - rotB) / 3

            self.angle += angle
            p = (rotA + rotB) / 2 / 1.8
            
            #print angle, self.angle, self.mA, self.mB
            
            self.rotA += rotA
            self.rotB += rotB
            self.rotC += rotC

            self.x += math.sin(math.radians(self.angle)) * p
            self.y += -math.cos(math.radians(self.angle)) * p

        self.draw()
        
        if touchedA:
            self.rotA += -2*rotA
        if touchedB:
            self.rotB += -2*rotB

        # print background.get_at((int(self.x), int(self.y)))

    def onCenter(self):
        #print "onCenter"

        # Turning off ? yes/no
        if self.screen_y == -1:
            if self.screen_x == 0:
                sys.exit(0)
            else:
                self.screen_y += 1
                self.screen_x = 0
                self.scrout()
                return
          
        if [self.screen_x, self.screen_y, self.screen_z] == [0, 3, 0]:
            if self.proc == None:

                module = __import__('e' + self.progs[self.prog])
                                                                                         
                self.proc = RoboThread(target=module.main,
                                       cleaner=self.cleaner)
                self.proc.setName("brick")

                ClearScreen()
                self.scr_runner = RoboThread(target=robot.running)

                self.scr_runner.start()
                self.proc.start()
            return

        if self.screen_z:
            self.screen_z += 1
            self.screen_x = 0
        else:
            if self.screen_x == 0:
                self.screen_y += 1
            else:
                self.screen_z += 1
                self.screen_x = 0
        
        # taking care of empty __progs__ directory
        if self.screen_y == 2 and len(self.progs) == 0:
            self.screen_y -= 1

        
        #print self.screen_x, self.screen_y, self.screen_z
        self.scrout()

    def onBack(self):
        #taking care of turning off screen
        if self.screen_y == -1:
            self.screen_y += 1
            self.screen_x = 0
            self.scrout()
            return

        if self.proc == None:
            if self.scr_view == None:
                if self.screen_z:
                    self.screen_z -= 1
                else:
                    self.screen_y -= 1
            else:
                self.viewing = False
                self.scr_view = None
                self.screen_z -= 1
            self.screen_x = 0
            self.scrout()
        else:
            self.die = True
            self.scr_running = False

        #print self.screen_x, self.screen_y, self.screen_z

    def onLeft(self):
        if self.proc == None and self.scr_view == None:
            self.screen_x -= 1
        self.scrout()

    def onRight(self):
        if self.proc == None and self.scr_view == None:
            self.screen_x += 1
        self.scrout()

    def cleaner(self):
        ClearScreen()

        self.scr_running = False

        Off(OUT_ABC)
        ResetTachoCount(OUT_ABC)

        self.proc = None
        

        #self.screen_y -= 1
        self.scrout()
        #print "cleaner"

    def onConsole(self):

        if self.console.is_open():
            if not self.console_clicked:
                self.console_clicked = True
                return

            return self.consoleQuit(self.console)

        width = env.w + env.WALL_HEIGHT*2 + 378
        height = env.h + env.WALL_HEIGHT*2 + 200
        
        env.window = pygame.display.set_mode((width, height))
        env.screen = pygame.display.get_surface()
        env.background = pygame.Surface(env.screen.get_size()).convert()

        env.init(self.ports)

        ClearScreen()
        self.header()
        self.textCenterOut(LCD_LINE5 + 2, "Live Console") 


        self.console.connect(gui.CHANGE, self.consoleQuit, self.console)
        self.console.connect(gui.CLOSE, self.consoleQuit, self.console)
        self.console.open()

        self.console.rect.y = env.h + env.WALL_HEIGHT*2 + 5
        
        # focusing the input
        x = int(self.console.rect.x) + 86 + 10
        y = int(self.console.rect.y) + 86 + 38 + 50
        self.console_clicked = False
        self.console.own_focus(x,y)

    def consoleQuit(self, d):
        env.window = pygame.display.set_mode((env.w + env.WALL_HEIGHT*2 + 378, 
                                                env.h + env.WALL_HEIGHT*2))
        env.screen = pygame.display.get_surface()
        env.background = pygame.Surface(env.screen.get_size()).convert()

        env.init(self.ports)
        ClearScreen()
        self.scrout()

        d.close()

    def imgUpdate(self):
        image = imgs.robot.convert_alpha()
        
        for x in self.inputs:
            inp = self.inputs[x]
            if inp['slot'] != '':
                dx = inp['slot']*7
                if inp['slot'] == 3:
                    dx += 1
                
                dw = 1 if inp['slot'] == 2 else 0
                pygame.draw.rect(image, (0xfa, 0x70, 0x0d),
                                 (13+dx, 9, 5+dw, 5))
                


       #pygame.draw.rect(image, (0xfa, 0x70, 0x0d), (20, 9, 5, 5))
       #pygame.draw.rect(image, (0xfa, 0x70, 0x0d), (27, 9, 6, 5))
       #pygame.draw.rect(image, (0xfa, 0x70, 0x0d), (35, 9, 5, 5))

        self.image = image

    def dialogClose(self, d):
        
        self.paused = False
        d.close()

    def open_and_center(self, dlg):
        if dlg.is_open():
            return self.dialogClose(dlg)

        dlg.change()
        dlg.open()
        dlg.rect.x = 120
        dlg.connect(gui.CLOSE, self.dialogClose, dlg)
        self.paused = True

    def writeit(self, d):
        env.write_config()
        self.imgUpdate()
        d.close()

    # background
    def bckg_return(self, d):
        self.paused = False
        out = d.out()

        if out is not None and os.path.isfile(out):
            robot.background = out
            env.init(self.ports)

            if robot.background is not "":
                env.cfg['others']['background'] = robot.background
                try:
                    img = pygame.image.load(robot.background)
                    if img.get_alpha() != None:
                        img = img.convert_alpha()
                    else:
                        img = img.convert()

                    img = pygame.transform.scale(img, (640, 480))
                    env.background.blit(img, (3, 3))
                except:
                    pass
            else:
                env.cfg['others']['background'] = "None"
        else:
            robot.background = None
            env.init(self.ports)

        self.writeit(d)
    
    def background_dialog(self):
        self.bckgDialog.connect(gui.CHANGE, self.bckg_return, self.bckgDialog)
        self.open_and_center(self.bckgDialog)

    def add_sensor(self, d, i):       
        self.paused = False
        out = d.out()

        env.cfg["inputs"][i]["type"] = out["type"]
        env.cfg["inputs"][i]["slot"] = out["slot"]

        robot.inputs[i] = out

        self.sensors[i] = sensor_generator(out['type'], out['slot'])
        self.ports[i] = out['slot']

        env.init(self.ports)
        self.writeit(d)

    # port 1
    def port1_return(self, d):
        self.add_sensor(d, 1)

    def port1(self):
        self.port_1.connect(gui.CHANGE, self.port1_return, self.port_1)
        self.open_and_center(self.port_1)

    # port 2
    def port2_return(self, d):
        self.add_sensor(d, 2)

    def port2(self):
        self.port_2.connect(gui.CHANGE, self.port2_return, self.port_2)
        self.open_and_center(self.port_2)

    # port 3
    def port3_return(self, d):
        self.add_sensor(d, 3)

    def port3(self):
        self.port_3.connect(gui.CHANGE, self.port3_return, self.port_3)
        self.open_and_center(self.port_3)

    # port 4
    def port4_return(self, d):
        self.add_sensor(d, 4)

    def port4(self):
        self.port_4.connect(gui.CHANGE, self.port4_return, self.port_4)
        self.open_and_center(self.port_4)    
