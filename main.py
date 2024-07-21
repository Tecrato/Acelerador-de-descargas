import sys
from Utilidades import win32_tools

if win32_tools.check_win('Download Manager by Edouard Sandoval'):
    win32_tools.front('Download Manager by Edouard Sandoval')
    sys.exit()

import Utilidades
import json
import os
import pygame as pag
import requests
import shutil

from urllib.parse import urlparse, unquote
from Utilidades import Text, Button, Multi_list, GUI, mini_GUI, Funcs_pool, Input, check_update, get_mediafire_url
from platformdirs import user_config_path, user_cache_path, user_downloads_dir, user_desktop_path
from pygame.constants import (MOUSEBUTTONDOWN, MOUSEMOTION, KEYDOWN, QUIT, K_ESCAPE, MOUSEBUTTONUP, MOUSEWHEEL,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)
from pygame import Vector2
from pprint import pprint

from funcs import Other_funcs
from textos import idiomas
from my_warnings import LinkCaido, LowSizeError, TrajoHTML
from DB import Data_Base


pag.init()

RESOLUCION = [800, 550]

def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


# noinspection PyAttributeOutsideInit
class DownloadManager(Other_funcs):
    def __init__(self) -> None:
        self.ventana: pag.Surface = pag.display.set_mode(RESOLUCION, pag.RESIZABLE|pag.DOUBLEBUF)
        self.ventana_rect: pag.Rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))
        pag.display.set_caption('Download Manager by Edouard Sandoval')

        self.carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_config.mkdir(parents=True, exist_ok=True)
        self.carpeta_cache = user_cache_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

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
        self.url_actualizacion: str = ''
        self.version: str = '2.11.1'
        self.save_dir = user_downloads_dir()
        self.threads: int = 4
        self.drawing: bool = True
        self.enfoques: bool = True
        self.detener_5min: bool = True
        self.low_detail_mode: bool = False
        self.mini_ventana_captar_extencion: bool = True
        self.draw_background = True
        self.redraw: bool = True
        self.framerate: int = 60
        self.relog: pag.time.Clock = pag.time.Clock()
        

        # self.font_mononoki: str = 'C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        # self.font_simbolos: str = 'C:/Users/Edouard/Documents/fuentes/Symbols.ttf'
        self.font_mononoki: str = './Assets/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        self.font_simbolos: str = './Assets/fuentes/Symbols.ttf'
        self.idioma: str = 'español'
        self.txts = idiomas[self.idioma]

        self.nomenclaturas: dict[int,str] = {
            0: 'bytes',
            1: 'Kb',
            2: 'Mb',
            3: 'Gb',
            4: 'Tb'
        }

        self.load_resources()
        self.generate_objs()
        self.reload_lista_descargas()
        self.move_objs()
        
            
        self.Func_pool = Funcs_pool()
        self.Func_pool.add('actualizacion', self.buscar_acualizaciones)
        self.Func_pool.add('descargar actualizacion', self.descargar_actualizacion)
        
        
        self.Func_pool.start('actualizacion')

        self.screen_main_bool: bool = True
        self.screen_new_download_bool: bool = True
        self.screen_configs_bool: bool = False
        self.screen_extras_bool: bool = False

        self.ciclo_general = [self.main_cycle, self.screen_configs, self.screen_extras]
        self.cicle_try = 0


        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

    def load_resources(self):
        self.DB = Data_Base(self.carpeta_config.joinpath('./downloads.sqlite3'))

        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except Exception:
            self.configs = {}
        self.threads = self.configs.get('hilos', 8)
        self.enfoques = self.configs.get('enfoques', True)
        self.detener_5min = self.configs.get('detener_5min', True)
        self.low_detail_mode = self.configs.get('ldm', False)

        self.idioma = self.configs.get('idioma', 'español')
        self.save_dir = self.configs.get('save_dir', self.save_dir)
        self.apagar_al_finalizar_cola = self.configs.get('apagar al finalizar cola', False)
        self.txts = idiomas[self.idioma]

        self.save_json()

    def save_json(self):
        self.configs['hilos'] = self.threads
        self.configs['enfoques'] = self.enfoques
        self.configs['detener_5min'] = self.detener_5min
        self.configs['ldm'] = self.low_detail_mode

        self.configs['idioma'] = self.idioma
        self.configs['save_dir'] = self.save_dir
        self.configs['apagar al finalizar cola'] = self.apagar_al_finalizar_cola

        json.dump(self.configs, open(self.carpeta_config.joinpath('./configs.json'), 'w'))

    def generate_objs(self) -> None:
        # Cosas varias
        Utilidades.GUI.configs['fuente_simbolos'] = self.font_simbolos
        self.GUI_manager = GUI.GUI_admin()
        self.Mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)

        # Pantalla principal
        self.txt_title = Text(self.txts['title'], 26, self.font_mononoki, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_extras = Button('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 10, 'topright', 'white',
                                       (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                       func=self.func_main_to_extras)
        self.btn_configs = Button('', 26, self.font_simbolos, (0, 0), 10, 'topleft', 'white', (20, 20, 20),
                                        (50, 50, 50), 0, -1, border_width=-1, func=self.func_main_to_config)

        self.btn_new_descarga = Button(self.txts['btn-nueva_descarga'], 16, self.font_mononoki, (30, 80), 20,
                                             'topleft', 'white', (50, 50, 50), (90, 90, 90), 0, 20,
                                             border_bottom_right_radius=0, border_top_right_radius=0, border_width=-1,
                                             func=lambda: self.screen_new_download(False))
        self.btn_change_dir = Button(self.txts['btn-cambiar_carpeta'], 16, self.font_mononoki,
                                           (self.btn_new_descarga.rect.right, 80), 20, 'topleft', 'white', (50, 50, 50),
                                           (90, 90, 90), 0, 20, border_bottom_left_radius=0, border_top_left_radius=0,
                                           border_width=-1, func=self.func_preguntar_carpeta)

        self.lista_descargas: Multi_list = Multi_list((self.ventana_rect.w - 60, self.ventana_rect.h - 140), (30, 120), 7, None, 11,
                                          10, (10,10,10), header_text=[self.txts['nombre'], self.txts['tipo'], self.txts['hilos'], self.txts['tamaño'], self.txts['estado'],self.txts['cola'], self.txts['fecha']],
                                          fonts=[self.font_mononoki for _ in range(7)], colums_witdh=[0, .27, .41, .49, .63, .77, .85], padding_left=5, border_color=(100,100,100),
                                          smothscroll=True if not self.low_detail_mode else False)
        self.btn_reload_list = Button('', 13, self.font_simbolos, self.lista_descargas.topright, 16, # (self.ventana_rect.w - 31, 120)
                                            'topright', 'black', 'darkgrey', 'lightgrey', 0, border_width=1,
                                            border_radius=0, border_top_right_radius=20, border_color=(100,100,100),
                                            func=self.reload_lista_descargas)

        # Cosas de la ventana de nueva descarga
        self.new_download_rect = pag.Rect(0, 0, 500, 300)
        self.new_download_rect.center = self.ventana_rect.center
        self.text_newd_title = Text(self.txts['agregar nueva descarga'], 16, self.font_mononoki,
                                           (self.new_download_rect.centerx, self.new_download_rect.top + 20))
        self.boton_newd_cancelar = Button(self.txts['cancelar'], 16, self.font_mononoki,
                                                Vector2(-20, 0) + self.new_download_rect.bottomright, (30, 20),
                                                'bottomright', border_radius=0, border_top_right_radius=20,
                                                func=self.func_newd_close)
        self.boton_newd_aceptar = Button(self.txts['aceptar'], 16, self.font_mononoki,
                                               (self.boton_newd_cancelar.rect.left, self.new_download_rect.bottom),
                                               (30, 19), 'bottomright', border_radius=0, border_top_left_radius=20,
                                               func=self.func_add_download_to_DB)

        self.input_newd_url = Input((self.new_download_rect.left + 20, self.new_download_rect.top + 100), 12,
                                         width=300, height= 20, font=self.font_mononoki, text_value='url de la descarga', max_letter=400,
                                         dire='left')
        self.input_newd_paste = Button('', 22, self.font_simbolos,
                                             (self.input_newd_url.right, self.input_newd_url.pos.y), (20, 10),
                                             'left', 'black', 'lightgrey', 'darkgrey', border_width=1, border_radius=0,
                                             border_top_right_radius=20, border_bottom_right_radius=20,
                                             func=self.func_paste_url)

        self.btn_comprobar_url = Button(self.txts['comprobar'], 16, self.font_mononoki,
                                              (self.new_download_rect.right - 20, self.input_newd_url.pos.y), (20, 10),
                                              'right', 'black', 'lightgrey', 'darkgrey', border_width=1,
                                              border_radius=20,
                                              func=self.func_comprobar_url)

        self.text_newd_title_details = Text(self.txts['detalles'], 20, self.font_mononoki, (400, 260))
        self.text_newd_filename = Text(self.txts['nombre']+': ----------', 16, self.font_mononoki,
                                              (self.new_download_rect.left + 20, 290), 'left')
        self.text_newd_file_type = Text(self.txts['tipo']+': ----------', 16, self.font_mononoki,
                                              (self.new_download_rect.left + 20, 310), 'left')
        self.text_newd_size = Text(self.txts['tamaño']+': -------', 16, self.font_mononoki,
                                          (self.new_download_rect.left + 20, 330), 'left')
        self.text_newd_status = Text(self.txts['descripcion-state[esperando]'], 16, self.font_mononoki,
                                            (self.new_download_rect.left + 20, 350), 'left')

        self.text_newd_hilos = Text(self.txts['config-hilos'].format(self.threads), 16, self.font_mononoki,
                                             (self.text_newd_file_type.right+170, 260), 'left', with_rect=True,
                                    color_rect=(40,40,40), padding=10,
                                    border_width=3, border_color='black')
        self.btn_newd_hilos = Button(self.txts['cambiar'],16, self.font_mononoki,
                                             (self.text_newd_hilos.left, self.text_newd_hilos.bottom+10),
                                             (20,10),color='white', color_rect=(20,20,20), color_rect_active=(40, 40, 40),
                                             border_radius=5, border_width=3, dire='topleft',
                                             func=lambda: self.Mini_GUI_manager.add(mini_GUI.select(self.btn_newd_hilos.topright,
                                                                [1,2,4,8,16,32],min_width=50),
                                                                self.func_select_box_hilos_newd)
        )


        # Pantalla de configuraciones
        self.text_config_title = Text(self.txts['title-configuraciones'], 26, self.font_mononoki,
                                             (self.ventana_rect.centerx, 30), with_rect=True, color_rect=(20,20,20))
        self.btn_config_exit = Button('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 10, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_exit_configs)

        self.text_config_hilos = Text(self.txts['config-hilos'].format(self.threads), 16, self.font_mononoki,
                                             (30, 100), 'left', with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_change_hilos = Button(self.txts['cambiar'],16, self.font_mononoki,
                                             (self.text_config_hilos.right + 60, self.text_config_hilos.centery),
                                             (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
                                             border_radius=0, border_width=3,
                                             func=lambda: self.Mini_GUI_manager.add(mini_GUI.select(self.btn_change_hilos.topright,
                                                                [1,2,4,8,16,32],min_width=50),
                                                                self.func_select_box_hilos)
        )

        self.text_config_idioma = Text(self.txts['config-idioma'], 16, self.font_mononoki, (30, 130), 'left', padding=10,with_rect=True, color_rect=(20,20,20))
        self.btn_config_idioma_es = Button('Español', 14, self.font_mononoki, (30, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('español'))
        self.btn_config_idioma_en = Button('English', 14, self.font_mononoki, (120, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('ingles'))
        
        self.text_config_apagar_al_finalizar_cola = Text(self.txts['apagar-al-finalizar']+' ('+self.txts['la']+' '+self.txts['cola']+')', 
                                                         16, self.font_mononoki, (30, 190), 'left', 'white', with_rect=True, 
                                                         color_rect=(20,20,20), padding=10)
        self.btn_config_apagar_al_finalizar_cola = Button('' if self.apagar_al_finalizar_cola else '', 16, self.font_simbolos, (self.text_config_apagar_al_finalizar_cola.right, 190), 10, 'left', 'white',with_rect=True,
                                                                color_rect=(20,20,20),color_rect_active=(40, 40, 40),border_width=-1,
                                                                 func=self.toggle_apagar_al_finalizar_cola)
        
        self.text_config_LDM = Text(self.txts['bajo consumo']+': ', 16, self.font_mononoki, (30, 225), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_LDM = Button('' if self.low_detail_mode else '', 16, self.font_simbolos, (self.text_config_LDM.right, 225),
                                     10, 'left', 'white',with_rect=True, color_rect=(20,20,20),color_rect_active=(40, 40, 40),
                                     border_width=-1, func=self.toggle_LDM)
        
        self.text_config_enfoques = Text(f'focus {self.txts["aplicacion"]}: ', 16, self.font_mononoki, (30, 260), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_enfoques = Button('' if self.enfoques else '', 16, self.font_simbolos, 
                                                (self.text_config_enfoques.right, 260), 10,'left',
                                                'white',with_rect=True, color_rect=(20,20,20),color_rect_active=(40, 40, 40),
                                                border_width=-1, func=self.toggle_enfoques)
        
        
        self.text_config_detener_5min = Text('Detener a los 5min sin cambio: ', 16, self.font_mononoki, (30, 295), 'left', 'white', 
                                                                 with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_detener_5min = Button('' if self.detener_5min else '', 16, self.font_simbolos, 
                                                (self.text_config_detener_5min.right, 295), 10,'left',
                                                'white',with_rect=True, color_rect=(20,20,20),color_rect_active=(40, 40, 40),
                                                border_width=-1, func=self.toggle_detener_5min)

        # Pantalla de extras
        self.text_extras_title = Text('Extras', 26, self.font_mononoki, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_extras_exit = Button('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 10, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_extras_to_main)

        self.text_extras_version = Text('Version '+self.version, 26, self.font_mononoki, self.ventana_rect.bottomright,
                                               'bottomright',with_rect=True,color_rect=(20,20,20))

        self.text_extras_mi_nombre = Text('Edouard Sandoval', 30, self.font_mononoki, (400, 100),
                                                 'center', padding=0,with_rect=True,color_rect=(20,20,20))
        self.btn_extras_link_github = Button('', 30, self.font_simbolos, (370, 200), 20, 'center',
                                                   func=lambda: os.startfile('http://github.com/Tecrato'))
        self.btn_extras_link_youtube = Button('輸', 30, self.font_simbolos, (430, 200), 20, 'center',
                                                    func=lambda: os.startfile('http://youtube.com/channel/UCeMfUcvDXDw2TPh-b7UO1Rw'))
        self.btn_extras_install_extension = Button('Instalar Extencion', 20, self.font_mononoki, (self.ventana_rect.centerx, 300),
                                                         20, 'center', 'black','purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                        func=lambda: \
                                                            self.GUI_manager.add(
                                                                GUI.Desicion(self.ventana_rect.center,"Instalar extension","Desea instalar la extencion?\n\n\
El Archivo de la extencion se copiara \n\
en el escritorio Y debera ejecutarlo\n\
con su navegador de preferencia"),
                                                                             lambda e: shutil.copy("./extencion.crx",user_desktop_path().joinpath('./Extencion.crx')) if e == 'aceptar' else None
                                                                )
        )

        # Pantalla principal
        self.list_to_draw = [self.txt_title, self.btn_extras, self.btn_configs, self.btn_new_descarga,
                             self.btn_change_dir, self.lista_descargas, self.btn_reload_list]
        self.list_to_click = [self.btn_new_descarga, self.btn_configs, self.btn_reload_list, self.btn_extras,
                              self.btn_change_dir,self.lista_descargas]

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
                                    self.btn_config_enfoques,self.text_config_detener_5min,self.btn_config_detener_5min]
        self.list_to_click_config = [self.btn_config_exit, self.btn_change_hilos, 
                                     self.btn_config_idioma_en, self.btn_config_idioma_es,
                                     self.btn_config_apagar_al_finalizar_cola,self.btn_config_LDM,
                                     self.btn_config_enfoques,self.btn_config_detener_5min]

        # Pantalla de Extras
        self.list_to_draw_extras = [self.text_extras_title, self.btn_extras_exit, self.text_extras_mi_nombre,
                                    self.btn_extras_link_github, self.btn_extras_link_youtube, self.text_extras_version,
                                    self.btn_extras_install_extension]
        self.list_to_click_extras = [self.btn_extras_exit, self.btn_extras_link_github, self.btn_extras_link_youtube,
                                     self.btn_extras_install_extension]
        self.move_objs()

    def move_objs(self):
        self.Mini_GUI_manager.limit = self.ventana_rect

        self.txt_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_extras.pos = (self.ventana_rect.w, 0)

        self.text_config_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_config_exit.pos = (self.ventana_rect.w, 0)

        self.text_extras_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_extras_exit.pos = (self.ventana_rect.w, 0)
        self.text_extras_mi_nombre.pos = (self.ventana_rect.centerx, 100)
        self.btn_extras_link_github.pos = (self.text_extras_mi_nombre.left,self.text_extras_mi_nombre.centery+100)
        self.btn_extras_link_youtube.pos = (self.text_extras_mi_nombre.right,self.text_extras_mi_nombre.centery+100)
        self.text_extras_version.pos = self.ventana_rect.bottomright
        self.btn_extras_install_extension.pos = (self.ventana_rect.centerx, 300)
        
        self.lista_descargas.resize((self.ventana_rect.w - 60, self.ventana_rect.h - 140))
        self.btn_reload_list.pos = self.lista_descargas.topright
        self.redraw = True


    def buscar_acualizaciones(self):
       
        sera = check_update('acelerador de descargas', self.version, 'last')
        if not sera:
            return
        self.Mini_GUI_manager.clear_group('actualizaciones')
        self.Mini_GUI_manager.add(mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['actualizacion'], 'Se a encontrado una nueva actualizacion\n\nObteniendo link...', (260,100)),group='actualizaciones')
        
        try:
            self.data_actualizacion['url'] = get_mediafire_url(sera['url'])
            response2 = requests.get(self.data_actualizacion['url'], stream=True, allow_redirects=True, timeout=30)

            self.data_actualizacion['file_type'] = response2.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if self.data_actualizacion['file_type'] in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')
            self.data_actualizacion['size'] = int(response2.headers.get('content-length'))
            self.data_actualizacion['file_name'] = response2.headers.get('content-disposition').split('filename=')[1].replace('"', '')

            self.Mini_GUI_manager.clear_group('actualizaciones')
            self.Mini_GUI_manager.add(
                mini_GUI.desicion_popup(Vector2(50000,50000), self.txts['actualizacion'], self.txts['gui-desea descargar la actualizacion'], (250,100), self.txts['agregar'], 'bottomright'),
                lambda _: self.Func_pool.start('descargar actualizacion'),
                group='actualizaciones'
            )
        except Exception as err:
            self.Mini_GUI_manager.clear_group('actualizaciones')
            self.Mini_GUI_manager.add(mini_GUI.simple_popup(Vector2(50000,50000), 'bottomright', self.txts['actualizacion'], 'Error al obtener actualizacion.', (250,100)),group='actualizaciones')
            print(type(err))
            print(err)

    def descargar_actualizacion(self):

        db = Data_Base(self.carpeta_config.joinpath('./downloads.sqlite3'))
        db.añadir_descarga(self.data_actualizacion['file_name'], self.data_actualizacion['file_type'], self.data_actualizacion['size'], self.data_actualizacion['url'], self.threads)

        self.reload_lista_descargas(db.cursor)
        ide = db.get_last_insert()[0]
        del db

        self.descargando.append(ide)
        self.init_download(ide,1)


    def comprobar_url(self) -> None:
        if not self.url:
            return
        
        self.can_add_new_download = False
        title: str = urlparse(self.url).path
        title: str = title.split('/')[-1]
        title: str = title.split('?')[0]
        title: str = title.replace('+', ' ')
        title: str = unquote(title)

        self.new_filename = title
        if len(title) > 33:
            title = title[:33] + '...'

        self.text_newd_filename.text = f'{title}'

        self.text_newd_status.text = self.txts['descripcion-state[conectando]']
        try:
            
            parse = urlparse(self.url)
            if (parse.netloc == "www.mediafire.com" or parse.netloc == ".mediafire.com") and 'file' in parse.path:
                try:
                    for x in parse.path[1:].split('/'):
                        if '.' in x:
                            self.new_filename = x
                            self.text_newd_filename.text = self.new_filename
                            break
                    url = get_mediafire_url(self.url)
                except:
                    raise LinkCaido('nt')
                response = requests.get(url, stream=True, allow_redirects=True, timeout=15)
            else:
                response = requests.get(self.url, stream=True, allow_redirects=True, timeout=15)


            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            pprint(response.headers) #Accept-Ranges
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
                print(response.headers)
                raise TrajoHTML('No paginas')

            # print(response.headers)
            self.new_file_size = int(response.headers.get('content-length', 1))
            if self.new_file_size < 8 *self.threads:
                raise LowSizeError('Peso muy pequeño')
            peso_formateado = format_size(self.new_file_size)
            self.text_newd_size.text = f'{peso_formateado[1]:.2f}{self.nomenclaturas[peso_formateado[0]]}'

            if a := response.headers.get('content-disposition', False):
                self.new_filename = a.split(';')
                for x in self.new_filename:
                    if 'filename=' in x:
                        self.new_filename = x[10:].replace('"', '')
                        break
                self.text_newd_filename.text = self.new_filename

            self.text_newd_status.text = self.txts['estado']+': '+self.txts['disponible']

            self.can_add_new_download = True
            self.redraw = True

            return
        except requests.URLRequired:
            return
        except (requests.exceptions.InvalidSchema,requests.exceptions.MissingSchema):
            self.text_newd_status.text = self.txts['descripcion-state[url invalida]']
            return
        except (requests.exceptions.ConnectTimeout,requests.exceptions.ReadTimeout):
            self.text_newd_status.text = self.txts['descripcion-state[tiempo agotado]']
            return
        except requests.exceptions.ConnectionError:
            self.text_newd_status.text = self.txts['descripcion-state[error internet]']
            return
        except TrajoHTML:
            self.text_newd_status.text = self.txts['descripcion-state[trajo un html]']
            # print(response.content)
            return
        except LinkCaido as err:
            self.text_newd_status.text = 'Link Caido'
            return
        except Exception as err:
            print(err)
            print(type(err))
            self.text_newd_status.text = 'Error'
            return

    def eventos_en_comun(self, evento: pag.event.Event):
        mx, my = pag.mouse.get_pos()
        if evento.type == QUIT:
            pag.quit()
            sys.exit()
        if evento.type == pag.WINDOWRESTORED:
            return True
        elif self.GUI_manager.active >= 0:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.GUI_manager.pop()
            elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                self.GUI_manager.click((mx, my))
            return True
        elif evento.type == MOUSEBUTTONDOWN and evento.button in [1,3] and self.Mini_GUI_manager.click(evento.pos) > 0:
            return True
        elif evento.type == WINDOWMINIMIZED:
            return True
        elif evento.type == WINDOWFOCUSLOST:
            self.framerate = 30 if not self.low_detail_mode else 5
            return True
        elif evento.type in [WINDOWTAKEFOCUS, WINDOWFOCUSGAINED, WINDOWMAXIMIZED]:
            self.framerate = 60 if not self.low_detail_mode else 30
            return True
        elif evento.type in [pag.WINDOWRESIZED,pag.WINDOWMAXIMIZED,pag.WINDOWSIZECHANGED,pag.WINDOWMINIMIZED]:
            size = pag.display.get_window_size()
            self.ventana = pag.display.set_mode(size, pag.RESIZABLE|pag.DOUBLEBUF)
            self.ventana_rect = self.ventana.get_rect()

            self.display = pag.Surface(self.ventana_rect.size)
            self.display_rect = self.display.get_rect()

            self.move_objs()
            return True
        elif evento.type == pag.WINDOWSHOWN or evento.type == pag.WINDOWMOVED:
            size = pag.display.get_window_size()
            self.ventana = pag.display.set_mode(size, pag.RESIZABLE|pag.DOUBLEBUF)
            self.ventana_rect = self.ventana.get_rect()

            self.display = pag.Surface(self.ventana_rect.size)
            self.display_rect = self.display.get_rect()

            self.move_objs()
            return True
        return False

    def draw_objs(self, lista):
        mx, my = pag.mouse.get_pos()
        if self.redraw:
            if self.draw_background:
                self.ventana.fill((20, 20, 20))
            for x in lista:
                if isinstance(x, Button):
                    x.draw(self.ventana, (mx,my))
                elif isinstance(x, Multi_list):
                    if self.lista_descargas.listas[0].lista_palabras:
                        x.draw(self.ventana)
                else:
                    x.draw(self.ventana)
            self.GUI_manager.draw(self.ventana, (mx, my))
            self.Mini_GUI_manager.draw(self.ventana, (mx, my))
            pag.display.update()
            self.redraw = False
        else:
            self.updates.clear()
            for x in lista:
                if isinstance(x, Button):
                    self.updates.append(x.draw(self.ventana, (mx,my)))
                else:
                    self.updates.append(x.draw(self.ventana))

            self.updates.append(self.GUI_manager.draw(self.ventana, (mx, my)))
            for x in self.Mini_GUI_manager.draw(self.ventana, (mx, my)):
                self.updates.append(x)

            self.updates = list(filter(lambda ele: isinstance(ele, pag.Rect),self.updates))

            pag.display.update(self.updates)

    def screen_configs(self):
        if self.screen_configs_bool:
            self.cicle_try = 0
            self.redraw = True
        while self.screen_configs_bool:
            self.relog.tick(self.framerate)

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
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_config:
                        if x.click((mx, my)):
                            break
            if self.drawing:
                self.draw_objs(self.list_to_draw_config)

    def screen_new_download(self, actualizar_url=0):
        if actualizar_url:
            self.actualizar_url = True
        else:
            self.actualizar_url = False

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

        self.screen_new_download_bool = True
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
            
            if self.drawing:
                self.ventana.fill((20, 20, 20))
                pag.draw.rect(self.ventana, (50, 50, 50), self.new_download_rect, 0, 20)
                self.draw_objs(self.list_to_draw_new_download)

        self.draw_background = True
    def main_cycle(self) -> None:
        if self.screen_main_bool:
            self.cicle_try = 0
            self.redraw = True

        while self.screen_main_bool:
            self.relog.tick(self.framerate)

            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)

            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                    continue
                elif evento.type == KEYDOWN and evento.key == K_ESCAPE:
                    pag.quit()
                    sys.exit()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click:
                        if x.click((mx, my)):
                            break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 3:
                    if result := self.lista_descargas.click((mx, my)):
                        self.Mini_GUI_manager.add(mini_GUI.select((mx, my),
                                                                  [self.txts['descargar'] if result['result'][-2] != 'Completado' else self.txts['redescargar'], self.txts['eliminar'],
                                                                   self.txts['actualizar_url'], 'get url', self.txts['añadir a la cola'], self.txts['remover de la cola'], self.txts['limpiar cola'],
                                                                   self.txts['reiniciar'], self.txts['cambiar nombre']],
                                                                  captured=result),
                                                  self.func_select_box)
                elif evento.type == MOUSEBUTTONUP:
                    self.lista_descargas.detener_scroll()
                elif evento.type == MOUSEWHEEL and self.lista_descargas.rect.collidepoint((mx,my)):
                    self.lista_descargas.rodar(evento.y*10)
                elif evento.type == MOUSEMOTION and self.lista_descargas.scroll:
                    self.lista_descargas.rodar_mouse(evento.rel[1])

            if self.drawing:
                self.draw_objs(self.list_to_draw)
            # pag.draw.rect(self.ventana,'green',self.lista_descargas.rect,3)
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

            if self.drawing:
                self.draw_objs(self.list_to_draw_extras)


if __name__ == '__main__':
    # clase = DownloadManager(sys.argv[1] if len(sys.argv) > 1 else False)
    clase = DownloadManager()
