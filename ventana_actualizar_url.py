import pygame as pag
import json
import requests
import Utilidades as uti
import Utilidades_pygame as uti_pag

from Utilidades_pygame.base_app_class import Base_class
from constants import Config, DICT_CONFIG_DEFAULT
from textos import idiomas

class Ventana_actualizar_url(Base_class):
    def load_resources(self):
        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT

        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.txts = idiomas[self.idioma]

    def generate_objs(self):
        # El resto de textos y demas cosas
        self.text_program_title = uti_pag.Text(self.txts['title'], 18, self.config.font_mononoki, (self.ventana_rect.centerx, 30))
        self.text_parrafo = uti_pag.Text('La siguiente descarga de su navegador\nactualizará la url de la descarga seleccionada', 14, self.config.font_mononoki, (self.config.resolution[0]//2,50), dire='top')
        self.btn_aceptar = uti_pag.Button(self.txts['cancelar'], 14, self.config.font_mononoki, (self.config.resolution[0]//2,120), padding=(20,15), border_radius=0, border_bottom_right_radius=20, border_top_left_radius=20, color_rect='purple', color_rect_active='cyan', border_color='black', border_width=1, func=self.func_cancelar)
        ...

        # Tambien se debe agregar a las respiectivas listas
        self.lists_screens["main"]["draw"].extend([
            self.text_parrafo,self.btn_aceptar,self.text_program_title
        ])
        self.lists_screens["main"]["update"].extend(self.lists_screens["main"]["draw"])
        self.lists_screens["main"]["click"].extend([self.btn_aceptar])

    def post_init(self):
        if self.enfoques:
            uti.win32_tools.front2(self.hwnd)

    def otro_evento(self, actual_screen, evento):
        if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
            self.exit()
        elif evento.type == pag.MOUSEBUTTONDOWN:
            ...

    def func_cancelar(self):
        print("cancelando actualizacion de url")
        try:
            requests.get('http://127.0.0.1:5000/descargas/cancel_update/url')
        except Exception as err:
            print(err)
        self.exit()


if __name__ == '__main__':
    Ventana_actualizar_url(config=Config(window_resize=False, resolution=(400, 150)))