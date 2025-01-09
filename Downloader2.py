import pygame as pag
import sys
import os
import time
import requests
import json
import subprocess
import shutil
import Utilidades_pygame as uti_pag
import Utilidades as uti


from platformdirs import user_downloads_dir, user_cache_path, user_config_path, user_downloads_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter.simpledialog import askstring
from pygame.constants import (MOUSEBUTTONDOWN, K_ESCAPE, QUIT, KEYDOWN, MOUSEWHEEL, MOUSEMOTION,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)


from textos import idiomas
from my_warnings import *

from constants import DICT_CONFIG_DEFAULT, FONT_MONONOKI

RESOLUTION = (700, 300)

class Downloader:
    def __init__(self, id, modificador=0) -> None:
        pag.init()
        
        self.ventana = pag.display.set_mode(RESOLUTION)
        self.ventana_rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))

        self.carpeta_cache = user_cache_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)
        self.carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_config.mkdir(parents=True, exist_ok=True)

        
        self.raw_data = requests.get(f'http://127.0.0.1:5000/descargas/get/{id}').json()
        
        self.id: int = self.raw_data[0]
        self.file_name: str = self.raw_data[1]
        self.type: str = self.raw_data[2]
        self.peso_total: int = self.raw_data[3]
        self.url: str = self.raw_data[4]
        self.num_hilos: int = self.raw_data[6]
        self.tiempo: float = float(self.raw_data[7])
        self.modificador = int(modificador)
        
        pag.display.set_caption(f'Downloader {self.id}_{self.file_name}')


        self.paused = True
        self.canceled = False
        self.screen_main = True
        self.can_download = False
        self.can_reanudar = True
        self.downloading = False
        self.apagar_al_finalizar = False
        self.ejecutar_al_finalizar = False if self.modificador != 1 else True
        self.cerrar_al_finalizar = False if self.modificador != 2 else True
        self.drawing = True
        self.finished = False
        self.detener_5min = True
        self.fallo_destino = False
        self.low_detail_mode = False
        self.last_change = time.time()
        self.db_update = time.time()
        self.speed_deltatime = uti.Deltatime(15,10)
        self.intentos = 0
        self.chunk = 128
        self.list_vels: list[int] = []
        self.save_dir = user_downloads_dir()
        self.relog = pag.time.Clock()
        self.returncode = 0
        self.velocidad_limite = 0
        self.current_velocity = 0
        self.last_tiempo_restante_update = time.time()
        self.downloading_threads = 0
        self.hilos_listos = 0
        self.peso_descargado = 0
        self.peso_descargado_vel = 0
        self.default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'}

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')
        self.carpeta_cache: Path = self.carpeta_cache.joinpath(f'./{self.id}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)


        self.prepared_session = requests.Session()

    
        self.cargar_configs()
        self.generar_objs()

        if self.enfoques:
            uti.win32_tools.front2(pag.display.get_wm_info()['window'])
        self.Func_pool.start('descargar')


        self.ciclo_general = [self.main_cycle]
        self.cicle_try = 0

        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

    def cargar_configs(self):
        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except Exception:
            self.configs = DICT_CONFIG_DEFAULT

        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.velocidad_limite = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])

        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.save_dir = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.txts = idiomas[self.idioma]

    def generar_objs(self):
        
        self.GUI_manager = uti_pag.GUI.GUI_admin()
        self.mini_GUI_manager = uti_pag.mini_GUI.mini_GUI_admin(self.ventana_rect)
        self.Func_pool = uti.Funcs_pool()
        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)
        ]
        
        # ------------------------------------------- Textos y botones -----------------------------------
        self.Titulo = uti_pag.Text((self.file_name if len(self.file_name) < 36 else (self.file_name[:38] + '...')), 14, FONT_MONONOKI, (10, 50), 'left')
        self.text_tamaño = uti_pag.Text(self.txts['descripcion-peso'].format(uti.format_size_bits_to_bytes_str(self.peso_total)), 12, FONT_MONONOKI, (10, 70), 'left')
        self.text_url = uti_pag.Text(f'url: {(self.url if len(self.url) < 37 else (self.url[:39] + "..."))}', 12, FONT_MONONOKI, (10, 90), 'left')
        self.text_num_hilos = uti_pag.Text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12, FONT_MONONOKI, (10, 110), 'left')
        self.text_estado_general = uti_pag.Text(self.txts['descripcion-state[esperando]'], 12, FONT_MONONOKI, (10, 130), 'left')
        self.text_peso_progreso = uti_pag.Text('0b', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 10), 'topleft', padding=(20,10), color_rect=(20, 20, 20))
        self.text_vel_descarga = uti_pag.Text(self.txts['velocidad'] + ': ' + '0kb/s', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 34), 'topleft', padding=(20,10))
        self.text_tiempo_restante = uti_pag.Text(self.txts['tiempo restante'] + ': 0Seg', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 58), 'topleft', padding=(20,10))
        self.text_porcentaje = uti_pag.Text('0.00%', 14, FONT_MONONOKI, (175, self.ventana_rect.bottom - 50), 'center', padding=(300, 5))
        self.text_title_hilos = uti_pag.Text(self.txts['title_hilos'], 14, FONT_MONONOKI, (550, 30), 'center')


        self.btn_cancelar_descarga = uti_pag.Button(self.txts['cancelar'], 16, FONT_MONONOKI, ((RESOLUTION[0] / 2) / 3, 20),
                                                  (20, 10), 'center', 'black',
                                                  'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda:
            self.GUI_manager.add(
                uti_pag.GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'], self.txts['gui-cancelar descarga'], (400, 200)), self.func_cancelar
            ))
        
        self.btn_pausar_y_reanudar_descarga = uti_pag.Button(self.txts['reanudar'], 16, FONT_MONONOKI, (((RESOLUTION[0] / 2) / 3) * 2, 20), (20, 10), 'center', 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.func_reanudar)
    
        self.btn_more_options = uti_pag.Button('', 16, FONT_MONONOKI, ((RESOLUTION[0]/2)-1, 20), 10, 'right', 'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1, func=self.func_select_of_options)

