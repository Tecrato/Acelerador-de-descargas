import Utilidades
import json
import os
import pygame as pag
import requests
import sqlite3
import sys
import time
import subprocess

from threading import Thread
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup as bsoup4
from Utilidades import Create_text, Create_boton, Multi_list, GUI, mini_GUI, Funcs_pool, Input_text, check_update
from platformdirs import user_config_path, user_cache_path
from pygame.constants import (MOUSEBUTTONDOWN, MOUSEMOTION, KEYDOWN, QUIT, K_ESCAPE,
                              WINDOWFOCUSLOST, WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS)
from pygame import Vector2

from funcs import Other_funcs
from textos import idiomas
from my_warnings import *

pag.init()

RESOLUCION = [800, 600]

def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


# noinspection PyAttributeOutsideInit
class DownloadManager(Other_funcs):
    def __init__(self, url=False) -> None:
        self.ventana = pag.display.set_mode(RESOLUCION)
        self.ventana_rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))

        self.carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_config.mkdir(parents=True, exist_ok=True)
        self.carpeta_cache = user_cache_path('Acelerador de descargas', 'Edouard Sandoval')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

        self.new_url: str = ''
        self.new_filename: str = ''
        self.new_file_type: str = ''
        self.new_file_size: int = 0
        self.thread_new_download = None
        self.actualizar_url = False

        self.cached_list_DB = []
        self.descargas_adyacentes = []

        self.data_actualizacion = {}
        self.url_actualizacion = ''
        self.version = '2.5.3'
        self.threads = 8
        self.drawing = True
        self.relog = pag.time.Clock()

        # self.font_mononoki: str = 'C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        # self.font_simbolos = 'C:/Users/Edouard/Documents/fuentes/Symbols.ttf'
        self.font_mononoki = './Assets/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        self.font_simbolos = './Assets/fuentes/Symbols.ttf'
        self.idioma = 'español'
        self.txts = idiomas[self.idioma]

        self.nomenclaturas = {
            0: 'bytes',
            1: 'Kb',
            2: 'Mb',
            3: 'Gb',
            4: 'Tb'
        }

        self.load_resources()
        self.generate_objs()
        self.reload_lista_descargas()
        self.Func_pool.start('actualizacion')

        self.screen_main_bool = True
        self.screen_new_download_bool = True
        self.screen_configs_bool = False
        self.screen_extras_bool = False

        self.ciclo_general = [self.main_cycle, self.screen_configs, self.screen_extras]
        self.cicle_try = 0

        if url:
            self.func_paste_url(url)
            self.func_comprobar_url()
            self.screen_new_download()

        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

    def load_resources(self):
        self.DB = sqlite3.connect(self.carpeta_config.joinpath('./downloads.sqlite3'))
        self.DB_cursor = self.DB.cursor()

        try:
            self.DB_cursor.execute('SELECT * FROM descargas')
        except sqlite3.OperationalError:
            self.DB_cursor.executescript(open('./descargas.sql').read())

        # noinspection PyBroadException
        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except Exception:
            self.configs = {}
        self.threads = self.configs.get('hilos', 8)
        self.idioma = self.configs.get('idioma', 'español')
        self.txts = idiomas[self.idioma]

        self.save_json()

    def save_json(self):
        self.configs['hilos'] = self.threads
        self.configs['idioma'] = self.idioma

        json.dump(self.configs, open(self.carpeta_config.joinpath('./configs.json'), 'w'))

    def generate_objs(self) -> None:
        # Cosas varias
        Utilidades.GUI.configs['fuente_simbolos'] = self.font_simbolos
        self.GUI_manager = GUI.GUI_admin()
        self.Mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)
        self.Func_pool = Funcs_pool()
        self.Func_pool.add('actualizacion', self.buscar_acualizaciones)
        self.Func_pool.add('descargar actualizacion', self.descargar_actualizacion)

        # Pantalla principal
        self.txt_title = Create_text(self.txts['title'], 26, self.font_mononoki, (self.ventana_rect.centerx, 30))
        self.btn_extras = Create_boton('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 20, 'topright', 'white',
                                       (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                       func=self.func_main_to_extras)
        self.btn_configs = Create_boton('', 26, self.font_simbolos, (0, 0), 20, 'topleft', 'white', (20, 20, 20),
                                        (50, 50, 50), 0, -1, border_width=-1, func=self.func_main_to_config)

        self.btn_new_descarga = Create_boton(self.txts['btn-nueva_descarga'], 16, self.font_mononoki, (30, 80), 20,
                                             'topleft', 'white', (50, 50, 50), (90, 90, 90), 0, 20,
                                             border_bottom_right_radius=0, border_top_right_radius=0, border_width=-1,
                                             func=self.screen_new_download)
        self.btn_change_dir = Create_boton(self.txts['btn-cambiar_carpeta'], 16, self.font_mononoki,
                                           (self.btn_new_descarga.rect.right, 80), 20, 'topleft', 'white', (50, 50, 50),
                                           (90, 90, 90), 0, 20, border_bottom_left_radius=0, border_top_left_radius=0,
                                           border_width=-1)

        self.lista_descargas = Multi_list((self.ventana_rect.w - 60, self.ventana_rect.h - 140), (30, 120), 6, None, 12,
                                          10, header_text=[self.txts['nombre'], self.txts['tipo'], self.txts['hilos'], self.txts['tamaño'], self.txts['estado'], self.txts['fecha']],
                                          fonts=[self.font_mononoki for _ in range(6)], colums_witdh=[0, .3, .45, .55, .68, .82], padding_left=5, border_color=(100,100,100))
        self.btn_reload_list = Create_boton('', 13, self.font_simbolos, (self.ventana_rect.w - 30, 121), 17,
                                            'topright', 'black', 'darkgrey', 'lightgrey', 0, border_width=1,
                                            border_radius=0, border_top_right_radius=20,
                                            func=self.reload_lista_descargas)

        # Cosas de la ventana de nueva descarga
        self.new_download_rect = pag.Rect(0, 0, 500, 300)
        self.new_download_rect.center = self.ventana_rect.center
        self.text_newd_title = Create_text(self.txts['agregar nueva descarga'], 16, self.font_mononoki,
                                           (self.new_download_rect.centerx, self.new_download_rect.top + 20))
        self.boton_newd_cancelar = Create_boton(self.txts['cancelar'], 16, self.font_mononoki,
                                                Vector2(-20, 0) + self.new_download_rect.bottomright, (30, 20),
                                                'bottomright', border_radius=0, border_top_right_radius=20,
                                                func=self.func_newd_close)
        self.boton_newd_aceptar = Create_boton(self.txts['aceptar'], 16, self.font_mononoki,
                                               (self.boton_newd_cancelar.rect.left, self.new_download_rect.bottom),
                                               (30, 19), 'bottomright', border_radius=0, border_top_left_radius=20,
                                               func=self.func_add_download_to_DB)

        self.input_newd_url = Input_text((self.new_download_rect.left + 20, self.new_download_rect.top + 100),
                                         (12, 300), self.font_mononoki, 'url de la descarga', max_letter=400)
        self.input_newd_paste = Create_boton('', 22, self.font_simbolos,
                                             (self.input_newd_url.text_rect.right, self.input_newd_url.pos.y), (20, 10),
                                             'left', 'black', 'lightgrey', 'darkgrey', border_width=1, border_radius=0,
                                             border_top_right_radius=20, border_bottom_right_radius=20,
                                             func=self.func_paste_url)

        self.btn_comprobar_url = Create_boton(self.txts['comprobar'], 16, self.font_mononoki,
                                              (self.new_download_rect.right - 20, self.input_newd_url.pos.y), (20, 10),
                                              'right', 'black', 'lightgrey', 'darkgrey', border_width=1,
                                              border_radius=20,
                                              func=self.func_comprobar_url)

        self.text_newd_title_details = Create_text(self.txts['detalles'], 20, self.font_mononoki, (400, 300))
        self.text_newd_filename = Create_text(self.txts['nombre']+': ----------', 16, self.font_mononoki,
                                              (self.new_download_rect.left + 20, 320), 'left')
        self.text_newd_file_type = Create_text(self.txts['tipo']+': ----------', 16, self.font_mononoki,
                                              (self.new_download_rect.left + 20, 340), 'left')
        self.text_newd_size = Create_text(self.txts['tamaño']+': -------', 16, self.font_mononoki,
                                          (self.new_download_rect.left + 20, 360), 'left')
        self.text_newd_status = Create_text(self.txts['descripcion-state[esperando]'], 16, self.font_mononoki,
                                            (self.new_download_rect.left + 20, 380), 'left')

        # Pantalla de configuraciones
        self.text_config_title = Create_text(self.txts['title-configuraciones'], 26, self.font_mononoki,
                                             (self.ventana_rect.centerx, 30))
        self.btn_config_exit = Create_boton('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 20, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_exit_configs)

        self.text_config_hilos = Create_text(self.txts['config-hilos'].format(self.threads), 16, self.font_mononoki,
                                             (20, 100), 'left')
        self.btn_mas_hilos = Create_boton('', 14, self.font_simbolos,
                                          (self.text_config_hilos.rect.right + 10, self.text_config_hilos.rect.centery),
                                          (5, 0), 'bottom', 'white', color_rect_active=(40, 40, 40), border_radius=0,
                                          border_width=-1, toggle_rect=True, func=lambda: self.func_change_hilos('up'))
        self.btn_menos_hilos = Create_boton('', 14, self.font_simbolos,
                                            (self.text_config_hilos.rect.right + 10,
                                             self.text_config_hilos.rect.centery), (5, 0), 'top', 'white',
                                            color_rect_active=(40, 40, 40), border_radius=0, border_width=-1,
                                            toggle_rect=True, func=lambda: self.func_change_hilos('down'))

        self.text_config_idioma = Create_text(self.txts['config-idioma'], 16, self.font_mononoki, (20, 130), 'left')
        self.btn_config_idioma_es = Create_boton('Español', 14, self.font_mononoki, (20, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('español'))
        self.btn_config_idioma_en = Create_boton('English', 14, self.font_mononoki, (110, 160), (20, 10), 'left',
                                                 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                 func=lambda: self.func_change_idioma('ingles'))

        # Pantalla de extras
        self.text_extras_title = Create_text('Extras', 26, self.font_mononoki, (self.ventana_rect.centerx, 30))
        self.btn_extras_exit = Create_boton('', 26, self.font_simbolos, (self.ventana_rect.w, 0), 20, 'topright',
                                            'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                            func=self.func_extras_to_main)

        self.text_extras_version = Create_text('Version '+self.version, 26, self.font_mononoki, self.ventana_rect.bottomright,
                                               'bottomright')

        self.text_extras_mi_nombre = Create_text('Edouard Sandoval', 30, self.font_mononoki, (400, 100),
                                                 'center')
        self.btn_extras_link_github = Create_boton('', 30, self.font_simbolos, (370, 200), 20, 'bottomright',
                                                   func=lambda: os.startfile('http://github.com/Tecrato'))
        self.btn_extras_link_youtube = Create_boton('輸', 30, self.font_simbolos, (430, 200), 20, 'bottomleft',
                                                    func=lambda: os.startfile(
                                                        'http://youtube.com/channel/UCeMfUcvDXDw2TPh-b7UO1Rw'))

        # Pantalla principal
        self.list_to_draw = [self.txt_title, self.btn_extras, self.btn_configs, self.btn_new_descarga,
                             self.btn_change_dir, self.lista_descargas, self.btn_reload_list]
        self.list_to_click = [self.btn_new_descarga, self.btn_configs, self.btn_reload_list, self.btn_extras]

        # Ventana de nueva descarga
        self.list_to_draw_new_download = [
            self.text_newd_title, self.boton_newd_aceptar, self.boton_newd_cancelar, self.input_newd_url,
            self.input_newd_paste,
            self.btn_comprobar_url, self.text_newd_title_details, self.text_newd_filename, self.text_newd_size,
            self.text_newd_status,self.text_newd_file_type
        ]

        self.list_to_click_newd = [self.boton_newd_aceptar, self.boton_newd_cancelar, self.input_newd_paste,
                                   self.btn_comprobar_url]
        self.list_inputs_newd = [self.input_newd_url]

        # Pantalla de configuraciones
        self.list_to_draw_config = [self.text_config_title, self.btn_config_exit, self.text_config_hilos,
                                    self.btn_mas_hilos, self.btn_menos_hilos, self.text_config_idioma,
                                    self.btn_config_idioma_en, self.btn_config_idioma_es]
        self.list_to_click_config = [self.btn_config_exit, self.btn_mas_hilos, self.btn_menos_hilos,
                                     self.btn_config_idioma_en, self.btn_config_idioma_es]

        # Pantalla de Extras
        self.list_to_draw_extras = [self.text_extras_title, self.btn_extras_exit, self.text_extras_mi_nombre,
                                    self.btn_extras_link_github, self.btn_extras_link_youtube, self.text_extras_version]
        self.list_to_click_extras = [self.btn_extras_exit, self.btn_extras_link_github, self.btn_extras_link_youtube]

    def buscar_acualizaciones(self):
       
        sera = check_update('acelerador de descargas', self.version, 'last')

        if not sera:
            return 
        
        self.Mini_GUI_manager.add(mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['actualizacion'], 'Se a encontrado una nueva actualizacion\n\nObteniendo link...', (260,100)))
        

        try:
            self.data_actualizacion['url'] = bsoup4(requests.get(sera['url']).text, 'html.parser').find(id='downloadButton').get('href',False)
            response2 = requests.get(self.data_actualizacion['url'], stream=True, allow_redirects=True, timeout=15)

            self.data_actualizacion['file_type'] = response2.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if self.data_actualizacion['file_type'] in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')
            self.data_actualizacion['size'] = int(response2.headers.get('content-length'))
            self.data_actualizacion['file_name'] = response2.headers.get('content-disposition').split('filename=')[1].replace('"', '')

            self.Mini_GUI_manager.clear()
            self.Mini_GUI_manager.add(
                mini_GUI.desicion_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['actualizacion'], self.txts['gui-desea descargar la actualizacion'], (250,100), self.txts['agregar']),
                lambda _: self.Func_pool.start('descargar actualizacion')
            )
        except Exception as err:
            self.Mini_GUI_manager.add(mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['actualizacion'], 'Error al obtener actualizacion.', (250,100)))
            print(err)

    def descargar_actualizacion(self):

        DB = sqlite3.connect(self.carpeta_config.joinpath('./downloads.sqlite3'))
        DB_cursor = DB.cursor()

        datos = [self.data_actualizacion['file_name'], self.data_actualizacion['file_type'], self.data_actualizacion['size'], self.data_actualizacion['url'], self.threads, time.time(),'en espera']
        DB_cursor.execute('INSERT INTO descargas VALUES(null,?,?,?,?,?,?,?)', datos)
        DB.commit()

        self.reload_lista_descargas(DB_cursor)

        DB_cursor.execute('SELECT id from descargas ORDER BY id DESC LIMIT 1')
        id = DB_cursor.fetchone()[0]
        
        self.descargas_adyacentes.append(
            Thread(target=subprocess.run,
                    args=(f'Downloader.exe "{id}" 1',))
            )
            # Thread(target=subprocess.run,
            #        args=(f'python Downloader.py "{id}" 1',))
            # )
        self.descargas_adyacentes[-1].start()

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
        if len(title) > 40:
            title = title[:40] + '...'

        self.text_newd_filename.change_text(f'{title}')

        self.text_newd_status.change_text(self.txts['descripcion-state[conectando]'])
        try:
            
            parse = urlparse(self.url)
            if parse.netloc == "www.mediafire.com" and parse.path[1:].split('/')[0] == 'file':
                url = bsoup4(requests.get(self.url).text, 'html.parser').find(id='downloadButton').get('href',False)

                response = requests.get(url, stream=True, allow_redirects=True, timeout=15)
            else:
                response = requests.get(self.url, stream=True, allow_redirects=True, timeout=15)
                
            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            self.new_file_type = tipo
            self.text_newd_file_type.change_text(self.txts['tipo']+': ' + tipo)
            if self.new_file_type in ['text/plain', 'text/html']:
                raise TrajoHTML('No paginas')

            self.new_file_size = int(response.headers.get('content-length', 1))
            if self.new_file_size < 1024 // (16*self.threads):
                raise LowSizeError('Peso muy pequeño')
            peso_formateado = format_size(self.new_file_size)
            self.text_newd_size.change_text(f'{peso_formateado[1]:.2f}{self.nomenclaturas[peso_formateado[0]]}')

            if a := response.headers.get('content-disposition', False):
                self.new_filename = a.split('filename=')[1].replace('"', '')
                self.text_newd_filename.change_text(a.split('filename=')[1].replace('"', ''))

            self.text_newd_status.change_text(self.txts['estado']+': '+self.txts['disponible'])

            self.can_add_new_download = True

            return
        except requests.URLRequired:
            return
        except (requests.exceptions.InvalidSchema,requests.exceptions.MissingSchema):
            self.text_newd_status.change_text(self.txts['descripcion-state[url invalida]'])
            return
        except (requests.exceptions.ConnectTimeout,requests.exceptions.ReadTimeout):
            self.text_newd_status.change_text(self.txts['descripcion-state[tiempo agotado]'])
            return
        except requests.exceptions.ConnectionError as err:
            self.text_newd_status.change_text(self.txts['descripcion-state[error internet]'])
            return
        except TrajoHTML:
            self.text_newd_status.change_text(self.txts['descripcion-state[trajo un html]'])
            print(response.content)
            return
        except Exception as err:
            print(err)
            print(type(err))
            print(response.headers)
            self.text_newd_status.change_text('Error')
            return

    def screen_configs(self):
        if self.screen_configs_bool:
            self.cicle_try = 0
        while self.screen_configs_bool:
            mx, my = pag.mouse.get_pos()

            eventos = pag.event.get()
            for evento in eventos:
                if evento.type == QUIT:
                    pag.quit()
                    sys.exit()
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx, my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.screen_configs_bool = False
                        self.screen_main_bool = True
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_config:
                        if x.click((mx, my)):
                            break

            self.ventana.fill((20, 20, 20))
            for x in self.list_to_draw_config:
                if isinstance(x, Create_boton):
                    x.draw(self.ventana, (mx, my))
                else:
                    x.draw(self.ventana)

            self.GUI_manager.draw(self.ventana, (mx, my))

            pag.display.flip()
            self.relog.tick(60)

    def screen_new_download(self):
        """La funcion para dibujar los textos y botones de la ventana de agregar una nueva descarga"""
        self.ventana.fill((20, 20, 20))
        for x in self.list_to_draw:
            if isinstance(x, Create_boton):
                x.draw(self.ventana, (-500, -500))
            else:
                x.draw(self.ventana)

        self.input_newd_url.clear()
        self.text_newd_filename.change_text(self.txts['nombre']+': ----------')
        self.text_newd_size.change_text(self.txts['tamaño']+': -------')
        self.text_newd_status.change_text(self.txts['descripcion-state[esperando]'])
        self.text_newd_file_type.change_text(self.txts['tipo']+': -------')

        self.screen_new_download_bool = True
        while self.screen_new_download_bool:
            mx, my = pag.mouse.get_pos()

            eventos = pag.event.get()

            for x in self.list_inputs_newd:
                if isinstance(x, Input_text):
                    x.eventos_teclado(eventos)
            for evento in eventos:
                if evento.type == QUIT:
                    pag.quit()
                    sys.exit()
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.func_newd_close()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_newd:
                        if x.click((mx, my)):
                            break

            pag.draw.rect(self.ventana, (50, 50, 50), self.new_download_rect, 0, 20)

            for x in self.list_to_draw_new_download:
                if isinstance(x, Create_boton):
                    x.draw(self.ventana, (mx, my))
                else:
                    x.draw(self.ventana)

            pag.display.flip()
            self.relog.tick(60)

    def main_cycle(self) -> None:
        if self.screen_main_bool:
            self.cicle_try = 0

        while self.screen_main_bool:
            self.relog.tick(60)

            mx, my = pag.mouse.get_pos()

            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)

            for evento in eventos:
                if evento.type == QUIT:
                    pag.quit()
                    sys.exit()
                elif evento.type in [WINDOWMINIMIZED]:
                    self.drawing = False
                elif evento.type in [WINDOWMAXIMIZED, WINDOWFOCUSGAINED, WINDOWTAKEFOCUS]:
                    self.drawing = True
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx, my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        pag.quit()
                        sys.exit()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if self.Mini_GUI_manager.click(evento.pos):
                        continue
                    elif self.lista_descargas.rect.collidepoint((mx, my)):
                        self.lista_descargas.click((mx, my))
                    for x in self.list_to_click:
                        if x.click((mx, my)):
                            break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 3:
                    for x in self.list_to_click:
                        x.click((mx, my))
                        break
                    if self.Mini_GUI_manager.click(evento.pos):
                        break
                    elif self.lista_descargas.rect.collidepoint((mx, my)):
                        self.lista_descargas.click((mx, my))
                    if (self.lista_descargas.rect.collidepoint((mx, my)) and
                            (result := self.lista_descargas.click((mx, my)))):
                        self.Mini_GUI_manager.add(mini_GUI.select((mx, my),
                                                                  [self.txts['descargar'] if result['result'][-2] != 'Completado' else self.txts['redescargar'], self.txts['eliminar'],
                                                                   self.txts['actualizar_url'], 'get url'],
                                                                  captured=result),
                                                  self.func_select_box)

            if not self.drawing:
                continue
            self.ventana.fill((20, 20, 20))

            for x in self.list_to_draw:
                if isinstance(x, Create_boton):
                    x.draw(self.ventana, (mx,my))
                else:
                    x.draw(self.ventana)

            self.GUI_manager.draw(self.ventana, (mx, my))
            self.Mini_GUI_manager.draw(self.ventana, (mx, my))


            pag.display.flip()

    def screen_extras(self):
        if self.screen_extras_bool:
            self.cicle_try = 0
        self.ventana.fill((20, 20, 20))
        for x in self.list_to_draw_extras:
            if isinstance(x, Create_boton):
                x.draw(self.ventana, (-500,-500))
            else:
                x.draw(self.ventana)
        while self.screen_extras_bool:
            mx, my = pag.mouse.get_pos()
            eventos = pag.event.get()

            for evento in eventos:
                if evento.type == QUIT:
                    pag.quit()
                    sys.exit()
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.screen_extras_bool = False
                        self.screen_main_bool = True
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_extras:
                        if x.click((mx, my)):
                            break
                elif evento.type == MOUSEMOTION:
                    for x in self.list_to_draw_extras:
                        if isinstance(x, Create_boton):
                            x.draw(self.ventana, (mx, my))

                    pag.display.flip()
            self.relog.tick(60)


if __name__ == '__main__':
    clase = DownloadManager(sys.argv[1] if len(sys.argv) > 1 else False)
