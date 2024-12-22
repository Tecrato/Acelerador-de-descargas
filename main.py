import sys
import requests
import time
import os
import json
import pygame as pag
import shutil
import pyperclip
import datetime
from pathlib import Path

from tkinter.filedialog import askdirectory
from tkinter.simpledialog import askstring
from threading import Thread
from urllib.parse import urlparse, unquote
from Utilidades_pygame import Text, Button, List, Multi_list, GUI, mini_GUI, Input, Select_box
from Utilidades import Funcs_pool, win32_tools, Deltatime,  UNIDADES_BYTES
from Utilidades.web_tools import get_mediafire_url, check_update
from Utilidades import format_size_bits_to_bytes, format_size_bits_to_bytes_str
from Utilidades.logger import Logger
from platformdirs import user_config_path, user_cache_path, user_downloads_dir, user_desktop_path, user_pictures_path, user_log_path
from pygame.constants import (MOUSEBUTTONDOWN, MOUSEMOTION, KEYDOWN, QUIT, K_ESCAPE, MOUSEBUTTONUP, MOUSEWHEEL,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)
from pygame import Vector2

from loader import Loader
from textos import idiomas
from my_warnings import LinkCaido, LowSizeError, TrajoHTML
from constants import TITLE, DICT_CONFIG_DEFAULT, MIN_RESOLUTION, RESOLUCION, VERSION, FONT_MONONOKI, FONT_SIMBOLS

# noinspection PyAttributeOutsideInit
class DownloadManager:
    def __init__(self) -> None:
        pag.init()

        self.ventana: pag.Surface = pag.display.set_mode(RESOLUCION, pag.RESIZABLE|pag.DOUBLEBUF)
        self.ventana_rect: pag.Rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))
        pag.display.set_caption(TITLE)

        self.carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_config.mkdir(parents=True, exist_ok=True)
        self.carpeta_cache = user_cache_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)
        self.carpeta_screenshots = user_pictures_path().joinpath('./Edouard Sandoval/Acelerador_de_descargas', )
        self.carpeta_screenshots.mkdir(parents=True, exist_ok=True)

        self.new_url: str = ''
        self.new_filename: str = ''
        self.new_file_type: str = ''
        self.new_file_size: int = 0
        self.new_threads: int = 1
        self.thread_new_download = None
        self.actualizar_url: bool = False

        self.cached_list_DB: list[tuple] = []
        self.cola: list[int] = []
        self.descargando: list[int] = []

        self.data_actualizacion = {}
        self.updates: list[pag.Rect] = []
        self.extenciones: list[str] = []
        self.url_actualizacion: str = ''
        self.save_dir = user_downloads_dir()
        self.threads: int = 4
        self.velocidad_limite = 0
        self.apagar_al_finalizar_cola = False
        self.can_add_new_download = False
        self.drawing: bool = True
        self.enfoques: bool = True
        self.detener_5min: bool = True
        self.low_detail_mode: bool = False
        self.mini_ventana_captar_extencion: bool = True
        self.draw_background = True
        self.redraw: bool = True
        self.loading = 0
        self.framerate: int = 60
        self.relog: pag.time.Clock = pag.time.Clock()
        self.delta_time: Deltatime = Deltatime(60)
        self.logger = Logger('Acelerador de descargas(UI)', user_log_path('Acelerador de descargas', 'Edouard Sandoval'))
        
        self.idioma: str = 'español'
        self.txts = idiomas[self.idioma]

        self.Func_pool = Funcs_pool()
        self.Func_pool.add('actualizacion', self.buscar_acualizaciones)
        self.Func_pool.add('reload list',self.reload_lista_descargas)

        self.logger.write(f"Acelerador de descargas iniciado en {datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')}")

        self.load_resources()
        self.generate_objs()
        self.Func_pool.start('reload list')
        self.move_objs()
        
        self.Func_pool.start('actualizacion')

        self.screen_main_bool: bool = True
        self.screen_new_download_bool: bool = False
        self.screen_configs_bool: bool = False
        self.screen_extras_bool: bool = False

        self.ciclo_general = [self.main_cycle, self.screen_configs, self.screen_extras,self.screen_new_download]
        self.cicle_try = 0


        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

        pag.quit()


    def load_resources(self):
        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT
        self.threads = self.configs.get('hilos',DICT_CONFIG_DEFAULT['hilos'])
        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.velocidad_limite = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])

        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.save_dir = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.apagar_al_finalizar_cola = self.configs.get('apagar al finalizar cola',DICT_CONFIG_DEFAULT['apagar al finalizar cola'])
        self.extenciones = self.configs.get('extenciones',DICT_CONFIG_DEFAULT['extenciones'])
        self.txts = idiomas[self.idioma]

        self.save_json()

    def save_json(self):
        self.configs['hilos'] = self.threads
        self.configs['enfoques'] = self.enfoques
        self.configs['detener_5min'] = self.detener_5min
        self.configs['ldm'] = self.low_detail_mode

        self.configs['idioma'] = self.idioma
        self.configs['save_dir'] = str(self.save_dir)
        self.configs['apagar al finalizar cola'] = self.apagar_al_finalizar_cola
        self.configs['extenciones'] = self.extenciones
        self.configs['velocidad_limite'] = self.velocidad_limite

        json.dump(self.configs, open(self.carpeta_config.joinpath('./configs.json'), 'w'))

    def generate_objs(self) -> None:
        # Cosas varias
        GUI.configs['fuente_simbolos'] = FONT_SIMBOLS
        self.GUI_manager = GUI.GUI_admin()
        self.Mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)

        # Loader
        self.loader = Loader((self.ventana_rect.w, self.ventana_rect.h))

        # Pantalla principal
        self.txt_title = Text(self.txts['title'], 26, FONT_MONONOKI, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_extras = Button('', 26, FONT_SIMBOLS, (self.ventana_rect.w, 0), 10, 'topright', 'white',
                                       (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                       func=self.func_main_to_extras)
        self.btn_configs = Button('', 26, FONT_SIMBOLS, (0, 0), 10, 'topleft', 'white', (20, 20, 20),
                                        (50, 50, 50), 0, -1, border_width=-1, func=self.func_main_to_config)

        self.btn_new_descarga = Button(self.txts['btn-nueva_descarga'], 16, FONT_MONONOKI, (30, 80), 20,
                                             'topleft', 'white', (50, 50, 50), (90, 90, 90), 0, 20,
                                             border_bottom_right_radius=0, border_top_right_radius=0, border_width=-1,
                                             func=lambda: self.func_main_to_new_download())
        self.btn_change_dir = Button(self.txts['btn-cambiar_carpeta'], 16, FONT_MONONOKI,
                                           (self.btn_new_descarga.rect.right, 80), 20, 'topleft', 'white', (50, 50, 50),
                                           (90, 90, 90), 0, 20, border_bottom_left_radius=0, border_top_left_radius=0,
                                           border_width=-1, func=self.func_preguntar_carpeta)

        self.lista_descargas: Multi_list = Multi_list((self.ventana_rect.w - 60, self.ventana_rect.h - 140), (30, 120), 8, None, 11,
                                          10, (10,10,10), header_text=["id",self.txts['nombre'], self.txts['tipo'], self.txts['hilos'], self.txts['tamaño'], self.txts['estado'],self.txts['cola'], self.txts['fecha']],
                                          fonts=[FONT_MONONOKI for _ in range(8)], colums_witdh=[0, .065, .33, .47, .55, .67, .79, .86], padding_left=10, border_color=(100,100,100),
                                          smothscroll=True if not self.low_detail_mode else False)
        self.btn_reload_list = Button('', 13, FONT_SIMBOLS, self.lista_descargas.topright, 16, # (self.ventana_rect.w - 31, 120)
                                            'topright', 'black', 'darkgrey', 'lightgrey', 0, border_width=1,
                                            border_radius=0, border_top_right_radius=20, border_color=(100,100,100),
                                            func=lambda :self.Func_pool.start('reload list'))

        # Cosas de la ventana de nueva descarga
        self.new_download_rect = pag.Rect(0, 0, 500, 300)
        self.new_download_rect.center = self.ventana_rect.center
        self.text_newd_title = Text(self.txts['agregar nueva descarga'], 18, FONT_MONONOKI,
                                           (self.new_download_rect.centerx, self.new_download_rect.top + 20))
        self.boton_newd_cancelar = Button(self.txts['cancelar'], 16, FONT_MONONOKI,
                                                Vector2(-20, 0) + self.new_download_rect.bottomright, (30, 20),
                                                'bottomright', border_radius=0, border_top_right_radius=20,
                                                func=self.func_newd_close)
        self.boton_newd_aceptar = Button(self.txts['aceptar'], 16, FONT_MONONOKI,
                                               (self.boton_newd_cancelar.rect.left, self.new_download_rect.bottom),
                                               (30, 19), 'bottomright', border_radius=0, border_top_left_radius=20,
                                               func=self.func_add_download)

        self.input_newd_url = Input((self.new_download_rect.left + 20, self.new_download_rect.top + 100), 12,
                                         width=300, height= 20, font=FONT_MONONOKI, text_value='url de la descarga', max_letter=800,
                                         dire='left')
        self.input_newd_paste = Button('', 22, FONT_SIMBOLS,
                                             (self.input_newd_url.right, self.input_newd_url.pos.y), (20, 10),
                                             'left', 'black', 'lightgrey', 'darkgrey', border_width=1, border_radius=0,
                                             border_top_right_radius=20, border_bottom_right_radius=20,
                                             func=self.func_paste_url)

        self.btn_comprobar_url = Button(self.txts['comprobar'], 16, FONT_MONONOKI,
                                              (self.new_download_rect.right - 20, self.input_newd_url.pos.y), (20, 10),
                                              'right', 'black', 'lightgrey', 'darkgrey', border_width=1,
                                              border_radius=20,
                                              func=self.func_comprobar_url)

        self.text_newd_title_details = Text(self.txts['detalles'], 20, FONT_MONONOKI, (self.new_download_rect.centerx, self.new_download_rect.centery-15))
        self.text_newd_filename = Text(self.txts['nombre']+': ----------', 16, FONT_MONONOKI,
                                              (self.new_download_rect.left + 20, self.new_download_rect.centery + 15), 'left')
        self.text_newd_file_type = Text(self.txts['tipo']+': ----------', 16, FONT_MONONOKI,
                                              (self.new_download_rect.left + 20, self.new_download_rect.centery+35), 'left')
        self.text_newd_size = Text(self.txts['tamaño']+': -------', 16, FONT_MONONOKI,
                                          (self.new_download_rect.left + 20, self.new_download_rect.centery+55), 'left')
        self.text_newd_status = Text(self.txts['descripcion-state[esperando]'], 16, FONT_MONONOKI,
                                            (self.new_download_rect.left + 20, 350), 'left')

        self.text_newd_hilos = Text(self.txts['config-hilos'].format(self.threads), 16, FONT_MONONOKI,
                                             (self.text_newd_file_type.right+170, self.new_download_rect.centery-20), 'left', with_rect=True,
                                    color_rect=(40,40,40), padding=10,
                                    border_width=3, border_color='black')
        self.btn_newd_hilos = Button(self.txts['cambiar'],16, FONT_MONONOKI,
                                             (self.text_newd_hilos.left, self.text_newd_hilos.bottom+10),
                                             (20,10),color='white', color_rect=(20,20,20), color_rect_active=(40, 40, 40),
                                             border_radius=5, border_width=3, dire='topleft',
                                             func=lambda: self.Mini_GUI_manager.add(mini_GUI.select(self.btn_newd_hilos.topright,
                                                                [1,2,4,8,16,32],min_width=50),
                                                                self.func_select_box_hilos_newd)
        )


        # Pantalla de configuraciones
        self.text_config_title = Text(self.txts['title-configuraciones'], 26, FONT_MONONOKI,
                                             (self.ventana_rect.centerx, 30), with_rect=True, color_rect=(20,20,20))
        self.btn_config_exit = Button('', 26, FONT_SIMBOLS, (self.ventana_rect.w, 0), 10, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_exit_configs)

        self.text_config_hilos = Text(self.txts['config-hilos'].format(self.threads), 16, FONT_MONONOKI,
                                             (30, 100), 'left', with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_change_hilos = Button(
            self.txts['cambiar'],16, FONT_MONONOKI,
            (self.text_config_hilos.right + 60, self.text_config_hilos.centery),
            (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
            border_radius=0, border_width=3
        )
        self.select_change_hilos: Select_box = Select_box(self.btn_change_hilos, [1,2,4,8,16,32], auto_open=False, position='right', animation_dir='vertical', func=self.func_select_box_hilos)

        self.text_config_idioma = Text(self.txts['config-idioma'], 16, FONT_MONONOKI, (30, 130), 'left', padding=10,with_rect=True, color_rect=(20,20,20))
        self.btn_config_idioma_es = Button('Español', 14, FONT_MONONOKI, (30, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('español'))
        self.btn_config_idioma_en = Button('English', 14, FONT_MONONOKI, (120, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('ingles'))
        
        self.text_config_apagar_al_finalizar_cola = Text(self.txts['apagar-al-finalizar']+' ('+self.txts['la']+' '+self.txts['cola']+')', 
                                                         16, FONT_MONONOKI, (30, 190), 'left', 'white', with_rect=True, 
                                                         color_rect=(20,20,20), padding=10)
        self.btn_config_apagar_al_finalizar_cola = Button('' if self.apagar_al_finalizar_cola else '', 16, FONT_SIMBOLS, (self.text_config_apagar_al_finalizar_cola.right, 190), 10, 'left', 'white',with_rect=True,
                                                                color_rect=(20,20,20),color_rect_active=(40, 40, 40),border_width=-1,
                                                                 func=self.toggle_apagar_al_finalizar_cola)
        
        self.text_config_LDM = Text(self.txts['bajo consumo']+': ', 16, FONT_MONONOKI, (30, 225), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_LDM = Button('' if self.low_detail_mode else '', 16, FONT_SIMBOLS, (self.text_config_LDM.right, 225),
                                     10, 'left', 'white', with_rect=True, color_rect=(20,20,20), color_rect_active=(40, 40, 40),
                                     border_width=-1, func=self.toggle_ldm)
        
        self.text_config_enfoques = Text(f'focus {self.txts["aplicacion"]}: ', 16, FONT_MONONOKI, (30, 260), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_enfoques = Button('' if self.enfoques else '', 16, FONT_SIMBOLS, 
                                                (self.text_config_enfoques.right, 260), 10,'left',
                                                'white',with_rect=True, color_rect=(20,20,20),color_rect_active=(40, 40, 40),
                                                border_width=-1, func=self.toggle_enfoques)
        
        
        self.text_config_detener_5min = Text('Detener a los 5min sin cambio: ', 16, FONT_MONONOKI, (30, 295), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_detener_5min = Button('' if self.detener_5min else '', 16, FONT_SIMBOLS, 
                                                (self.text_config_detener_5min.right, 295), 10,'left',
                                                'white',with_rect=True, color_rect=(20,20,20),color_rect_active=(40, 40, 40),
                                                border_width=-1, func=self.toggle_detener_5min)

        self.text_limitador_velocidad = Text(self.txts['limitar-velocidad']+': '+format_size_bits_to_bytes_str(self.velocidad_limite), 16, FONT_MONONOKI, (30, 340), 'left', 'white',padding=10)
        self.btn_config_velocidad = Button(
            self.txts['cambiar'],16, FONT_MONONOKI,
            (self.text_limitador_velocidad.right + 60, self.text_limitador_velocidad.centery),
            (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
            border_radius=0, border_width=3
        )
        self.select_config_velocidad = Select_box(self.btn_config_velocidad, [0]+[format_size_bits_to_bytes_str(2**x) for x in range(15,25)], auto_open=False, position='right', animation_dir='vertical', func=self.func_select_box_velocidad)

        self.list_config_extenciones = List(
            (self.ventana_rect.w*.3,self.ventana_rect.h*.7), (self.ventana_rect.w*.80,self.ventana_rect.centery),
            self.extenciones.copy(), 16, 10, (40,40,40), header=True, text_header=self.txts['extenciones'], background_color=(20,20,20), font=FONT_MONONOKI, dire='center',
            border_width = 3,smothscroll=True if not self.low_detail_mode else False
        )
        self.btn_config_añair_extencion: Button = Button(self.txts['añadir'], 16, FONT_MONONOKI, (self.list_config_extenciones.right, self.list_config_extenciones.top), (0,15), 'topleft', 'white', (20, 20, 20), (50, 50, 50), border_radius=0, border_bottom_left_radius=20, func=self.func_añadir_extencion)
        self.btn_config_eliminar_extencion: Button = Button(self.txts['eliminar'], 16, FONT_MONONOKI, (self.list_config_extenciones.right, self.list_config_extenciones.bottom), (0,15), 'topright', 'white', (20, 20, 20), (50, 50, 50), border_radius=0, border_bottom_right_radius=20, func=lambda: \
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar los elementos']),
                lambda r: (self.func_eliminar_extencion() if r == 'aceptar' and self.list_config_extenciones.get_selects() else None)
            ))


        # Pantalla de extras
        self.text_extras_title = Text('Extras', 26, FONT_MONONOKI, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_extras_exit = Button('', 26, FONT_SIMBOLS, (self.ventana_rect.w, 0), 10, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_extras_to_main)

        self.btn_extras_read_version_notes = Button('', 20, FONT_SIMBOLS, (0,0), 10, 'right',
                                                      'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                                      func=lambda: os.startfile(Path(__file__).parent / 'version.txt'))
        self.text_extras_version = Text('Version '+VERSION, 26, FONT_MONONOKI, (0,0),
                                               'right',with_rect=True,color_rect=(20,20,20))

        self.text_extras_mi_nombre = Text('Edouard Sandoval', 30, FONT_MONONOKI, (400, 100),
                                                 'center', padding=0,with_rect=True,color_rect=(20,20,20))
        self.btn_extras_link_github = Button('', 30, FONT_SIMBOLS, (370, 200), 20, 'center',
                                                   func=lambda: os.startfile('http://github.com/Tecrato'))
        self.btn_extras_link_youtube = Button('輸', 30, FONT_SIMBOLS, (430, 200), 20, 'center',
                                                    func=lambda: os.startfile('http://youtube.com/channel/UCeMfUcvDXDw2TPh-b7UO1Rw'))
        self.btn_extras_install_extension = Button(self.txts['instalar']+' '+self.txts['extencion'], 20, FONT_MONONOKI, (self.ventana_rect.centerx, 300),
                                                         20, 'center', 'black','purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                        func=lambda: self.GUI_manager.add(
                                                                GUI.Desicion(self.ventana_rect.center, "Instalar extension","Desea instalar la extencion?\n\n\
El Archivo de la extencion se copiara \n\
en el escritorio Y debera ejecutarlo\n\
con su navegador de preferencia"),
                                                                             lambda e: shutil.copy("./extencion.crx",user_desktop_path().joinpath('./Extencion.crx')) if e == 'aceptar' else None
                                                                )
        )

        self.btn_extras_borrar_todo = Button(self.txts['borrar datos'], 20, FONT_MONONOKI, (0,self.ventana_rect.h), dire="bottomleft",
                                                func=lambda: self.GUI_manager.add(
                                                 GUI.Desicion(self.ventana_rect.center, "Borrar todas las descargas","Desea borrar todas las descargas?",),
                                                lambda e: self.func_borrar_todas_las_descargas() if e == 'aceptar' else None
                                             )
        )

        # Pantalla principal
        self.list_to_draw: list[Text|Button|Input|Multi_list|Select_box]  = [
            self.txt_title, self.btn_extras, self.btn_configs, self.btn_new_descarga,
            self.btn_change_dir, self.lista_descargas, self.btn_reload_list
        ]
        self.list_to_click = [self.lista_descargas,self.btn_new_descarga, self.btn_configs, self.btn_reload_list, self.btn_extras,
                              self.btn_change_dir]

        # Ventana de nueva descarga
        self.list_to_draw_new_download = [
            self.text_newd_title, self.boton_newd_aceptar, self.boton_newd_cancelar,
            self.input_newd_paste, self.btn_comprobar_url, self.text_newd_title_details,
            self.text_newd_filename, self.text_newd_size, self.text_newd_status,
            self.text_newd_file_type, self.text_newd_hilos, self.btn_newd_hilos, self.input_newd_url,
        ]

        self.list_to_click_newd = [self.boton_newd_aceptar, self.boton_newd_cancelar, self.input_newd_paste,
                                   self.btn_comprobar_url, self.btn_newd_hilos]
        self.list_inputs_newd = [self.input_newd_url]

        # Pantalla de configuraciones
        self.list_to_draw_config = [self.text_config_title, self.btn_config_exit, self.text_config_hilos,
                                    self.text_config_idioma, self.btn_config_idioma_en, self.btn_config_idioma_es,
                                    self.btn_config_apagar_al_finalizar_cola,self.text_config_apagar_al_finalizar_cola,
                                    self.text_config_LDM,self.btn_config_LDM,self.btn_change_hilos,self.text_config_enfoques,
                                    self.btn_config_enfoques,self.text_config_detener_5min,self.btn_config_detener_5min,
                                    self.list_config_extenciones,self.btn_config_añair_extencion,self.select_change_hilos,
                                    self.btn_config_eliminar_extencion,self.text_limitador_velocidad,
                                    self.btn_config_velocidad,self.select_config_velocidad]
        self.list_to_click_config = [self.list_config_extenciones,self.btn_config_exit, 
                                     self.btn_config_idioma_en, self.btn_config_idioma_es,
                                     self.btn_config_apagar_al_finalizar_cola,self.btn_config_LDM,
                                     self.btn_config_enfoques,self.btn_config_detener_5min,self.btn_config_añair_extencion,
                                     self.btn_config_eliminar_extencion,self.select_change_hilos,
                                     self.select_config_velocidad]

        # Pantalla de Extras
        self.list_to_draw_extras = [self.text_extras_title, self.btn_extras_exit, self.text_extras_mi_nombre,
                                    self.btn_extras_link_github, self.btn_extras_link_youtube, self.text_extras_version,
                                    self.btn_extras_install_extension,self.btn_extras_borrar_todo,
                                    self.btn_extras_read_version_notes]
        self.list_to_click_extras = [self.btn_extras_exit, self.btn_extras_link_github, self.btn_extras_link_youtube,
                                     self.btn_extras_install_extension,self.btn_extras_borrar_todo,
                                     self.btn_extras_read_version_notes]
        self.move_objs()

    def move_objs(self):
        self.Mini_GUI_manager.limit = self.ventana_rect

        self.txt_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_extras.pos = (self.ventana_rect.w, 0)

        self.text_config_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_config_exit.pos = (self.ventana_rect.w, 0)

        #Loader
        self.loader.pos = (self.ventana_rect.w - 40, self.ventana_rect.h - 80)

        # Nueva descarga
        self.new_download_rect.center = self.ventana_rect.center
        self.text_newd_title.pos = (self.new_download_rect.centerx, self.new_download_rect.top + 20)
        self.input_newd_url.pos = (self.new_download_rect.left + 20, self.new_download_rect.top + 80)
        self.input_newd_paste.pos = (self.input_newd_url.right, self.input_newd_url.pos.y)
        self.btn_comprobar_url.pos = (self.new_download_rect.right - 20, self.input_newd_url.pos.y)

        self.text_newd_title_details.pos = (self.new_download_rect.centerx, self.new_download_rect.centery-20)
        self.text_newd_filename.pos = (self.new_download_rect.left + 20, self.new_download_rect.centery + 15)
        self.text_newd_file_type.pos = (self.new_download_rect.left + 20, self.new_download_rect.centery+35)
        self.text_newd_hilos.pos = (self.text_newd_file_type.right + 170, self.new_download_rect.centery - 20)
        self.text_newd_size.pos = (self.new_download_rect.left + 20, self.new_download_rect.centery+55)
        self.text_newd_status.pos = (self.new_download_rect.left + 20, self.new_download_rect.centery+75)
        self.btn_newd_hilos.pos = (self.text_newd_hilos.left, self.text_newd_hilos.bottom+10)

        self.boton_newd_cancelar.pos = Vector2(-20, 0) + self.new_download_rect.bottomright
        self.boton_newd_aceptar.pos = (self.boton_newd_cancelar.rect.left, self.new_download_rect.bottom)

        # Pantalla extras
        self.text_extras_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_extras_exit.pos = (self.ventana_rect.w, 0)
        self.text_extras_mi_nombre.pos = (self.ventana_rect.centerx, 100)
        self.btn_extras_link_github.pos = (self.text_extras_mi_nombre.left,self.text_extras_mi_nombre.centery+100)
        self.btn_extras_link_youtube.pos = (self.text_extras_mi_nombre.right,self.text_extras_mi_nombre.centery+100)
        self.btn_extras_install_extension.pos = (self.ventana_rect.centerx, 300)
        self.btn_extras_borrar_todo.pos = (3,self.ventana_rect.h-3)
        self.btn_extras_read_version_notes.pos = (self.ventana_rect.w-5, self.ventana_rect.h-20)
        self.text_extras_version.pos = (self.btn_extras_read_version_notes.left, self.btn_extras_read_version_notes.centery)
        
        # if len(self.lista_descargas.listas) > 0:
        self.lista_descargas.resize((self.ventana_rect.w - 60, self.ventana_rect.h - 140))
        self.btn_reload_list.pos = self.lista_descargas.topright

        # Pantalla Configuraciones
        self.list_config_extenciones.size = (self.ventana_rect.w*.3,self.ventana_rect.h*.7)
        self.list_config_extenciones.pos = (self.ventana_rect.w*.8,self.ventana_rect.centery)

        self.btn_config_añair_extencion.pos = self.list_config_extenciones.bottomleft
        self.btn_config_eliminar_extencion.pos = self.list_config_extenciones.bottomright

        self.btn_config_añair_extencion.width =  self.list_config_extenciones.width/2
        self.btn_config_eliminar_extencion.width =  self.list_config_extenciones.width/2

        self.btn_config_velocidad.pos = (self.text_limitador_velocidad.right + 60, self.text_limitador_velocidad.centery)

        self.redraw = True


    def buscar_acualizaciones(self):
        try:
            sera = check_update('acelerador de descargas', VERSION, 'last')
        except:
            return
        try:
            if not sera:
                return
            self.logger.write(f"\nSe a encontrado una nueva actualizacion\nObteniendo link...")
            self.logger.write(f"{sera}")

            self.Mini_GUI_manager.clear_group('actualizaciones')
            self.Mini_GUI_manager.add(mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['actualizacion'], 'Se a encontrado una nueva actualizacion\n\nObteniendo link...', (260,100)),group='actualizaciones')
        
            self.data_actualizacion['url'] = get_mediafire_url(sera['url'])
            self.logger.write(f"Obteniendo informacion de {self.data_actualizacion['url']}")
            response2 = requests.get(self.data_actualizacion['url'], stream=True, allow_redirects=True, timeout=30)

            self.data_actualizacion['file_type'] = response2.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if self.data_actualizacion['file_type'] in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')
            self.data_actualizacion['size'] = int(response2.headers.get('content-length'))
            self.data_actualizacion['file_name'] = response2.headers.get('content-disposition').split('filename=')[1].replace('"', '')

            self.Mini_GUI_manager.clear_group('actualizaciones')
            self.Mini_GUI_manager.add(
                mini_GUI.desicion_popup(Vector2(50000,50000), self.txts['actualizacion'], self.txts['gui-desea descargar la actualizacion'], (250,100), self.txts['agregar'], 'bottomright'),
                lambda _: (requests.get('http://127.0.0.1:5000/descargas/add_from_program', params={'url': self.data_actualizacion['url'], "tipo": self.data_actualizacion['file_type'], 'hilos': self.threads, 'nombre': self.data_actualizacion['file_name'], 'size':self.data_actualizacion['size']}),self.Func_pool.start('reload list')),
                group='actualizaciones'
            )
        except Exception as err:
            self.Mini_GUI_manager.clear_group('actualizaciones')
            self.Mini_GUI_manager.add(
                mini_GUI.desicion_popup(
                    Vector2(50000,50000),
                    self.txts['actualizacion'], 
                    'Error al obtener actualizacion.',
                    (250,100),
                    "abrir link",
                    'bottomright',
                ),
                func=lambda x: (os.startfile(sera['url']) if x != 'exit' else None),
                group='actualizaciones'
            )
            print(type(err))
            print(err)
        self.redraw = True


    def comprobar_url(self) -> None:
        if not self.url:
            return

        self.can_add_new_download = False

        title: str = urlparse(self.url).path
        for x in title.split('/')[::-1]:
            if '.' in x:
                title = unquote(x).replace('+', ' ')
                break
        else:
            title: str = title.split('/')[-1]
            title: str = unquote(title).replace('+', ' ')

        self.new_filename = title
        if len(self.new_filename) > 33:
            self.new_filename = self.new_filename[:33] + '...'
        else:
            self.text_newd_filename.text = f'{self.new_filename}'

        self.text_newd_status.text = self.txts['descripcion-state[conectando]']
        try:
            response = requests.get(self.url, stream=True, timeout=15,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'})

            self.logger.write(f"Informacion obtenida: {self.url}")
            self.logger.write(response.headers)

            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            print(response.headers) #Accept-Ranges
            if 'bytes' in response.headers.get('Accept-Ranges', ''):
                self.btn_newd_hilos.pos = (self.text_newd_hilos.left, self.text_newd_hilos.bottom + 10)
                self.new_threads = self.threads
            else:
                self.btn_newd_hilos.pos = (-self.text_newd_hilos.left, -self.text_newd_hilos.bottom + 10)
                self.new_threads = 1
                self.text_newd_hilos.text = self.txts['config-hilos'].format(self.new_threads)

            self.new_file_type = tipo
            self.text_newd_file_type.text = self.txts['tipo']+': ' + tipo
            if self.new_file_type in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')

            # print(response.headers)
            self.new_file_size = int(response.headers.get('content-length', 1))
            if self.new_file_size < 8 *self.threads:
                print(response.text)
                raise LowSizeError('Peso muy pequeño')
            peso_formateado = format_size_bits_to_bytes(self.new_file_size)
            self.text_newd_size.text = f'{peso_formateado[1]:.2f}{UNIDADES_BYTES[peso_formateado[0]]}'

            if a := response.headers.get('content-disposition', False):
                nuevo_nombre = a.split(';')
                for x in nuevo_nombre :
                    if 'filename=' in x:
                        nuevo_nombre = x[10:].replace('"', '')
                        break
                print(nuevo_nombre)
                if isinstance(nuevo_nombre, str):
                    self.new_filename = nuevo_nombre
                    self.text_newd_filename.text = self.new_filename

            self.text_newd_status.text = self.txts['estado']+': '+self.txts['disponible']

            self.can_add_new_download = True
        except requests.URLRequired:
            return
        except (requests.exceptions.InvalidSchema,requests.exceptions.MissingSchema):
            self.text_newd_status.text = self.txts['descripcion-state[url invalida]']
        except (requests.exceptions.ConnectTimeout,requests.exceptions.ReadTimeout):
            self.text_newd_status.text = self.txts['descripcion-state[tiempo agotado]']
        except requests.exceptions.ConnectionError:
            self.text_newd_status.text = self.txts['descripcion-state[error internet]']
        except TrajoHTML:
            self.text_newd_status.text = self.txts['descripcion-state[trajo un html]']
        except LinkCaido:
            self.text_newd_status.text = 'Link Caido'
        except Exception as err:
            print(err)
            print(type(err))
            self.logger.write(f'Error conprobar {self.url} - {type(err)} -> {err}')
            self.text_newd_status.text = 'Error'
        finally:
            self.redraw = True

    def eventos_en_comun(self, evento: pag.event.Event):
        mx, my = pag.mouse.get_pos()
        if evento.type == QUIT:
            self.cicle_try = 20
            self.screen_main_bool: bool = False
            self.screen_new_download_bool: bool = False
            self.screen_configs_bool: bool = False
            self.screen_extras_bool: bool = False
        elif evento.type == pag.KEYDOWN and evento.key == pag.K_F12:
            momento = datetime.datetime.today().strftime('%d-%m-%y %f')
            pag.image.save(self.ventana,self.carpeta_screenshots.joinpath('Download Manager {}.png'.format(momento)))
        if evento.type == pag.WINDOWRESTORED:
            return True
        elif evento.type == MOUSEBUTTONDOWN and evento.button in [1,3] and self.Mini_GUI_manager.click(evento.pos):
            return True
        elif evento.type == WINDOWMINIMIZED:
            return True
        elif evento.type == WINDOWFOCUSLOST:
            # self.framerate = 30
            return True
        elif evento.type in [WINDOWTAKEFOCUS, WINDOWFOCUSGAINED, WINDOWMAXIMIZED]:
            # self.framerate = 60
            return True
        elif evento.type in [pag.WINDOWRESIZED,pag.WINDOWMAXIMIZED,pag.WINDOWSIZECHANGED,pag.WINDOWMINIMIZED,pag.WINDOWSHOWN,pag.WINDOWMOVED]:
            size = Vector2(pag.display.get_window_size())
            if size.x < MIN_RESOLUTION[0]:
                size.x = MIN_RESOLUTION[0]
            if size.y < MIN_RESOLUTION[1]:
                size.y = MIN_RESOLUTION[1]
            self.ventana = pag.display.set_mode(size, pag.RESIZABLE|pag.DOUBLEBUF)
            self.ventana_rect = self.ventana.get_rect()
            self.move_objs()
            return True
        elif self.loading > 0:
            return True
        elif self.GUI_manager.active >= 0:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.GUI_manager.pop()
            elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                self.GUI_manager.click((mx, my))
            return True
        return False

    def draw_objs(self, lista: list[Text|Button|Input|Multi_list|Select_box]):
        if self.draw_background:
            self.ventana.fill((20, 20, 20))
            
        redraw = self.redraw
        self.redraw = False
        if redraw:
            for x in lista:
                x.redraw = 2

        if self.loading > 0:
            self.loader.update(self.delta_time.dt)
            self.loader.redraw = 1
        self.updates.clear()
        for i,x in sorted(enumerate(lista+[self.GUI_manager,self.Mini_GUI_manager,self.loader]),reverse=False):
            re = x.redraw
            if isinstance(x, (Button,Select_box,mini_GUI.mini_GUI_admin,GUI.GUI_admin)):
                r = x.draw(self.ventana, pag.mouse.get_pos())
            else:
                r = x.draw(self.ventana)
            [self.updates.append(s) for s in r]
            for y in r:
                for p in lista[i+1:]:
                    if p.collide(y) and p.redraw < 1:
                        p.redraw = 1
            if re < 2:
                continue
            for y in r:
                for p in lista[:i]:
                    if p.collide(y) and p.redraw < 1:
                        p.redraw = 1
        
        if redraw:
            pag.display.update()
        else:
            try:
                pag.display.update(self.updates)
            except:
                print('error')
                print(self.updates)
                # pag.display.update()

    def screen_configs(self):
        if self.screen_configs_bool:
            self.cicle_try = 0
            self.draw_background = True
            self.redraw = True
        while self.screen_configs_bool:
            self.relog.tick(self.framerate)
            self.delta_time.update()

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()
            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                    continue
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.screen_configs_bool = False
                        self.screen_main_bool = True
                    # elif evento.key == pag.K_v and pag.key.get_pressed()[pag.K_LCTRL]:
                    #     for x in self.list_inputs:
                    #         if x.typing:
                    #             x.set(pyperclip.paste())
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for i,x in sorted(enumerate(self.list_to_click_config), reverse=True):
                        if isinstance(x, List) and x.click((mx,my),pag.key.get_pressed()[pag.K_LCTRL]):
                            self.redraw = True
                            break
                        elif x.click((mx, my)):
                            self.redraw = True
                            break
                elif evento.type == MOUSEBUTTONUP:
                    self.list_config_extenciones.scroll = False
                elif evento.type == MOUSEWHEEL and self.list_config_extenciones.rect.collidepoint((mx,my)):
                    self.list_config_extenciones.rodar(evento.y*15)
                elif evento.type == MOUSEMOTION and self.list_config_extenciones.scroll:
                    self.list_config_extenciones.rodar_mouse(evento.rel[1])
            
            for x in self.list_to_draw_config:
                x.update()

            if not self.drawing:
                continue
            self.draw_objs(self.list_to_draw_config)

    def screen_new_download(self):
        if self.screen_new_download_bool:
            self.cicle_try = 0
            self.redraw = True
        else:
            return

        self.input_newd_url.clear()
        self.text_newd_filename.text = self.txts['nombre']+': ----------'
        self.text_newd_size.text = self.txts['tamaño']+': -------'
        self.text_newd_status.text = self.txts['descripcion-state[esperando]']
        self.text_newd_file_type.text = self.txts['tipo']+': -------'
        self.new_threads = self.threads
        self.text_newd_hilos.text = self.txts['config-hilos'].format(self.new_threads)
        self.btn_newd_hilos.pos = (-self.text_newd_hilos.left, -self.text_newd_hilos.bottom + 10)
        self.redraw = True
        self.draw_background = False

        while self.screen_new_download_bool:
            self.relog.tick(self.framerate)

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()

            for x in self.list_inputs_newd:
                x.eventos_teclado(eventos)
            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                    continue
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.func_newd_close()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_newd:
                        if x.click((mx, my)):
                            self.redraw = True
                            break
            
            
            for x in self.list_to_draw_new_download:
                x.update(dt=self.delta_time.dt)
            if not self.drawing:
                continue
            self.ventana.fill((20, 20, 20))
            pag.draw.rect(self.ventana, (50, 50, 50), self.new_download_rect, 0, 20)
            self.draw_objs(self.list_to_draw_new_download)

        self.draw_background = True
        self.ventana.fill((20, 20, 20))
        pag.display.update()

    def main_cycle(self) -> None:
        if self.screen_main_bool:
            self.cicle_try = 0
            self.draw_background = True
            self.redraw = True

        while self.screen_main_bool:
            self.relog.tick(self.framerate)
            self.delta_time.update()

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)


            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                    continue
                elif evento.type == KEYDOWN and evento.key == K_ESCAPE:
                    self.screen_main_bool = False
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for i,x in sorted(enumerate(self.list_to_click), reverse=True):
                        if isinstance(x, Multi_list) and x.click((mx,my),pag.key.get_pressed()[pag.K_LCTRL]):
                            break
                        elif x.click((mx, my)):
                            break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 3:
                    if self.lista_descargas.click((mx, my),pag.key.get_pressed()[pag.K_LCTRL],button=3) and (result := self.lista_descargas.get_selects()):
                        self.Mini_GUI_manager.add(mini_GUI.select((mx+1, my+1),
                                                                  [self.txts['descargar'], self.txts['eliminar'],
                                                                   self.txts['actualizar_url'], 'get url', self.txts['añadir a la cola'], self.txts['remover de la cola'], self.txts['limpiar cola'],
                                                                   self.txts['reiniciar'], self.txts['cambiar nombre']],
                                                                  captured=result),
                                                  self.func_select_box)
                elif evento.type == MOUSEBUTTONUP:
                    self.lista_descargas.detener_scroll()
                elif evento.type == MOUSEWHEEL and self.lista_descargas.rect.collidepoint((mx,my)):
                    self.lista_descargas.rodar(evento.y*15)
                elif evento.type == MOUSEMOTION and self.lista_descargas.scroll:
                    self.lista_descargas.rodar_mouse(evento.rel[1])

            for x in self.list_to_draw:
                x.update(dt=self.delta_time.dt)

            if not self.drawing:
                continue
            self.draw_objs(self.list_to_draw)

    def screen_extras(self):
        if self.screen_extras_bool:
            self.cicle_try = 0
            self.redraw = True

        while self.screen_extras_bool:
            self.relog.tick(self.framerate)

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()

            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                    continue
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.screen_extras_bool = False
                        self.screen_main_bool = True
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_extras:
                        if x.click((mx, my)):
                            break

            for x in self.list_to_draw_extras:
                x.update(dt=self.delta_time.dt)
            if not self.drawing:
                continue
            self.draw_objs(self.list_to_draw_extras)


    def func_select_box(self, respuesta) -> None:
        if not self.cached_list_DB: return

        if len(respuesta['obj']) > 1 and respuesta['index'] == 1:
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar los elementos']),
                lambda r: (self.del_downloads(respuesta['obj']) if r == 'aceptar' else None)
            )
            return
        elif len(respuesta['obj']) > 1 and respuesta['index'] in [2,3,6,8]:
            self.mini_ventana(4)
            return

        if len(respuesta['obj']) > 1:
            for x in respuesta['obj']:
                self.func_select_box({'obj': [x], 'index': respuesta['index']})
            return
        else:
            print(respuesta)
            obj_cached = self.cached_list_DB[respuesta['obj'][0]['index']]

        if respuesta['index'] == 0:
            # 0 descargar
            Thread(target=self.func_descargar, args=(obj_cached,)).start()
        elif respuesta['index'] == 1:
            # Eliminar la descarga

            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar el elemento']+f'\n\n{obj_cached[0]} -> "{obj_cached[1]}"'),
                lambda r: (self.del_download(obj_cached[0]) if r == 'aceptar' else None)
            )
        elif respuesta['index'] == 2:
            # Cambiar la url
            response = requests.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached[0]}').json()
            if response['downloading'] == True or response['cola'] == True:
                self.mini_ventana(1)
                return
            self.new_url_id = obj_cached[0]
            self.func_main_to_new_download()
            self.redraw = True
        elif respuesta['index'] == 3:
            # copiar url al portapapeles
            pyperclip.copy(obj_cached[4])
            self.mini_ventana(3)
        elif respuesta['index'] == 4:
            # 4 añadir a la cola
            response = requests.get(f'http://127.0.0.1:5000/cola/add/{obj_cached[0]}').json()
            if response['status'] == 'ok':
                self.cola.append(obj_cached[0])
                self.lista_descargas[6][respuesta['obj'][0]['index']] = f'[{self.cola.index(obj_cached[0])}]'         
        elif respuesta['index'] == 5:
            # 5 remover de la cola
            response = requests.get(f'http://127.0.0.1:5000/cola/delete/{obj_cached[0]}').json()
            if response['status'] == 'ok':
                self.cola.remove(obj_cached[0])
                self.lista_descargas[6][respuesta['obj'][0]['index']] = f' - '   
        elif respuesta['index'] == 6:
            # 6 limpiar cola
            response = requests.get(f'http://127.0.0.1:5000/cola/clear').json()
            if response['status'] == 'ok':
                self.cola.clear()
                for x in range(len(self.lista_descargas)):
                    self.lista_descargas[6][x] = f' - '
        elif respuesta['index'] == 7:
            # 7 reiniciar descarga
            response = requests.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached[0]}').json()
            if response['downloading'] == False and requests.get(f'http://127.0.0.1:5000/descargas/update/estado/{obj_cached[0]}/esperando').json()['status'] == 'ok':
                shutil.rmtree(self.carpeta_cache.joinpath(f'./{obj_cached[0]}'), True)
                self.lista_descargas[5][respuesta['obj'][0]['index']] = self.txts['esperando'].capitalize()
        elif respuesta['index'] == 8:
            # 8 cambiar nombre
            response = requests.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached[0]}').json()
            if response['downloading'] == True:
                self.mini_ventana(1)
                return
            nombre = askstring(self.txts['nombre'], self.txts['gui-nombre del archivo'],initialvalue=obj_cached[1])
            if not nombre or nombre == '':
                return
            response = requests.get(f'http://127.0.0.1:5000/descargas/update/nombre/{obj_cached[0]}/{nombre}').json()
            if response['status'] == 'ok':
                self.lista_descargas[1][int(respuesta['obj'][0]['index'])] = nombre
        self.redraw = True

    def mini_ventana(self,num):
        if num == 0:
            self.Mini_GUI_manager.clear_group("descarga iniciada")
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', self.txts['descargar'],
                                    self.txts['gui-descarga iniciada']),
                group='descarga iniciada'
            )
        elif num == 1:
            self.Mini_GUI_manager.clear_group("descarga en curso")
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Error',
                                    self.txts['gui-descarga en curso']),
                group='descarga en curso'
            )
        elif num == 2:
            self.Mini_GUI_manager.clear_group("descarga eliminada")
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', self.txts['eliminar'],
                                    self.txts['gui-descarga eliminada']),
                group='descarga eliminada'
            )
        elif num == 3:
            self.Mini_GUI_manager.clear_group('portapapeles')
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Copiado',
                                      self.txts['copiado al portapapeles']),
                group='portapapeles'
            )
        elif num == 4:
            # Mini ventana de que solo esta disponible si selecciona 1 descarga
            self.Mini_GUI_manager.clear_group("solo una descarga")
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Error',
                                        self.txts['gui-solo una descarga'],(200,90)),
                group='solo una descarga'
            )

    def func_añadir_extencion(self):
        nombre = askstring('Extencion', 'Ingrese la extencion que desea agregar')
        if not nombre or nombre == '':
            return
        self.extenciones.append(nombre)
        self.list_config_extenciones.append(nombre)
        self.save_json()


    def func_eliminar_extencion(self):
        for i,x in sorted(self.list_config_extenciones.get_selects(), reverse=True):
            self.extenciones.pop(i)
            self.list_config_extenciones.pop(i)
        self.save_json()

    def func_select_box_hilos(self, respuesta) -> None:
        self.threads = 2**respuesta['index']

        self.text_config_hilos.text = self.txts['config-hilos'].format(self.threads)

    def func_select_box_hilos_newd(self, respuesta) -> None:
        self.new_threads = 2**respuesta['index']

        self.text_newd_hilos.text = self.txts['config-hilos'].format(self.new_threads)

    def func_select_box_velocidad(self, respuesta) -> None:
        diccionario_velocidades = {
            0: 0,
            1: 2**15,
            2: 2**16,
            3: 2**17,
            4: 2**18,
            5: 2**19,
            6: 2**20,
            7: 2**21,
            8: 2**22,
            9: 2**23,
            10: 2**24,
        }
        self.velocidad_limite = diccionario_velocidades[respuesta['index']]

        self.text_limitador_velocidad.text = self.txts['limitar-velocidad']+': '+format_size_bits_to_bytes_str(self.velocidad_limite)
        self.btn_config_velocidad.pos = (self.text_limitador_velocidad.right + 60, self.text_limitador_velocidad.centery)

    def del_download(self, index):
        response = requests.get(f'http://127.0.0.1:5000/descargas/delete/{index}')
        if response.json().get('status') == 'ok':
            self.mini_ventana(2)
            self.Func_pool.start('reload list')
        elif response.json().get('status') == 'error':
            self.mini_ventana(1)

    def del_downloads(self,obj):
        for x in obj:
            requests.get(f'http://127.0.0.1:5000/descargas/delete/{self.cached_list_DB[x['index']][0]}')
        self.Func_pool.start('reload list')
        return
    
    def func_add_download(self):
        if not self.can_add_new_download:
            return 0
        if self.actualizar_url:
            response = requests.get(f'http://127.0.0.1:5000/descargas/update/url/{self.new_url_id}/{self.url}')
            self.actualizar_url = False
            if response.json().get('status') == 'error':
                self.mini_ventana(1)
        else:
            requests.get('http://127.0.0.1:5000/descargas/add_from_program', params={'url': self.url, "tipo": self.new_file_type, 'hilos': self.new_threads, 'nombre': self.new_filename, 'size':self.new_file_size})

        self.Func_pool.start('reload list')
        self.screen_new_download_bool = False
        self.screen_main_bool = True

    def func_descargar(self, obj_cached):
        self.loading += 1
        if win32_tools.check_win(f'Downloader {obj_cached[0]}_{obj_cached[1]}'):
            if self.enfoques:
                win32_tools.front(f'Downloader {obj_cached[0]}_{obj_cached[1]}')
            return
        response = requests.get(f'http://localhost:5000/descargas/download/{obj_cached[0]}')
        if response.json().get('status') == 'ok':
            self.mini_ventana(0)
        else:
            self.mini_ventana(1)
        self.loading -= 1
        self.redraw = True

    def func_preguntar_carpeta(self):
        try:
            ask = askdirectory(initialdir=self.save_dir, title=self.txts['cambiar carpeta'])
            if not ask:
                return
            self.save_dir = ask
            self.save_json()
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'bottomright', self.txts['carpeta cambiada'], self.txts['gui-carpeta cambiada con exito'])
            )
        except:
            pass
    
    def reload_lista_descargas(self):
        try:
            self.loading += 1
            response = requests.get('http://127.0.0.1:5000/descargas/get_all',timeout=5)
            self.cached_list_DB = response.json()['lista']
            self.cola = response.json()['cola']
            
            diff = self.lista_descargas.listas[0].desplazamiento
            self.lista_descargas.clear()

            if not self.cached_list_DB:
                self.lista_descargas.clear()
                self.lista_descargas.append((None, None, None))
                return 0

            
            for row in self.cached_list_DB:
                id = row[0]
                nombre = row[1]
                tipo = row[2].split('/')[0]
                peso_formateado = format_size_bits_to_bytes(row[3])
                peso = f'{peso_formateado[1]:.2f}{UNIDADES_BYTES[peso_formateado[0]]}'
                hilos = row[6]
                fecha = datetime.datetime.fromtimestamp(float(row[7]))
                # txt_fecha = f'{fecha.hour}:{fecha.minute}:{fecha.second} - {fecha.day}/{fecha.month}/{fecha.year}'
                txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
                estado = self.txts[f'{row[8]}'.lower()] if f'{row[8]}'.lower() in self.txts else row[8]
                cola = ' - 'if not row[0] in self.cola else f'[{self.cola.index(row[0])}]'
                self.lista_descargas.append([id,nombre, tipo, hilos, peso, estado, cola, txt_fecha])

            self.lista_descargas.rodar(diff)

            self.Mini_GUI_manager.clear_group('lista_descargas')
            # self.Mini_GUI_manager.add(
            #     mini_GUI.more_objs.aviso1((50000, 50000), 'bottomright', self.txts['lista actualizada'],FONT_MONONOKI),
            #     group='lista_descargas'
            # )
        except Exception as err:
            print(type(err))
            print(err)
            self.Mini_GUI_manager.clear_group('lista_descargas')
            self.Mini_GUI_manager.add(
                mini_GUI.more_objs.aviso1((50000, 50000), 'bottomright', 'error updating list',FONT_MONONOKI),
                group='lista_descargas'
            )
            raise ConnectionError("No se pudo conectar con el servidor")
        finally:
            self.loading -= 1
            self.redraw = True

    def func_borrar_todas_las_descargas(self):
        requests.get('http://127.0.0.1:5000/descargas/delete_all',timeout=5)
        self.Func_pool.start('reload list')


    def func_paste_url(self, url=False):
        """Pegar la url en el input"""
        if url:
            self.input_newd_url.set(url)
        else:
            self.input_newd_url.set(pyperclip.paste())

    def toggle_apagar_al_finalizar_cola(self):
        self.apagar_al_finalizar_cola = not self.apagar_al_finalizar_cola
        self.btn_config_apagar_al_finalizar_cola.text = ''if self.apagar_al_finalizar_cola else ''

    def toggle_ldm(self):
        self.low_detail_mode = not self.low_detail_mode
        self.btn_config_LDM.text = ''if self.low_detail_mode else ''
        self.lista_descargas.smothscroll = not self.low_detail_mode  
        self.list_config_extenciones.smothscroll = not self.low_detail_mode  
    def toggle_enfoques(self):
        self.enfoques = not self.enfoques
        self.btn_config_enfoques.text = '' if self.enfoques else ''
    def toggle_detener_5min(self):
        self.detener_5min = not self.detener_5min
        self.btn_config_detener_5min.text = '' if self.detener_5min else ''

    def func_comprobar_url(self):
        self.url = self.input_newd_url.get_text()
        self.thread_new_download = Thread(target=self.comprobar_url, daemon=True)
        self.thread_new_download.start()

    def func_change_idioma(self, idioma):
        self.idioma = idioma
        self.txts = idiomas[self.idioma]
        self.configs['idioma'] = self.idioma

        self.generate_objs()
        self.Func_pool.start('reload list')
        self.move_objs()
        self.redraw = True

    def func_newd_close(self):
        self.screen_new_download_bool = False
        if self.thread_new_download and self.thread_new_download.is_alive():
            self.thread_new_download.join(.1)
            
        self.screen_main_bool = True

    def func_main_to_config(self):
        self.screen_main_bool = False
        self.screen_configs_bool = True
        self.screen_new_download_bool = False

    def func_exit_configs(self):
        self.screen_configs_bool = False
        self.screen_main_bool = True
        self.screen_new_download_bool = False

        self.save_json()

    def func_extras_to_main(self):
        self.screen_main_bool = True
        self.screen_configs_bool = False
        self.screen_new_download_bool = False
        self.screen_extras_bool = False

    def func_main_to_extras(self):
        self.screen_main_bool = False
        self.screen_configs_bool = False
        self.screen_new_download_bool = False
        self.screen_extras_bool = True

    def func_main_to_new_download(self):
        self.screen_main_bool = False
        self.screen_configs_bool = False
        self.screen_new_download_bool = True
        self.screen_extras_bool = False


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    if not (len(sys.argv) > 1 and str(sys.argv[1]) == '--run'):
        try:
            requests.get('http://127.0.0.1:5000/open_program')
        except requests.exceptions.ConnectionError:
            os.startfile(Path(__file__).parent / 'listener.exe')
            time.sleep(3)
            requests.get('http://127.0.0.1:5000/open_program')
        finally:
            sys.exit()

    clase = DownloadManager()
