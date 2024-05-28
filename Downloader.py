import pygame as pag, sys, os, time, requests, json, sqlite3, subprocess, shutil

from platformdirs import user_downloads_dir, user_cache_path, user_config_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from numpy import mean
from urllib.parse import urlparse
from pygame.constants import (MOUSEBUTTONDOWN, K_ESCAPE, QUIT, KEYDOWN, MOUSEWHEEL, MOUSEMOTION,
                              WINDOWMINIMIZED, WINDOWFOCUSGAINED, WINDOWMAXIMIZED, WINDOWTAKEFOCUS, WINDOWFOCUSLOST)

import Utilidades

from Utilidades import Create_text, Create_boton, Barra_de_progreso, get_mediafire_url
from Utilidades import GUI, mini_GUI
from Utilidades import multithread
from Utilidades import win32_tools
from Utilidades import format_date

from textos import idiomas
from my_warnings import *

pag.init()

def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


class Downloader:
    def __init__(self, id, modificador=0) -> None:

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

        self.Database: sqlite3.Connection = sqlite3.Connection(self.carpeta_config.joinpath('./downloads.sqlite3'))
        self.DB_cursor = self.Database.cursor()
        self.DB_cursor.execute('SELECT * FROM descargas WHERE id=?', [id])
        self.raw_data = self.DB_cursor.fetchone()

        self.id: int = self.raw_data[0]
        self.file_name: str = self.raw_data[1]
        self.type: str = self.raw_data[2]
        self.peso_total: int = self.raw_data[3]
        self.url: str = self.raw_data[4]
        self.num_hilos: int = self.raw_data[5]
        self.tiempo: float = float(self.raw_data[6])
        self.estado: str = self.raw_data[7]
        self.modificador = int(modificador)

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')
        pag.display.set_caption(f'Downloader {self.id}_{self.file_name}')

        self.division = self.peso_total // self.num_hilos
        self.peso_total_formateado = format_size(self.peso_total)
        self.reanudar_bool = False if self.estado == 'en espera' else True

        self.paused = True
        self.canceled = False
        self.screen_main = True
        self.can_download = False
        self.downloading = False
        self.apagar_al_finalizar = False
        self.ejecutar_al_finalizar = False if self.modificador != 1 else True
        self.cerrar_al_finalizar = False if self.modificador != 2 else True
        self.drawing = True
        self.finished = False
        self.detener_5min = True
        self.last_time = 0.0
        self.last_peso = 0.0
        self.last_vel = 0.0
        self.last_change = time.time()
        self.framerate = 60
        self.intentos = 0
        self.divisor = 6
        self.list_vels: list[dict[str|int]] = []
        self.save_dir = user_downloads_dir()
        self.relog = pag.time.Clock()

        self.carpeta_cache: Path = self.carpeta_cache.joinpath(f'./{self.id}_{"".join(self.file_name.split(".")[:-1])}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

        self.hilos_listos = 0
        self.lista_status_hilos: list[dict] = []
        self.lista_status_hilos_text: list[Create_text] = []
        self.surface_hilos = pag.Surface((self.ventana_rect.w // 2, self.ventana_rect.h - 70))
        self.surface_hilos.fill((254, 1, 1))
        self.surface_hilos.set_colorkey((254, 1, 1))
        self.surf_h_diff = 0
        self.surf_h_max = 1

        self.peso_descargado = 0

        self.nomenclaturas = {
            0: 'bytes',
            1: 'Kb',
            2: 'Mb',
            3: 'Gb',
            4: 'Tb'
        }

        self.prepared_request = requests.Request('GET', 'https://www.google.com').prepare()
        self.prepared_session = requests.session()

        self.idioma = 'español'
        self.txts = idiomas[self.idioma]
        self.font_mononoki = 'C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        self.font_simbols = 'C:/Users/Edouard/Documents/fuentes/Symbols.ttf'
        # self.font_mononoki = './Assets/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        # self.font_simbols = './Assets/fuentes/Symbols.ttf'

        self.cargar_configs()
        self.generate_objects()
        self.Func_pool.start('descargar')

        self.ciclo_general = [self.main_cycle]
        self.cicle_try = 0

        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

    def generate_objects(self) -> None:
        # Cosas varias
        Utilidades.GUI.configs['fuente_simbolos'] = self.font_simbols
        self.GUI_manager = GUI.GUI_admin()
        self.mini_GUI_manager = mini_GUI.mini_GUI_admin(self.ventana_rect)
        self.Func_pool = multithread.Funcs_pool()

        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)]

        # ------------------------------------------- Textos y botones -----------------------------------

        self.Titulo = Create_text((self.file_name if len(self.file_name) < 36 else (self.file_name[:38] + '...')), 14, self.font_mononoki, (10, 50), 'left')
        self.text_tamaño = Create_text(self.txts['descripcion-peso'].format(
            f'{self.peso_total_formateado[1]:.2f}{self.nomenclaturas[self.peso_total_formateado[0]]}'), 12,
            self.font_mononoki, (10, 70), 'left')
        self.text_url = Create_text(f'url: {(self.url if len(self.url) < 37 else (self.url[:39] + "..."))}', 12,
                                    self.font_mononoki, (10, 90), 'left')
        self.text_num_hilos = Create_text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12,
                                          self.font_mononoki, (10, 110), 'left')
        self.text_estado_general = Create_text(self.txts['descripcion-state[esperando]'], 12, self.font_mononoki,
                                               (10, 130), 'left')

        self.text_peso_progreso = Create_text('0b', 14, self.font_mononoki, (10, self.ventana_rect.centery + 10),
                                              'topleft', padding=(20,10), color_rect=(20, 20, 20))
        self.text_vel_descarga = Create_text(self.txts['velocidad'] + ': ' + '0kb/s', 14, self.font_mononoki,
                                             (10, self.ventana_rect.centery + 34),
                                             'topleft', padding=(20,10))
        self.text_tiempo_restante = Create_text(self.txts['tiempo restante'] + ': 0Seg', 14, self.font_mononoki,
                                             (10, self.ventana_rect.centery + 58),
                                             'topleft', padding=(20,10))

        self.text_porcentaje = Create_text('0.00%', 14, self.font_mononoki, (175, self.ventana_rect.bottom - 50),
                                           'center', padding=(300, 5))

        self.text_title_hilos = Create_text(self.txts['title_hilos'], 14, self.font_mononoki, (550, 30), 'center')

        self.btn_cancelar_descarga = Create_boton(self.txts['cancelar'], 16, self.font_mononoki, ((700 / 2) / 3, 20),
                                                  (20, 10), 'center', 'black',
                                                  'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda:
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'],
                             'Desea cerrar la ventana de descarga?\n\nLa descarga se podrá reanudar luego.',
                             (400, 200)),
                self.func_cancelar
            ))

        self.btn_pausar_y_reanudar_descarga = Create_boton(self.txts['reanudar'], 16, self.font_mononoki,
                                                           (((700 / 2) / 3) * 2, 20), (20, 10), 'center', 'black',
                                                           'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1,
                                                           func=self.func_reanudar)

        self.btn_more_options = Create_boton('', 16, self.font_simbols, ((700/2)-1, 20), 10, 'right', 'white',
                                             (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                             func=self.func_select_of_options)

        #   Barra de progreso
        self.barra_progreso = Barra_de_progreso((20, self.ventana_rect.bottom - 30), (310, 20), 'horizontal')
        self.barra_progreso.set_volumen(.0)

        self.list_to_draw = [self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
                             self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
                             self.text_title_hilos, self.text_vel_descarga,self.text_peso_progreso,
                             self.text_tiempo_restante, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]
        self.list_to_click = [self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]

    def cargar_configs(self):

        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except:
            self.configs = {}
        self.idioma = self.configs.get('idioma', 'español')
        self.enfoques = self.configs.get('enfoques', True)
        self.detener_5min = self.configs.get('enfoques', True)
        self.txts = idiomas[self.idioma]

        self.save_dir = self.configs.get('save_dir',user_downloads_dir())

    def func_pausar(self) -> None:
        self.paused = True
        self.last_change = time.time()
        self.downloading = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.list_vels.clear()
        self.last_peso = self.peso_descargado
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
            os.startfile(self.save_dir)
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
            sys.exit(1)
        else:
            sys.exit(0)

    def func_reanudar(self) -> None:
        if not self.can_download: return 0
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.reanudar_bool = True
        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['pausado']}"
        self.start_download()
        self.draw_main()

    def func_select_of_options(self):
        texto1 = self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No')
        texto2 = self.txts['ejecutar-al-finalizar'] + ': ' + (self.txts['si'] if self.ejecutar_al_finalizar else 'No')
        self.mini_GUI_manager.add(mini_GUI.select(self.btn_more_options.rect.topright, [texto1,texto2]), self.func_select_box)

    def func_select_box(self, result):
        if result['index'] == 0:
            self.func_toggle_apagar()
        elif result['index'] == 1:
            self.func_toggle_ejecutar()


    def func_toggle_apagar(self):
        self.apagar_al_finalizar = not self.apagar_al_finalizar
        if self.apagar_al_finalizar:
            self.ejecutar_al_finalizar = False
    def func_toggle_ejecutar(self):
        self.ejecutar_al_finalizar = not self.ejecutar_al_finalizar
        if self.ejecutar_al_finalizar:
            self.apagar_al_finalizar = False

    def crear_conexion(self):
        self.can_download = False
        self.downloading = False
        self.text_estado_general.text = self.txts['descripcion-state[conectando]']
        try:
            parse = urlparse(self.url)

            if (parse.netloc == "www.mediafire.com" or parse.netloc == ".mediafire.com") and 'file' in parse.path:
                if os.path.exists(self.carpeta_cache.joinpath(f'./url cache.txt')):
                    with open(self.carpeta_cache.joinpath(f'./url cache.txt'), 'r+') as file:
                        url = file.read()
                else:
                    url = get_mediafire_url(self.url)
                    if not url: raise Exception('no cargo xD')
                    with open(self.carpeta_cache.joinpath(f'./url cache.txt'), 'w') as file:
                        file.write(url)
            else:
                url = self.url
            response = requests.get(url, stream=True, allow_redirects=True, timeout=15)

            if (parse.netloc == "www.mediafire.com" or parse.netloc == ".mediafire.com") and 'file' in parse.path and int(response.headers.get('Expires', 123123)) == 0:
                os.remove(self.carpeta_cache.joinpath(f'./url cache.txt'))
                print(response.headers)
                return self.crear_conexion()

            self.prepared_request = response.request

            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('No es el tipo de archivo')

            peso = int(response.headers.get('content-length', False))
            if peso < 1024 // (8*self.num_hilos) or peso != self.peso_total:
                raise LowSizeError('Peso muy pequeño')

            self.can_download = True
            self.last_change = time.time()
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            if self.modificador == 2:
                self.intentos += 1
                if self.intentos > 10:
                    pag.exit()
                    sys.exit(0)
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, 'Error',
                             'El servidor no responde\n\nDesea volver a intentarlo?'),
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
            )
        except (requests.exceptions.MissingSchema, DifferentTypeError, LowSizeError):
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
        self.estado = f'{progreso * 100:.2f}%' if float(progreso) != 1.0 else 'Completado'
        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?', [f'{progreso * 100:.2f}%', self.id])
        self.Database.commit()

    def start_download(self) -> None:
        if not self.can_download:
            return
        if self.downloading:
            return
        self.paused = False
        self.canceled = False
        self.hilos_listos = 0

        self.lista_status_hilos.clear()
        self.lista_status_hilos_text.clear()
        for x in range(self.num_hilos):
            if not self.reanudar_bool:
                try:
                    os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
                except:
                    pass

            self.lista_status_hilos_text.append(
                Create_text(self.txts['status_hilo[iniciando]'].format(x), 12, self.font_mononoki, (50, (30 * x) + 5),
                            'left', with_rect=True, color_rect=(20, 20, 20)))
            if x == self.num_hilos - 1:
                self.surf_h_max = self.lista_status_hilos_text[-1].rect.bottom

            self.lista_status_hilos.append({
                'status':0,
                'num':x,
                'start':self.division * x,
                'end':(self.division * x + self.division - 1 if x < self.num_hilos - 1 else self.peso_total - 1),
                'local_count':0,
                'tiempo_reset':2
                })
            self.pool_hilos.submit(self.init_download_thread,x)
        self.last_change = time.time()
        self.downloading = True

        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['descargando']}"
        self.draw_main()

    def init_download_thread(self,num):
        while self.lista_status_hilos[num]['status'] == 0:
            self.download_thread(**self.lista_status_hilos[num])

    def download_thread(self, num, start, end, local_count=0, tiempo_reset=2,status='relleno'):

        if self.paused:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[pausado]'].format(num)
            while self.paused:
                time.sleep(.5)
        if self.canceled:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
            self.lista_status_hilos[num]['status'] = 2
            return
        self.lista_status_hilos_text[num].text = self.txts['status_hilo[iniciando]'].format(num)
        if local_count == 0 and self.reanudar_bool and Path(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).is_file():
            local_count = os.stat(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).st_size
            self.peso_descargado += local_count
            if local_count >= end - start-1:
                self.hilos_listos += 1
                self.lista_status_hilos_text[num].text = self.txts['status_hilo[finalizado]'].format(num)
                self.lista_status_hilos[num]['status'] = 1
                return 0
        headers = {'Range': f'bytes={start + local_count}-{end}'}
        try:
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[conectando]'].format(num)
            re = self.prepared_request.copy()
            re.prepare_headers(headers)
            response = self.prepared_session.send(re, stream=True, allow_redirects=True, timeout=15)

            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('ay')

            peso = response.headers.get('content-length', False)
            if int(peso) < 1024 // 16:
                raise LowSizeError('Peso muy pequeño')

            tiempo_reset = 2
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[descargando]'].format(num)

            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'ab') as file_p:
                for data in response.iter_content(1024 // 16):
                    if self.paused or self.canceled:
                        raise Exception('')
                    if not data:
                        continue
                    if local_count + len(data) > end-start+1:
                        d = data[:(end-start)-local_count+1]
                        local_count += len(d)
                        self.peso_descargado += len(d)
                        file_p.write(d)
                        break
                    local_count += len(data)
                    self.peso_descargado += len(data)
                    file_p.write(data)

            self.lista_status_hilos[num]['status'] = 1
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[finalizado]'].format(num)
            self.hilos_listos += 1
            return
        except (Exception, LowSizeError) as err:
            # print(err)
            # print(type(err))

            if self.canceled:
                self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
                self.lista_status_hilos[num]['status'] = 2
                return
            self.lista_status_hilos_text[num].text = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time() - t < tiempo_reset:
                if self.canceled:
                    self.lista_status_hilos_text[num].text = self.txts['status_hilo[cancelado]'].format(num)
                    self.lista_status_hilos[num]['status'] = 2
                    return
                time.sleep(.3)
            self.lista_status_hilos[num]['local_count'] = local_count
            self.lista_status_hilos[num]['tiempo_reset'] = (tiempo_reset * 2) if tiempo_reset < 30 else tiempo_reset

    def finish_download(self):
        self.downloading = False

        with open(self.save_dir + '/' + self.file_name, 'wb') as file:
            for x in range(self.num_hilos):
                with open(self.carpeta_cache.joinpath(f'./parte{x}.tmp'), 'rb') as parte:
                    file.write(parte.read())
                os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
            file.close()
        shutil.rmtree(self.carpeta_cache, True)

        self.pool_hilos.shutdown(False,cancel_futures=True)

        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?', ['Completado', self.id])
        self.Database.commit()

        self.can_download = True
        self.drawing = True
        self.finished = True
        self.hilos_listos = 0
        self.list_vels.clear()
        self.last_peso = 0
        self.peso_descargado = 0
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["finalizado"]}'
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar

        if self.cerrar_al_finalizar:
            pag.quit()
            sys.exit(1)
        elif self.apagar_al_finalizar:
            subprocess.call('shutdown /s /t 10', shell=True)
            self.cerrar_todo('aceptar')
            return
        elif self.ejecutar_al_finalizar:
            self.actualizar_porcentaje_db()
            pag.quit()
            subprocess.run(self.save_dir + '/' + self.file_name, shell=True)
            sys.exit(0)
        self.GUI_manager.add(
            GUI.Desicion(self.ventana_rect.center, self.txts['enhorabuena'], self.txts['gui-desea_abrir_la_carpeta'], (400, 200)),
            self.func_abrir_carpeta_antes_de_salir
        )
        if self.enfoques:
            win32_tools.front2(pag.display.get_wm_info()['window'])

    def draw_main(self):
        self.display.fill((20, 20, 20))

        for x in self.list_to_draw:
            if isinstance(x, Create_boton):
                x.draw(self.display, (-500, -500))
            else:
                x.draw(self.display)

        for x in self.lineas_para_separar:
            pag.draw.line(self.display, 'black', x[0], x[1], width=3)

    def main_cycle(self) -> None:
        if self.screen_main:
            self.cicle_try: int = 0

        self.draw_main()
        while self.screen_main:
            self.relog.tick(self.framerate)
            mx, my = pag.mouse.get_pos()


            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)


            for evento in eventos:
                if evento.type == QUIT:
                    self.cerrar_todo('a')
                elif evento.type == WINDOWMINIMIZED:
                    self.drawing = False
                elif evento.type == WINDOWFOCUSLOST:
                    self.framerate = 30
                elif evento.type in [WINDOWTAKEFOCUS, WINDOWFOCUSGAINED, WINDOWMAXIMIZED]:
                    self.framerate = 60
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
                elif evento.type == MOUSEMOTION:
                    for x in self.list_to_draw:
                        if isinstance(x, Create_boton):
                            x.draw(self.display, (mx, my))

            if self.hilos_listos == self.num_hilos:
                self.finish_download()

            t = time.time() - self.last_time
            
            if t > 1/self.divisor:
                for i,x in sorted(enumerate(self.list_vels),reverse=True):
                    if time.time() - x['time'] > 10:
                        self.list_vels.pop(i)

                
                vel = (self.peso_descargado-self.last_peso)*(self.divisor)
                self.list_vels.append({'time':time.time(),'vel':vel})
                
                media = mean([x['vel'] for x in self.list_vels])
                if media > 0:
                    self.last_change = time.time()
                elif time.time() - self.last_change > 300 and self.downloading and self.detener_5min:
                    # self.func_cancelar('ies (osea yes)')
                    self.func_pausar()
                    self.GUI_manager.add(
                        GUI.Desicion(self.ventana_rect.center, 'Error',
                                    'El servidor no responde\n\nDesea volver a intentarlo?'),
                        lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
                    )

                vel_format = format_size(media)
                vel_text = f'{vel_format[1]:.2f}{self.nomenclaturas[vel_format[0]]}/s'
                self.text_vel_descarga.text = self.txts['velocidad']+': '+vel_text
                
                if (t := media) > 0:
                    delta_date = format_date((self.peso_total-self.peso_descargado)/int(t),3)
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
                    # self.text_tiempo_restante.text = self.txts['tiempo restante'] + f': {delta_date['hour']:02.0f}:{delta_date['min']:02.0f}:{delta_date['seg']:02.0f}seg'
                    self.text_tiempo_restante.text = self.txts['tiempo restante'] + f": {self.txts['calculando']}..."

                
                self.last_time = time.time()
                self.last_peso = self.peso_descargado
                

            if self.peso_total > 0:
                progreso = (self.peso_descargado / self.peso_total)
                self.text_porcentaje.text = f'{progreso * 100:.2f}%'
                descargado = format_size(self.peso_descargado)
                descargado_text = f'{descargado[1]:.2f}{self.nomenclaturas[descargado[0]]}'
                self.text_peso_progreso.text = self.txts['descargado']+': '+descargado_text
                self.barra_progreso.set_volumen(progreso)
                
            if not self.drawing:
                self.last_peso = self.peso_descargado
                continue

            pag.draw.rect(self.display, (20,20,20), [0, self.ventana_rect.centery+1, (self.ventana_rect.w/2)-1, self.ventana_rect.h/2])
            self.text_peso_progreso.draw(self.display)
            self.barra_progreso.draw(self.display)
            self.text_porcentaje.draw(self.display)
            self.text_vel_descarga.draw(self.display)
            self.text_tiempo_restante.draw(self.display)
            self.ventana.blit(self.display, (0, 0))

            self.surface_hilos.fill((254, 1, 1))
            for i, x in enumerate(self.lista_status_hilos_text):
                x.draw(self.surface_hilos)
            self.ventana.blit(self.surface_hilos, (self.ventana_rect.centerx, 50))

            self.surf_GUI.fill((254, 1, 1))
            self.GUI_manager.draw(self.surf_GUI, (mx, my))
            self.mini_GUI_manager.draw(self.surf_GUI, (mx, my))
            self.ventana.blit(self.surf_GUI, (0, 0))

            pag.display.flip()


if __name__ == '__main__' and len(sys.argv) > 1:
    clase = Downloader(*sys.argv[1:])
