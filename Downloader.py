import pygame as pag, sys, os, time, requests, json, sqlite3

from platformdirs import user_downloads_dir, user_cache_path, user_config_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup as bsoup4
from pygame.constants import MOUSEBUTTONDOWN, K_ESCAPE, QUIT, SCALED, KEYDOWN, MOUSEWHEEL, MOUSEMOTION

import Utilidades

from Utilidades import Create_text, Create_boton, Barra_de_progreso
from Utilidades import GUI, mini_GUI
from Utilidades import multithread
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
    def __init__(self, id) -> None:

        self.ventana = pag.display.set_mode((700, 300), SCALED)
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

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')

        self.division = self.peso_total // self.num_hilos
        self.peso_total_formateado = format_size(self.peso_total)
        self.reanudar_bool = False if self.estado == 'en espera' else True

        self.paused = True
        self.canceled = False
        self.screen_main = True
        self.can_download = False
        self.downloading = False
        self.apagar_al_finalizar = False
        self.relog = pag.time.Clock()

        self.carpeta_cache: Path = self.carpeta_cache.joinpath(f'./{self.id}_{''.join(self.file_name.split('.')[:-1])}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

        self.hilos_listos = 0
        self.lista_status_hilos: list[Create_text] = []
        self.lista_status_hilos_text: list[str] = []
        self.surface_hilos = pag.Surface((self.ventana_rect.w // 2, self.ventana_rect.h - 80))
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

        self.Titulo = Create_text(self.file_name, 14, self.font_mononoki, (20, 50), 'left')
        self.text_tamaño = Create_text(self.txts['descripcion-peso'].format(
            f'{self.peso_total_formateado[1]:.2f}{self.nomenclaturas[self.peso_total_formateado[0]]}'), 12,
            self.font_mononoki, (20, 70), 'left')
        self.text_url = Create_text(f'url: {(self.url if len(self.url) < 37 else (self.url[:37] + '...'))}', 12,
                                    self.font_mononoki, (20, 90), 'left')
        self.text_num_hilos = Create_text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12,
                                          self.font_mononoki, (20, 110), 'left')
        self.text_estado_general = Create_text(self.txts['descripcion-state[esperando]'], 12, self.font_mononoki,
                                               (20, 130), 'left')

        self.text_porcentaje = Create_text('0.00%', 14, self.font_mononoki, (175, self.ventana_rect.bottom - 90),
                                           'center', padding=(300, 5), color_rect=(20, 20, 20), with_rect=True)
        self.text_peso_progreso = Create_text('0 - 0b', 14, self.font_mononoki, (175, self.ventana_rect.bottom - 70),
                                              'center', padding=(100, 10), color_rect=(20, 20, 20), with_rect=True)
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

        self.btn_more_options = Create_boton('', 16, self.font_simbols, (700 / 2, 20), (20, 10), 'right', 'white',
                                             (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1,
                                             func=self.func_select_of_options)

        #   Barra de progreso
        self.barra_progreso = Barra_de_progreso((20, self.ventana_rect.bottom - 50), (310, 20), 'horizontal')
        self.barra_progreso.set_volumen(.0)

        self.list_to_draw = [self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
                             self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
                             self.text_title_hilos,
                             self.text_peso_progreso, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]
        self.list_to_click = [self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga, self.btn_more_options]

    def cargar_configs(self):

        try:
            self.configs: dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except:
            self.configs = {}
        self.idioma = self.configs.get('idioma', 'español')
        self.txts = idiomas[self.idioma]

    def func_pausar(self) -> None:
        self.paused = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.actualizar_porcentaje_db()
        self.draw_main()

    def func_cancelar(self,result) -> None:
        if not self.downloading or result == 'cancelar':
            return
        self.paused = False
        self.canceled = True
        self.downloading = False
        self.can_download = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.actualizar_porcentaje_db()
        for num in range(self.num_hilos):
            self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
        self.cerrar_todo('aceptar')
        self.draw_main()

    def func_abrir_carpeta_antes_de_salir(self, resultado):
        if resultado == 'aceptar':
            os.startfile(user_downloads_dir())
        self.cerrar_todo('a')

    def cerrar_todo(self, result):
        if result == 'cancelar':
            return
        self.actualizar_porcentaje_db()
        self.paused = False
        self.canceled = True
        pag.quit()
        sys.exit()

    def func_reanudar(self) -> None:
        if not self.can_download: return 0
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.reanudar_bool = True
        self.start_download()
        self.draw_main()

    def func_select_of_options(self):
        texto = self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No')
        self.mini_GUI_manager.add(mini_GUI.select(self.btn_more_options.rect.topright, [texto]), self.func_select_box)

    def func_select_box(self, result):
        if result['index'] == 0:
            self.GUI_manager.add(
                # GUI para saber si quiere apagar al finalizar la descarga
                GUI.Desicion(self.ventana_rect.center, self.txts['apagar-al-finalizar'], self.txts['Desea_apagar']),
                self.func_toggle_apagar
            )

    def func_toggle_apagar(self, result):
        self.apagar_al_finalizar = True if result == 'aceptar' else False

    def crear_conexion(self):
        self.text_estado_general.change_text(self.txts['descripcion-state[conectando]'])
        try:
            parse = urlparse(self.url)

            if parse.netloc == "www.mediafire.com" and parse.path[1:].split('/')[0] == 'file':
                if os.path.exists(self.carpeta_cache.joinpath(f'./url cache.txt')):
                    with open(self.carpeta_cache.joinpath(f'./url cache.txt'), 'r+') as file:
                        url = file.read()
                else:
                    url = bsoup4(requests.get(self.url, timeout=15).text, 'html.parser').find(id='downloadButton').get(
                        'href', False)
                    with open(self.carpeta_cache.joinpath(f'./url cache.txt'), 'w') as file:
                        file.write(url)
            else:
                url = self.url

            response = requests.get(url, stream=True, allow_redirects=True, timeout=15)

            if parse.netloc == "www.mediafire.com" and parse.path[1:].split('/')[0] == 'file' and int(
                    response.headers.get('Expires', 1)) == 0:
                os.remove(self.carpeta_cache.joinpath(f'./url cache.txt'))
                return self.crear_conexion()

            # response = requests.get(self.url, stream=True, allow_redirects=True, timeout=15)
            self.prepared_request = response.request
            response = self.prepared_session.send(self.prepared_request, stream=True, allow_redirects=True, timeout=15)

            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('No es el tipo de archivo')

            peso = response.headers.get('content-length', False)
            if int(peso) < 1024 // 8:
                raise LowSizeError('Peso muy pequeño')

            self.can_download = True
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
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
                GUI.Desicion(self.ventana_rect.center, 'Error',
                             self.txts['gui-error inesperado']),
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
        self.downloading = True
        self.hilos_listos = 0
        self.peso_descargado = 0

        self.lista_status_hilos.clear()
        for x in range(self.num_hilos):
            if not self.reanudar_bool:
                try:
                    os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
                except:
                    pass

            self.lista_status_hilos.append(
                Create_text(self.txts['status_hilo[iniciando]'].format(x), 12, self.font_mononoki, (50, (30 * x) + 5),
                            'left', with_rect=True, color_rect=(20, 20, 20)))
            if x == self.num_hilos - 1:
                self.surf_h_max = self.lista_status_hilos[-1].rect.bottom
            self.lista_status_hilos_text.append(self.txts['status_hilo[iniciando]'].format(x))

            self.pool_hilos.submit(self.download_thread, x, self.division * x, (
                self.division * x + self.division - 1 if x < self.num_hilos - 1 else self.peso_total - 1))

        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

        self.text_estado_general.change_text(self.txts['descripcion-state[descargando]'])
        self.draw_main()

    def download_thread(self, num, start, end, local_count=0, tiempo_reset=2):
        if self.paused:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[pausado]'].format(num)
            while self.paused:
                time.sleep(1)
        if self.canceled:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
            return 0
        self.lista_status_hilos_text[num] = self.txts['status_hilo[iniciando]'].format(num)
        if local_count == 0 and self.reanudar_bool and Path(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).is_file():
            local_count = os.stat(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).st_size
            self.peso_descargado += local_count
            if local_count >= end - start - 10:
                self.hilos_listos += 1
                self.lista_status_hilos_text[num] = self.txts['status_hilo[finalizado]'].format(num)
                return 0
        headers = {'Range': f'bytes={start + local_count}-{end}'}
        try:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[conectando]'].format(num)
            re = self.prepared_request.copy()
            re.prepare_headers(headers)
            response = self.prepared_session.send(re, stream=True, allow_redirects=True, timeout=15)

            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if tipo != self.type:
                # print(tipo,self.type, response.headers)
                raise DifferentTypeError('ay')

            peso = response.headers.get('content-length', False)
            if int(peso) < 1024 // 8:
                raise LowSizeError('Peso muy pequeño')

            tiempo_reset = 2
            self.lista_status_hilos_text[num] = self.txts['status_hilo[descargando]'].format(num)

            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'ab') as file_p:
                for data in response.iter_content(1024 // 8):
                    if self.paused or self.canceled: raise Exception('')
                    if data:
                        local_count += len(data)
                        self.peso_descargado += len(data)
                        file_p.write(data)

            self.lista_status_hilos_text[num] = self.txts['status_hilo[finalizado]'].format(num)
            self.hilos_listos += 1
            return
        except (Exception, LowSizeError) as err:
            # print(err)
            # print(type(err))

            if self.canceled:
                self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
                return 0
            self.lista_status_hilos_text[num] = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time() - t < tiempo_reset:
                if self.canceled:
                    self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
                    return 0
                time.sleep(.3)
            return self.download_thread(num, start, end, local_count,
                                        (tiempo_reset * 2) if tiempo_reset < 30 else tiempo_reset)

    def finish_download(self):
        self.downloading = False

        with open(user_downloads_dir() + '/' + self.file_name, 'wb') as file:
            for x in range(self.num_hilos):
                with open(self.carpeta_cache.joinpath(f'./parte{x}.tmp'), 'rb') as parte:
                    file.write(parte.read())
                os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
            file.close()
        os.rmdir(self.carpeta_cache)

        self.pool_hilos.shutdown()

        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?', ['Completado', self.id])
        self.Database.commit()

        self.can_download = True
        self.hilos_listos = 0
        self.peso_descargado = 0
        self.text_estado_general.change_text(self.txts['descripcion-state[finalizado]'])
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar

        if self.apagar_al_finalizar:
            os.system('shutdown /s /t 10')
            self.cerrar_todo('aceptar')
            return 0

        self.GUI_manager.add(
            GUI.Desicion(self.ventana_rect.center, self.txts['enhorabuena'], self.txts['gui-desea_abrir_la_carpeta']),
            self.func_abrir_carpeta_antes_de_salir
        )

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
            mx, my = pag.mouse.get_pos()

            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)

            for evento in eventos:
                if evento.type == QUIT:
                    self.cerrar_todo('a')
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx, my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        # GUI preguntando si desea salir del programa, y si acepta ejecutar la funcion self.cerrar_todo()
                        self.GUI_manager.add(
                            GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'], '¿Desea cerrar el programa?'),
                            self.cerrar_todo
                        )
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    if self.mini_GUI_manager.click(evento.pos):
                        continue
                    for x in self.list_to_click:
                        x.click((mx, my))
                elif evento.type == MOUSEWHEEL and mx > self.ventana_rect.centerx:
                    if -self.surf_h_max + 300 < self.surf_h_diff + evento.y * 20 < 5:
                        self.surf_h_diff += evento.y * 20
                        for x in self.lista_status_hilos:
                            x.move_rel((0, evento.y * 20))
                elif evento.type == MOUSEMOTION:
                    for x in self.list_to_draw:
                        if isinstance(x, Create_boton):
                            x.draw(self.display, (mx, my))

            if self.peso_total > 0:
                progreso = (self.peso_descargado / self.peso_total)
                self.text_porcentaje.change_text(f'{progreso * 100:.2f}%')
                descargado = format_size(self.peso_descargado)
                self.text_peso_progreso.change_text(
                    f'{descargado[1]:.2f}{self.nomenclaturas[descargado[0]]} - {self.peso_total_formateado[1]:.2f}{self.nomenclaturas[self.peso_total_formateado[0]]}')
                self.barra_progreso.set_volumen(progreso)

            if self.hilos_listos == self.num_hilos:
                self.finish_download()

            self.text_peso_progreso.draw(self.display)
            self.barra_progreso.draw(self.display)
            self.text_porcentaje.draw(self.display)
            self.ventana.blit(self.display, (0, 0))
            self.surface_hilos.fill((254, 1, 1))
            for i, x in enumerate(self.lista_status_hilos):
                x.change_text(self.lista_status_hilos_text[i])
                x.draw(self.surface_hilos)
            self.ventana.blit(self.surface_hilos, (self.ventana_rect.centerx, 50))

            self.surf_GUI.fill((254, 1, 1))
            self.GUI_manager.draw(self.surf_GUI, (mx, my))
            self.mini_GUI_manager.draw(self.surf_GUI, (mx, my))
            self.ventana.blit(self.surf_GUI, (0, 0))

            pag.display.flip()
            self.relog.tick(60)


if __name__ == '__main__':
    clase = Downloader(*sys.argv[1:])
