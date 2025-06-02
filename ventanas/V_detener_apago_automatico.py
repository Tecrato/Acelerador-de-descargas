import os
import pygame as pag
import Utilidades as uti
import Utilidades_pygame as uti_pag

from Utilidades_pygame.base_app_class import Base_class
from constants import Config, DICT_CONFIG_DEFAULT
from textos import idiomas

class Ventana_detener_apago_automatico(Base_class):
    def load_resources(self):
        try:
            self.configs: dict = uti.web_tools.get('http://127.0.0.1:5000/get_configurations').json
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT

        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.txts = idiomas[self.idioma]

    def generate_objs(self):
        # El resto de textos y demas cosas
        self.text_program_title = uti_pag.Text(self.txts['title'], 16, self.config.font_mononoki, (self.ventana_rect.centerx, 30))
        self.pregunta = uti_pag.Text(self.txts['gui-detener apagado automatico'], 16, self.config.font_mononoki, (self.config.resolution[0]//2,50), dire='top')
        self.btn_aceptar = uti_pag.Button(self.txts['detener'], 14, self.config.font_mononoki, (self.config.resolution[0]//2,100), border_radius=0, border_bottom_right_radius=20, border_top_left_radius=20, color_rect='purple', color_rect_active='cyan', border_color='black', border_width=1, func=self.func_detener_apago)
        ...

        # Tambien se debe agregar a las respiectivas listas
        self.lists_screens["main"]["draw"].extend([
            self.pregunta,self.btn_aceptar,self.text_program_title
        ])
        self.lists_screens["main"]["update"].extend(self.lists_screens["main"]["draw"])
        self.lists_screens["main"]["click"].extend([self.btn_aceptar])

    def post_init(self):
        if self.enfoques:
            uti.win32_tools.front2(self.hwnd)
            uti.win32_tools.topmost(self.hwnd)

    def otro_evento(self, actual_screen, evento):
        if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
            self.exit()
        elif evento.type == pag.MOUSEBUTTONDOWN:
            ...

    def func_detener_apago(self):
        os.system('shutdown /a')
        self.exit()

if __name__ == '__main__':
    Ventana_detener_apago_automatico(config=Config(window_resize=False, resolution=(400, 130)))