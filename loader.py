import pygame as pag
from librerias.Utilidades_pygame.figuras.engranajes import Engranaje
class Loader:
    def __init__(self, pos) -> None:
        self.__pos = pos
        self.redraw = 1
        self.updates = []

        self.engranajes: list[Engranaje] = [
            Engranaje((0,0), 8, 5, 20, 20),
            Engranaje((0,0), 8, 5, 20, 0),
            Engranaje((0,0), 4, 5, 10, 75),
        ]
        self.posicionar_engranajes()
        self.engranajes[0].color = (140,30,160)
        self.engranajes[1].color = (200,80,220)
        self.engranajes[2].color = (150,120,200)
        self.rect = self.engranajes[0].rect.unionall([r.rect for r in self.engranajes[1:]])

    def update(self, dt=1) -> None:
        self.engranajes[0].angle += 1
        self.engranajes[1].angle -= 1
        self.engranajes[2].angle += 2

    def draw(self, surface) -> pag.Rect:
        self.updates.clear()
        for x in self.engranajes:
            x.draw(surface)
            self.updates.append(x.rect)
        return self.updates

    def posicionar_engranajes(self):
        self.engranajes[0].pos = self.pos[0] - 40, self.pos[1] - 50
        self.engranajes[1].pos = self.pos[0] - 70, self.pos[1] - 20
        self.engranajes[2].pos = self.pos[0] - 91, self.pos[1] - 46

    @property
    def pos(self):
        return self.__pos
    @pos.setter
    def pos(self,pos):
        self.__pos = pos
        self.posicionar_engranajes()

        self.rect = self.engranajes[0].rect.unionall([r for r in self.engranajes[1:]])

    @property
    def collide_rect(self):
        return self.rect
    def collide(self, rect: pag.Rect) -> bool:
        return self.collide_rect.colliderect(rect)
    def collide_all(self, lista) -> str:
        lista = []
        for i,x in enumerate(lista):
            if x.collide(self.collide_rect):
                lista.append(i)
        return lista
    def get_update_rects(self):
        return [self.collide_rect]