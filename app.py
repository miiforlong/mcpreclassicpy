import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1024, 768
MAP_W, MAP_D, MAP_H = 128, 64, 128 

class Textures:
    @staticmethod
    def load_texture(filename):
        try:
            surf = pygame.image.load(filename)
            data = pygame.image.tostring(surf, "RGBA", 1)
            w, h = surf.get_rect().size
            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            return tex_id
        except:
            return None

class AABB:
    def __init__(self, x0, y0, z0, x1, y1, z1):
        self.x0, self.y0, self.z0 = x0, y0, z0
        self.x1, self.y1, self.z1 = x1, y1, z1
        self.eps = 0.01

    def expand(self, xa, ya, za):
        _x0, _y0, _z0, _x1, _y1, _z1 = self.x0, self.y0, self.z0, self.x1, self.y1, self.z1
        if xa < 0: _x0 += xa
        if xa > 0: _x1 += xa
        if ya < 0: _y0 += ya
        if ya > 0: _y1 += ya
        if za < 0: _z0 += za
        if za > 0: _z1 += za
        return AABB(_x0, _y0, _z0, _x1, _y1, _z1)

    def clipX(self, c, xa):
        if c.y1 <= self.y0 or c.y0 >= self.y1 or c.z1 <= self.z0 or c.z0 >= self.z1: return xa
        if xa > 0 and c.x1 <= self.x0:
            v = self.x0 - c.x1 - self.eps
            if v < xa: xa = v
        if xa < 0 and c.x0 >= self.x1:
            v = self.x1 - c.x0 + self.eps
            if v > xa: xa = v
        return xa

    def clipY(self, c, ya):
        if c.x1 <= self.x0 or c.x0 >= self.x1 or c.z1 <= self.z0 or c.z0 >= self.z1: return ya
        if ya > 0 and c.y1 <= self.y0:
            v = self.y0 - c.y1 - self.eps
            if v < ya: ya = v
        if ya < 0 and c.y0 >= self.y1:
            v = self.y1 - c.y0 + self.eps
            if v > ya: ya = v
        return ya

    def clipZ(self, c, za):
        if c.x1 <= self.x0 or c.x0 >= self.x1 or c.y1 <= self.y0 or c.y0 >= self.y1: return za
        if za > 0 and c.z1 <= self.z0:
            v = self.z0 - c.z1 - self.eps
            if v < za: za = v
        if za < 0 and c.z0 >= self.z1:
            v = self.z1 - c.z0 + self.eps
            if v > za: za = v
        return za

    def move(self, xa, ya, za):
        self.x0 += xa; self.y0 += ya; self.z0 += za
        self.x1 += xa; self.y1 += ya; self.z1 += za

class Level:
    def __init__(self, w, d, h):
        self.w, self.d, self.h = w, d, h
        self.blocks = np.zeros((w, d, h), dtype=np.uint8)
        self.blocks[:, 0:30, :] = 1 # Stone
        self.blocks[:, 30:32, :] = 2 # Dirt

    def get_tile(self, x, y, z):
        if 0 <= x < self.w and 0 <= y < self.d and 0 <= z < self.h:
            return self.blocks[int(x), int(y), int(z)]
        return 0

    def is_solid(self, x, y, z):
        return self.get_tile(x, y, z) > 0

class Player:
    def __init__(self, level):
        self.level = level
        self.x, self.y, self.z = 64.0, 35.0, 64.0
        self.xd, self.yd, self.zd = 0, 0, 0
        self.yRot, self.xRot = 0, 0
        self.bb = AABB(self.x-0.3, self.y-1.6, self.z-0.3, self.x+0.3, self.y+0.2, self.z+0.3)
        self.onGround = False

    def tick(self):
        keys = pygame.key.get_pressed()
        xa, za = 0, 0
        if keys[K_z] or keys[K_w]: za -= 1
        if keys[K_s]: za += 1
        if keys[K_q] or keys[K_a]: xa -= 1
        if keys[K_d]: xa += 1
        if keys[K_SPACE] and self.onGround: self.yd = 0.12

        speed = 0.02 if self.onGround else 0.01
        m = math.sqrt(xa*xa + za*za)
        if m > 0.01:
            xa *= speed/m; za *= speed/m
            s, c = math.sin(math.radians(self.yRot)), math.cos(math.radians(self.yRot))
            self.xd += xa * c - za * s
            self.zd += za * c + xa * s

        self.yd -= 0.005
        self.move(self.xd, self.yd, self.zd)
        self.xd *= 0.91; self.yd *= 0.98; self.zd *= 0.91
        if self.onGround: self.xd *= 0.7; self.zd *= 0.7

    def move(self, xa, ya, za):
        yO = ya
        cubes = []
        # Optimisation : get the nearby blocs
        for ix in range(int(self.bb.x0-1), int(self.bb.x1+2)):
            for iy in range(int(self.bb.y0-1), int(self.bb.y1+2)):
                for iz in range(int(self.bb.z0-1), int(self.bb.z1+2)):
                    if self.level.is_solid(ix, iy, iz): cubes.append(AABB(ix,iy,iz,ix+1,iy+1,iz+1))
        
        for c in cubes: ya = c.clipY(self.bb, ya)
        self.bb.move(0, ya, 0)
        for c in cubes: xa = c.clipX(self.bb, xa)
        self.bb.move(xa, 0, 0)
        for c in cubes: za = c.clipZ(self.bb, za)
        self.bb.move(0, 0, za)
        
        self.onGround = (yO != ya and yO < 0)
        self.x, self.y, self.z = (self.bb.x0+self.bb.x1)/2, self.bb.y0+1.62, (self.bb.z0+self.bb.z1)/2

class RubyDung:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        self.level = Level(MAP_W, MAP_D, MAP_H)
        self.player = Player(self.level)
        self.tex = Textures.load_texture("terrain.png")
        self.list = glGenLists(1)
        self.dirty = True

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glClearColor(0.5, 0.8, 1.0, 1.0)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(70, WIDTH/HEIGHT, 0.05, 1000)
        glMatrixMode(GL_MODELVIEW)

    def draw_face(self, x, y, z, f, b, color):
        u = 16/256 if b == 1 else 0
        v, s = 240/256, 16/256
        glColor3f(*color)
        if f == 0: # Top
            glTexCoord2f(u, v+s); glVertex3f(x, y+1, z)
            glTexCoord2f(u, v); glVertex3f(x, y+1, z+1)
            glTexCoord2f(u+s, v); glVertex3f(x+1, y+1, z+1)
            glTexCoord2f(u+s, v+s); glVertex3f(x+1, y+1, z)
        elif f == 1: # Bottom
            glTexCoord2f(u+s, v+s); glVertex3f(x+1, y, z)
            glTexCoord2f(u+s, v); glVertex3f(x+1, y, z+1)
            glTexCoord2f(u, v); glVertex3f(x, y, z+1)
            glTexCoord2f(u, v+s); glVertex3f(x, y, z)
        elif f == 2: # Front
            glTexCoord2f(u, v); glVertex3f(x, y, z+1)
            glTexCoord2f(u+s, v); glVertex3f(x+1, y, z+1)
            glTexCoord2f(u+s, v+s); glVertex3f(x+1, y+1, z+1)
            glTexCoord2f(u, v+s); glVertex3f(x, y+1, z+1)
        elif f == 3: # Back
            glTexCoord2f(u+s, v); glVertex3f(x+1, y, z)
            glTexCoord2f(u, v); glVertex3f(x, y, z)
            glTexCoord2f(u, v+s); glVertex3f(x, y+1, z)
            glTexCoord2f(u+s, v+s); glVertex3f(x+1, y+1, z)
        elif f == 4: # Right
            glTexCoord2f(u+s, v); glVertex3f(x+1, y, z+1)
            glTexCoord2f(u, v); glVertex3f(x+1, y, z)
            glTexCoord2f(u, v+s); glVertex3f(x+1, y+1, z)
            glTexCoord2f(u+s, v+s); glVertex3f(x+1, y+1, z+1)
        elif f == 5: # Left
            glTexCoord2f(u, v); glVertex3f(x, y, z)
            glTexCoord2f(u+s, v); glVertex3f(x, y, z+1)
            glTexCoord2f(u+s, v+s); glVertex3f(x, y+1, z+1)
            glTexCoord2f(u, v+s); glVertex3f(x, y+1, z)

    def compile(self):
        glNewList(self.list, GL_COMPILE)
        glBegin(GL_QUADS)
        r = 32
        px, py, pz = int(self.player.x), int(self.player.y), int(self.player.z)
        for x in range(max(0, px-r), min(MAP_W, px+r)):
            for y in range(max(0, py-r), min(MAP_D, py+r)):
                for z in range(max(0, pz-r), min(MAP_H, pz+r)):
                    b = self.level.get_tile(x, y, z)
                    if b == 0: continue
                    # Ombrage Face : Top=1.0, Côtés=0.8, Avant/Arrière=0.6
                    if not self.level.is_solid(x, y+1, z): self.draw_face(x,y,z,0,b,(1,1,1))
                    if not self.level.is_solid(x, y-1, z): self.draw_face(x,y,z,1,b,(0.5,0.5,0.5))
                    if not self.level.is_solid(x, y, z+1): self.draw_face(x,y,z,2,b,(0.8,0.8,0.8))
                    if not self.level.is_solid(x, y, z-1): self.draw_face(x,y,z,3,b,(0.8,0.8,0.8))
                    if not self.level.is_solid(x+1, y, z): self.draw_face(x,y,z,4,b,(0.6,0.6,0.6))
                    if not self.level.is_solid(x-1, y, z): self.draw_face(x,y,z,5,b,(0.6,0.6,0.6))
        glEnd()
        glEndList()
        self.dirty = False

    def get_ray(self):
        x, y, z = self.player.x, self.player.y, self.player.z
        dx = math.sin(math.radians(self.player.yRot)) * math.cos(math.radians(self.player.xRot))
        dy = -math.sin(math.radians(self.player.xRot))
        dz = -math.cos(math.radians(self.player.yRot)) * math.cos(math.radians(self.player.xRot))
        for _ in range(500):
            x += dx*0.01; y += dy*0.01; z += dz*0.01
            if self.level.is_solid(x,y,z):
                return (int(x), int(y), int(z)), (int(x-dx*0.01), int(y-dy*0.01), int(z-dz*0.01))
        return None, None

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for ev in pygame.event.get():
                if ev.type == QUIT or (ev.type == KEYDOWN and ev.key == K_ESCAPE): return
                if ev.type == MOUSEBUTTONDOWN:
                    t, p = self.get_ray()
                    if ev.button == 1 and t: self.level.blocks[t] = 0; self.dirty = True
                    if ev.button == 3 and p:
                        self.level.blocks[p] = 2 if p[1] >= 30 else 1
                        self.dirty = True

            dx, dy = pygame.mouse.get_rel()
            self.player.yRot += dx * 0.15
            self.player.xRot = max(-90, min(90, self.player.xRot + dy * 0.15))
            self.player.tick()
            
            if self.dirty: self.compile()
            
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            glRotatef(self.player.xRot, 1, 0, 0)
            glRotatef(self.player.yRot, 0, 1, 0)
            glTranslatef(-self.player.x, -self.player.y, -self.player.z)
            
            glBindTexture(GL_TEXTURE_2D, self.tex)
            glCallList(self.list)
            
            # contour bloc
            t, _ = self.get_ray()
            if t:
                glDisable(GL_TEXTURE_2D); glLineWidth(2); glColor3f(0,0,0)
                x, y, z = t
                glBegin(GL_LINES)
                for i in range(2):
                    for j in range(2):
                        glVertex3f(x+i, y, z+j); glVertex3f(x+i, y+1, z+j)
                        glVertex3f(x, y+i, z+j); glVertex3f(x+1, y+i, z+j)
                        glVertex3f(x+i, y+j, z); glVertex3f(x+i, y+j, z+1)
                glEnd(); glEnable(GL_TEXTURE_2D)
            
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    RubyDung().run()
