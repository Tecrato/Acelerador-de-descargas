import pygame as pag
import sys
import os
import time
import requests
import json
import subprocess
import shutil


from platformdirs import user_downloads_dir, user_cache_path, user_config_path, user_downloads_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter.simpledialog import askstring
from pygame.constants import (MOUSEBUTTONDOWN, K_ESCAPE, QUIT, KEYDOWN, MOUSEWHEEL, MOUSEMOTION,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)

from Utilidades_pygame import Text, Button, Barra_de_progreso, GUI, mini_GUI, Input, Select_box
from Utilidades import multithread
from Utilidades import win32_tools
from Utilidades import format_date
from Utilidades import format_size_bits_to_bytes, UNIDADES_BYTES, Deltatime, format_size_bits_to_bytes_str

from textos import idiomas
from my_warnings import *

from constants import DICT_CONFIG_DEFAULT, FONT_MONONOKI


class Downloader:
    def __init__(self, id, modificador=0) -> None:
        pag.init()
        
        self.ventana = pag.display.set_mode((700, 300))
        self.ventana_rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))

        self.display = pag.Surface(self.ventana_rect.size)
        self.display_rect = pag.Surface(self.ventana_rect.size)
        self.display.fill((254, 1, 1))
        self.display.set_colorkey((254, 1, 1))

        self.surf_GUI = pag.Surface(self.ventana_rect.size)
        self.surf_GUI.fill((254, 1, 1))
        self.surf_GUI.set_colorkey((254, 1, 1))

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

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')
        pag.display.set_caption(f'Downloader {self.id}_{self.file_name}')

        self.division = self.peso_total // self.num_hilos
        self.peso_total_formateado = format_size_bits_to_bytes(self.peso_total)

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
        self.speed_deltatime = Deltatime(15,10)
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
        
        self.default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            }

        self.carpeta_cache: Path = self.carpeta_cache.joinpath(f'./{self.id}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

        self.hilos_listos = 0
        self.lista_status_hilos: list[dict] = []
        self.lista_status_hilos_text: list[Text] = []
        self.lista_status_hilos_porcentaje: list[Text] = []
        self.surface_hilos = pag.Surface((self.ventana_rect.w // 2, self.ventana_rect.h - 70))
        self.surface_hilos.fill((254, 1, 1))
        self.surface_hilos.set_colorkey((254, 1, 1))
        self.surf_h_diff = 0
        self.surf_h_max = 1

        self.peso_descargado = 0
        self.peso_descargado_vel = 0

        self.prepared_request = requests.Request('GET', 'https://www.google.com').prepare()
        self.prepared_session = requests.Session()

        self.idioma = 'español'
        self.txts = idiomas[self.idioma]

        self.cargar_configs()
        self.generate_objects()
        if self.enfoques:
            win32_tools.front2(pag.display.get_wm_info()['window'])
        self.Func_pool.start('descargar')

        self.ciclo_general = [self.main_cycle]
        self.cicle_try = 0

        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

    def generate_objects(self) -> None:
        # Cosas varias
        self.GUI_manager = GUI.GUI_admin()
        self.mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)
        self.Func_pool = multithread.Funcs_pool()

        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)
        ]

        # ------------------------------------------- Textos y botones -----------------------------------

        self.Titulo = Text((self.file_name if len(self.file_name) < 36 else (self.file_name[:38] + '...')), 14, FONT_MONONOKI, (10, 50), 'left')
        self.text_tamaño = Text(self.txts['descripcion-peso'].format(
            f'{self.peso_total_formateado[1]:.2f}{UNIDADES_BYTES[self.peso_total_formateado[0]]}'), 12,
            FONT_MONONOKI, (10, 70), 'left')
        self.text_url = Text(f'url: {(self.url if len(self.url) < 37 else (self.url[:39] + "..."))}', 12,
                                    FONT_MONONOKI, (10, 90), 'left')
        self.text_num_hilos = Text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12,
                                          FONT_MONONOKI, (10, 110), 'left')
        self.text_estado_general = Text(self.txts['descripcion-state[esperando]'], 12, FONT_MONONOKI,
                                               (10, 130), 'left')

        self.text_peso_progreso = Text('0b', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 10),
                                              'topleft', padding=(20,10), color_rect=(20, 20, 20))
        self.text_vel_descarga = Text(self.txts['velocidad'] + ': ' + '0kb/s', 14, FONT_MONONOKI,
                                             (10, self.ventana_rect.centery + 34),
                                             'topleft', padding=(20,10))
        self.text_tiempo_restante = Text(self.txts['tiempo restante'] + ': 0Seg', 14, FONT_MONONOKI,
                                             (10, self.ventana_rect.centery + 58),
                                             'topleft', padding=(20,10))

        self.text_porcentaje = Text('0.00%', 14, FONT_MONONOKI, (175, self.ventana_rect.bottom - 50),
                                           'center', padding=(300, 5))

        self.text_title_hilos = Text(self.txts['title_hilos'], 14, FONT_MONONOKI, (550, 30), 'center')

        self.btn_cancelar_descarga = Button(self.txts['cancelar'], 16, FONT_MONONOKI, ((700 / 2) / 3, 20),
                                                  (20, 10), 'center', 'black',
                                                  'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda:
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'],
                             'Desea cerrar la ventana de descarga?\n\nLa descarga se podrá reanudar luego.',
                             (400, 200)),
                self.func_cancelar
            ))

        self.btn_pausar_y_reanudar_descarga = Button(self.txts['reanudar'], 16, FONT_MONONOKI,
                                                           (((700 / 2) / 3) * 2, 20), (20, 10), 'center', 'black',
                                                           'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                           func=self.func_reanudar)

        self.btn_more_options = Button('', 16, FONT_MONONOKI, ((700/2)-1, 20), 10, 'right', 'white',
                                             (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                             func=self.func_select_of_options)

        #   Barra de progreso
        self.barra_progreso = Barra_de_progreso((20, self.ventana_rect.bottom - 30), (310, 20), 'horizontal')
        self.barra_progreso.volumen = .0

        self.list_to_draw = [self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
                             self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
                             self.text_title_hilos, self.text_vel_descarga,self.text_peso_progreso,
                             self.text_tiempo_restante, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]
        self.list_to_click = [self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]

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

    def func_pausar(self) -> None:
        self.paused = True
        self.last_change = time.time()
        self.downloading = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["pausado"]}'
        self.actualizar_porcentaje_db()
        self.draw_main()

    def func_cancelar(self, result) -> None:
        if result == 'cancelar':
            return
        self.paused = False
        self.canceled = True
        self.actualizar_porcentaje_db()
        self.cerrar_todo('aceptar')

    def func_abrir_carpeta_antes_de_salir(self, resultado):
        if resultado == 'aceptar':
            if not self.fallo_destino:
                file = Path(self.save_dir)/self.file_name
            else:
                file = user_downloads_path()/self.file_name
            subprocess.call(['explorer','/select,{}'.format(file.as_uri())], shell = True)
        self.cerrar_todo('a')

    def cerrar_todo(self, result):
        if result == 'cancelar':
            return
        self.actualizar_porcentaje_db()
        self.paused = False
        self.canceled = True
        self.pool_hilos.shutdown(False)
        pag.quit()
        if self.finished:
            self.returncode = 1
        else:
            self.returncode = 0
        sys.exit(self.returncode)

    def func_reanudar(self) -> None:
        if not self.can_download: return
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['pausado']}"
        self.start_download()
        self.draw_main()

    def func_select_of_options(self):
        texto1 = self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No')
        texto2 = self.txts['ejecutar-al-finalizar'] + ': ' + (self.txts['si'] if self.ejecutar_al_finalizar else 'No')
        texto3 = self.txts['limitar-velocidad'] + ': ' + format_size_bits_to_bytes_str(self.velocidad_limite)
        self.mini_GUI_manager.add(mini_GUI.select(self.btn_more_options.rect.topright, [texto1,texto2, texto3]), self.func_select_box)

    def func_select_box(self, result):
        if result['index'] == 0:
            self.func_toggle_apagar()
        elif result['index'] == 1:
            self.func_toggle_ejecutar()
        elif result['index'] == 2:
            respuesta = askstring('Velocidad limite', 'Ingrese la velocidad limite en kb/s')
            if not respuesta:
                return
            try:
                self.velocidad_limite = int(respuesta) * 1024
            except:
                self.GUI_manager.add(
                    GUI.Info(self.ventana_rect.center, 'Error', 'Numero invalido'),
                )

    def func_toggle_apagar(self):
        self.apagar_al_finalizar = not self.apagar_al_finalizar
        if self.apagar_al_finalizar:
            self.ejecutar_al_finalizar = False
    def func_toggle_ejecutar(self):
        self.ejecutar_al_finalizar = not self.ejecutar_al_finalizar
        if self.ejecutar_al_finalizar:
            self.apagar_al_finalizar = False

    def formatear_tiempo_restante(self,bytes):
        if (t := bytes) > 0:
            delta_date = format_date((self.peso_total-self.peso_descargado)/t,3)
            if delta_date['year']>0:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}: {delta_date['year']}{self.txts['año']}s {delta_date['day']}{self.txts['dia']}s"
            elif delta_date['day']>0:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}: {delta_date['day']}{self.txts['dia']}s {delta_date['hour']}{self.txts['hora']}s"
            elif delta_date['hour']>0:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}: {delta_date['hour']}{self.txts['hora']}s {delta_date['min']}{self.txts['minuto']}s"
            elif delta_date['min']>0:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}: {delta_date['min']}{self.txts['minuto']}s {delta_date['seg']}{self.txts['segundo']}s"
            elif delta_date['seg']>5:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}:{delta_date['seg']}{self.txts['segundo']}s ~"
            else:
                self.text_tiempo_restante.text = f"{self.txts['tiempo restante']}: {self.txts['casi termina']}..."
        else:
            delta_date = format_date(0,2)
            self.text_tiempo_restante.text = self.txts['tiempo restante'] + f": {self.txts['calculando']}..."

    def crear_conexion(self):
        self.can_download = False
        self.downloading = False
        self.text_estado_general.text = self.txts['descripcion-state[conectando]']
        try:
            response = self.prepared_session.get(self.url, stream=True, allow_redirects=True, timeout=30, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'})


            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            if tipo != self.type:
                print(response.headers)
                raise DifferentTypeError(f'No es el tipo de archivo {tipo}')

            peso = int(response.headers.get('content-length', 0))
            if peso < self.chunk * self.num_hilos or peso != self.peso_total:
                raise LowSizeError('Peso muy pequeño')

            self.intentos = 0
            self.can_download = True
            self.last_change = time.time()
            if 'bytes' not in response.headers.get('Accept-Ranges', ''):
                self.can_reanudar = False
                try:
                    os.remove(self.carpeta_cache.joinpath(f'./parte0.tmp'))
                except:
                    pass
                self.GUI_manager.add(
                    GUI.Info(self.ventana_rect.center, 'Error',
                                 'La descarga no se puede reanudar\n\nEl link no permite reanudar la descarga\n\nDescargando archivo desde el inicio.'),
                )

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            if self.modificador == 2:
                self.intentos += 1
                if self.intentos > 10:
                    self.cerrar_todo('a')
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, 'Error',
                             'El servidor no responde\n\nDesea volver a intentarlo?'),
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
            )
        except (requests.exceptions.MissingSchema, DifferentTypeError, LowSizeError) as err:
            print(type(err))
            print(err)
            self.GUI_manager.add(
                GUI.Info(self.ventana_rect.center, 'Error',
                         self.txts['gui-url no sirve']),
                self.cerrar_todo
            )
        except Exception as err:
            print(type(err))
            print(err)
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, 'Error', self.txts['gui-error inesperado'], (400, 200)),
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
            )

    def actualizar_porcentaje_db(self):
        if self.peso_descargado == 0:
            return
        progreso = (self.peso_descargado / self.peso_total)
        requests.get(f'http://127.0.0.1:5000/descargas/update/estado/{self.id}/{f'{progreso * 100:.2f}%' if float(progreso) != 1.0 else 'Completado'}')

    def start_download(self) -> None:
        if not self.can_download:
            return
        if self.downloading:
            return
        self.paused = False
        self.canceled = False
        self.hilos_listos = 0
        self.peso_descargado = 0
        self.can_download = False

        self.lista_status_hilos.clear()
        self.lista_status_hilos_text.clear()
        self.lista_status_hilos_porcentaje.clear()
        self.pool_hilos.shutdown(True, cancel_futures=True)
        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')
        for x in range(self.num_hilos):
            self.lista_status_hilos_text.append(
                Text(self.txts['status_hilo[iniciando]'].format(x), 12, FONT_MONONOKI, (50, (30 * x) + 5),
                            'left', with_rect=True, color_rect=(20, 20, 20))
            )
            self.lista_status_hilos_porcentaje.append(
                Text('0%', 12, FONT_MONONOKI, (self.surface_hilos.get_width(), (30 * x) + 5),
                            'right', with_rect=True, color_rect=(20, 20, 20))
            )
            if x == self.num_hilos - 1:
                self.surf_h_max = self.lista_status_hilos_text[-1].rect.bottom

            self.lista_status_hilos.append({
                'status':0,
                'num':x,
                'start':self.division * x,
                'end':(self.division*x + self.division-1 if x < self.num_hilos - 1 else self.peso_total - 1),
                'local_count':0,
                'tiempo_reset':2,
                'time_chunk': 0,
                'actual_chunk_to_limit': 0
                })
            self.pool_hilos.submit(self.init_download_thread,x)
        self.last_change = time.time()
        self.downloading = True
        self.can_download = True

        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['descargando']}"
        self.draw_main()

    def init_download_thread(self,num):
        while self.lista_status_hilos[num]['status'] == 0:
            self.peso_descargado -= self.lista_status_hilos[num]['local_count']
            self.download_thread(num)

    def download_thread(self, num):
        tiempo_reset = self.lista_status_hilos[num]['tiempo_reset']
        if self.canceled:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
            self.lista_status_hilos[num]['status'] = 2
            return
        self.lista_status_hilos_text[num].text = self.txts['status_hilo[iniciando]'].format(num)
        if Path(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).is_file() and self.can_reanudar:
            self.lista_status_hilos[num]['local_count'] = os.stat(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).st_size
            self.peso_descargado += self.lista_status_hilos[num]['local_count']
            if self.lista_status_hilos[num]['local_count'] >= self.lista_status_hilos[num]['end'] - self.lista_status_hilos[num]['start']:
                self.hilos_listos += 1
                self.lista_status_hilos_text[num].text = self.txts['status_hilo[finalizado]'].format(num)
                self.lista_status_hilos[num]['status'] = 1
                return 0
        else:
            self.lista_status_hilos[num]['local_count'] = 0
        if not self.can_reanudar:
            try:
                os.remove(self.carpeta_cache.joinpath(f'./parte{num}.tmp'))
            except:
                pass
        if self.paused:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[pausado]'].format(num)
            while self.paused:
                time.sleep(.1)
        if self.can_reanudar:
            self.default_headers['Range'] = f'bytes={self.lista_status_hilos[num]["start"] + self.lista_status_hilos[num]["local_count"]}-{self.lista_status_hilos[num]["end"]}'
        else:
            self.default_headers.pop('Range')
        try:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[conectando]'].format(num)
            
            response = self.prepared_session.get(self.url, stream=True, allow_redirects=True, timeout=15, headers=headers)

            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('ay')

            tiempo_reset = 2
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[descargando]'].format(num)

            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'ab') as file_p:
                self.downloading_threads += 1
                for data in response.iter_content(self.chunk):
                    if self.paused or self.canceled:
                        raise Exception('')
                    if not data:
                        continue
                    tanto = len(data)
                    self.lista_status_hilos[num]['local_count'] += tanto
                    self.peso_descargado_vel += tanto
                    self.peso_descargado += tanto
                    file_p.write(data)

                    if self.velocidad_limite <= 0:
                        continue

                    self.lista_status_hilos[num]['actual_chunk_to_limit'] += tanto
                    actual_time = time.perf_counter()
                    if self.lista_status_hilos[num]['actual_chunk_to_limit'] > self.velocidad_limite/self.downloading_threads:
                        time.sleep(self.lista_status_hilos[num]['actual_chunk_to_limit'] / (self.velocidad_limite/self.downloading_threads))
                        self.lista_status_hilos[num]['actual_chunk_to_limit'] = 0
                        self.lista_status_hilos[num]['time_chunk'] = actual_time
                    elif actual_time - self.lista_status_hilos[num]['time_chunk'] > 1:
                        self.lista_status_hilos[num]['time_chunk'] = actual_time
                        self.lista_status_hilos[num]['actual_chunk_to_limit'] = 0

            # codigo para comprobar que la parte pese lo mismo que el tamaño que se le asigno, sino borra lo descargado y vulve a empezar
            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'rb') as file_p:
                if self.lista_status_hilos[num]['local_count'] != os.stat(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).st_size and self.lista_status_hilos[num]['local_count'] != self.lista_status_hilos[num]['end']-self.lista_status_hilos[num]['start']+1:
                    os.remove(self.carpeta_cache.joinpath(f'./parte{num}.tmp'))
                    print(f'hilo {num} descargado de nuevo')
                    raise DifferentSizeError('ay')

            print(f'parte {num} finalizado')
            self.lista_status_hilos[num]['status'] = 1
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[finalizado]'].format(num)
            self.hilos_listos += 1
            self.downloading_threads -= 1
            return
        except (Exception, LowSizeError) as err:
            print(err)
            print(type(err))

            self.downloading_threads -= 1
            if self.canceled:
                self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
                self.lista_status_hilos[num]['status'] = 2
                return
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time() - t < tiempo_reset:
                if self.canceled:
                    break
                time.sleep(.1)
            if self.canceled:
                self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
                self.lista_status_hilos[num]['status'] = 2
                return
            self.lista_status_hilos[num]['tiempo_reset'] = (tiempo_reset + 1) if tiempo_reset <= 15 else tiempo_reset
            return

    def finish_download(self):
        self.downloading = False

        try:
            file = open(self.save_dir + '/' + self.file_name, 'wb')
        except:
            file = open(user_downloads_dir() + '/' + self.file_name, 'wb')
            self.fallo_destino = True

        for x in range(self.num_hilos):
            with open(self.carpeta_cache.joinpath(f'./parte{x}.tmp'), 'rb') as parte:
                file.write(parte.read())
            os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
        file.close()
        shutil.rmtree(self.carpeta_cache, True)

        self.pool_hilos.shutdown(False,cancel_futures=True)

        self.actualizar_porcentaje_db()

        self.can_download = True
        self.drawing = True
        self.finished = True
        self.hilos_listos = 0
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["finalizado"]}'
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar


        if self.cerrar_al_finalizar or requests.get(f'http://127.0.0.1:5000/descargas/check/{self.id}').json()['cola'] == True:
            self.cerrar_todo('aceptar')
        elif self.apagar_al_finalizar:
            subprocess.call(f'shutdown /s /t 30 Descarga finalizada - {self.file_name}', shell=True)
            self.cerrar_todo('aceptar')
            return
        elif self.ejecutar_al_finalizar:
            self.actualizar_porcentaje_db()
            pag.quit()
            os.startfile(self.save_dir + '/' + self.file_name)
            self.returncode = 1
            sys.exit(self.returncode)

        self.GUI_manager.add(
            GUI.Desicion(self.ventana_rect.center, self.txts['enhorabuena'], self.txts['gui-desea_abrir_la_carpeta'], (400, 200)),
            self.func_abrir_carpeta_antes_de_salir
        )
        if self.enfoques:
            win32_tools.front2(pag.display.get_wm_info()['window'])

    def draw_main(self):
        self.display.fill((20, 20, 20))

        for x in self.list_to_draw:
            if isinstance(x, Button):
                x.draw(self.display, (-500, -500))
            else:
                x.draw(self.display)

        for x in self.lineas_para_separar:
            pag.draw.line(self.display, 'black', x[0], x[1], width=3)

    def draw_objs(self, lista: list[Text|Button|Input|Select_box]):
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

    def main_cycle(self) -> None:
        if self.screen_main:
            self.cicle_try: int = 0

        # self.draw_main()
        while self.screen_main:
            self.relog.tick(60)
            mx, my = pag.mouse.get_pos()


            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)


            for evento in eventos:
                if evento.type == QUIT:
                    self.cerrar_todo('a')
                elif evento.type == WINDOWMINIMIZED:
                    self.drawing = False
                elif evento.type in [WINDOWTAKEFOCUS, WINDOWFOCUSGAINED, WINDOWMAXIMIZED]:
                    self.drawing = True
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx, my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.GUI_manager.add(
                            GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'],
                                        'Desea cerrar la ventana de descarga?\n\nLa descarga se podrá reanudar luego.',
                                        (400, 200)),
                            self.cerrar_todo
                        )
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if self.mini_GUI_manager.click(evento.pos):
                        continue
                    for x in self.list_to_click:
                        x.click((mx, my))
                elif evento.type == MOUSEWHEEL and mx > self.ventana_rect.centerx:
                    if -self.surf_h_max + 200 < self.surf_h_diff + evento.y * 20 < 5:
                        self.surf_h_diff += evento.y * 20
                        for x in self.lista_status_hilos_text:
                            x.pos += (0, evento.y * 20)
                        for x in self.lista_status_hilos_porcentaje:
                            x.pos += (0, evento.y * 20)
                elif evento.type == MOUSEMOTION:
                    for x in self.list_to_draw:
                        if isinstance(x, Button):
                            x.draw(self.display, (mx, my))

            if self.hilos_listos == self.num_hilos:
                self.finish_download()
                
            if time.time() - self.speed_deltatime.last_time > 1/15:
                self.speed_deltatime.update()
                vel = self.peso_descargado_vel * self.speed_deltatime.dt * 10
                self.peso_descargado_vel = 0

                self.list_vels.append(vel)
                if len(self.list_vels) > 60:
                    self.list_vels.pop(0)

                
                self.current_velocity = (sum(self.list_vels)/len(self.list_vels)) if self.list_vels else 0

                if self.velocidad_limite > 0 and self.current_velocity > self.velocidad_limite:
                    self.current_velocity = self.velocidad_limite

                vel_format = format_size_bits_to_bytes(self.current_velocity)
                vel_text = f'{vel_format[1]:.2f}{UNIDADES_BYTES[vel_format[0]]}/s'
                self.text_vel_descarga.text = self.txts['velocidad']+': '+vel_text


                if self.current_velocity > 0:
                    self.last_change = time.time()
                elif time.time() - self.last_change > 300 and self.downloading and self.detener_5min:
                    self.func_pausar()
                    self.GUI_manager.add(
                        GUI.Desicion(self.ventana_rect.center, 'Error',
                                    'El servidor no responde\n\nDesea volver a intentarlo?'),
                        lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
                    )

            if time.time() - self.last_tiempo_restante_update > 1:
                self.last_tiempo_restante_update = time.time()
                self.formatear_tiempo_restante(self.current_velocity)
            

            if self.peso_total > 0:
                progreso = (self.peso_descargado / self.peso_total)
                self.text_porcentaje.text = f'{progreso * 100:.2f}%'
                descargado = format_size_bits_to_bytes(self.peso_descargado)
                descargado_text = f'{descargado[1]:.2f}{UNIDADES_BYTES[descargado[0]]}'
                self.text_peso_progreso.text = self.txts['descargado']+': '+descargado_text
                self.barra_progreso.volumen = progreso
            
            if time.time()-self.db_update > 10:
                self.actualizar_porcentaje_db()
                self.db_update = time.time()
                
            if not self.drawing:
                continue

            for x in self.list_to_draw:
                x.redraw = 2

            pag.draw.rect(self.display, (20,20,20), [0, self.ventana_rect.centery+1, (self.ventana_rect.w/2)-1, self.ventana_rect.h/2])
            self.text_peso_progreso.draw(self.display)
            self.barra_progreso.draw(self.display)
            self.text_porcentaje.draw(self.display)
            self.text_vel_descarga.draw(self.display)
            self.text_tiempo_restante.draw(self.display)
            self.ventana.blit(self.display, (0, 0))

            self.surface_hilos.fill((254, 1, 1))

            if not self.low_detail_mode:
                for i,x in enumerate(self.lista_status_hilos_porcentaje):
                    x.text = f'{int(self.lista_status_hilos[i]['local_count'])/self.division * 100:.2f}%'
                    x.redraw = 2
                    x.draw(self.surface_hilos)

            for x in self.lista_status_hilos_text:
                x.redraw = 2
                x.draw(self.surface_hilos)
            self.ventana.blit(self.surface_hilos, (self.ventana_rect.centerx, 50))

            self.surf_GUI.fill((254, 1, 1))
            self.GUI_manager.draw(self.surf_GUI, (mx, my))
            self.mini_GUI_manager.draw(self.surf_GUI, (mx, my))
            self.ventana.blit(self.surf_GUI, (0, 0))

            pag.display.flip()


if __name__ == '__main__' and len(sys.argv) > 1:
    clase = Downloader(*sys.argv[1:])
