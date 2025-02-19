import pygame as pag
import os
import sys
import time
import shutil
import requests
import subprocess
import Utilidades as uti
import Utilidades_pygame as uti_pag

from pathlib import Path
from Utilidades import win32_tools
from tkinter.simpledialog import askstring
from concurrent.futures import ThreadPoolExecutor

from my_warnings import *
from textos import idiomas
from Utilidades_pygame.GUI import AdC_theme
from constants import DICT_CONFIG_DEFAULT, Config
from Utilidades_pygame.base_app_class import Base_class


# Cargo la carpeta de guardado de descarga al inicio y al final

class Downloader(Base_class):
    def otras_variables(self):
        self.download_id = self.args[0]
        self.modificador = self.args[1]

        self.config: Config
        
        self.raw_data = requests.get(f'http://127.0.0.1:5000/descargas/get/{self.download_id}').json()
        
        self.file_name: str = self.raw_data[1]
        self.type: str = self.raw_data[2]
        self.peso_total: int = int(self.raw_data[3])
        self.url: str = self.raw_data[4]
        self.num_hilos: int = int(self.raw_data[6])
        self.tiempo: float = float(self.raw_data[7])

        pag.display.set_caption(f'Downloader {self.download_id}_{self.file_name}')
        

        # booleanos
        self.apagar_al_finalizar: bool = False
        self.can_download: bool = False
        self.can_reanudar: bool = True
        self.canceled: bool = False
        self.cerrar_al_finalizar: bool = False if self.modificador != 2 else True
        self.cerrando = False
        self.detener_5min: bool = True
        self.downloading: bool = False
        self.ejecutar_al_finalizar: bool = False if self.modificador != 1 else True
        self.fallo_destino: bool = False
        self.finished: bool = False
        self.low_detail_mode: bool = False
        self.paused: bool = True

        # Integers
        self.chunk: int = 128
        self.current_velocity: int = 0
        self.division: int = self.peso_total // self.num_hilos
        self.downloading_threads: int = 0
        self.hilos_listos: int = 0
        self.intentos: int = 0
        self.peso_descargado: int = 0
        self.peso_descargado_vel: int = 0
        self.velocidad_limite: int = 0
        self.last_updated_progress = 0

        # Strings

        # Listas
        self.list_vels: list[float] = []
        self.lista_status_hilos: list[dict] = []

        # Otros
        self.db_update: float = time.time()
        self.last_change: float = time.time()
        self.last_velocity_update: float = time.time()

        self.default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'}
        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloads_threads')
        self.prepared_session = requests.Session()
        
        self.carpeta_cache = self.config.cache_dir.joinpath(f'./{self.download_id}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

    def post_init(self):

        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)
        self.Func_pool.start('descargar')
        self.Func_pool.add('__terminar_programa', self.__terminar_de_cerrar)
        self.class_intervals.add('actualizar_progress', self.update_progress_db, 1, start=True)
        self.class_intervals.add('actualizar_vel', self.calc_velocity, .4, start=True)
        self.class_intervals.add('actualizar_tiempo_restante', self.calc_tiempo_restante, 1, start=True)
        
        if self.enfoques:
            win32_tools.front2(self.hwnd)

    def load_resources(self):
        try:
            self.configs = self.request_session.get('http://127.0.0.1:5000/get_configurations').json()
        except:
            self.configs = DICT_CONFIG_DEFAULT

        self.enfoques = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.velocidad_limite = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])
        
        self.idioma = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.save_dir = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.txts = idiomas[self.idioma]

    def generate_objs(self):
        
        self.lineas_para_separar = (
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)
        )

        self.text_finalizando_hilos = uti_pag.Text(f'Finalizando los {self.num_hilos} hilos...' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, self.config.font_mononoki, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        self.text_finalizando_hilos2 = uti_pag.Text(f'Restantes: {self.downloading_threads}' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, self.config.font_mononoki, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        
        
        # ------------------------------------------- Textos y botones -----------------------------------
        self.Titulo = uti_pag.Text((self.file_name if len(self.file_name) < 36 else (self.file_name[:38] + '...')), 14, self.config.font_mononoki, (10, 50), 'left')
        self.text_tamaño = uti_pag.Text(self.txts['descripcion-peso'].format(uti.format_size_bits_to_bytes_str(self.peso_total)), 12, self.config.font_mononoki, (10, 70), 'left')
        self.text_url = uti_pag.Text(f'url: {(self.url if len(self.url) < 40 else (self.url[:43] + "..."))}', 11, self.config.font_mononoki, (10, 90), 'left')
        self.text_num_hilos = uti_pag.Text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12, self.config.font_mononoki, (10, 110), 'left')
        self.text_estado_general = uti_pag.Text(self.txts['descripcion-state[esperando]'], 12, self.config.font_mononoki, (10, 130), 'left')
        self.text_peso_progreso = uti_pag.Text('0b', 14, self.config.font_mononoki, (10, self.ventana_rect.centery + 20), 'left',)
        self.text_vel_descarga = uti_pag.Text(self.txts['velocidad'] + ': ' + '0kb/s', 14, self.config.font_mononoki, (10, self.ventana_rect.centery + 45), 'left')
        self.text_tiempo_restante = uti_pag.Text(self.txts['tiempo restante'] + ': 0Seg', 14, self.config.font_mononoki, (10, self.ventana_rect.centery + 70), 'left')
        self.text_porcentaje = uti_pag.Text('0.00%', 14, self.config.font_mononoki, (175, self.ventana_rect.bottom - 50), 'center')
        self.text_title_hilos = uti_pag.Text(self.txts['title_hilos'], 14, self.config.font_mononoki, (550, 30), 'center')

        self.btn_cancelar_descarga =  uti_pag.Button(
            self.txts['cancelar'], 16, self.config.font_mononoki, ((self.ventana_rect.width / 2) / 3, 20), (20, 10), 'center', 'black','purple', 'cyan', 0, 0, 20, 
            0, 0, 20, -1, func= lambda: self.open_GUI_dialog(self.txts['gui-cancelar descarga'], (400, 200),self.func_cancelar)
        )
        self.btn_pausar_y_reanudar_descarga = uti_pag.Button(
            self.txts['reanudar'], 16, self.config.font_mononoki, (((self.ventana_rect.width / 2) / 3) * 2, 20), (20, 10), 
            'center', 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.func_reanudar
        )

        self.btn_more_options = uti_pag.Button('', 16, self.config.font_mononoki, ((self.ventana_rect.width/2)-1, 20), 10, 'right', 'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1)
        self.select_more_options = uti_pag.Select_box(self.btn_more_options, options=['apagar','ejecutar','limitar'], auto_open=True, position='right', animation_dir='horizontal', func=self.func_select_box)
        self.set_select_options()
        
        self.list_textos_hilos = uti_pag.Multi_list(
            (330, self.ventana_rect.h - 70), (self.ventana_rect.centerx+20, 50), 2, None, 12, separation=15, colums_witdh=[0,.7], 
            padding_left=10, border_color=(20,20,20), header=False, fonts=[self.config.font_mononoki, self.config.font_mononoki], background_color=(20,20,20),
            smothscroll=True
        )

        #   Barra de progreso
        self.barra_progreso = uti_pag.Barra_de_progreso((20, self.ventana_rect.bottom - 30), (310, 20), 'horizontal', smoth=True)
        self.barra_progreso.volumen = .0

        
        # GUI
        self.gui_informacion = AdC_theme.Info(self.ventana_rect.center, self.config.font_mononoki, 'Acelerador de descargas', self.txts['informacion'], (550,275))
        self.gui_desicion = AdC_theme.Desicion(self.ventana_rect.center, self.config.font_mononoki, 'Acelerador de descargas', self.txts['desicion'], (550,275))
        

        self.overlay = [self.gui_informacion,self.gui_desicion]

        self.lists_screens['main']['draw'] = [
            self.list_textos_hilos, self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
            self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
            self.text_title_hilos, self.text_vel_descarga,self.text_peso_progreso,
            self.text_tiempo_restante, self.btn_pausar_y_reanudar_descarga, self.btn_more_options,
            self.select_more_options, self.text_finalizando_hilos, self.text_finalizando_hilos2
        ]
        self.lists_screens['main']['update'] = self.lists_screens['main']['draw']
        self.lists_screens['main']['click'] = [
            self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga,
            self.select_more_options, self.list_textos_hilos
        ]

    def on_exit(self):
        pag.quit()
        sys.exit(self.config.returncode)


    def otro_evento(self, actual_screen, evento):
        if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
            self.open_GUI_dialog(self.txts['gui-cerrar la ventana descarga'],self.cerrar_todo)
            ...

    def update(self, actual_screen='main'):
        if self.hilos_listos == self.num_hilos:
            self.finish_download()
        
        self.text_vel_descarga.text = self.txts['velocidad']+': ' + uti.format_size_bits_to_bytes_str(self.current_velocity)
        self.text_porcentaje.text = f'{(self.peso_descargado / self.peso_total) * 100:.2f}%'
        self.text_peso_progreso.text = self.txts['descargado']+': '+ uti.format_size_bits_to_bytes_str(self.peso_descargado)
        self.barra_progreso.volumen = self.peso_descargado / self.peso_total

        if self.cerrando and self.num_hilos > 1:
            self.text_finalizando_hilos2. text = f'Restantes: {self.downloading_threads}'

        if self.downloading:
            for i,x in sorted(enumerate(self.lista_status_hilos), reverse=False):
                self.list_textos_hilos[1][i] = f'{int(x["local_count"])/self.division * 100:.2f}%'



    def draw_before(self, actual_screen):
        for x in self.lineas_para_separar:
            pag.draw.line(self.ventana, 'black', x[0], x[1], width=3)

    # Ahora si, funciones del programa
    def open_GUI_dialog(self, texto, title='Acelerador de descargas', func=None,tipo=1):
        p = {
            1:self.gui_desicion,
            2:self.gui_informacion
        }[tipo]

        p.title.text = title
        p.body.text = texto
        p.func = func
        p.active = True
        p.redraw += 1

    # ---------------------------------------------------------------------------------- #

    def func_cancelar(self, result):
        if result == 'cancelar':
            return
        self.paused = False
        self.canceled = True
        self.cerrar_todo('aceptar')

    def func_pausar(self):
        self.paused = True
        self.last_change = time.time()
        self.downloading = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["pausado"]}'

    def func_reanudar(self):
        if not self.can_download: return
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['esperando']}..."
        self.start_download()

    def func_abrir_carpeta_antes_de_salir(self, resultado):
        if resultado == 'aceptar':
            if not self.fallo_destino:
                file = Path(self.save_dir)/self.file_name
            else:
                file = DICT_CONFIG_DEFAULT['save_dir']/self.file_name
            subprocess.call(['explorer','/select,{}'.format(file.as_uri())], shell = True)
        self.cerrar_todo('a')

    def func_select_box(self, result):
        if result['index'] == 0:
            self.apagar_al_finalizar = not self.apagar_al_finalizar
            if self.apagar_al_finalizar:
                self.ejecutar_al_finalizar = False
            self.set_select_options()
        elif result['index'] == 1:
            self.ejecutar_al_finalizar = not self.ejecutar_al_finalizar
            if self.ejecutar_al_finalizar:
                self.apagar_al_finalizar = False
            self.set_select_options()
        elif result['index'] == 2:
            respuesta = askstring('Velocidad limite', 'Ingrese la velocidad limite en kb/s')
            if not respuesta:
                return
            try:
                self.velocidad_limite = int(respuesta) * 1024
                self.set_select_options()
            except:
                self.open_GUI_dialog(self.txts['numero invalido'],'Error',tipo=2)


    # ---------------------------------------------------------------------------------- #

    def set_select_options(self):
        self.select_more_options.options = [
            self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No'),
            self.txts['ejecutar-al-finalizar'] + ': ' + (self.txts['si'] if self.ejecutar_al_finalizar else 'No'),
            self.txts['limitar-velocidad'] + ': ' + uti.format_size_bits_to_bytes_str(self.velocidad_limite)
        ]

    def update_progress_db(self):
        if self.peso_descargado == 0 or not self.downloading:
            return
        progreso = (self.peso_descargado / self.peso_total)
        if progreso == self.last_updated_progress:
            return
        self.last_updated_progress = progreso
        self.prepared_session.get(f'http://127.0.0.1:5000/descargas/update/estado/{self.download_id}/{f'{progreso * 100:.2f}%' if float(progreso) < 1.0 else 'Completado'}')

    def calc_velocity(self):
        if not self.downloading:
            return
        
        vel = self.peso_descargado_vel / (time.time() - self.last_velocity_update)
        self.last_velocity_update = time.time()
        self.peso_descargado_vel = 0

        self.list_vels.append(vel)
        if len(self.list_vels) > 30:
            self.list_vels.pop(0)

        self.current_velocity = (sum(self.list_vels)/len(self.list_vels)) if self.list_vels else 0

        if self.velocidad_limite > 0 and self.current_velocity > self.velocidad_limite:
            self.current_velocity = self.velocidad_limite
        
        if self.current_velocity > 0:
            self.last_change = time.time()
        elif time.time() - self.last_change > 300 and self.detener_5min:
            self.func_pausar()
            self.open_GUI_dialog(
                self.txts['gui-servidor no responde'],
                'Error',
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
            )

    def calc_tiempo_restante(self):
        if self.current_velocity > 0:
            delta_date = uti.format_date((self.peso_total-self.peso_descargado)/self.current_velocity,3)
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
            delta_date = uti.format_date(0,2)
            self.text_tiempo_restante.text = self.txts['tiempo restante'] + f": {self.txts['calculando']}..."

    def cerrar_todo(self, result):
        if result == 'cancelar' or self.cerrando:
            return
        self.cerrando = True
        self.paused = False
        self.canceled = True
        self.Func_pool.start('__terminar_programa')
        
    def __terminar_de_cerrar(self):
        self.text_finalizando_hilos.pos = self.ventana_rect.center
        self.text_finalizando_hilos2.pos = (self.text_finalizando_hilos.centerx, self.text_finalizando_hilos.bottom+10)
        self.loading += 1
        self.pool_hilos.shutdown(True, cancel_futures=True)
        self.update_progress_db()
        self.exit()


    def crear_conexion(self):
        self.can_download = False
        self.downloading = False
        self.text_estado_general.text = self.txts['descripcion-state[conectando]']
        try:
            response = self.prepared_session.get(self.url, stream=True, allow_redirects=True, timeout=30, headers=self.default_headers)
            print(response.headers)

            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            if tipo != self.type:
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
                self.open_GUI_dialog(self.txts['gui-no se puede reanudar'], 'Error', tipo=2)

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            if self.modificador == 2:
                self.intentos += 1
                if self.intentos > 10:
                    self.cerrar_todo('a')
            else:
                self.open_GUI_dialog(
                    self.txts['gui-servidor no responde'], 
                    'Error', 
                    lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
                )
        except (requests.exceptions.MissingSchema, DifferentTypeError, LowSizeError) as err:
            print(type(err))
            print(err)
            self.open_GUI_dialog(self.txts['gui-url no sirve'], 'Error', tipo=2)
        except Exception as err:
            print(type(err))
            print(err)
            self.open_GUI_dialog(
                self.txts['gui-error inesperado'], 
                'Error',
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a')),
                1
            )

    def start_download(self):
        if not self.can_download:
            return
        if self.downloading:
            return
        self.downloading_threads = 0
        self.paused = False
        self.canceled = False
        self.hilos_listos = 0
        self.peso_descargado = 0
        self.can_download = False

        self.lista_status_hilos.clear()
        self.list_textos_hilos.clear()
        self.pool_hilos.shutdown(True, cancel_futures=True)
        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')
        for x in range(self.num_hilos):
            self.list_textos_hilos.append((self.txts['status_hilo[iniciando]'].format(x),'0.00%'))

            self.lista_status_hilos.append({
                'status':0,
                'num':x,
                'start':self.division * x,
                'end':(self.division*x + self.division-1 if x < self.num_hilos - 1 else self.peso_total - 1),
                'local_count':0,
                'tiempo_reset':2,
                'time_chunk': 0,
                'actual_chunk_to_limit': 0,
                })
            self.pool_hilos.submit(self.init_download_thread,x)
        self.last_change = time.time()
        self.downloading = True
        self.can_download = True

        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['descargando']}"

    def init_download_thread(self,num):
        self.downloading_threads += 1
        while self.lista_status_hilos[num]['status'] == 0:
            self.peso_descargado -= self.lista_status_hilos[num]['local_count']
            try:
                self.download_thread(num)
            except Exception as err:
                print(type(err))
                print(err)
                raise err
        self.downloading_threads -= 1


    def download_thread(self, num):
        tiempo_reset = self.lista_status_hilos[num]['tiempo_reset']
        if self.canceled:
            self.list_textos_hilos[0][num] = self.txts['status_hilo[cancelado]'].format(num)
            self.lista_status_hilos[num]['status'] = 2
            return
        self.list_textos_hilos[0][num] = self.txts['status_hilo[iniciando]'].format(num)
        if Path(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).is_file() and self.can_reanudar:
            self.lista_status_hilos[num]['local_count'] = os.stat(self.carpeta_cache.joinpath(f'./parte{num}.tmp')).st_size
            self.peso_descargado += self.lista_status_hilos[num]['local_count']
            if self.lista_status_hilos[num]['local_count'] >= self.lista_status_hilos[num]['end'] - self.lista_status_hilos[num]['start']:
                self.hilos_listos += 1
                self.list_textos_hilos[0][num] = self.txts['status_hilo[finalizado]'].format(num)
                self.lista_status_hilos[num]['status'] = 1
                return 0
        else:
            self.lista_status_hilos[num]['local_count'] = 0
        if not self.can_reanudar:
            try:
                os.remove(self.carpeta_cache.joinpath(f'./parte{num}.tmp'))
            except FileNotFoundError:
                pass
        if self.paused:
            self.list_textos_hilos[0][num] = self.txts['status_hilo[pausado]'].format(num)
            while self.paused:
                time.sleep(.1)

        this_header = self.default_headers.copy()
        if self.can_reanudar:
            this_header['Range'] = f'bytes={self.lista_status_hilos[num]["start"] + self.lista_status_hilos[num]["local_count"]}-{self.lista_status_hilos[num]["end"]}'

        try:
            self.list_textos_hilos[0][num] = self.txts['status_hilo[conectando]'].format(num)
            
            response = self.prepared_session.get(self.url, stream=True, allow_redirects=True, timeout=15, headers=this_header)

            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('ay')

            tiempo_reset = 2
            self.list_textos_hilos[0][num] = self.txts['status_hilo[descargando]'].format(num)

            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'ab') as file_p:
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
                    raise DifferentSizeError('ay')

            self.lista_status_hilos[num]['status'] = 1
            self.list_textos_hilos[0][num] = self.txts['status_hilo[finalizado]'].format(num)
            self.hilos_listos += 1
            return
        except Exception as err:
            print(err)
            print(type(err))

            if self.canceled:
                self.list_textos_hilos[0][num] = self.txts['status_hilo[cancelado]'].format(num)
                self.lista_status_hilos[num]['status'] = 2
                return
            self.list_textos_hilos[0][num] = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time() - t < tiempo_reset:
                if self.canceled:
                    break
                time.sleep(.1)
            if self.canceled:
                self.list_textos_hilos[0][num] = self.txts['status_hilo[cancelado]'].format(num)
                self.lista_status_hilos[num]['status'] = 2
                return
            self.lista_status_hilos[num]['tiempo_reset'] = (tiempo_reset + 1) if tiempo_reset <= 15 else tiempo_reset
            return
             
    def finish_download(self):
        self.save_dir = Path(self.prepared_session.get('http://127.0.0.1:5000/configuration/save_dir').json())
        try:
            file = open(Path(self.save_dir)/self.file_name, 'wb')
        except Exception as err:
            print(type(err))
            print(err)
            file = open(DICT_CONFIG_DEFAULT['save_dir'] + '/' + self.file_name, 'wb')
            self.fallo_destino = True

        for x in range(self.num_hilos):
            with open(self.carpeta_cache.joinpath(f'./parte{x}.tmp'), 'rb') as parte:
                file.write(parte.read())
            os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
        file.close()
        shutil.rmtree(self.carpeta_cache, True)

        self.pool_hilos.shutdown(False,cancel_futures=True)

        self.peso_descargado = self.peso_total
        self.update_progress_db()

        self.downloading = False
        self.can_download = True
        self.drawing = True
        self.finished = True
        self.hilos_listos = 0
        self.config.returncode = 3
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["finalizado"]}'
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar

        if self.cerrar_al_finalizar or self.prepared_session.get(f'http://127.0.0.1:5000/descargas/check/{self.download_id}').json()['cola']:
            self.cerrar_todo('aceptar')
        elif self.apagar_al_finalizar:
            subprocess.call(f'shutdown /s /t 30 Descarga finalizada - {self.file_name}', shell=True)
            self.cerrar_todo('aceptar')
            return
        elif self.ejecutar_al_finalizar:
            os.startfile(Path(self.save_dir)/self.file_name)
            self.cerrar_todo('aceptar')
            return
        self.open_GUI_dialog(self.txts['gui-desea_abrir_la_carpeta'],self.txts['enhorabuena'],self.func_abrir_carpeta_antes_de_salir)
        if self.enfoques:
            win32_tools.front2(self.hwnd)


if __name__=='__main__':
    Downloader(Config(window_resize=False,resolution=(700, 300)))