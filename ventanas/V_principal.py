import os
import json
import time
import urllib
import shutil
import socket
import datetime
import pyperclip
import urllib.error
import urllib.parse
import pygame as pag
import Utilidades as uti
import Utilidades_pygame as uti_pag
import Utilidades.win32_tools as win32_tools

from pathlib import Path
from typing import override
from threading import Thread
from http.client import InvalidURL
from urllib.parse import urlparse, unquote
from tkinter.filedialog import askdirectory
from tkinter.simpledialog import askstring

from Utilidades_pygame.base_app_class import Base_class
from constants import DICT_CONFIG_DEFAULT, Config, INITIAL_DIR
from textos import idiomas
from loader import Loader
from my_warnings import TrajoHTML, LinkCaido
from enums.Download import Download
from GUI import AdC_theme

class Downloads_manager(Base_class):
    def otras_variables(self):
        self.config:Config

        self.new_threads = 1
        self.new_file_size = 0
        self.thread_elevation_limit = 7

        self.url: str = ''
        self.new_filename = ''
        self.new_file_type = ''
        self.low_detail_mode: bool = False
        self.can_add_new_download = False
        self.can_change_new_threads = False
        self.agregar_a_cola_automaticamente = False
        self.last_update = time.time()
        self.thread_new_download: Thread = Thread()
        self.session = uti.Http_Session()
        
        self.logger = uti.Logger('Acelerador de descargas(UI)', self.config.config_dir/'Logs')
        # self.logger.write(f"Acelerador de descargas iniciado en {datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')}")

        self.Func_pool.add('reload list',self.func_reload_lista_descargas)
        self.Func_pool.add('get sockets clients',self.get_server_updates)
        
    def load_resources(self):
        try:
            self.configs = uti.get('http://127.0.0.1:5000/get_configurations').json
        except Exception as err:
            uti.debug_print(f"No se pudo cargar las configuraciones", priority=2)
            self.configs = DICT_CONFIG_DEFAULT
        self.threads = self.configs.get('hilos',DICT_CONFIG_DEFAULT['hilos'])
        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode = bool(self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm']))
        self.velocidad_limite = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])

        self.save_dir = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.apagar_al_finalizar_cola = self.configs.get('apagar al finalizar cola',DICT_CONFIG_DEFAULT['apagar al finalizar cola'])
        self.extenciones = self.configs.get('extenciones',DICT_CONFIG_DEFAULT['extenciones'])

        self.allow_particles = self.configs.get('particulas',DICT_CONFIG_DEFAULT['particulas'])
        self.agregar_a_cola_automaticamente = self.configs.get('agregar a cola automaticamente',DICT_CONFIG_DEFAULT['agregar a cola automaticamente'])

        try:
            self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
            self.txts = idiomas[self.idioma]
        except:
            self.idioma = 'español'
            self.txts = idiomas[self.idioma]
            uti.send_post('http://127.0.0.1:5000/set_configuration', data={"key":'idioma', "value":self.idioma})
        self.txts = idiomas[self.idioma]

    def save_conf(self, key, value, parser='json'):
        uti.send_post('http://127.0.0.1:5000/set_configuration', data={"key":key, "value":value}, parser=parser)

    def post_init(self):
        if self.enfoques:
            win32_tools.front2(self.hwnd)
        self.Func_pool.start('reload list')
        self.Func_pool.start('get sockets clients')

    def on_exit(self):
        del self.logger

    def generate_objs(self):
        self.particulas_mouse = uti_pag.Particles(
            (0,0), radio=10, radio_dispersion=5, color=(255,255,255), velocity=1, 
            vel_dispersion=2, angle=-90, angle_dispersion=60, radio_down=.2, 
            gravity=0.15, max_particles=100, time_between_spawns=1, max_distance=1000, 
            spawn_count=5, auto_spawn=False
        )

        # Loader
        self.loader = Loader((self.ventana_rect.w, self.ventana_rect.h))

        # Pantalla principal
        self.text_main_title = uti_pag.Text(self.txts['title'], 26, self.config.font_mononoki, (self.ventana_rect.centerx, 30),with_rect=True,color_rect=(20,20,20))
        self.btn_main_extras = uti_pag.Button(
            '', 26, self.config.font_symbols, (self.ventana_rect.w, 0), 10, 'topright', 'white',
            (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,func=lambda :self.goto('extras')
        )
        self.btn_main_configs = uti_pag.Button(
            '', 26, self.config.font_symbols, (0, 0), 10, 'topleft', 'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1, func=lambda :self.goto('config')
        )
        
        self.list_main_descargas = uti_pag.Multi_list(
            size=(self.ventana_rect.w - 60, self.ventana_rect.h - 140),
            pos=(30, 120),
            num_lists=7,
            lista=None,
            text_size=12,
            separation=10,
            header_text=[self.txts['id'],self.txts['nombre'], self.txts['hilos'], self.txts['tamaño'], self.txts['estado'],self.txts['cola'], self.txts['fecha']],
            fonts=[self.config.font_mononoki for _ in range(7)],
            colums_witdh=[0, .065, .47, .55, .67, .79, .86],
            padding_left= 10,
            border_color=(100,100,100),
            smothscroll=True if not self.low_detail_mode else False
            )
        self.btn_main_reload_list = uti_pag.Button('', 13, self.config.font_symbols, self.list_main_descargas.topright, 16,'topright', 'black', 'darkgrey', 'lightgrey', 0, border_width=1,border_radius=0, border_top_right_radius=20, border_color=(100,100,100), func=lambda :self.Func_pool.start('reload list'))

        self.btn_main_new_descarga = uti_pag.Button(self.txts['btn-nueva_descarga'], 15, self.config.font_mononoki, (30, 80), height=40, dire='topleft', color='white', color_rect=(50,50,50), color_rect_active=(90,90,90), border_radius=20, border_bottom_right_radius=0, border_top_right_radius=0, border_width=-1,func=lambda: self.goto('new_download'))
        self.btn_main_change_save_dir = uti_pag.Button(self.txts['btn-cambiar_carpeta'], 15, self.config.font_mononoki, (self.btn_main_new_descarga.right, 80), height=40, dire='topleft', color='white', color_rect=(50,50,50), color_rect_active=(90,90,90), border_radius=20, border_bottom_left_radius=0, border_top_left_radius=0, border_width=-1,func=self.func_preguntar_carpeta)

        # Pantalla Configuraciones
        self.registrar_pantalla('config')

        self.text_config_title: uti_pag.Text = uti_pag.Text(self.txts['title-configuraciones'], 26, self.config.font_mononoki, (self.ventana_rect.centerx, 30), with_rect=True, color_rect=(20,20,20))
        self.btn_config_exit: uti_pag.Button = uti_pag.Button('', 26, self.config.font_symbols, (self.ventana_rect.w, 0), 10, 'topright','white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,func=lambda :self.goto('main'))

        self.text_config_hilos = uti_pag.Text(self.txts['config-hilos'].format(self.threads), 16, self.config.font_mononoki,(30, 100), 'left', with_rect=True, color_rect=(20,20,20), padding=10)
        self.btn_config_change_hilos = uti_pag.Button(
            self.txts['cambiar'],16, self.config.font_mononoki,
            (self.text_config_hilos.right + 60, self.text_config_hilos.centery),
            (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
            border_radius=0, border_width=3
        )
        self.select_config_change_hilos = uti_pag.Select_box(
            self.btn_config_change_hilos, 
            [2**x for x in range(self.thread_elevation_limit)], 
            auto_open=False, 
            position='right', 
            animation_dir='vertical', 
            text_size=20, 
            padding_horizontal=20,
            func=self.func_select_box_hilos
        )


        self.text_config_idioma = uti_pag.Text(self.txts['config-idioma'], 16, self.config.font_mononoki, (30, 130), 'left', padding=10,with_rect=True, color_rect=(20,20,20))
        self.btn_config_idioma_es = uti_pag.Button(
            'Español', 14, self.config.font_mononoki, (30, 160), (20, 10), 'left','black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
            func=lambda: self.func_change_idioma('español')
        )
        self.btn_config_idioma_en = uti_pag.Button(
            'English', 14, self.config.font_mononoki, (120, 160), (20, 10), 'left', 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
            func=lambda: self.func_change_idioma('ingles')
        )
        
        self.text_config_apagar_al_finalizar_cola = uti_pag.Text(
            self.txts['apagar-al-finalizar']+' ('+self.txts['la']+' '+self.txts['cola']+')', 16, 
            self.config.font_mononoki, (30, 190), 'left', 'white', with_rect=True, color_rect=(20,20,20), padding=10
        )
        self.btn_config_apagar_al_finalizar_cola = uti_pag.Button(
            '' if self.apagar_al_finalizar_cola else '', 16, self.config.font_symbols, 
            (self.text_config_apagar_al_finalizar_cola.right, 190), 10, 'left', 'white',
            color_rect=(20,20,20),color_rect_active=(40, 40, 40),border_width=-1,func=self.func_toggle_apagar_al_finalizar_cola
        )
        
        self.text_config_LDM = uti_pag.Text(
            self.txts['bajo consumo']+': ', 16, self.config.font_mononoki, (30, 225), 'left', 'white', with_rect=True, 
            color_rect=(20,20,20), padding=10
        )
        self.btn_config_LDM = uti_pag.Button(
            '' if self.low_detail_mode else '', 16, self.config.font_symbols, (self.text_config_LDM.right, 225),
            10, 'left', 'white', with_rect=True, color_rect=(20,20,20), color_rect_active=(40, 40, 40),
            border_width=-1, func=self.func_toggle_ldm)
        

        self.text_config_enfoques = uti_pag.Text(f'focus {self.txts["aplicacion"]}: ', 16, self.config.font_mononoki, (30, 260), 'left')
        self.btn_config_enfoques = uti_pag.Button(
            '' if self.enfoques else '', 16, self.config.font_symbols, 
            pos=(self.text_config_enfoques.right, 260), dire='left',color='white',with_rect=True, 
            color_rect=(20,20,20),color_rect_active=(40, 40, 40),border_width=-1, padding=10,
            func=self.func_toggle_enfoques
        )

        self.text_config_detener_5min = uti_pag.Text('Detener a los 5min sin cambio: ', 16, self.config.font_mononoki, (30, 295), 'left')
        self.btn_config_detener_5min = uti_pag.Button(
            '' if self.detener_5min else '', 16, self.config.font_symbols,(self.text_config_detener_5min.right, 295), 10,'left',
            'white', color_rect=(20,20,20),color_rect_active=(40, 40, 40),border_width=-1, func=self.func_toggle_detener_5min
        )

        
        self.text_config_limitador_velocidad = uti_pag.Text(self.txts['limitar-velocidad']+': '+uti.format_size_bits_to_bytes_str(self.velocidad_limite), 16, self.config.font_mononoki, (30, 335), 'left', 'white',padding=10)
        self.btn_config_velocidad = uti_pag.Button(
            self.txts['cambiar'],16, self.config.font_mononoki,
            (self.text_config_limitador_velocidad.right + 60, self.text_config_limitador_velocidad.centery),
            (20,10),color='white', color_rect=(40,40,40), color_rect_active=(60, 60, 60),
            border_radius=0, border_width=3
        )
        self.select_config_velocidad = uti_pag.Select_box(self.btn_config_velocidad, ['off']+[uti.format_size_bits_to_bytes_str(2**x) for x in [15,16,17,19,20,23,24]]+['Otro'], auto_open=False, position='right', animation_dir='vertical', padding_horizontal=10, func=self.func_select_box_velocidad)

        self.text_config_particulas = uti_pag.Text(self.txts['particulas']+': ', 16, self.config.font_mononoki, (30, 375), 'left')
        self.btn_config_particulas = uti_pag.Button(
            '' if self.allow_particles else '', 16, self.config.font_symbols, (self.text_config_particulas.right, 375),
            10, 'left', 'white', with_rect=True, color_rect=(20,20,20), color_rect_active=(40, 40, 40),
            border_width=-1, func=self.func_toggle_particles
        )

        self.text_config_agregar_a_cola_automaticamente = uti_pag.Text(self.txts['config-agregar a cola automaticamente'], 16, self.config.font_mononoki, (30, 415), 'left')
        self.btn_config_agregar_a_cola_automaticamente = uti_pag.Button(
            '' if self.agregar_a_cola_automaticamente else '', 16, self.config.font_symbols, (self.text_config_agregar_a_cola_automaticamente.right, 415),
            10, 'left', 'white', with_rect=True, color_rect=(20,20,20), color_rect_active=(40, 40, 40),
            border_width=-1, func=self.func_toggle_agregar_a_cola_automaticamente
        )

        #lista de extenciones
        self.list_config_extenciones = uti_pag.List(
            (self.ventana_rect.w*.3,self.ventana_rect.h*.7), (self.ventana_rect.w*.80,self.ventana_rect.centery),
            self.extenciones.copy(), 16, 10, (40,40,40),dire='center', header=True, text_header=self.txts['extenciones'], background_color=(20,20,20), 
            font=self.config.font_mononoki, 
            border_width = 3,smothscroll=True if not self.low_detail_mode else False
        )
        self.btn_config_añair_extencion: uti_pag.Button = uti_pag.Button(
            self.txts['añadir'], 16, self.config.font_mononoki, (self.list_config_extenciones.right, self.list_config_extenciones.top), 
            (0,15), 'topleft', 'white', (20, 20, 20), (50, 50, 50), border_radius=0, border_bottom_left_radius=20, 
            func=self.func_añadir_extencion
        )
        self.btn_config_eliminar_extencion: uti_pag.Button = uti_pag.Button(
            self.txts['eliminar'], 16, self.config.font_mononoki, 
            (self.list_config_extenciones.right, self.list_config_extenciones.bottom), (0,15), 'topright', 'white', (20, 20, 20), 
            (50, 50, 50), border_radius=0, border_bottom_right_radius=20, 
            func=lambda: self.open_desicion(
                self.txts['confirmar'], self.txts['gui-desea borrar los elementos'],
                self.func_eliminar_extencion,
                options=['Eliminar', 'Cancelar']
            )
        )


        # Pantalla de nueva descarga
        self.registrar_pantalla('new_download')

        self.rect_new_download_fondo = pag.Rect(0,0,500,300)
        self.text_new_download_title = uti_pag.Text(self.txts['agregar nueva descarga'], 18, self.config.font_mononoki, (0,0))

        self.btn_new_download_cancelar = uti_pag.Button(self.txts['cancelar'], 14, self.config.font_mononoki, dire='bottomleft', border_radius=0, border_top_right_radius=20, func=self.func_salir_nueva_descarga)
        self.btn_new_download_aceptar = uti_pag.Button(self.txts['aceptar'], 14, self.config.font_mononoki, dire='bottomright', padding=(20,19), border_radius=0, border_top_left_radius=20, func=self.func_add_download)

        self.input_new_download_url =uti_pag.Input(self.ventana_rect.center, 14, self.config.font_mononoki, 'URL', 1_000, width=300, height=35, hover_border_color='purple', dire='center')
        self.btn_new_download_paste = uti_pag.Button(
            '', 20, self.config.font_symbols, (0,0), padding=0, dire='topleft',height=34, border_width=2,
            color_rect='purple', color_rect_active='cyan', border_radius=-1, border_top_left_radius=20, border_bottom_left_radius=20,
            func=lambda: self.input_new_download_url.set(pyperclip.paste().strip())
        )

        self.btn_new_download_comprobar_url = uti_pag.Button(
            self.txts['comprobar'], 14, self.config.font_mononoki, (0,0), padding=(20,10), dire='left',
            func=self.func_comprobar_url
        )

        # Los detalles de la nueva descarga
        self.text_new_download_title_details = uti_pag.Text(self.txts['detalles'], 20, self.config.font_mononoki)
        self.text_new_download_filename = uti_pag.Text(self.txts['nombre']+': ----------', 16, self.config.font_mononoki, dire='left')
        self.text_new_download_file_type = uti_pag.Text(self.txts['tipo']+': ----------', 16, self.config.font_mononoki, dire='left')
        self.text_new_download_size = uti_pag.Text(self.txts['tamaño']+': ----------', 16, self.config.font_mononoki, dire='left')
        self.text_new_download_status = uti_pag.Text(self.txts['descripcion-state[esperando]'], 16, self.config.font_mononoki, dire='left')
        
        self.text_new_download_hilos = uti_pag.Text(self.txts['config-hilos'].format(self.threads), 16, self.config.font_mononoki,padding=10,with_rect=True,color_rect=(40,40,40),border_width=3, border_color='black')
        self.btn_new_download_hilos = uti_pag.Button(self.txts['cambiar'],16, self.config.font_mononoki, (0,0), (20,10), 'center', color='white', color_rect=(20,20,20), color_rect_active=(40,40,40), border_radius=5, border_width=3)
        self.select_new_download_hilos = uti_pag.Select_box(
            self.btn_new_download_hilos, 
            [2**x for x in range(self.thread_elevation_limit)], 
            auto_open=True, 
            padding_horizontal=20,
            func=self.func_select_box_hilos_newd
        )

        # Pantalla de extras
        self.registrar_pantalla('extras')

        self.text_extras_title = uti_pag.Text('Extras', 26, self.config.font_mononoki, (self.ventana_rect.centerx, 30), with_rect=True, color_rect=(20,20,20))
        self.btn_extras_exit = uti_pag.Button('', 26, self.config.font_symbols, (self.ventana_rect.w, 0), 10, 'topright', 'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1, func=lambda :self.goto('main'))

        self.text_extras_nombre = uti_pag.Text('Edouard Sandoval', 30, self.config.font_mononoki, (self.ventana_rect.centerx, 100), 'center', padding=0,with_rect=True,color_rect=(20,20,20))
        self.btn_extras_link_github = uti_pag.Button('', 30, self.config.font_symbols, (self.ventana_rect.w*.25, 200), 20, 'center',func=lambda: os.startfile('http://github.com/Tecrato'))
        self.btn_extras_link_youtube = uti_pag.Button('輸', 30, self.config.font_symbols, (self.ventana_rect.w*.75, 200), 20, 'center', func=lambda: os.startfile('http://youtube.com/channel/UCeMfUcvDXDw2TPh-b7UO1Rw'))
        self.btn_extras_install_extension = uti_pag.Button(
            self.txts['instalar']+' '+self.txts['extencion'], 20, self.config.font_mononoki, (self.ventana_rect.centerx, 300),
            20, 'center', 'black','purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
            func=lambda: os.startfile(INITIAL_DIR / 'extencion.crx')
        )
        self.btn_extras_borrar_todo = uti_pag.Button(
            self.txts['borrar datos'], 20, self.config.font_mononoki, (0,self.ventana_rect.h), dire="bottomleft",
            func=lambda: self.open_desicion(
                self.txts['borrar datos'],
                self.txts['gui-desea borrar todos los datos?'],
                func=lambda e: self.func_borrar_todas_las_descargas() if e['index'] == 0 else None,
                options=['Borrar todo', 'Cancelar']
            )
        )

        self.text_extras_version = uti_pag.Text(f'Version {self.config.version}', 26, self.config.font_mononoki, (0,0), dire='bottomright')
        self.btn_extras_version_notes = uti_pag.Button(
            '', 26, self.config.font_symbols, (0,0), 10, 'bottomright','white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
            func=self.func_abrir_change_log
        )


        # GUI
        self.gui_informacion = AdC_theme.Info(self.ventana_rect.center, self.config.font_mononoki, 'Acelerador de descargas', self.txts['informacion'], (550,275))
        self.gui_desicion = AdC_theme.Desicion(self.ventana_rect.center, self.config.font_mononoki, 'Acelerador de descargas', self.txts['desicion'], (550,275))
        
    
        # Listas finales
        # Overlay
        self.overlay = [self.gui_informacion,self.gui_desicion,self.particulas_mouse,]
        # Main
        self.lists_screens['main']["draw"] = [
            self.text_main_title,self.btn_main_extras, self.btn_main_configs,self.list_main_descargas,self.btn_main_reload_list,
            self.btn_main_new_descarga,self.btn_main_change_save_dir,
        ]
        self.lists_screens['main']["update"] = self.lists_screens['main']["draw"]
        self.lists_screens['main']["click"] = [
            self.btn_main_extras, self.btn_main_configs,self.list_main_descargas,self.btn_main_reload_list,
            self.btn_main_new_descarga,self.btn_main_change_save_dir,
        ]

        # Config
        self.lists_screens['config']["draw"] = [
            self.text_config_title,self.btn_config_exit,self.text_config_hilos,
            self.btn_config_change_hilos, self.text_config_idioma,
            self.btn_config_idioma_es,self.btn_config_idioma_en,self.text_config_apagar_al_finalizar_cola,
            self.btn_config_apagar_al_finalizar_cola,self.text_config_LDM,self.btn_config_LDM,
            self.text_config_enfoques, self.btn_config_enfoques,self.text_config_detener_5min,
            self.btn_config_detener_5min,self.text_config_limitador_velocidad,
            self.btn_config_velocidad,self.text_config_particulas, self.btn_config_particulas,
            self.btn_config_añair_extencion,self.btn_config_eliminar_extencion,self.list_config_extenciones,
            self.text_config_agregar_a_cola_automaticamente, self.btn_config_agregar_a_cola_automaticamente,

            self.select_config_change_hilos, self.select_config_velocidad,
        ]
        self.lists_screens['config']["update"] = self.lists_screens['config']["draw"]

        self.lists_screens['config']["click"] = [
            self.btn_config_exit, self.btn_config_idioma_es,
            self.btn_config_idioma_en,self.btn_config_apagar_al_finalizar_cola,self.btn_config_LDM,
            self.btn_config_enfoques,self.btn_config_detener_5min,
            self.btn_config_particulas,
            self.btn_config_añair_extencion,self.btn_config_eliminar_extencion,self.list_config_extenciones,
            self.btn_config_agregar_a_cola_automaticamente,

            self.select_config_change_hilos, self.select_config_velocidad,
        ]

        # Nueva descarga
        self.lists_screens['new_download']['draw'] = [
            self.text_new_download_title,self.btn_new_download_cancelar,self.btn_new_download_aceptar,
            self.input_new_download_url,self.btn_new_download_paste,self.btn_new_download_comprobar_url,
            self.text_new_download_title_details,self.btn_new_download_hilos,self.select_new_download_hilos,

            # Detalles descarga
            self.text_new_download_filename,self.text_new_download_file_type,self.text_new_download_size,
            self.text_new_download_status,self.text_new_download_hilos,
        ]
        self.lists_screens['new_download']['update'] = self.lists_screens['new_download']['draw']
        self.lists_screens['new_download']['click'] = [
            self.btn_new_download_cancelar,self.btn_new_download_aceptar,self.input_new_download_url,
            self.btn_new_download_paste,self.btn_new_download_comprobar_url,

            self.select_new_download_hilos,
        ]
        self.lists_screens['new_download']['inputs'] = [
            self.input_new_download_url
        ]

        self.lists_screens['extras']['draw'] = [
            self.text_extras_title,self.btn_extras_exit,self.btn_extras_version_notes,
            self.text_extras_nombre,self.btn_extras_link_github,self.btn_extras_link_youtube,
            self.btn_extras_install_extension,self.btn_extras_borrar_todo,self.text_extras_version,
        ]
        self.lists_screens['extras']['update'] = self.lists_screens['extras']['draw']
        self.lists_screens['extras']['click'] = [
            self.btn_extras_exit,self.btn_extras_version_notes,
            self.btn_extras_link_github, self.btn_extras_link_youtube,
            self.btn_extras_install_extension,self.btn_extras_borrar_todo,
        ]

    @override
    def move_objs(self):
        # loader
        self.loader.pos = (self.ventana_rect.w-10, self.ventana_rect.h-30)

        # GUI
        self.gui_informacion.pos = self.ventana_rect.center
        self.gui_desicion.pos = self.ventana_rect.center

        # Main
        self.text_main_title.pos = (self.ventana_rect.centerx, 30)

        self.btn_main_extras.pos = (self.ventana_rect.w, 0)

        self.list_main_descargas.resize((self.ventana_rect.w - 60, self.ventana_rect.h - 140))
        self.btn_main_reload_list.pos = self.list_main_descargas.topright

        # Config
        self.text_config_title.pos = (self.ventana_rect.centerx, 30)
        self.btn_config_exit.pos = (self.ventana_rect.w, 0)
        
        self.list_config_extenciones.size = (self.ventana_rect.w*.3,self.ventana_rect.h*.7)
        self.list_config_extenciones.pos = (self.ventana_rect.w*.8,self.ventana_rect.centery)
        
        self.btn_config_añair_extencion.width =  self.list_config_extenciones.width/2
        self.btn_config_eliminar_extencion.width =  self.list_config_extenciones.width/2

        self.btn_config_añair_extencion.pos = self.list_config_extenciones.bottomleft
        self.btn_config_eliminar_extencion.pos = self.list_config_extenciones.bottomright


        # Pantalla nueva descarga
        self.rect_new_download_fondo.center = self.ventana_rect.center
        self.text_new_download_title.pos = (self.ventana_rect.centerx,self.ventana_rect.centery-120)
        
        self.input_new_download_url.pos = (self.ventana_rect.centerx-50,self.ventana_rect.centery-70)
        self.btn_new_download_paste.pos = self.input_new_download_url.topright+(0,1)
        self.btn_new_download_comprobar_url.pos = (self.btn_new_download_paste.right + 10,self.input_new_download_url.centery)

        # ---> Los detalles
        self.text_new_download_title_details.pos = (self.ventana_rect.centerx,self.ventana_rect.centery-30)
        self.text_new_download_filename.pos = (self.ventana_rect.centerx-220,self.ventana_rect.centery-10)
        self.text_new_download_file_type.pos = (self.ventana_rect.centerx-220,self.ventana_rect.centery+10)
        self.text_new_download_size.pos = (self.ventana_rect.centerx-220,self.ventana_rect.centery+30)
        self.text_new_download_status.pos = (self.ventana_rect.centerx-220,self.ventana_rect.centery+50)

        self.text_new_download_hilos.pos = (self.ventana_rect.centerx+150,self.ventana_rect.centery-10)
        if self.can_change_new_threads:
            self.btn_new_download_hilos.pos = (self.ventana_rect.centerx+150,self.ventana_rect.centery+30)
        else:
            self.btn_new_download_hilos.pos = (-1000,-1000)

        self.btn_new_download_cancelar.pos = (self.ventana_rect.centerx+125,self.ventana_rect.centery+150)
        self.btn_new_download_aceptar.pos = (self.ventana_rect.centerx+125,self.ventana_rect.centery+150)
        

        # Extras
        self.btn_extras_exit.pos = (self.ventana_rect.w, 0)
        self.btn_extras_link_github.pos = (self.ventana_rect.w*.25, 200)
        self.btn_extras_link_youtube.pos = (self.ventana_rect.w*.75, 200)

        self.btn_extras_version_notes.pos = (self.ventana_rect.w,self.ventana_rect.h)
        self.text_extras_version.pos = (self.btn_extras_version_notes.left,self.ventana_rect.h)

    @override
    def otro_evento(self, actual_screen: str, evento: pag.event.Event):
        if evento.type == pag.MOUSEBUTTONDOWN and evento.button == 1 and not self.low_detail_mode and self.allow_particles:
            self.particulas_mouse.spawn_pos = pag.mouse.get_pos()
            self.particulas_mouse.spawn()

        if actual_screen == 'main':
            if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
                self.exit()
            elif evento.type == pag.MOUSEBUTTONDOWN and evento.button == 3:
                if self.list_main_descargas.click(pag.mouse.get_pos(),pag.key.get_pressed()[pag.K_LCTRL],button=3) and (result := self.list_main_descargas.get_selects()):
                    self.list_main_descargas.redraw += 1
                    self.Mini_GUI_manager.add(
                        uti_pag.mini_GUI.select(
                            pag.Vector2(pag.mouse.get_pos())+(1, 1),
                            [
                                self.txts['descargar'], self.txts['eliminar'],self.txts['actualizar_url'], 'get url', 
                                self.txts['añadir a la cola'], self.txts['remover de la cola'], self.txts['limpiar cola'],
                                self.txts['reiniciar'], self.txts['cambiar nombre']
                            ],
                            captured=result
                        ),
                        func=self.func_select_box
                    )
        elif actual_screen == 'config':
            if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
                self.goto('main')
        elif actual_screen == 'extras':
            if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
                self.goto('main')
        elif actual_screen == 'new_download':
            if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
                self.func_salir_nueva_descarga()

    @override
    def draw_before(self, actual_screen):
        if actual_screen == 'new_download':
            pag.draw.rect(self.ventana, (50,50,50),self.rect_new_download_fondo, border_radius=20)

    @override
    def goto(self, screen):
        if screen == 'new_download':
            self.limpiar_textos_new_download()
            self.input_new_download_url.clear()
        super().goto(screen)

    
    # Ahora si, funciones del programa
    # Funciones de botones

    def func_abrir_change_log(self):
        self.Mini_GUI_manager.clear_group('change_log')
        self.Mini_GUI_manager.add(
            uti_pag.mini_GUI.simple_popup(
                pag.Vector2(50000,50000), 'botomright', 'Change Log', self.txts['gui-abriendo change log']
            ),
            group='change_log'
        )

        os.startfile(INITIAL_DIR/'version.txt')

    def func_reload_lista_descargas(self):
        try:
            self.loading += 1
            response = self.session.get('http://127.0.0.1:5000/descargas/get_all',timeout=5).json
            self.cached_list_DB = response['lista']
            self.cola = response['cola']
            
            diff = self.list_main_descargas.listas[0].desplazamiento
            self.list_main_descargas.clear()

            if not self.cached_list_DB:
                self.list_main_descargas.append((None, None, None))
                return

            to_set = [[] for _ in range(self.list_main_descargas.num_list)]
            for row in self.cached_list_DB:
                id_descarga = row[0]
                nombre = row[1]
                peso = uti.format_size_bits_to_bytes_str(row[3])
                hilos = row[5]
                fecha = datetime.datetime.fromtimestamp(float(row[6]))
                txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
                estado = self.txts[f'{row[7]}'.lower()] if f'{row[7]}'.lower() in self.txts else row[7]
                cola = ' - 'if not row[0] in self.cola else f'[{self.cola.index(row[0])}]'
                for i, j in enumerate((id_descarga, nombre, hilos, peso, estado, cola, txt_fecha)):
                    to_set[i].append(j)

            self.list_main_descargas.lista_palabras = to_set
            self.list_main_descargas.on_wheel(diff)
        except Exception as err:
            uti.debug_print(err)
            self.Mini_GUI_manager.clear_group('lista_descargas')
            self.Mini_GUI_manager.add(
                uti_pag.mini_GUI.more_objs.aviso1((50000, 50000), 'bottomright', 'error updating list',self.config.font_mononoki),
                group='lista_descargas'
            )
            raise ConnectionError("No se pudo conectar con el servidor")
        finally:
            self.loading -= 1

    def func_comprobar_url(self):
        self.url = self.input_new_download_url.get_text()
        self.thread_new_download = Thread(target=self.comprobar_url, daemon=True)
        self.thread_new_download.start()

    def func_salir_nueva_descarga(self):
        if self.thread_new_download and self.thread_new_download.is_alive():
            self.thread_new_download.join(.1)
        self.goto('main')

    def func_borrar_todas_las_descargas(self):
        uti.get('http://127.0.0.1:5000/descargas/delete_all')
        self.Func_pool.start('reload list')

    def func_select_box_hilos(self, respuesta) -> None:
        self.threads = 2**respuesta['index']
        self.text_config_hilos.text = self.txts['config-hilos'].format(self.threads)
        self.save_conf('hilos',self.threads)

    def func_change_idioma(self, idioma: str):
        self.loading += 1
        self.idioma = str(idioma)
        self.txts = idiomas[self.idioma]
        self.configs['idioma'] = self.idioma
        self.save_conf('idioma',self.idioma)

        self.generate_objs()
        self.Func_pool.start('reload list')
        self.move_objs()

        self.loading -= 1

    def func_preguntar_carpeta(self):
        try:
            ask = askdirectory(initialdir=self.save_dir, title=self.txts['cambiar carpeta'])
            if not ask:
                return
            self.save_dir = ask
            self.save_conf('save_dir',self.save_dir)
            self.Mini_GUI_manager.add(
                uti_pag.mini_GUI.simple_popup(pag.Vector2(50000,50000), 'bottomright', self.txts['carpeta cambiada'], self.txts['gui-carpeta cambiada con exito'])
            )
        except:
            pass

    def func_select_box(self, respuesta) -> None:
        if not self.cached_list_DB: return

        if len(respuesta['obj']) > 1 and respuesta['index'] == 1:
            self.open_desicion(self.txts['confirmar'], self.txts['gui-desea borrar los elementos'],
                lambda r: (self.del_downloads(respuesta['obj']) if r['index'] == 0 else None),
                options=['Eliminar', 'Cancelar']
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
            obj_cached: Download = Download(*self.cached_list_DB[respuesta['obj'][0]['index']])

        if respuesta['index'] == 0:
            # 0 descargar
            Thread(target=self.func_descargar, args=(obj_cached,)).start()
        elif respuesta['index'] == 1:
            # Eliminar la descarga
            txt = f'{self.txts["gui-desea borrar el elemento"]}\n\nid -> {obj_cached.id}\n'
            if len(f'"{obj_cached.nombre}"') <= 40:
                txt += f' "{obj_cached.nombre}"'
            else:
                txt += f'"{obj_cached.nombre[:36]}..."'
            self.open_desicion(
                self.txts['confirmar'], txt,
                lambda r: (self.del_download(obj_cached[0]) if r['index'] == 0 else None),
                options=['Eliminar', 'Cancelar']
            )
        elif respuesta['index'] == 2:
            # Cambiar la url
            response = uti.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached.id}').json
            if response['downloading'] == True or response['cola'] == True:
                self.mini_ventana(1)
                return
            response = uti.get(f'http://127.0.0.1:5000/descargas/update/url/{obj_cached.id}').json
            if response['status'] != 'ok':
                self.mini_ventana(6)
            else:
                self.mini_ventana(7)
        elif respuesta['index'] == 3:
            # copiar url al portapapeles
            pyperclip.copy(obj_cached[4])
            self.mini_ventana(3)
        elif respuesta['index'] == 4:
            # 4 añadir a la cola
            response = uti.get(f'http://127.0.0.1:5000/cola/add/{obj_cached.id}').json
            if response['status'] == 'ok':
                self.cola.append(obj_cached.id)
                self.list_main_descargas[5][respuesta['obj'][0]['index']] = f'[{self.cola.index(obj_cached.id)}]'         
        elif respuesta['index'] == 5:
            # 5 remover de la cola
            response = uti.get(f'http://127.0.0.1:5000/cola/delete/{obj_cached.id}').json
            if response['status'] == 'ok':
                self.cola.remove(obj_cached.id)
                self.list_main_descargas[5][respuesta['obj'][0]['index']] = f' - '   
        elif respuesta['index'] == 6:
            # 6 limpiar cola
            response = uti.get(f'http://127.0.0.1:5000/cola/clear').json
            if response['status'] == 'ok':
                self.cola.clear()
                for x in range(len(self.list_main_descargas)):
                    self.list_main_descargas[5][x] = f' - '
        elif respuesta['index'] == 7:
            # 7 reiniciar descarga
            response = uti.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached.id}').json
            if response['downloading'] == False and uti.get(f'http://127.0.0.1:5000/descargas/update/estado/{obj_cached.id}/esperando').json['status'] == 'ok':
                shutil.rmtree(self.config.cache_dir.joinpath(f'./{obj_cached.id}'), True)
                self.list_main_descargas[4][respuesta['obj'][0]['index']] = self.txts['esperando'].capitalize()
        elif respuesta['index'] == 8:
            # 8 cambiar nombre
            response = uti.get(f'http://127.0.0.1:5000/descargas/check/{obj_cached.id}').json
            if response['downloading'] == True:
                self.mini_ventana(1)
                return
            nombre = askstring(self.txts['nombre'], self.txts['gui-nombre del archivo'],initialvalue=obj_cached.nombre)
            if not nombre or nombre == '':
                return
            response = uti.send_post(f'http://127.0.0.1:5000/descargas/update/nombre', data={'id': obj_cached.id, 'nombre': nombre}).json
            if response['status'] == 'ok':
                self.list_main_descargas[1][int(respuesta['obj'][0]['index'])] = nombre
        self.redraw = True

    def func_descargar(self, obj_cached: Download):
        self.loading += 1
        response = uti.get(f'http://127.0.0.1:5000/descargas/download/{obj_cached.id}').json
        if response.get('status') == 'ok':
            self.mini_ventana(0)
        else:
            self.mini_ventana(1)
        self.loading -= 1
        self.redraw = True

    def func_select_box_velocidad(self, respuesta) -> None:
        uti.debug_print(respuesta)
        if respuesta['index'] == 8:
            num = askstring('Velocidad limite', 'Ingrese la velocidad limite en kb/s')
            if not num:
                return
            try:
                self.velocidad_limite = int(num) * 1024
            except Exception as err:
                uti.debug_print(err)
                self.open_info('Error',self.txts['numero invalido'])
        else:
            diccionario_velocidades = {
                0: 0,
                1: 2**15,
                2: 2**16,
                3: 2**17,
                4: 2**19,
                5: 2**20,
                6: 2**23,
                7: 2**24,
                8: 'Otro'
            }
            self.velocidad_limite = diccionario_velocidades[respuesta['index']]

        self.text_config_limitador_velocidad.text = self.txts['limitar-velocidad']+': '+uti.format_size_bits_to_bytes_str(self.velocidad_limite)
        self.btn_config_velocidad.pos = (self.text_config_limitador_velocidad.right + 60, self.text_config_limitador_velocidad.centery)
        self.save_conf('velocidad_limite',self.velocidad_limite)

    def func_select_box_hilos_newd(self, respuesta) -> None:
        self.new_threads = 2**respuesta['index']
        self.text_new_download_hilos.text = self.txts['config-hilos'].format(self.new_threads)

    def func_añadir_extencion(self):
        nombre = askstring('Extencion', 'Ingrese la extencion que desea agregar')
        if not nombre or nombre == '':
            return
        self.extenciones.append(nombre)
        self.list_config_extenciones.append(nombre)
        self.save_conf('extenciones',self.extenciones, parser='json')

    def func_eliminar_extencion(self,r):
        if r['index'] != 0 or not self.list_config_extenciones.get_selects():
            return
        for i,x in sorted(self.list_config_extenciones.get_selects(), reverse=True):
            self.extenciones.pop(i)
            self.list_config_extenciones.pop(i)
        self.save_conf('extenciones',self.extenciones, parser='json')

    def func_toggle_apagar_al_finalizar_cola(self):
        self.apagar_al_finalizar_cola = not self.apagar_al_finalizar_cola
        self.btn_config_apagar_al_finalizar_cola.text = ''if self.apagar_al_finalizar_cola else ''
        self.save_conf('apagar al finalizar cola',self.apagar_al_finalizar_cola)
    def func_toggle_ldm(self):
        self.low_detail_mode = not self.low_detail_mode
        self.btn_config_LDM.text = ''if self.low_detail_mode else ''
        self.list_main_descargas.smothscroll = not self.low_detail_mode
        # self.list_config_extenciones.smothscroll = not self.low_detail_mode
        self.save_conf('ldm',self.low_detail_mode)
    def func_toggle_enfoques(self):
        self.enfoques = not self.enfoques
        self.btn_config_enfoques.text = '' if self.enfoques else ''
        self.save_conf('enfoques',self.enfoques)
    def func_toggle_detener_5min(self):
        self.detener_5min = not self.detener_5min
        self.btn_config_detener_5min.text = '' if self.detener_5min else ''
        self.save_conf('detener_5min',self.detener_5min)
    def func_toggle_particles(self):
        self.allow_particles = not self.allow_particles
        self.btn_config_particulas.text = ''if self.allow_particles else ''
        self.save_conf('particulas', self.allow_particles)
    def func_toggle_agregar_a_cola_automaticamente(self):
        self.agregar_a_cola_automaticamente = not self.agregar_a_cola_automaticamente
        self.btn_config_agregar_a_cola_automaticamente.text = '' if self.agregar_a_cola_automaticamente else ''
        self.save_conf('agregar a cola automaticamente', self.agregar_a_cola_automaticamente)


    # Funciones Variadas
    def mini_ventana(self,num):
        txts_dict = {
            0: ('descarga iniciada', 'Descargando', self.txts['gui-descarga iniciada']),
            1: ('descarga en curso', 'Error', self.txts['gui-descarga en curso']),
            2: ('descarga eliminada', 'Error', self.txts['gui-descarga eliminada']),
            3: ('portapapeles', 'Copiado', self.txts['copiado al portapapeles']),
            4: ('solo una descarga', 'Error', self.txts['gui-solo una descarga']),
            5: ('error', 'Error', self.txts['gui-error inesperado']),
            6: ('error', 'Error', self.txts['gui-error actualizando url']),
            7: ('actualizando url', 'Actualizando', self.txts['gui-actualizando url mini'])
        }
        txt_group, txt_header, txt_body = txts_dict[num]
        self.Mini_GUI_manager.clear_group(txt_group)
        self.Mini_GUI_manager.add(
            uti_pag.mini_GUI.simple_popup(
                pag.Vector2(50000,50000), 'botomright', txt_header,txt_body,(200,90)
            ),
            group=txt_group
        )

    def func_add_download(self):
        if not self.can_add_new_download:
            return
        self.session.post('http://127.0.0.1:5000/descargas/add_from_program', data={'url': self.url, "tipo": self.new_file_type, 'hilos': self.new_threads, 'nombre': self.new_filename, 'size':self.new_file_size})

        self.Func_pool.start('reload list')
        self.goto('main')

    def del_downloads(self,obj):
        for x in obj:
            uti.get(f'http://127.0.0.1:5000/descargas/delete/{self.cached_list_DB[x['index']][0]}').json
        self.last_update = 0
        self.last_click = 0
        # self.Func_pool.start('reload list')
        return

    def del_download(self, index):
        response = uti.get(f'http://127.0.0.1:5000/descargas/delete/{index}').json
        if response.get('status') == 'ok':
            self.mini_ventana(2)
            self.last_update = 0
            self.last_click = 0
            # self.Func_pool.start('reload list')
        elif response.get('status') == 'error':
            self.mini_ventana(1)

    def open_info(self, title, texto, func=None):
        self.gui_informacion.func = func
        self.gui_informacion.title.text = title
        self.gui_informacion.body.text = texto
        self.gui_informacion.active = True
        self.gui_desicion.redraw += 1
    
    def open_desicion(self, title, texto, func=None, options: list[str] = None):
        self.gui_desicion.title.text = title
        self.gui_desicion.body.text = texto
        self.gui_desicion.active = True
        self.gui_desicion.func = func
        self.gui_desicion.options = options
        self.gui_desicion.redraw += 1

    def limpiar_textos_new_download(self):
        self.text_new_download_filename.text = self.txts['nombre']+': ----------'
        self.text_new_download_file_type.text = self.txts['tipo']+': ----------'
        self.text_new_download_size.text = self.txts['tamaño']+': ----------'
        self.text_new_download_status.text = self.txts['descripcion-state[esperando]']
        self.btn_new_download_hilos.pos = (-10000,-100000)
        self.new_threads = self.threads
        self.can_change_new_threads = False
        self.new_file_size = 0
        self.new_filename = ''
        self.new_file_type = ''

    def comprobar_url(self):
        if not self.url:
            return 
        self.limpiar_textos_new_download()
        self.can_add_new_download = False

        url_parsed: str = urlparse(self.url).path
        for x in url_parsed.split('/')[::-1]:
            if '.' in x:
                new_title = unquote(x)
                break
        else:
            new_title: str = unquote(url_parsed.split('/')[-1])

        self.new_filename = new_title
        if len(self.new_filename) > 33:
            self.text_new_download_filename.text = self.new_filename[:33] + '...'
        else:
            self.text_new_download_filename.text = self.new_filename

        self.text_new_download_status.text = self.txts['descripcion-state[conectando]']

        try:
            url_parsed = urllib.parse.urlparse(self.url)
            if not url_parsed.scheme or not url_parsed.netloc:
                raise urllib.error.URLError('URL invalida')
            
            response = self.session.get(self.url, timeout=15).headers
            
            self.logger.write(f"Informacion obtenida: {self.url}")
            self.logger.write(response)
            uti.debug_print(response)

            # Validacion de tipo
            tipo = response.get('Content-Type', 'unknown/Nose').split(';')[0]
            self.new_file_type = tipo
            self.text_new_download_file_type.text = self.txts['tipo']+': ' + tipo
            if self.new_file_type in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')
            
            # Validacion de reanudar
            if 'bytes' in response.get('Accept-Ranges', ''):
                self.can_change_new_threads = True
                self.btn_new_download_hilos.pos = (self.ventana_rect.centerx+150,self.ventana_rect.centery+30)
                self.new_threads = self.threads
                self.text_new_download_hilos.text = self.txts['config-hilos'].format(self.new_threads)
            else:
                self.can_change_new_threads = False
                self.btn_new_download_hilos.pos = (-10000,-100000)
                self.new_threads = 1
                self.text_new_download_hilos.text = self.txts['config-hilos'].format(self.new_threads)

            # Validacion de tamaño
            self.new_file_size = int(response.get('content-length', 0))
            if self.new_file_size < 4096:
                self.new_threads = 1
                self.can_change_new_threads = False
            self.text_new_download_size.text = f"{self.txts['tamaño']}: {uti.format_size_bits_to_bytes_str(self.new_file_size)}"
            
            if a := response.get('content-disposition', False):
                nuevo_nombre = a.split(';')
                for x in nuevo_nombre:
                    if 'filename=' in x:
                        nuevo_nombre = x.replace('filename=', '').replace('"', '').strip()
                        break
                if isinstance(nuevo_nombre, str):
                    self.new_filename = unquote(nuevo_nombre)
                    self.text_new_download_filename.text = self.new_filename
            
            self.text_new_download_status.text = self.txts['estado']+': '+self.txts['disponible']
            self.can_add_new_download = True
        except InvalidURL as err:
            self.text_new_download_status.text = self.txts['descripcion-state[url invalida]']
            uti.debug_print(err, priority=3)
        except TimeoutError as err:
            self.text_new_download_status.text = self.txts['descripcion-state[tiempo agotado]']
            uti.debug_print(err, priority=3)
        except urllib.error.HTTPError as err:
            self.text_new_download_status.text = self.txts['descripcion-state[error internet]']
            uti.debug_print(err, priority=3)
        except uti.web_tools.errors.InternetError as err:
            uti.debug_print("", priority=3)
            self.text_new_download_status.text = self.txts['descripcion-state[error internet]']
        except TrajoHTML as err:
            self.text_new_download_status.text = self.txts['descripcion-state[trajo un html]']
            uti.debug_print(err, priority=3)
        except LinkCaido as err:
            self.text_new_download_status.text = self.txts['descripcion-state[link caido]']
            uti.debug_print(err, priority=3)
        except Exception as err:
            uti.debug_print(err, priority=3)
            self.logger.write(f'Error comprobar {self.url} - {type(err)} -> {err}')
            self.text_new_download_status.text = self.txts['descripcion-state[error]']

    def reload_elemento_individual(self, id):
        response = Download(*self.session.get(f'http://127.0.0.1:5000/descargas/get/{id}',timeout=5).json)
        self.cola = self.session.get('http://127.0.0.1:5000/cola/get_all',timeout=5).json['cola']
        nombre = response.nombre
        peso = uti.format_size_bits_to_bytes_str(response.peso)
        hilos = response.partes
        fecha = datetime.datetime.fromtimestamp(float(response.fecha))
        txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
        estado = self.txts[f'{response.estado}'.lower()] if f'{response.estado}'.lower() in self.txts else response.estado
        cola = ' - 'if not response.id in self.cola else f'[{self.cola.index(response.id)}]'
        # self.list_main_descargas.append([id,nombre, hilos, peso, estado, cola, txt_fecha])
        for i,d in enumerate(self.cached_list_DB):
            if d[0] == id:
                self.cached_list_DB[i] = response
                self.list_main_descargas[i] = (id,nombre, hilos, peso, estado, cola, txt_fecha)
                break

    def get_server_updates(self):
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_client.connect(('127.0.0.1', 5001))
        try:
            self.socket_client.sendall(json.dumps({'status': 'idle'}).encode())
            while True:
                if not self.running:
                    break
                r = self.socket_client.recv(1024).decode()
                if not r:
                    continue
                try:
                    respuesta = json.loads(r)
                except Exception as err:
                    uti.debug_print(r, priority=1)
                    uti.debug_print(err, priority=2)
                    self.socket_client.sendall(json.dumps({'status': 'idle'}).encode())
                    continue
                    
                # if respuesta['last_update'] != self.last_update and respuesta['last_update_type'] > 0:
                #     uti.debug_print(f'Actualizacion: {respuesta["last_update"]} - {self.last_update}', priority=3)
                #     uti.debug_print(f'result: {respuesta}', priority=3)
                #     pass

                to_send = 'idle'

                if (time.time() - self.last_update > 2) and (time.time()-self.last_click > 4) and respuesta["last_update_type"] > 1:
                    self.func_reload_lista_descargas()
                    self.last_update = respuesta["last_update"]
                    to_send = 'updated'

                elif self.last_update != respuesta["last_update"] and respuesta["last_update_type"] == 1:
                    to_send = 'updated'
                    for i in respuesta['last_downloads_changed']:
                        self.reload_elemento_individual(i)
                    self.last_update = respuesta["last_update"]
                
                
                else:
                    to_send = 'idle'

                if to_send == 'idle' and time.time() - self.last_update > .5:
                    time.sleep(0.2)
                else:
                    time.sleep(1/30)

                self.socket_client.sendall(json.dumps({"status": to_send}).encode())
        except Exception as err:
            uti.debug_print(err, priority=3)
        finally:
            self.socket_client.close()
            self.socket_client = None

if __name__ == '__main__':
    Downloads_manager(Config(resolution=(800, 550), min_resolution=(600,450)))
