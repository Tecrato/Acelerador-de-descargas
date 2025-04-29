from typing import Iterable
import pygame as pag
import Utilidades_pygame as uti_pag
from Utilidades_pygame.figuras.poligono_irregular import PoligonoIrregular
from Utilidades_pygame.GUI.base import Base_win

puntos = (
    (386.68010278853194, 0.9960020080301043),
    (153.43494882292202, 1.0),
    (158.19859051364818, 0.7224956747275377),
    (163.30075576600638, 0.9338094023943001),
    (201.80140948635182, 0.9633275663033837),
    (338.0993771417917, 0.9591767303265859),
    (376.7784549386164, 0.929526761314595),
    (381.8014094863518, 0.7224956747275377)
)

class Desicion(Base_win):
    """
    Returns Default:
        0: Aceptar
        1: Cancelar
    """
    def __init__(self, pos, font_mononoki, title, texto, size = (400,200), func=None, options: list[str] = None):
        super().__init__(pos, size, scroll_y=False)

        self.font = font_mononoki
        self.func = func
        self.__botons_pointer = -1

        self.poligono = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size),0, color=(0,0,0))
        self.add(self.poligono,f'{(size[0]/2,size[1]/2)}')
        self.poligono2 = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size)-10,0, color=(10,10,10))
        self.add(self.poligono2,f'{(size[0]/2,size[1]/2)}')
        self.poligono3 = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size)-30,0, color=(40,40,40))
        self.add(self.poligono3,f'{(size[0]/2,size[1]/2)}')
        
        self.title = uti_pag.Text(title, 20, self.font, (0,0), 'top')
        self.add(self.title, f'({size[0]/2},{size[1]*.1})')

        self.body = uti_pag.Text(texto, 20, self.font, (0,0), 'center',border_radius=-1)
        self.add(self.body, f'({size[0]/2},{size[1]/2 - 10})')

        self.options = ('aceptar', 'cancelar') if options is None else options

    def draw_after(self):
        pag.draw.line(self.surf, (0,0,0), self.poligono3.figura[2], self.poligono3.figura[7], 2)

    def execute_func(self, index:int ,text: str):
        if not self.active:
            return True
        self.active = False
        if self.func:
            self.func({'index':int(index), 'text':text})
        return True
    
    @property
    def options(self):
        return self.__options
    
    @options.setter
    def options(self, value: list[str]):
        if not isinstance(value, Iterable) or not all(isinstance(i, str) for i in value):
            raise ValueError("options debe ser una lista de strings")
        if self.__botons_pointer >= 0:
            for x in reversed(range(self.__botons_pointer, self.__botons_pointer + len(self.__options))):
                self.list_objs.pop(x)
                
        self.__options = value
        last_g = len(self.list_objs)-1
        self.__botons_pointer = len(self.list_objs)
        
        for i, op in enumerate(self.options):
            gui = uti_pag.Button(op, 20, self.font, (0,0), (15,15), 'bottomright','black','purple', color_rect_active='cyan', border_width=-1, border_radius=0, func=lambda n=i, op=op: self.execute_func('{}'.format(n), '{}'.format(op)))
            pos = '({},{})'.format((self.list_objs[last_g]['GUI'].left-10) if i > 0 else (self.size[0]-20), self.size[1]-20)
            self.add(gui, pos, clicking=True)
            last_g += 1