import pygame as pag
from Utilidades_pygame.figuras.engranajes import Engranaje
class Loader:
    def __init__(self, pos) -> None:
        self.__pos = pos
        self.redraw = 1

        self.engranajes: list[Engranaje] = [
            Engranaje((self.__pos[0] - 40, self.__pos[1] - 50), 8, 5, 20, 20),
            Engranaje((self.__pos[0] - 70, self.__pos[1] - 20), 8, 5, 20, 0),
            Engranaje((self.__pos[0] - 90, self.__pos[1] - 55), 4, 5, 10, 30),
        ]
        self.engranajes[0].color = (153,44,170)
        self.engranajes[1].color = (190,70,210)
        self.engranajes[2].color = (190,60,230)

    def update(self, dt=1) -> None:
        self.engranajes[0].angle += 1
        self.engranajes[1].angle -= 1
        self.engranajes[2].angle += 2

    def draw(self, surface) -> pag.Rect:
        if self.redraw:
            for x in self.engranajes:
                for y in x.dientes:
                    pag.draw.polygon(surface, x.color, y.figure)
                pag.draw.circle(surface, x.color, x.pos, x.radio)
            self.redraw = 0
        # return (pag.Rect(0, 0, 200, 200).move(self.pos[0] - 200, self.pos[1] - 200),)
        return []

    @property
    def pos(self):
        return self.__pos
    @pos.setter
    def pos(self,pos):
        self.__pos = pos
        self.engranajes[0].pos = self.__pos[0] - 40, self.__pos[1] - 50
        self.engranajes[1].pos = self.__pos[0] - 70, self.__pos[1] - 20
        self.engranajes[2].pos = self.__pos[0] - 90, self.__pos[1] - 45

        
    @property
    def collide_rect(self):
        return pag.Rect(0, 0, 200, 200).move(self.pos[0] - 100, self.pos[1] - 100)
    def collide(self, rect: pag.Rect) -> bool:
        return self.collide_rect.collidepoint(rect)
    def collide_all(self, lista) -> str:
        lista = []
        for i,x in enumerate(lista):
            if x.collide(self.collide_rect):
                lista.append(i)
        return lista
    def get_update_rects(self):
        return [self.collide_rect]