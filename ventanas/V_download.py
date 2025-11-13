import os
import sys
import time
import shutil
import subprocess
import http.client
import pygame as pag 
import Utilidades as uti
import Utilidades_pygame as uti_pag
from pathlib import Path
from threading import Lock
from io import BufferedWriter
from tkinter.simpledialog import askstring
from concurrent.futures import ThreadPoolExecutor
from Utilidades import win32_tools, LinearRegressionSimple

from my_warnings import *
from textos import idiomas
from GUI import AdC_theme
from constants import DICT_CONFIG_DEFAULT, Config
from Utilidades_pygame.base_app_class import Base_class
from enums.Download import Download


class Downloader(Base_class):
    def otras_variables(self):
        self.download_id: int = self.args[0]
        self.modificador: int = self.args[1]

        self.config: Config
        
        self.raw_data = Download(*uti.get(f'http://127.0.0.1:5000/descargas/get/{self.download_id}').json)
        
        
        self.file_name: str = self.raw_data.nombre
        self.type: str = self.raw_data.tipo
        self.peso_total: int = int(self.raw_data.peso)
        self.url: str = self.raw_data.url
        self.num_hilos: int = int(self.raw_data.partes)
        self.tiempo: float = float(self.raw_data.fecha)
        self.cookies: str = self.raw_data.cookies

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
        self.current_velocity: int = 0
        self.division: int = (self.peso_total // self.num_hilos) if self.peso_total > 0 else self.peso_total
        self.downloading_threads: int = 0
        self.hilos_listos: int = 0
        self.intentos: int = 0
        self.peso_nuevo: int = 0
        self.peso_descargado: int = 0
        self.peso_descargado_vel: int = 0
        self.peso_descargado_max_vel: int = 0
        self.velocidad_limite: int = 0
        self.last_updated_progress: float = 0
        self.last_updated_max_vel: float = 0
        
        # Chunk
        self.chunk: int = 128
        self.max_chunk_change: float = 0.25
        self.min_chunk: int = 64
        self.max_chunk: int = 1024*1024*10

        # Strings

        # Listas
        self.list_vels: list[float] = []
        self.lista_status_hilos: list[dict] = []
        self.list_to_train_chunk_regressor: list[list[int]] = [
            [
                1024*100,
                1024*500,
                1024*1024,
                1024*1024*2
            ],
            [
                256,
                512,
                1024*100,
                1024*200
            ]
        ]

        # Otros
        self.db_update: float = time.time()
        self.last_change: float = time.time()
        self.last_velocity_update: float = time.time()
        self.lock: Lock = Lock()
        self.max_vel_lock: Lock = Lock()

        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            'Accept-Encoding': 'identity'
            }
        self.pool_hilos: ThreadPoolExecutor = ThreadPoolExecutor(self.num_hilos, 'downloads_threads')
        self.chunk_regressor: LinearRegressionSimple = LinearRegressionSimple(*self.list_to_train_chunk_regressor)

        self.session = uti.Http_Session(verify=False)
        self.session.headers = self.default_headers
        
        if self.cookies:
            self.session.cookies = self.cookies
        
        self.carpeta_cache: Path = self.config.cache_dir.joinpath(f'./{self.download_id}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)

    def post_init(self):

        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)
        self.Func_pool.start('descargar')
        self.Func_pool.add('__terminar_programa', self.__terminar_de_cerrar)
        self.Func_pool.add('finalizar descarga', self.finish_download)
        self.class_intervals.add('actualizar_progress', self.update_progress_db, .1, start=True)
        self.class_intervals.add('actualizar_vel', self.calc_velocity, .4, start=True)
        self.class_intervals.add('actualizar_tiempo_restante', self.calc_tiempo_restante, 1, start=True)
        
        if self.enfoques:
            win32_tools.front2(self.hwnd)

    def load_resources(self):
        try:
            self.configs: dict = uti.get('http://127.0.0.1:5000/get_configurations').json
        except Exception as err:
            uti.debug_print(type(err), priority=3)
            uti.debug_print(err, priority=3)
            self.configs: dict = DICT_CONFIG_DEFAULT

        self.enfoques: bool = self.configs.get('enfoques',DICT_CONFIG_DEFAULT['enfoques'])
        self.detener_5min: bool = self.configs.get('detener_5min',DICT_CONFIG_DEFAULT['detener_5min'])
        self.low_detail_mode: bool = self.configs.get('ldm',DICT_CONFIG_DEFAULT['ldm'])
        self.velocidad_limite: int = self.configs.get('velocidad_limite',DICT_CONFIG_DEFAULT['velocidad_limite'])
        
        self.idioma: str = self.configs.get('idioma',DICT_CONFIG_DEFAULT['idioma'])
        self.save_dir: Path = Path(self.configs.get('save_dir',DICT_CONFIG_DEFAULT['save_dir']))
        self.txts: dict = idiomas[self.idioma]

    def generate_objs(self):
        
        self.lineas_para_separar = (
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)
        )

        self.text_finalizando_hilos = uti_pag.Text(f'Finalizando los {self.num_hilos} hilos...' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, self.config.font_mononoki, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        self.text_finalizando_hilos2 = uti_pag.Text(f'Restantes: {self.downloading_threads}' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, self.config.font_mononoki, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        
        self.text_juntando_partes = uti_pag.Text(f'Juntando archivo final...', 16, self.config.font_mononoki, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        
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
            self.txts['cancelar'], 16, self.config.font_mononoki, ((self.ventana_rect.width / 2) / 3, 20), (10, 5), 'center', 'black','purple', 'cyan', 0, 0, 20, 
            0, 0, 20, -1, func= lambda: self.open_GUI_dialog(self.txts['gui-cancelar descarga'], (400, 200),self.func_cancelar, options=[self.txts['aceptar'], self.txts['cancelar']])
        )
        self.btn_pausar_y_reanudar_descarga = uti_pag.Button(
            self.txts['reanudar'], 16, self.config.font_mononoki, (((self.ventana_rect.width / 2) / 3) * 2, 20), (10, 5), 
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
            self.select_more_options, 
            
            self.text_finalizando_hilos, self.text_finalizando_hilos2,self.text_juntando_partes
        ]
        self.lists_screens['main']['update'] = self.lists_screens['main']['draw']
        self.lists_screens['main']['click'] = [
            self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga,
            self.list_textos_hilos,
            self.select_more_options
        ]

    def exit(self):
        self.cerrar_todo('aceptar')
        return super().exit()

    def on_exit(self):
        sys.exit(self.config.returncode)


    def otro_evento(self, actual_screen, evento):
        if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
            self.open_GUI_dialog(self.txts['gui-cerrar la ventana descarga'],func=self.cerrar_todo, options=[self.txts['cerrar'], self.txts['cancelar']])
            ...

    def update(self, actual_screen='main'):
        if self.hilos_listos == self.num_hilos:
            self.hilos_listos = 0
            self.Func_pool.start('finalizar descarga')
        
        self.text_vel_descarga.text = self.txts['velocidad']+': ' + uti.format_size_bits_to_bytes_str(self.current_velocity)
        self.text_peso_progreso.text = self.txts['descargado']+': '+ uti.format_size_bits_to_bytes_str(self.peso_descargado)
        if self.peso_total > 0:
            self.text_porcentaje.text = f'{(self.peso_descargado / self.peso_total) * 100:.2f}%'
            self.barra_progreso.volumen = self.peso_descargado / self.peso_total
        else:
            self.text_porcentaje.text = f'?%...'
            self.barra_progreso.volumen = .5

        if self.cerrando and self.num_hilos > 1:
            self.text_finalizando_hilos2.text = f'Restantes: {self.downloading_threads}'

        if not self.downloading:
            return
        if self.num_hilos == 1 and self.peso_total > 0:
            self.list_textos_hilos[1][0] = f'{int(self.lista_status_hilos[0]["local_count"])/self.peso_total * 100:.2f}%'
        elif self.num_hilos > 1:
            for i,x in sorted(enumerate(self.lista_status_hilos), reverse=False):
                self.list_textos_hilos[1][i] = f'{int(x["local_count"])/self.division * 100:.2f}%'



    def draw_before(self, actual_screen):
        for x in self.lineas_para_separar:
            pag.draw.line(self.ventana, 'black', x[0], x[1], width=3)

    # Ahora si, funciones del programa
    def open_GUI_dialog(self, texto, title='Acelerador de descargas', func=None,tipo=1, options=None):
        p = {
            1:self.gui_desicion,
            2:self.gui_informacion
        }[tipo]
        
        if options:
            p.options = options
        p.title.text = title
        p.body.text = texto
        p.func = func
        p.active = True
        p.redraw += 1

    # ---------------------------------------------------------------------------------- #

    def func_cancelar(self, result):
        if result['index'] == 1:
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
        if resultado['index'] == 0:
            if not self.fallo_destino:
                file = Path(self.save_dir)/self.file_name
            else:
                file = Path(DICT_CONFIG_DEFAULT['save_dir'])/self.file_name
            subprocess.call(['explorer','/select,{}'.format(file.as_uri())], shell = True)
        elif resultado['index'] == 1:
            if not self.fallo_destino:
                file = Path(self.save_dir)/self.file_name
            else:
                file = Path(DICT_CONFIG_DEFAULT['save_dir'])/self.file_name
            os.startfile(file)
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

    def func_cambio_tamanio(self, resultado):
        uti.debug_print(resultado)
        if resultado['index'] == 1:
            self.cerrar_todo('a')
            return
        
        self.session.get(f"http://127.0.0.1:5000/descargas/update/size/{self.download_id}/{self.peso_nuevo}", timeout=30)
        self.peso_total = self.peso_nuevo
        self.division = (self.peso_total // self.num_hilos) if self.peso_total > 0 else self.peso_total
        uti.debug_print(self.peso_nuevo)
        shutil.rmtree(self.carpeta_cache, ignore_errors=True)
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)
        self.Func_pool.start('descargar')

    # ---------------------------------------------------------------------------------- #

    def set_select_options(self):
        self.select_more_options.options = [
            self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No'),
            self.txts['ejecutar-al-finalizar'] + ': ' + (self.txts['si'] if self.ejecutar_al_finalizar else 'No'),
            self.txts['limitar-velocidad'] + ': ' + uti.format_size_bits_to_bytes_str(self.velocidad_limite)
        ]

    def update_progress_db(self):
        if self.peso_total == 0:
            return
        if self.peso_descargado == 0 or not self.downloading:
            return
        progreso = (self.peso_descargado / self.peso_total)
        if progreso == self.last_updated_progress:
            return
        self.last_updated_progress = progreso
        uti.get(f'http://127.0.0.1:5000/descargas/update/estado/{self.download_id}/{f'{progreso * 100:.2f}%' if float(progreso) < 1.0 else 'Completado'}').json

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

        self.calc_chunk()

        if self.velocidad_limite > 0 and self.current_velocity > self.velocidad_limite:
            self.current_velocity = self.velocidad_limite
        
        if self.current_velocity > 0:
            self.last_change = time.time()
        elif time.time() - self.last_change > 300 and self.detener_5min:
            self.func_pausar()
            self.open_GUI_dialog(
                self.txts['gui-servidor no responde'],
                'Error',
                lambda r: (self.Func_pool.start('descargar') if r['index'] == 0 else self.cerrar_todo({'index':0})), 
                options=[self.txts['aceptar'], self.txts['cancelar']]
            )

    def calc_chunk(self):
        """Calcula el tamaño óptimo del chunk basado en regresión lineal de velocidades históricas"""
        actual_time = time.time()
        
        # Actualiza el tiempo de la última actualización
        self.last_velocity_update = actual_time
        
        # Si no hay suficientes datos, usa un valor base
        if len(self.list_vels) < 3:
            self.chunk = self.min_chunk
            return 
        
        try:
            # Usa regresión lineal para predecir el próximo chunk
            predicted_chunk = int(self.chunk_regressor.predict(self.current_velocity))
            
            # Limita el cambio máximo del chunk para suavizar transiciones
            chunk_change_diff = (self.chunk - predicted_chunk) * self.max_chunk_change
            new_chunk = max(self.min_chunk, min(self.chunk - chunk_change_diff, self.max_chunk))
            
            self.chunk = int(new_chunk)
        except Exception as err:
            uti.debug_print(f"Error en regresión lineal: {err}", priority=3)
            self.chunk = self.min_chunk

    def calc_tiempo_restante(self):
        if self.current_velocity > 0 and self.peso_total > 0:
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

    def max_vel_throttle(self, chunk_size: int):
        if self.velocidad_limite == 0:
            return

        with self.max_vel_lock:
            self.peso_descargado_max_vel += chunk_size

            transcurrido = time.perf_counter() - self.last_updated_max_vel

            if transcurrido > 1:
                self.last_updated_max_vel = time.perf_counter()
                self.peso_descargado_max_vel = 0
            
            permitido = self.velocidad_limite - self.peso_descargado_max_vel
            
            if permitido <= 0:
                if self.velocidad_limite == 0:
                    return
                tiempo_reset = 1 * (self.peso_descargado_max_vel / self.velocidad_limite)
                time.sleep(tiempo_reset if tiempo_reset <= 1 else 1)
                

    def cerrar_todo(self, result):
        if isinstance(result, dict) and result['index'] == 1 or self.cerrando:
            return
        self.Func_pool.start('__terminar_programa')
        
    def __terminar_de_cerrar(self):
        self.loading += 1
        self.update_progress_db()
        self.cerrando = True
        self.paused = False
        self.canceled = True
        self.text_finalizando_hilos.pos = self.ventana_rect.center
        self.text_finalizando_hilos2.pos = (self.text_finalizando_hilos.centerx, self.text_finalizando_hilos.bottom+10)
        self.velocidad_limite = 0
        self.pool_hilos.shutdown(True, cancel_futures=True)
        super().exit()


    def crear_conexion(self):
        self.can_download = False
        self.downloading = False
        self.text_estado_general.text = self.txts['descripcion-state[conectando]']
        try:
            intentos = 0

            while intentos < 10:
                intentos += 1
                try:
                    # response = uti.get(self.url, timeout=30).headers
                    response = self.session.get(self.url, timeout=30).headers
                    if (response.get('Content-Type', 'unknown/Nose').split(';')[0] != self.type):
                        raise TrajoHTML(f'No paginas= type:{response.get("Content-Type", "unknown/Nose").split(";")[0]}')
                    if (int(response.get('content-length', 0)) != self.peso_total):
                        self.peso_nuevo = int(response.get('content-length', 0))
                        raise DifferentSizeError(f"ahora pesa distinto: de {self.peso_total} a {response.get('content-length', 0)}")
                    else:
                        break
                except http.client.HTTPException as err:
                    uti.debug_print(err, priority=3)
                    continue

            uti.debug_print(response, priority=0)
            self.intentos = 0
            self.can_download = True
            self.last_change = time.time()
            if 'bytes' not in response.get('Accept-Ranges', ''):
                self.can_reanudar = False
                try:
                    os.remove(self.carpeta_cache.joinpath(f'./parte0.tmp'))
                except:
                    pass
                self.open_GUI_dialog(self.txts['gui-no se puede reanudar'], 'Error', tipo=2)

        except http.client.HTTPException:
            if self.modificador == 2:
                self.intentos += 1
                if self.intentos > 10:
                    self.cerrar_todo('a')
            else:
                self.open_GUI_dialog(
                    self.txts['gui-servidor no responde'], 
                    'Error', 
                    func=lambda r: (self.Func_pool.start('descargar') if r['index'] == 0 else self.cerrar_todo({'index':0})), 
                    options=[self.txts['reintentar'], self.txts['cancelar']]
                )
        except (http.client.HTTPException, DifferentTypeError, LowSizeError, TrajoHTML) as err:
            uti.debug_print(err, priority=3)
            self.open_GUI_dialog(
                self.txts['gui-url no sirve'], 
                'Error', 
                func=lambda r: (self.Func_pool.start('descargar') if r['index'] == 0 else self.cerrar_todo({'index':0})),
                options=[self.txts['reintentar'], self.txts['cancelar']]
            )
        except DifferentSizeError as err:
            uti.debug_print(err, priority=3)
            self.open_GUI_dialog(
                self.txts['gui-cambio de tamanio'], 
                'Error', 
                func=self.func_cambio_tamanio,
                options=[self.txts['aceptar'], self.txts['cancelar']]
            )
        except Exception as err:
            uti.debug_print(type(err), priority=3)
            uti.debug_print(err, priority=3)
            self.open_GUI_dialog(
                self.txts['gui-error inesperado'], 
                'Error',
                tipo=1,
                func=lambda r: (self.Func_pool.start('descargar') if r['index'] == 0 else self.cerrar_todo({'index':0})), 
                options=[self.txts['reintentar'], self.txts['cancelar']]
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
                uti.debug_print(type(err), priority=3)
                uti.debug_print(err, priority=3)
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
        if self.can_reanudar and self.num_hilos > 1:
            this_header['Range'] = f'bytes={self.lista_status_hilos[num]["start"] + self.lista_status_hilos[num]["local_count"]}-{self.lista_status_hilos[num]["end"]}'

        try:
            self.list_textos_hilos[0][num] = self.txts['status_hilo[conectando]'].format(num)
            r = self.session.copy()
            r.headers = this_header
            response = r.get(self.url, timeout=15)

            tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('ay')

            tiempo_reset = 1
            self.list_textos_hilos[0][num] = self.txts['status_hilo[descargando]'].format(num)

            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'), 'ab') as file_p:
                buffered_write = BufferedWriter(file_p, 1024*1024)
                while True:
                    data = response.read(self.chunk)
                    if not data:
                        break
                    if self.paused or self.canceled:
                        response.close()
                        buffered_write.flush()
                        buffered_write.close()
                        raise Exception('Paused or Canceled')
                    tanto = len(data)
                    self.lock.acquire()
                    self.lista_status_hilos[num]['local_count'] += tanto
                    self.peso_descargado_vel += tanto
                    self.peso_descargado += tanto
                    buffered_write.write(data)
                    self.lock.release()


                    self.max_vel_throttle(tanto)
                response.close()
    
                buffered_write.flush()
                buffered_write.close()
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
            uti.debug_print(type(err), priority=2)

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
        self.loading += 1
        self.text_juntando_partes.pos = (self.ventana_rect.centerx, self.ventana_rect.centery)

        self.save_dir = Path(uti.get(f'http://127.0.0.1:5000/configuration/save_dir').json)
        try:
            file = open(self.save_dir.joinpath(self.file_name), 'wb')
        except Exception:
            uti.debug_print(self.save_dir, priority=3)
            uti.debug_print(DICT_CONFIG_DEFAULT, priority=3)

            destino = Path(DICT_CONFIG_DEFAULT['save_dir'])
            destino.mkdir(parents=True, exist_ok=True)
            file = open(destino.joinpath(self.file_name), 'wb')
            self.fallo_destino = True

        for x in range(self.num_hilos):
            parte_path = self.carpeta_cache.joinpath(f'./parte{x}.tmp')
            with open(parte_path, 'rb') as parte:
                shutil.copyfileobj(parte, file, length=1024*1024*16)
            os.remove(parte_path)

        file.close()
        shutil.rmtree(self.carpeta_cache, True)

        self.pool_hilos.shutdown(False,cancel_futures=True)

        self.loading -= 1
        self.text_juntando_partes.pos = (-1000,-1000)

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

        if self.cerrar_al_finalizar or uti.get(f'http://127.0.0.1:5000/descargas/check/{self.download_id}').json['cola']:
            self.cerrar_todo('aceptar')
        elif self.apagar_al_finalizar:
            self.config.returncode = 4
            subprocess.call(f'shutdown /s /t 30 /c "Descarga finalizada, se apagara el sistema en 30 segundos"', shell=True)
            self.cerrar_todo('aceptar')
            return
        elif self.ejecutar_al_finalizar:
            os.startfile(Path(self.save_dir)/self.file_name)
            self.cerrar_todo('aceptar')
            return
        self.open_GUI_dialog(
            self.txts['gui-desea_abrir_la_carpeta'],
            self.txts['enhorabuena'],
            self.func_abrir_carpeta_antes_de_salir,
            options=[self.txts['ir a la carpeta'], self.txts['abrirlo'], self.txts['cerrar']]
            )
        if self.enfoques:
            win32_tools.front2(self.hwnd)


if __name__=='__main__':
    Downloader(Config(window_resize=False,resolution=(700, 300)))