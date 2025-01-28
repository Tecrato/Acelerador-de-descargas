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
import datetime


from platformdirs import user_downloads_dir, user_downloads_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter.simpledialog import askstring
from pygame.constants import ( K_ESCAPE, KEYDOWN)


from textos import idiomas
from my_warnings import *

from constants import DICT_CONFIG_DEFAULT, FONT_MONONOKI, SCREENSHOTS_DIR, CACHE_DIR, CONFIG_DIR

RESOLUTION = (700, 300)
RETURNCODE = 0

class Downloader:
    def __init__(self, id, modificador=0):
        pag.init()
        self.ventana = pag.display.set_mode(RESOLUTION)
        self.ventana_rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))
        self.hwnd = pag.display.get_wm_info()['window']

        self.raw_data = requests.get(f'http://127.0.0.1:5000/descargas/get/{id}').json()
        
        self.id: int = self.raw_data[0]
        self.file_name: str = self.raw_data[1]
        self.type: str = self.raw_data[2]
        self.peso_total: int = self.raw_data[3]
        self.url: str = self.raw_data[4]
        self.num_hilos: int = int(self.raw_data[6])
        self.tiempo: float = float(self.raw_data[7])
        self.modificador: int = int(modificador)
        
        pag.display.set_caption(f'Downloader {self.id}_{self.file_name}')
        
        self.carpeta_cache = CACHE_DIR.joinpath(f'./{self.id}')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)


        self.paused: bool = True
        self.canceled: bool = False
        self.can_download: bool = False
        self.can_reanudar: bool = True
        self.downloading: bool = False
        self.apagar_al_finalizar: bool = False
        self.ejecutar_al_finalizar: bool = False if self.modificador != 1 else True
        self.cerrar_al_finalizar: bool = False if self.modificador != 2 else True
        self.drawing: bool = True
        self.finished: bool = False
        self.detener_5min: bool = True
        self.fallo_destino: bool = False
        self.low_detail_mode: bool = False
        self.draw_background: bool = False
        self.cerrando = False
        self.hitboxes = False
        self.loading = 0
        self.intentos: int = 0
        self.chunk: int = 128
        self.velocidad_limite: int = 0
        self.current_velocity: int = 0
        self.downloading_threads: int = 0
        self.hilos_listos: int = 0
        self.peso_descargado: int = 0
        self.peso_descargado_vel: int = 0
        self.division: int = self.peso_total // self.num_hilos
        self.list_vels: list[int] = []
        self.updates: list[pag.Rect] = []
        self.lista_status_hilos: list[dict] = []
        self.background_color: tuple[int,int,int] = (20,20,20)
        self.last_change: float = time.time()
        self.db_update: float = time.time()
        self.last_tiempo_restante_update: float = time.time()
        self.last_velocity_update: float = time.time()
        self.relog = pag.time.Clock()
        self.prepared_session = requests.Session()
        self.speed_deltatime = uti.Deltatime(15,10)
        self.save_dir = user_downloads_dir()
        self.Func_pool = uti.Funcs_pool()
        self.class_intervals = uti.multithread.Interval_funcs()
        self.default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'}

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos, 'downloader')

        self.screen_main_bool: bool = True

        self.list_to_draw_main: list[uti_pag.Text|uti_pag.Button|uti_pag.Input|uti_pag.Multi_list|uti_pag.List|uti_pag.Bloque] = []
        self.list_to_update_main: list[uti_pag.Text|uti_pag.Button|uti_pag.Input|uti_pag.Multi_list|uti_pag.List|uti_pag.Bloque] = []
        self.list_to_click_main: list[uti_pag.Button|uti_pag.Bloque] = []
        self.list_inputs: list[uti_pag.Input] = []
    
        self.cargar_configs()
        self.generar_objs()

        if self.enfoques:
            uti.win32_tools.front2(pag.display.get_wm_info()['window'])
        self.Func_pool.add('descargar', self.crear_conexion, self.start_download)
        self.Func_pool.start('descargar')
        self.Func_pool.add('__terminar_programa', self.__terminar_de_cerrar)

        self.class_intervals.add('actualizar_progress', self.update_progress_db, 1, start=True)
        self.class_intervals.add('actualizar_vel', self.calc_velocity, .4, start=True)
        self.class_intervals.add('actualizar_tiempo_restante', self.calc_tiempo_restante, 1, start=True)


        self.ciclo_general = [self.screen_main]
        self.cicle_try = 0
        while self.cicle_try < 5:
            self.cicle_try += 1
            for x in self.ciclo_general:
                x()

        pag.quit()
        sys.exit(RETURNCODE)

    def cargar_configs(self):
        try:
            self.configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
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
        self.Mini_GUI_manager = uti_pag.mini_GUI.mini_GUI_admin(self.ventana_rect)
        self.list_textos_hilos = uti_pag.Multi_list(
            (330, self.ventana_rect.h - 70), (self.ventana_rect.centerx+20, 50), 2, None, 12, separation=15, colums_witdh=[0,.7], 
            padding_left=10, border_color=(20,20,20), header=False, fonts=[FONT_MONONOKI, FONT_MONONOKI], background_color=(20,20,20),
            smothscroll=True
        )

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx, 0), (self.ventana_rect.centerx, self.ventana_rect.h)),
            ((0, self.ventana_rect.centery), self.ventana_rect.center)
        ]

        self.text_finalizando_hilos = uti_pag.Text(f'Finalizando los {self.num_hilos} hilos...' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, FONT_MONONOKI, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        self.text_finalizando_hilos2 = uti_pag.Text(f'Restantes: {self.downloading_threads}' if self.num_hilos > 1 else 'Finalizando el hilo...', 16, FONT_MONONOKI, (-1000,-1111), 'center', with_rect=True, color_rect='white', padding=20, color='black')
        
        # ------------------------------------------- Textos y botones -----------------------------------
        self.Titulo = uti_pag.Text((self.file_name if len(self.file_name) < 36 else (self.file_name[:38] + '...')), 14, FONT_MONONOKI, (10, 50), 'left')
        self.text_tamaño = uti_pag.Text(self.txts['descripcion-peso'].format(uti.format_size_bits_to_bytes_str(self.peso_total)), 12, FONT_MONONOKI, (10, 70), 'left')
        self.text_url = uti_pag.Text(f'url: {(self.url if len(self.url) < 37 else (self.url[:39] + "..."))}', 12, FONT_MONONOKI, (10, 90), 'left')
        self.text_num_hilos = uti_pag.Text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12, FONT_MONONOKI, (10, 110), 'left')
        self.text_estado_general = uti_pag.Text(self.txts['descripcion-state[esperando]'], 12, FONT_MONONOKI, (10, 130), 'left')
        self.text_peso_progreso = uti_pag.Text('0b', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 20), 'left',)
        self.text_vel_descarga = uti_pag.Text(self.txts['velocidad'] + ': ' + '0kb/s', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 45), 'left')
        self.text_tiempo_restante = uti_pag.Text(self.txts['tiempo restante'] + ': 0Seg', 14, FONT_MONONOKI, (10, self.ventana_rect.centery + 70), 'left')
        self.text_porcentaje = uti_pag.Text('0.00%', 14, FONT_MONONOKI, (175, self.ventana_rect.bottom - 50), 'center')
        self.text_title_hilos = uti_pag.Text(self.txts['title_hilos'], 14, FONT_MONONOKI, (550, 30), 'center')


        self.btn_cancelar_descarga = uti_pag.Button(
            self.txts['cancelar'], 16, FONT_MONONOKI, ((RESOLUTION[0] / 2) / 3, 20), (20, 10), 'center', 'black','purple', 'cyan', 0, 0, 20, 
            0, 0, 20, -1, 
            func=lambda:self.GUI_manager.add(
                uti_pag.GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'], self.txts['gui-cancelar descarga'], (400, 200)), self.func_cancelar
            ))
        
        self.btn_pausar_y_reanudar_descarga = uti_pag.Button(self.txts['reanudar'], 16, FONT_MONONOKI, (((RESOLUTION[0] / 2) / 3) * 2, 20), (20, 10), 'center', 'black', 'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.func_reanudar)
    
        self.btn_more_options = uti_pag.Button('', 16, FONT_MONONOKI, ((RESOLUTION[0]/2)-1, 20), 10, 'right', 'white', (20, 20, 20), (50, 50, 50), 0, -1, border_width=-1)
        self.select_more_options = uti_pag.Select_box(self.btn_more_options, options=['apagar','ejecutar','limitar'], auto_open=True, position='right', animation_dir='horizontal', func=self.func_select_box)
        self.set_select_options()

        #   Barra de progreso
        self.barra_progreso = uti_pag.Barra_de_progreso((20, self.ventana_rect.bottom - 30), (310, 20), 'horizontal', smoth=True)
        self.barra_progreso.volumen = .0

        self.list_to_draw_main.extend([
            self.list_textos_hilos, self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
            self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
            self.text_title_hilos, self.text_vel_descarga,self.text_peso_progreso,
            self.text_tiempo_restante, self.btn_pausar_y_reanudar_descarga, self.btn_more_options,
            self.select_more_options, self.text_finalizando_hilos, self.text_finalizando_hilos2
        ])
        self.list_to_update_main.extend([
            self.Titulo, self.text_tamaño, self.text_url, self.text_num_hilos, self.barra_progreso,
            self.text_porcentaje, self.text_estado_general, self.btn_cancelar_descarga,
            self.text_title_hilos, self.text_vel_descarga,self.text_peso_progreso,
            self.text_tiempo_restante, self.btn_pausar_y_reanudar_descarga, self.btn_more_options,
            self.select_more_options, self.list_textos_hilos, self.text_finalizando_hilos, self.text_finalizando_hilos2
        ])
        self.list_to_click_main.extend([
            self.btn_cancelar_descarga, self.btn_pausar_y_reanudar_descarga,
            self.select_more_options, self.list_textos_hilos
        ])

    def eventos_en_comun(self,evento):
        mx, my = pag.mouse.get_pos()
        if evento.type == pag.QUIT:
            self.cerrar_todo('a')
        elif evento.type == pag.KEYDOWN and evento.key == pag.K_F12:
            momento = datetime.datetime.today().strftime('%d-%m-%y %f')
            result = uti.win32_tools.take_window_snapshot(self.hwnd)
            surf = pag.image.frombuffer(result['buffer'],(result['bmpinfo']['bmWidth'], result['bmpinfo']['bmHeight']),'BGRA')
            pag.image.save(surf,SCREENSHOTS_DIR.joinpath('Download Manager {}.png'.format(momento)))
        elif evento.type == pag.KEYDOWN and evento.key == pag.K_F11:
            self.hitboxes = not self.hitboxes
        elif evento.type == pag.WINDOWRESTORED:
            return True
        elif evento.type == pag.MOUSEBUTTONDOWN and evento.button in [1,3] and self.Mini_GUI_manager.click(evento.pos):
            return True
        elif evento.type == pag.WINDOWMINIMIZED:
            self.drawing = False
            return True
        elif evento.type == pag.WINDOWFOCUSLOST:
            return True
        elif evento.type in [pag.WINDOWTAKEFOCUS, pag.WINDOWFOCUSGAINED,pag.WINDOWMAXIMIZED]:
            self.drawing = True
            return True
        elif self.loading > 0:
            return True
        elif self.GUI_manager.active >= 0:
            if evento.type == pag.KEYDOWN and evento.key == pag.K_ESCAPE:
                self.GUI_manager.pop()
            elif evento.type == pag.MOUSEBUTTONDOWN and evento.button == 1:
                self.GUI_manager.click((mx, my))
            return True
        return False
    
    # Para dibujar los objetos de las utilidades
    def draw_objs(self, lista: list[uti_pag.Text|uti_pag.Button|uti_pag.Input|uti_pag.Multi_list|uti_pag.Select_box|uti_pag.Bloque]):
        if self.draw_background:
            self.ventana.fill(self.background_color)
            
        redraw = self.redraw
        self.redraw = False
        if redraw:
            for x in lista:
                x.redraw += 1

        self.updates.clear()
        for i,x in sorted(enumerate(lista+[self.GUI_manager,self.Mini_GUI_manager]),reverse=False): #,self.loader
            re = x.redraw
            r = x.draw(self.ventana)
            for s in r:
                self.updates.append(s)
            for y in r:
                for p in lista[i+1:]:
                    if p.collide(y) and p.redraw < 1:
                        p.redraw = 1
            if self.hitboxes:
                for x in r:
                    pag.draw.rect(self.ventana, 'green', x, 1)
            if re < 2:
                continue
            for y in r:
                for p in lista[:i]:
                    if p.collide(y) and p.redraw < 1:
                        p.redraw = 1
        
        if redraw:
            pag.display.update()
        else:
            pag.display.update(self.updates)

    # Se dibuja todo y listo, pa' que tanto peo
    def draw_always(self, lista):
        if self.draw_background:
            self.ventana.fill(self.background_color)
        for x in lista:
            x.redraw += 1

        new_list = lista+[self.GUI_manager,self.Mini_GUI_manager]
        if self.loading > 0 and self.loader:
            new_list.append(self.loader)

        for i,x in sorted(enumerate(new_list),reverse=False):
            x.draw(self.ventana)

        pag.display.update()

    def screen_main(self):
        if self.screen_main_bool:
            self.cicle_try: int = 0
            self.redraw = True

        while self.screen_main_bool:
            self.relog.tick(60)

            eventos = pag.event.get()
            for evento in eventos:
                if self.eventos_en_comun(evento):
                    self.redraw = True
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.GUI_manager.add(
                            uti_pag.GUI.Desicion(self.ventana_rect.center, self.txts['cerrar'],
                                        'Desea cerrar la ventana de descarga?\n\nLa descarga se podrá reanudar luego.',
                                        (400, 200)),
                            self.cerrar_todo
                        )
                elif evento.type == pag.MOUSEBUTTONDOWN and evento.button == 1 and not self.on_mouse_click_main(evento, self.list_to_click_main):
                    ...
                elif evento.type == pag.MOUSEWHEEL and not self.wheel_event_main(evento,self.list_to_click_main):
                    ...
                elif evento.type == pag.MOUSEBUTTONUP and evento.button == 1:
                    for i,x in sorted(enumerate(self.list_to_click_main), reverse=True):
                        if isinstance(x, (uti_pag.Multi_list,uti_pag.List, uti_pag.Bloque)):
                            x.scroll = False
                elif evento.type == pag.MOUSEMOTION and not self.mouse_motion_event_main(evento,self.list_to_click_main):
                    ...

            self.update_main()

            if not self.drawing:
                continue
            self.ventana.fill((20, 20, 20))
            for x in self.lineas_para_separar:
                pag.draw.line(self.ventana, 'black', x[0], x[1], width=3)

            self.draw_objs(self.list_to_draw_main)

    def update_main(self):
            if self.hilos_listos == self.num_hilos:
                self.finish_download()
            
            self.text_vel_descarga.text = self.txts['velocidad']+': '+uti.format_size_bits_to_bytes_str(self.current_velocity)
            self.text_porcentaje.text = f'{(self.peso_descargado / self.peso_total) * 100:.2f}%'
            self.text_peso_progreso.text = self.txts['descargado']+': '+ uti.format_size_bits_to_bytes_str(self.peso_descargado)
            self.barra_progreso.volumen = self.peso_descargado / self.peso_total

            if self.cerrando and self.num_hilos > 1:
                self.text_finalizando_hilos2. text = f'Restantes: {self.downloading_threads}'

            mx,my = pag.mouse.get_pos()
            for i,x in sorted(enumerate(self.list_to_update_main), reverse=True):
                x.update(dt=1,mouse_pos=(mx,my))

            if self.downloading:
                for i,x in sorted(enumerate(self.lista_status_hilos), reverse=False):
                    self.list_textos_hilos[1][i] = f'{int(x["local_count"])/self.division * 100:.2f}%'


            self.GUI_manager.update()
            self.Mini_GUI_manager.update()
            self.GUI_manager.update_hover(mouse_pos=(mx,my))
            self.Mini_GUI_manager.update_hover(mouse_pos=(mx,my))

    def wheel_event_main(self,evento,lista):
        for i,x in sorted(enumerate(lista), reverse=True):
            if isinstance(x, (uti_pag.Multi_list,uti_pag.List,uti_pag.Bloque)) and not x.scroll and x.rect.collidepoint(pag.mouse.get_pos()):
                x.rodar(evento.y*15)
                return True
        # aqui va el codigo que el programador desee (recordar acabar con return True para que no ejecute el resto de eventos)
        return False
    def mouse_motion_event_main(self,evento, lista):
        for i,x in sorted(enumerate(lista), reverse=True):
            if isinstance(x, (uti_pag.Multi_list, uti_pag.List, uti_pag.Bloque)) and x.scroll:
                x.rodar_mouse(evento.rel[1])
                return True
            
        # aqui va el codigo que el programador desee (recordar acabar con return True para que no ejecute el resto de eventos)
        return False 
    def on_mouse_click_main(self,evento,lista):
        for i,x in sorted(enumerate(lista), reverse=True):
            if isinstance(x, (uti_pag.Multi_list,uti_pag.List)) and x.click(evento.pos,pag.key.get_pressed()[pag.K_LCTRL]):
                self.redraw = True
                return True
            elif x.click(evento.pos):
                self.redraw = True
                return True
        # aqui va el codigo que el programador desee (recordar acabar con return True para que no ejecute el resto de eventos)
        return False

    def set_select_options(self):
        self.select_more_options.options = [
            self.txts['apagar-al-finalizar'] + ': ' + (self.txts['si'] if self.apagar_al_finalizar else 'No'),
            self.txts['ejecutar-al-finalizar'] + ': ' + (self.txts['si'] if self.ejecutar_al_finalizar else 'No'),
            self.txts['limitar-velocidad'] + ': ' + uti.format_size_bits_to_bytes_str(self.velocidad_limite)
        ]

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
            self.GUI_manager.add(
                uti_pag.GUI.Desicion(self.ventana_rect.center, 'Error',
                            'El servidor no responde\n\nDesea volver a intentarlo?', (400, 200)),
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

    def update_progress_db(self):
        if self.peso_descargado == 0 or not self.downloading:
            return
        progreso = (self.peso_descargado / self.peso_total)
        self.prepared_session.get(f'http://127.0.0.1:5000/descargas/update/estado/{self.id}/{f'{progreso * 100:.2f}%' if float(progreso) < 1.0 else 'Completado'}')

    def func_pausar(self):
        self.paused = True
        self.last_change = time.time()
        self.downloading = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["pausado"]}'

    def func_cancelar(self, result):
        if result == 'cancelar':
            return
        self.paused = False
        self.canceled = True
        self.cerrar_todo('aceptar')

    def func_reanudar(self):
        if not self.can_download: return
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.text = self.txts['pausar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.text_estado_general.text = f"{self.txts['estado']}: {self.txts['esperando']}..."
        self.start_download()

    def cerrar_todo(self, result):
        if result == 'cancelar' or self.cerrando:
            return
        self.cerrando = True
        self.paused = False
        self.canceled = True
        self.Func_pool.start('__terminar_programa')
        
    def __terminar_de_cerrar(self):
        self.text_finalizando_hilos.pos = pag.Vector2(RESOLUTION)//2
        self.text_finalizando_hilos2.pos = (self.text_finalizando_hilos.centerx, self.text_finalizando_hilos.bottom+10)
        self.loading += 1
        self.pool_hilos.shutdown(True, cancel_futures=True)
        self.update_progress_db()
        self.screen_main_bool: bool = False


    def func_abrir_carpeta_antes_de_salir(self, resultado):
        if resultado == 'aceptar':
            if not self.fallo_destino:
                file = Path(self.save_dir)/self.file_name
            else:
                file = user_downloads_path()/self.file_name
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
                self.GUI_manager.add(uti_pag.GUI.Info(self.ventana_rect.center, 'Error', self.txts['numero invalido'], (300,125)))


    def crear_conexion(self):
        self.can_download = False
        self.downloading = False
        self.text_estado_general.text = self.txts['descripcion-state[conectando]']
        try:
            response = self.prepared_session.get(self.url, stream=True, allow_redirects=True, timeout=30, headers=self.default_headers)
            print(response.headers)

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
                    uti_pag.GUI.Info(self.ventana_rect.center, 'Error',self.txts['gui-no se puede reanudar']))

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            if self.modificador == 2:
                self.intentos += 1
                if self.intentos > 10:
                    self.cerrar_todo('a')
            else:
                self.GUI_manager.add(
                    uti_pag.GUI.Desicion(
                        self.ventana_rect.center, 'Error','El servidor no responde\n\nDesea volver a intentarlo?', (400, 200)),
                    lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
                )
        except (requests.exceptions.MissingSchema, DifferentTypeError, LowSizeError) as err:
            print(type(err))
            print(err)
            self.GUI_manager.add(
                uti_pag.GUI.Info(self.ventana_rect.center, 'Error', self.txts['gui-url no sirve']),self.cerrar_todo
            )
        except Exception as err:
            print(type(err))
            print(err)
            self.GUI_manager.add(
                uti_pag.GUI.Desicion(self.ventana_rect.center, 'Error', self.txts['gui-error inesperado'], (400, 200)),
                lambda r: (self.Func_pool.start('descargar') if r == 'aceptar' else self.cerrar_todo('a'))
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
        # text_var = self.list_textos_hilos[0][num]
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
        if self.can_reanudar:
            this_header = self.default_headers.copy()
            this_header['Range'] = f'bytes={self.lista_status_hilos[num]["start"] + self.lista_status_hilos[num]["local_count"]}-{self.lista_status_hilos[num]["end"]}'
        else:
            this_header = self.default_headers.copy()
            this_header.pop('Range')
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

        self.peso_descargado = self.peso_total
        self.update_progress_db()

        self.downloading = False
        self.can_download = True
        self.drawing = True
        self.finished = True
        self.hilos_listos = 0
        global RETURNCODE
        RETURNCODE = 3
        self.list_vels.clear()
        self.text_estado_general.text = f'{self.txts["estado"]}: {self.txts["finalizado"]}'
        self.btn_pausar_y_reanudar_descarga.text = self.txts['reanudar']
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar


        if self.cerrar_al_finalizar or self.prepared_session.get(f'http://127.0.0.1:5000/descargas/check/{self.id}').json()['cola']:
            self.cerrar_todo('aceptar')
        elif self.apagar_al_finalizar:
            subprocess.call(f'shutdown /s /t 30 Descarga finalizada - {self.file_name}', shell=True)
            self.cerrar_todo('aceptar')
            return
        elif self.ejecutar_al_finalizar:
            os.startfile(self.save_dir + '/' + self.file_name)
            self.cerrar_todo('aceptar')
            return
        self.GUI_manager.add(
            uti_pag.GUI.Desicion(self.ventana_rect.center, self.txts['enhorabuena'], self.txts['gui-desea_abrir_la_carpeta'], (400, 200)),
            self.func_abrir_carpeta_antes_de_salir
        )
        if self.enfoques:
            uti.win32_tools.front2(pag.display.get_wm_info()['window'])

if __name__ == '__main__' and len(sys.argv) > 1:
    clase = Downloader(*sys.argv[1:])