import sys
import requests
import time
import os
import json
import pygame as pag
import shutil
import pyperclip
import datetime
import socket
from pathlib import Path

from tkinter.filedialog import askdirectory
from tkinter.simpledialog import askstring
from threading import Thread
from urllib.parse import urlparse, unquote
from Utilidades_pygame import Text, Button, List, Multi_list, GUI, mini_GUI, Input, Select_box, Particles, Bloque
from Utilidades import Funcs_pool, win32_tools, Deltatime,  UNIDADES_BYTES
from Utilidades import format_size_bits_to_bytes, format_size_bits_to_bytes_str
from Utilidades.logger import Logger
from platformdirs import user_desktop_path, user_log_path
from pygame.constants import (MOUSEBUTTONDOWN, MOUSEMOTION, KEYDOWN, QUIT, K_ESCAPE, MOUSEBUTTONUP, MOUSEWHEEL,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)
from pygame import Vector2

from loader import Loader
from textos import idiomas
from my_warnings import LinkCaido, LowSizeError, TrajoHTML
from constants import TITLE, DICT_CONFIG_DEFAULT, VERSION, FONT_MONONOKI, FONT_SIMBOLS, SCREENSHOTS_DIR, CONFIG_DIR, CACHE_DIR

RESOLUCION = [800, 550]
MIN_RESOLUTION = [600,450]

# noinspection PyAttributeOutsideInit
class DownloadManager:
    def __init__(self) -> None:
        pag.init()

        self.ventana: pag.Surface = pag.display.set_mode(RESOLUCION, pag.RESIZABLE|pag.DOUBLEBUF|pag.HWACCEL)
        self.ventana_rect: pag.Rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))
        pag.display.set_caption(TITLE)
        self.hwnd = pag.display.get_wm_info()['window']

        self.new_filename: str = ''
        self.new_file_type: str = ''
        self.new_file_size: int = 0
        self.new_threads: int = 1
        self.thread_new_download = None

        self.cached_list_DB: list[tuple] = []
        self.cola: list[int] = []

        self.updates: list[pag.Rect] = []
        self.extenciones: list[str] = []
        self.save_dir = './'
        self.url = ''
        self.threads: int = 4
        self.velocidad_limite = 0
        self.allow_particles = True
        self.apagar_al_finalizar_cola = False
        self.can_add_new_download = False
        self.drawing: bool = True
        self.enfoques: bool = True
        self.detener_5min: bool = True
        self.low_detail_mode: bool = False
        self.draw_background = True
        self.redraw: bool = True
        self.hitboxes = False
        self.running = True
        self.navegate_with_keys = True
        self.click = False
        self.loading = 0
        self.framerate: int = 60
        self.last_update = time.time()
        self.last_click = time.time()
        self.relog: pag.time.Clock = pag.time.Clock()
        self.delta_time: Deltatime = Deltatime(60)
        self.socket_client: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = Logger('Acelerador de descargas(UI)', user_log_path('Acelerador de descargas', 'Edouard Sandoval'))

        self.idioma: str = 'español'
        self.txts = idiomas[self.idioma]

        self.Func_pool = Funcs_pool()
        self.Func_pool.add('reload list',self.reload_lista_descargas)
        self.Func_pool.add('get sockets clients',self.get_server_updates)

        self.logger.write(f"Acelerador de descargas iniciado en {datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')}")


        self.lists_screens = {
            "main":{
                "func": self.main_cycle,
                "draw": [],
                "update": [],
                "click": [],
                "inputs": [],
                "active": True
                },
            "config":{
                "func": self.screen_configs,
                "draw": [],
                "update": [],
                "click": [],
                "inputs": [],
                "active": False
                },
            "extras":{
                "func": self.screen_extras,
                "draw": [],
                "update": [],
                "click": [],
                "inputs": [],
                "active": False
                },
            "new_download":{
                "func": self.screen_new_download,
                "draw": [],
                "update": [],
                "click": [],
                "inputs": [],
                "active": False
                }
            }
        self.load_resources()
        self.generate_objs()
        self.move_objs()
        self.Func_pool.start('reload list')
        self.Func_pool.start('get sockets clients')

        self.cicle_try = 0

        if self.enfoques:
            win32_tools.front2(pag.display.get_wm_info()['window'], sw_code=1)

        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.lists_screens.keys():
                if not self.lists_screens[x]["active"]:
                    continue
                self.redraw = True
                self.lists_screens[x]["func"]()
                self.cicle_try = 0
        self.running = False
        self.Func_pool.join('get sockets clients')
        pag.quit()


    def load_resources(self):
        try:
            self.configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT
        self.threads = self.configs.get('hilos',DICT_CONFIG_DEFAULT['hilos'])
        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.velocidad_limite = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])

        self.save_dir = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.apagar_al_finalizar_cola = self.configs.get('apagar al finalizar cola',DICT_CONFIG_DEFAULT['apagar al finalizar cola'])
        self.extenciones = self.configs.get('extenciones',DICT_CONFIG_DEFAULT['extenciones'])

        self.allow_particles = self.configs.get('particulas',DICT_CONFIG_DEFAULT['particulas'])

        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
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
        self.configs['particulas'] = self.allow_particles

        json.dump(self.configs, open(CONFIG_DIR.joinpath('./configs.json'), 'w'))

    def generate_objs(self) -> None:
        # Cosas varias
        self.GUI_manager = GUI.GUI_admin()
        self.Mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)

        self.particulas_mouse = Particles((0,0), radio=10, radio_dispersion=5, color=(255,255,255), velocity=1, vel_dispersion=2, angle=-90, angle_dispersion=60, radio_down=.2, gravity=0.15, max_particles=100, time_between_spawns=1, max_distance=1000, spawn_count=5, auto_spawn=False)

        # Loader
        self.loader = Loader((self.ventana_rect.w, self.ventana_rect.h))

        # Pantalla principal
        self.txt_title = Text(self.txts['title'], 26, FONT_MONONOKI, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_extras = Button(
            '', 26, FONT_SIMBOLS, (self.ventana_rect.w, 0), 10, 'topright', 'white',
            (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,func=self.func_main_to_extras
            )
        self.btn_configs = Button(
            '', 26, FONT_SIMBOLS, (0, 0), 10, 'topleft', 'white', (20, 20, 20),
            (50, 50, 50), 0, -1, border_width=-1, func=self.func_main_to_config
            )

        self.btn_new_descarga = Button(self.txts['btn-nueva_descarga'], 16, FONT_MONONOKI, (30, 80), 20,
                                             'topleft', 'white', (50, 50, 50), (90, 90, 90), 0, 20,
                                             border_bottom_right_radius=0, border_top_right_radius=0, border_width=-1,
                                             func=lambda: self.func_main_to_new_download())
        self.btn_change_dir = Button(self.txts['btn-cambiar_carpeta'], 16, FONT_MONONOKI,
                                           (self.btn_new_descarga.rect.right, 80), 20, 'topleft', 'white', (50, 50, 50),
                                           (90, 90, 90), 0, 20, border_bottom_left_radius=0, border_top_left_radius=0,
                                           border_width=-1, func=self.func_preguntar_carpeta)

        self.lista_descargas: Multi_list = Multi_list((self.ventana_rect.w - 60, self.ventana_rect.h - 140), (30, 120), 7, None, 11,
                                          10, (10,10,10), header_text=["id",self.txts['nombre'], self.txts['hilos'], self.txts['tamaño'], self.txts['estado'],self.txts['cola'], self.txts['fecha']],
                                          fonts=[FONT_MONONOKI for _ in range(7)], colums_witdh=[0, .065, .47, .55, .67, .79, .86], padding_left=10, border_color=(100,100,100),
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
        self.select_change_hilos: Select_box = Select_box(self.btn_change_hilos, [1,2,4,8,16,32], auto_open=False, position='right', animation_dir='vertical', text_size=20, padding_horizontal=20, func=self.func_select_box_hilos)

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

        self.text_limitador_velocidad = Text(self.txts['limitar-velocidad']+': '+format_size_bits_to_bytes_str(self.velocidad_limite), 16, FONT_MONONOKI, (30, 335), 'left', 'white',padding=10)
        self.btn_config_velocidad = Button(
            self.txts['cambiar'],16, FONT_MONONOKI,
            (self.text_limitador_velocidad.right + 60, self.text_limitador_velocidad.centery),
            (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
            border_radius=0, border_width=3
        )
        self.select_config_velocidad = Select_box(self.btn_config_velocidad, ['off']+[format_size_bits_to_bytes_str(2**x) for x in [15,16,17,19,20,23,24]], auto_open=False, position='right', animation_dir='vertical', padding_horizontal=10, func=self.func_select_box_velocidad)

        self.text_config_particulas = Text(self.txts['particulas']+': ', 16, FONT_MONONOKI, (30, 375), 'left', 'white', with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_particulas = Button('' if self.allow_particles else '', 16, FONT_SIMBOLS, (self.text_config_particulas.right, 375),
                                     10, 'left', 'white', with_rect=True, color_rect=(20,20,20), color_rect_active=(40, 40, 40),
                                     border_width=-1, func=self.toggle_particles)
        

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
        self.lists_screens['main']["draw"] = [
            self.txt_title, self.btn_extras, self.btn_configs, self.btn_new_descarga,
            self.btn_change_dir, self.lista_descargas, self.btn_reload_list, self.particulas_mouse
        ]
        self.lists_screens['main']["click"] = [
            self.lista_descargas,self.btn_new_descarga, self.btn_configs, self.btn_reload_list, self.btn_extras,
            self.btn_change_dir
        ]
        self.lists_screens['main']["update"].extend(self.lists_screens['main']["draw"])

        # Ventana de nueva descarga
        self.lists_screens['new_download']["draw"] = [
            self.text_newd_title, self.boton_newd_aceptar, self.boton_newd_cancelar,
            self.input_newd_paste, self.btn_comprobar_url, self.text_newd_title_details,
            self.text_newd_filename, self.text_newd_size, self.text_newd_status,
            self.text_newd_file_type, self.text_newd_hilos, self.btn_newd_hilos, self.input_newd_url,
        ]
        self.lists_screens['new_download']["click"] = [
            self.boton_newd_aceptar, self.boton_newd_cancelar, self.input_newd_paste,
            self.btn_comprobar_url, self.btn_newd_hilos, self.input_newd_url
        ]
        self.lists_screens['new_download']["inputs"] = [self.input_newd_url]
        self.lists_screens['new_download']["update"].extend(self.lists_screens['new_download']["draw"])

        # Pantalla de configuraciones
        self.lists_screens['config']["draw"] = [
            self.text_config_title, self.btn_config_exit, self.text_config_hilos,
            self.text_config_idioma, self.btn_config_idioma_en, self.btn_config_idioma_es,
            self.btn_config_apagar_al_finalizar_cola,self.text_config_apagar_al_finalizar_cola,
            self.text_config_LDM,self.btn_config_LDM,self.btn_change_hilos,self.text_config_enfoques,
            self.btn_config_enfoques,self.text_config_detener_5min,self.btn_config_detener_5min,
            self.list_config_extenciones,self.btn_config_añair_extencion,self.select_change_hilos,
            self.btn_config_eliminar_extencion,self.text_limitador_velocidad,self.text_config_particulas,
            self.btn_config_velocidad,self.select_config_velocidad,self.btn_config_particulas,
            self.particulas_mouse
        ]
        self.lists_screens['config']["click"] = [
            self.list_config_extenciones,self.btn_config_exit, 
            self.btn_config_idioma_en, self.btn_config_idioma_es,self.btn_config_particulas,
            self.btn_config_apagar_al_finalizar_cola,self.btn_config_LDM,
            self.btn_config_enfoques,self.btn_config_detener_5min,self.btn_config_añair_extencion,
            self.btn_config_eliminar_extencion,self.btn_change_hilos,self.btn_config_velocidad,
            self.select_config_velocidad,self.select_change_hilos,
        ]
        self.lists_screens['config']["update"].extend(self.lists_screens['config']["draw"])

        # Pantalla de Extras
        self.lists_screens['extras']["draw"] = [
            self.text_extras_title, self.btn_extras_exit, self.text_extras_mi_nombre,
            self.btn_extras_link_github, self.btn_extras_link_youtube, self.text_extras_version,
            self.btn_extras_install_extension,self.btn_extras_borrar_todo,
            self.btn_extras_read_version_notes, self.particulas_mouse
        ]
        self.lists_screens['extras']["click"] = [
            self.btn_extras_exit, self.btn_extras_link_github, self.btn_extras_link_youtube,
            self.btn_extras_install_extension,self.btn_extras_borrar_todo,
            self.btn_extras_read_version_notes
        ]
        self.lists_screens['extras']["update"].extend(self.lists_screens['extras']["draw"])
        self.move_objs()


        # Controles de los botones de la pantalla principal
        self.btn_new_descarga.controles_adyacentes = {
            'top': self.btn_configs,
            'left': self.btn_configs,
            'right': self.btn_change_dir
        }
        self.btn_change_dir.controles_adyacentes = {
            'top': self.btn_configs,
            'left': self.btn_new_descarga,
            'right': self.btn_extras
        }
        self.btn_extras.controles_adyacentes = {
            'bottom': self.btn_change_dir,
            'left': self.btn_configs,
            'right': self.btn_configs
        }
        self.btn_configs.controles_adyacentes = {
            'bottom': self.btn_new_descarga,
            'left': self.btn_extras,
            'right': self.btn_extras
        }

        # Controles de los botones de configuracion
        self.btn_config_idioma_es.controles_adyacentes = {
            'right': self.btn_config_idioma_en,
            'bottom': self.btn_config_apagar_al_finalizar_cola,
            'top': self.btn_config_exit
        }
        self.btn_config_idioma_en.controles_adyacentes = {
            'left': self.btn_config_idioma_es,
            'bottom': self.btn_config_apagar_al_finalizar_cola,
            'top': self.btn_config_exit
        }
        self.btn_config_apagar_al_finalizar_cola.controles_adyacentes = {
            'top': self.btn_config_idioma_en,
            'left': self.btn_config_idioma_en,
            'right': self.btn_config_exit,
            'bottom': self.btn_config_LDM
        }
        self.btn_config_LDM.controles_adyacentes = {
            'top': self.btn_config_apagar_al_finalizar_cola,
            'bottom': self.btn_config_enfoques,
        }
        self.btn_config_enfoques.controles_adyacentes = {
            'top': self.btn_config_LDM,
            'bottom': self.btn_config_detener_5min,
            'right': self.btn_config_exit
        }
        self.btn_config_detener_5min.controles_adyacentes = {
            'top': self.btn_config_enfoques,
            'bottom': self.btn_config_particulas,
            'right': self.btn_config_exit
        }
        self.btn_config_particulas.controles_adyacentes = {
            'top': self.btn_config_detener_5min,
            'bottom': self.btn_config_exit,
            'right': self.btn_config_exit
        }
        self.btn_config_exit.controles_adyacentes = {
            'bottom': self.btn_config_idioma_en,
            'left': self.btn_config_idioma_en,
            'top': self.btn_config_particulas
        }

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
                    self.new_filename = unquote(nuevo_nombre)
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

    def exit(self):
        self.cicle_try = 20
        for x in self.lists_screens.keys():
            self.lists_screens[x]["active"] = False

    def select_inputs_with_TAB(self, evento: pag.event.Event, screen_alias: str):
        if len(self.lists_screens[screen_alias]["inputs"]) == 0:
            return False
        if evento.key == pag.K_TAB:
            next_typ = False
            for x in self.lists_screens[screen_alias]["inputs"]:
                if x.typing:
                    x.typing = False
                    next_typ = True
                elif next_typ:
                    x.typing = True
                    break
            else:
                return False # ojojojojojooojojojojojojojojojojojojojojojojo
            return True
        else: 
            return False
        
    def move_hover(self, direccion: str, lista):
        for i,x in sorted(enumerate(lista), reverse=True):
            if isinstance(x, (Button)) and x.controles_adyacentes.get(direccion,False) and x.hover:
                if not x.controles_adyacentes.get(direccion,False):
                    break
                x.hover = False
                x.controles_adyacentes.get(direccion,False).hover = True
                break
        else:
            for x in lista:
                if isinstance(x, Button):
                    x.hover = False
            for x in lista:
                if isinstance(x, (Button)):
                    x.hover = True
                    break

    def select_btns_with_arrows(self, evento: pag.event.Event, screen_alias: str):
        if evento.key == pag.K_RIGHT:
            self.move_hover('right',self.lists_screens[screen_alias]["click"])
        elif evento.key == pag.K_LEFT:
            self.move_hover('left',self.lists_screens[screen_alias]["click"])
        elif evento.key == pag.K_UP:
            self.move_hover('top',self.lists_screens[screen_alias]["click"])
        elif evento.key == pag.K_DOWN:
            self.move_hover('bottom',self.lists_screens[screen_alias]["click"])
        else: return False
        return True

    def eventos_en_comun(self, evento: pag.event.Event, screen_alias: str):
        mx, my = pag.mouse.get_pos()
        if evento.type == pag.MOUSEBUTTONDOWN:
            self.last_click = time.time()
            if evento.button == 1:
                self.click = True
        elif evento.type == pag.MOUSEBUTTONUP:
            self.click = False
            
        if evento.type == QUIT:
            self.exit()
        elif evento.type == pag.KEYDOWN:
            if evento.key == pag.K_F12:
                momento = datetime.datetime.today().strftime('%d-%m-%y %f')
                result = win32_tools.take_window_snapshot(self.hwnd)
                surf = pag.image.frombuffer(result['buffer'],(result['bmpinfo']['bmWidth'], result['bmpinfo']['bmHeight']),'BGRA')
                pag.image.save(surf,SCREENSHOTS_DIR.joinpath('Download Manager {}.png'.format(momento)))
            elif evento.key == pag.K_F11:
                self.hitboxes = not self.hitboxes
        elif evento.type == pag.WINDOWRESTORED:
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
            self.ventana = pag.display.set_mode(size, pag.RESIZABLE|pag.DOUBLEBUF|pag.HWACCEL)
            self.ventana_rect = self.ventana.get_rect()
            self.move_objs()
            return True
        elif self.loading > 0:
            return True
        elif self.GUI_manager.active >= 0:
            self.GUI_manager.update_hover(evento.pos)
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
            r = x.draw(self.ventana)
            for s in r:
                self.updates.append(s)
            if self.hitboxes:
                for x in r:
                    pag.draw.rect(self.ventana, 'green', x, 1)
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
    
    def screen_configs(self):
        while self.lists_screens['config']["active"]:
            self.relog.tick(self.framerate)
            self.delta_time.update()

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()
            for evento in eventos:
                if self.eventos_en_comun(evento, 'config'):
                    self.redraw = True
                    continue
                elif evento.type == pag.KEYDOWN:
                    if evento.key == pag.K_ESCAPE:
                        self.lists_screens['config']["active"] = False
                        self.lists_screens['main']["active"] = True
                    elif evento.key == pag.K_TAB:
                        self.select_inputs_with_TAB(evento, 'config') # Opcional para que se puedan usar TAB para seleccionar otro input de la lista
                    elif self.select_btns_with_arrows(evento, 'config') and self.navegate_with_keys: # Opcional
                        continue
                    elif evento.key == pag.K_SPACE and self.navegate_with_keys:
                        for i,x in sorted(enumerate(self.lists_screens['config']["click"]),reverse=True):
                            if isinstance(x, Button) and x.hover:
                                x.click((mx,my))
                                break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.low_detail_mode and self.allow_particles:
                        self.particulas_mouse.spawn_pos = (mx,my)
                        self.particulas_mouse.spawn_particles()
                    self.on_mouse_click_general(evento, 'config')
                elif evento.type == MOUSEBUTTONUP:
                    self.list_config_extenciones.scroll = False
                elif evento.type == MOUSEWHEEL and self.list_config_extenciones.rect.collidepoint((mx,my)):
                    self.list_config_extenciones.rodar(evento.y*15)
                elif evento.type == MOUSEMOTION:
                    self.mouse_motion_event_general(evento, 'config')
            
            self.update_general(self.lists_screens['config']["update"], (mx,my))

            if not self.drawing:
                continue
            self.draw_objs(self.lists_screens['config']["draw"])

    def screen_new_download(self):
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

        while self.lists_screens['new_download']["active"]:
            self.relog.tick(self.framerate)

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()

            for x in self.lists_screens['new_download']["inputs"]:
                x.eventos_teclado(eventos)
            for evento in eventos:
                if self.eventos_en_comun(evento, 'new_download'):
                    self.redraw = True
                    continue
                elif evento.type == pag.KEYDOWN:
                    if evento.key == pag.K_ESCAPE:
                        self.func_newd_close()
                    elif evento.key == pag.K_TAB:
                        self.select_inputs_with_TAB(evento, 'new_download') # Opcional para que se puedan usar TAB para seleccionar otro input de la lista
                    elif self.select_btns_with_arrows(evento, 'new_download') and self.navegate_with_keys: # Opcional
                        continue
                    elif evento.key == pag.K_SPACE and self.navegate_with_keys:
                        for i,x in sorted(enumerate(self.lists_screens['new_download']["click"]),reverse=True):
                            if isinstance(x, Button) and x.hover:
                                x.click((mx,my))
                                break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    self.on_mouse_click_general(evento, 'new_download')
                elif evento.type == MOUSEMOTION:
                    self.mouse_motion_event_general(evento, 'new_download')
            
            self.update_general(self.lists_screens['new_download']["update"], (mx,my))
            if not self.drawing:
                continue
            self.ventana.fill((20, 20, 20))
            pag.draw.rect(self.ventana, (50, 50, 50), self.new_download_rect, 0, 20)
            self.draw_objs(self.lists_screens['new_download']["draw"])

        self.draw_background = True
        self.ventana.fill((20, 20, 20))
        pag.display.update()

    def main_cycle(self) -> None:
        while self.lists_screens['main']["active"]:
            self.relog.tick(self.framerate)
            self.delta_time.update()

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()
            for evento in eventos:
                if self.eventos_en_comun(evento, 'main'):
                    self.redraw = True
                    continue
                elif evento.type == pag.KEYDOWN:
                    if evento.key == pag.K_ESCAPE:
                        self.lists_screens['main']["active"] = False
                    elif evento.key == pag.K_TAB:
                        self.select_inputs_with_TAB(evento, 'main') # Opcional para que se puedan usar TAB para seleccionar otro input de la lista
                    elif self.select_btns_with_arrows(evento, 'main') and self.navegate_with_keys: # Opcional
                        continue
                    elif evento.key == pag.K_SPACE and self.navegate_with_keys:
                        for i,x in sorted(enumerate(self.lists_screens['main']["click"]),reverse=True):
                            if isinstance(x, Button) and x.hover:
                                x.click((mx,my))
                                break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.low_detail_mode and self.allow_particles:
                        self.particulas_mouse.spawn_pos = (mx,my)
                        self.particulas_mouse.spawn_particles()
                    self.on_mouse_click_general(evento, 'main')
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 3:
                    if self.lista_descargas.click((mx, my),pag.key.get_pressed()[pag.K_LCTRL],button=3) and (result := self.lista_descargas.get_selects()):
                        self.Mini_GUI_manager.add(mini_GUI.select((mx+1, my+1),
                                                                  [self.txts['descargar'], self.txts['eliminar'],
                                                                   self.txts['actualizar_url'], 'get url', self.txts['añadir a la cola'], self.txts['remover de la cola'], self.txts['limpiar cola'],
                                                                   self.txts['reiniciar'], self.txts['cambiar nombre']],
                                                                  captured=result),
                                                  self.func_select_box)
                elif evento.type == MOUSEBUTTONUP:
                    self.lista_descargas.scroll = False
                elif evento.type == MOUSEWHEEL and self.lista_descargas.rect.collidepoint((mx,my)):
                    self.lista_descargas.rodar(evento.y*15)
                elif evento.type == MOUSEMOTION:
                    self.mouse_motion_event_general(evento, 'main')

            
            self.update_general(self.lists_screens['main']["update"], (mx,my))

            if not self.drawing:
                continue
            self.draw_objs(self.lists_screens['main']["draw"])

    def screen_extras(self):
        while self.lists_screens['extras']["active"]:
            self.relog.tick(self.framerate)

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()

            for evento in eventos:
                if self.eventos_en_comun(evento, 'extras'):
                    self.redraw = True
                    continue
                elif evento.type == pag.KEYDOWN:
                    if evento.key == pag.K_ESCAPE:
                        self.lists_screens['extras']["active"] = False
                        self.lists_screens['main']["active"] = True
                    elif evento.key == pag.K_TAB:
                        self.select_inputs_with_TAB(evento, 'extras') # Opcional para que se puedan usar TAB para seleccionar otro input de la lista
                    elif self.select_btns_with_arrows(evento, 'extras') and self.navegate_with_keys: # Opcional
                        continue
                    elif evento.key == pag.K_SPACE and self.navegate_with_keys:
                        for i,x in sorted(enumerate(self.lists_screens['extras']["click"]),reverse=True):
                            if isinstance(x, Button) and x.hover:
                                x.click((mx,my))
                                break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.low_detail_mode and self.allow_particles:
                        self.particulas_mouse.spawn_pos = (mx,my)
                        self.particulas_mouse.spawn_particles()
                    self.on_mouse_click_general(evento, 'extras')
                elif evento.type == MOUSEMOTION:
                    self.mouse_motion_event_general(evento, 'extras')

            self.update_general(self.lists_screens['extras']["update"], (mx,my))
            if not self.drawing:
                continue
            self.draw_objs(self.lists_screens['extras']["draw"])

    def update_general(self,lista,mouse_pos):
        for i,x in sorted(enumerate(lista), reverse=True):
            x.update(dt=self.delta_time.dt,mouse_pos=mouse_pos)
        self.GUI_manager.update(mouse_pos=mouse_pos)
        self.Mini_GUI_manager.update(mouse_pos=mouse_pos)
        if self.loading > 0 and self.loader:
            self.loader.update(self.delta_time.dt)

    def wheel_event_general(self,evento,screen_alias: str) -> bool:
        for i,x in sorted(enumerate(self.lists_screens[screen_alias]["click"]), reverse=True):
            if isinstance(x, (Multi_list,List,Bloque)) and not x.scroll and x.rect.collidepoint(pag.mouse.get_pos()):
                x.rodar(evento.y*self.scroll_speed)
                return True
        return False

    def mouse_motion_event_general(self,evento, screen_alias: str) -> bool:
        if self.click:
            for i,x in sorted(enumerate(self.lists_screens[screen_alias]["click"]), reverse=True):
                if isinstance(x, (Multi_list, List, Bloque)) and x.scroll:
                    x.rodar_mouse(evento.rel[1])
                    return True
        self.Mini_GUI_manager.update_hover(evento.pos)
        for i,x in sorted(enumerate(self.lists_screens[screen_alias]["click"]), reverse=True):
            if isinstance(x, Button):
                x.update_hover(evento.pos)
        return False
    
    def on_mouse_click_general(self,evento,screen_alias: str) -> bool:
        for i,x in sorted(enumerate(self.lists_screens[screen_alias]["click"]), reverse=True):
            if isinstance(x, (Multi_list,List)) and x.click(evento.pos,pag.key.get_pressed()[pag.K_LCTRL]):
                self.redraw = True
                return True
            elif x.click(mouse_pos=evento.pos):
                self.redraw = True
                return True
        return False

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
                self.lista_descargas[5][respuesta['obj'][0]['index']] = f'[{self.cola.index(obj_cached[0])}]'         
        elif respuesta['index'] == 5:
            # 5 remover de la cola
            response = requests.get(f'http://127.0.0.1:5000/cola/delete/{obj_cached[0]}').json()
            if response['status'] == 'ok':
                self.cola.remove(obj_cached[0])
                self.lista_descargas[5][respuesta['obj'][0]['index']] = f' - '   
        elif respuesta['index'] == 6:
            # 6 limpiar cola
            response = requests.get(f'http://127.0.0.1:5000/cola/clear').json()
            if response['status'] == 'ok':
                self.cola.clear()
                for x in range(len(self.lista_descargas)):
                    self.lista_descargas[5][x] = f' - '
        elif respuesta['index'] == 7:
            # 7 reiniciar descarga
            response = requests.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached[0]}').json()
            if response['downloading'] == False and requests.get(f'http://127.0.0.1:5000/descargas/update/estado/{obj_cached[0]}/esperando').json()['status'] == 'ok':
                shutil.rmtree(CACHE_DIR.joinpath(f'./{obj_cached[0]}'), True)
                self.lista_descargas[4][respuesta['obj'][0]['index']] = self.txts['esperando'].capitalize()
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
        self.save_json()
        
    def func_select_box_hilos_newd(self, respuesta) -> None:
        self.new_threads = 2**respuesta['index']

        self.text_newd_hilos.text = self.txts['config-hilos'].format(self.new_threads)

    def func_select_box_velocidad(self, respuesta) -> None:
        diccionario_velocidades = {
            0: 0,
            1: 2**15,
            2: 2**16,
            3: 2**17,
            4: 2**19,
            5: 2**20,
            6: 2**23,
            7: 2**24,
        }
        self.velocidad_limite = diccionario_velocidades[respuesta['index']]

        self.text_limitador_velocidad.text = self.txts['limitar-velocidad']+': '+format_size_bits_to_bytes_str(self.velocidad_limite)
        self.btn_config_velocidad.pos = (self.text_limitador_velocidad.right + 60, self.text_limitador_velocidad.centery)
        self.save_json()

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
        requests.get('http://127.0.0.1:5000/descargas/add_from_program', params={'url': self.url, "tipo": self.new_file_type, 'hilos': self.new_threads, 'nombre': self.new_filename, 'size':self.new_file_size})

        self.Func_pool.start('reload list')
        self.lists_screens['new_download']["active"] = False
        self.lists_screens['main']["active"] = True

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
                peso_formateado = format_size_bits_to_bytes(row[3])
                peso = f'{peso_formateado[1]:.2f}{UNIDADES_BYTES[peso_formateado[0]]}'
                hilos = row[6]
                fecha = datetime.datetime.fromtimestamp(float(row[7]))
                # txt_fecha = f'{fecha.hour}:{fecha.minute}:{fecha.second} - {fecha.day}/{fecha.month}/{fecha.year}'
                txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
                estado = self.txts[f'{row[8]}'.lower()] if f'{row[8]}'.lower() in self.txts else row[8]
                cola = ' - 'if not row[0] in self.cola else f'[{self.cola.index(row[0])}]'
                self.lista_descargas.append([id,nombre, hilos, peso, estado, cola, txt_fecha])

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

    def get_server_updates(self):
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_client.connect(('127.0.0.1', 5001))
        try:
            while True:
                if not self.running:
                    break
                self.socket_client.send(b'a')
                respuesta = json.loads(self.socket_client.recv(1024).decode())
                if (respuesta["last_update"]) - self.last_update > 3 and time.time()-self.last_click > 4:
                    self.last_update = int(respuesta["last_update"])
                    self.reload_lista_descargas()
                time.sleep(0.1)
        except Exception as err:
            print(err)
        finally:
            self.socket_client.close()
            self.socket_client = None
           


    def func_paste_url(self, url=False):
        """Pegar la url en el input"""
        if url:
            self.input_newd_url.set(url)
        else:
            self.input_newd_url.set(pyperclip.paste().strip())

    def toggle_apagar_al_finalizar_cola(self):
        self.apagar_al_finalizar_cola = not self.apagar_al_finalizar_cola
        self.btn_config_apagar_al_finalizar_cola.text = ''if self.apagar_al_finalizar_cola else ''
        self.save_json()

    def toggle_particles(self):
        self.allow_particles = not self.allow_particles
        self.btn_config_particulas.text = ''if self.allow_particles else ''
        self.save_json()
    def toggle_ldm(self):
        self.low_detail_mode = not self.low_detail_mode
        self.btn_config_LDM.text = ''if self.low_detail_mode else ''
        self.lista_descargas.smothscroll = not self.low_detail_mode  
        self.list_config_extenciones.smothscroll = not self.low_detail_mode  
        self.save_json()
    def toggle_enfoques(self):
        self.enfoques = not self.enfoques
        self.btn_config_enfoques.text = '' if self.enfoques else ''
        self.save_json()
    def toggle_detener_5min(self):
        self.detener_5min = not self.detener_5min
        self.btn_config_detener_5min.text = '' if self.detener_5min else ''
        self.save_json()

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
        self.save_json()

    def func_newd_close(self):
        self.lists_screens['new_download']["active"] = False
        if self.thread_new_download and self.thread_new_download.is_alive():
            self.thread_new_download.join(.1)
            
        self.lists_screens['main']["active"] = True

    def func_main_to_config(self):
        self.lists_screens['main']["active"] = False
        self.lists_screens['config']["active"] = True

    def func_exit_configs(self):
        self.lists_screens['config']["active"] = False
        self.lists_screens['main']["active"] = True

        self.save_json()

    def func_extras_to_main(self):
        self.lists_screens['main']["active"] = True
        self.lists_screens['extras']["active"] = False

    def func_main_to_extras(self):
        self.lists_screens['main']["active"] = False
        self.lists_screens['extras']["active"] = True

    def func_main_to_new_download(self):
        self.lists_screens['main']["active"] = False
        self.lists_screens['new_download']["active"] = True
 

if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    if not (len(sys.argv) > 1 and str(sys.argv[1]) == '--run'):
        try:
            requests.get('http://127.0.0.1:5000/open_program')
        except requests.exceptions.ConnectionError:
            os.startfile(Path(__file__).parent / 'Download Manager.exe')
            time.sleep(3)
            requests.get('http://127.0.0.1:5000/open_program')
        finally:
            sys.exit()

    clase = DownloadManager()
    sys.exit()
