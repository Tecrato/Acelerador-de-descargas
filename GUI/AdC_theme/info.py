import pygame as pag
import librerias.Utilidades_pygame as uti_pag

from librerias.Utilidades_pygame.figuras.poligono_irregular import PoligonoIrregular
from librerias.Utilidades_pygame.GUI.base import Base_win

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
# puntos = import_from_file(r"C:\Users\Edouard\Documents\curso de programacion\Python\API's\Acelerador-de-descargas\lista.txt")

class Info(Base_win):
    def __init__(self, pos, font_mononoki, title, texto, size = (400,200), func=None):
        super().__init__(pos, size, scroll_y=False)

        self.font = font_mononoki
        self.func = func

        self.poligono = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size),0, color=(0,0,0))
        self.add(self.poligono,f'{(size[0]/2,size[1]/2)}')
        self.poligono2 = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size)-10,0, color=(15,15,15))
        self.add(self.poligono2,f'{(size[0]/2,size[1]/2)}')
        self.poligono3 = PoligonoIrregular(puntos, pag.Vector2(size)/2, min(size)-30,0, color=(40,40,40))
        self.add(self.poligono3,f'{(size[0]/2,size[1]/2)}')
        # self.poligono_btn_aceptar = PoligonoIrregular(puntos, pag.Vector2(self.size), min(self.size),0, color=(10,10,10))

        self.title = uti_pag.Text(title, 20, self.font, (0,0), 'top')
        self.add(self.title, f'({size[0]/2},{size[1]*.1})')

        self.body = uti_pag.Text(texto, 20, self.font, (0,0), 'center')
        self.add(self.body, f'({size[0]/2},{size[1]/2 - 10})')

        self.btn_aceptar = uti_pag.Button('Aceptar',16,self.font,(0,0), 15, 'bottomright','black','purple', color_rect_active='cyan', border_width=-1, border_radius=0, func=self.func_aceptar)
        self.add(self.btn_aceptar, f'{self.size[0]-20},{self.size[1]-10}', clicking=True)

    def draw_after(self):
        pag.draw.line(self.surf, (0,0,0), self.poligono3.figura[2], self.poligono3.figura[7], 2)

    def func_aceptar(self):
        self.active = False
        if self.func:
            self.func('aceptar')
        return True
    