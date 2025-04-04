import os
import Utilidades as uti
import Utilidades_pygame as uti_pag
from pathlib import Path

from Utilidades_pygame.base_app_class import Base_class
from constants import DICT_CONFIG_DEFAULT, Config
from textos import idiomas

class Ventana_actualizar(Base_class):
    def load_resources(self):
        try:
            self.configs: dict = uti.web_tools.get('http://127.0.0.1:5000/get_configurations').json
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT

        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.low_detail_mode = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.txts = idiomas[self.idioma]

    def generate_objs(self):
        # El resto de textos y demas cosas
        self.text_program_title = uti_pag.Text(self.txts['title'], 16, self.config.font_mononoki, (self.ventana_rect.centerx, 30))
        self.pregunta = uti_pag.Text(self.txts['nueva descarga disponible'], 20, self.config.font_mononoki, (self.config.resolution[0]//2,50), dire='top')
        self.btn_aceptar = uti_pag.Button(self.txts['descargar'], 14, self.config.font_mononoki, (self.config.resolution[0]//4,100), padding=(20,15), border_radius=0, border_bottom_right_radius=20, border_top_left_radius=20, color_rect='purple', color_rect_active='cyan', border_color='black', border_width=1, func=lambda:(os.startfile(self.args[0]),self.exit()))
        self.btn_cancelar = uti_pag.Button(self.txts['cancelar'], 14, self.config.font_mononoki, (self.config.resolution[0]//4 *3,100), padding=(20,15), border_radius=0, border_bottom_right_radius=20, border_top_left_radius=20, color_rect='purple', color_rect_active='cyan', border_color='black', border_width=1, func=self.exit)

        # Tambien se debe agregar a las respiectivas listas
        self.lists_screens["main"]["draw"].extend([
            self.pregunta,self.btn_aceptar,self.btn_cancelar,self.text_program_title
        ])
        self.lists_screens["main"]["update"].extend(self.lists_screens["main"]["draw"])
        self.lists_screens["main"]["click"].extend([self.btn_aceptar,self.btn_cancelar])

        # Y se mueven los objetos a su posicion en pantalla
        self.move_objs()

if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    Ventana_actualizar(Config(window_resize=False, resolution=(300, 130)), 'https://www.google.com')
