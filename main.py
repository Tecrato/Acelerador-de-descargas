import pygame as pag, sys, os, time, requests
from platformdirs import user_downloads_dir, user_cache_path
from threading import Thread
from pathlib import Path
from pygame.locals import MOUSEBUTTONDOWN, MOUSEBUTTONUP, K_ESCAPE, QUIT, SCALED, KEYDOWN, MOUSEWHEEL

import Utilidades

from Utilidades import Create_text,Create_boton, Barra_de_progreso
from Utilidades import GUI
from Utilidades import multithread
from textos import idiomas

pag.init()

carpeta_cache = Path(user_cache_path('Acelerador de descargar','Edouard Sandoval'))
carpeta_cache.mkdir(parents=True, exist_ok=True)
carpeta_cache.joinpath('/')


class My_Execption(Exception):
    """Trajo un texto"""
    def __init__(self, mensaje) -> None:
        super().__init__(mensaje)
    

class Download_manager:
    def __init__(self) -> None:

        self.ventana = pag.display.set_mode((800,600), SCALED)
        self.ventana_rect = self.ventana.get_rect()

        self.url = ''
        self.division = 0
        self.paused = False
        self.canceled = False
        self.screen_main = True
        self.screen_config_bool = False
        self.can_download = False
        self.downloading = False
        self.relog = pag.time.Clock()
        self.font_mononoki = './Assets/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        self.font_simbols = './Assets/fuentes/Symbols.ttf'
        self.file_name = ''
        self.idioma = 'español'
        self.txts = idiomas[self.idioma]
        self.button1_mouse_time = 0
        self.button1_mouse_func = None
        
        self.num_hilos = 8
        self.hilos_listos = 0
        self.lista_hilos: list[Thread] = []
        self.lista_status_hilos: list[Create_text] = []
        self.lista_status_hilos_text: list[str] = []
        self.surface_hilos = pag.Surface((self.ventana_rect.w//2,self.ventana_rect.h-70))
        self.surface_hilos.fill((20,20,20))
        self.surf_h_diff = 0
        self.surf_h_max = 1

        self.peso_total = 0
        self.peso_total_formateado = [0,0]
        self.peso_descargado = 0


        self.prepared_request = requests.Request('GET','https://www.google.com').prepare()
        self.prepared_session = requests.session()

        self.nomenclaturas = {
            0: 'bytes',
            1: 'Kb',
            2: 'Mb',
            3: 'Gb',
            4: 'Tb'
        }

        self.generate_objs()
        self.bienvenida()

        self.ciclo_general = [self.main_cycle,self.screen_config]
        self.cicletry = 0

        while self.cicletry < 5:
            self.cicletry += 1
            for x in self.ciclo_general:
                x()

    def generate_objs(self) -> None:
        # Cosas varias
        Utilidades.GUI.configs['fuente_simbolos'] = self.font_simbols
        self.GUI_manager = GUI.GUI_admin()
        self.Func_pool = multithread.Funcs_pool()

        self.Func_pool.add('descargar detalles del url', self.func_detalles_archivo)

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx,0),(self.ventana_rect.centerx,self.ventana_rect.h)),
            ((0,self.ventana_rect.centery),self.ventana_rect.center)]

        # Textos y botones 
        # Main Cycle
        self.Titulo = Create_text('Titulo: Hola :)', 16, self.font_mononoki, (30,100), 'left')
        self.btn_config = Create_boton('', 14, self.font_simbols, (10,10), 20, 'topleft', 'white', (20,20,20), (50,50,50), 0, -1, border_width=-1, func=self.func_to_config)
        self.text_tamaño = Create_text(self.txts['descripcion-peso'].format(f'0.00bytes'), 12, self.font_mononoki, (30,120), 'left')
        self.text_url = Create_text('url: http:// -------', 12, self.font_mononoki, (30,140), 'left')
        self.text_num_hilos = Create_text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12, self.font_mononoki, (30,160), 'left')
        self.text_estado_general = Create_text(self.txts['descripcion-state[esperando]'], 12, self.font_mononoki, (30,180), 'left')

        self.text_porcentaje = Create_text('0.00%', 16, self.font_mononoki, (200,self.ventana_rect.bottom-90), 'center')
        self.text_peso_progreso = Create_text('0 - 0b', 16, self.font_mononoki, (200,self.ventana_rect.bottom-70), 'center')
        self.text_title_hilos = Create_text(self.txts['title_hilos'], 20, self.font_mononoki, (600, 30), 'center')

        self.btn_get_url = Create_boton(self.txts['btn-nueva_url'], 20, self.font_mononoki, (100,60), (20,10), 'center', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda: (
            self.GUI_manager.add(GUI.Text_return(self.ventana_rect.center, 'Nueva direccion de descarga', 'Ingrese la URL del archivo', True), 
                                 lambda text: self.func_nueva_url(text)
        )))

        self.btn_iniciar_cancelar_descarga = Create_boton(self.txts['btn-iniciar'], 20, self.font_mononoki, (230,60), (20,10), 'center', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.start_download)
        
        self.btn_pausar_y_reanudar_descarga = Create_boton(self.txts['btn-pausar'], 20, self.font_mononoki, (340,60), (20,10), 'center', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.start_download)
    
        #   Barra de progreso
        self.barra_progreso = Barra_de_progreso((20, self.ventana_rect.bottom-50), (360,20), 'horizontal')
        self.barra_progreso.set_volumen(.0)


        # Configuraciones
        self.title_config = Create_text(self.txts['title-configuraciones'],30, self.font_mononoki, (self.ventana_rect.centerx,50))
        self.btn_exit_config = Create_boton('', 14, self.font_simbols, (10,10), 20, 'topleft', 'white', (20,20,20), (50,50,50), 0, -1, border_width=-1, func=self.func_to_main_from_config)
        self.config_version = Create_text('Version: 1.1',16, self.font_mononoki, (20,self.ventana_rect.h-20),'left')

        self.text_config_hilos = Create_text(self.txts['config-hilos'].format(self.num_hilos),16, self.font_mononoki, (20,100), 'left')
        self.btn_mas_hilos = Create_boton('',14, self.font_simbols, (self.text_config_hilos.rect.right + 10,self.text_config_hilos.rect.centery), (5,0), 'bottom', 'white', color_rect_active=(40,40,40), border_radius=0, border_width=-1, toggle_rect=True, func=lambda: self.func_change_hilos('up'))
        self.btn_menos_hilos = Create_boton('',14, self.font_simbols, (self.text_config_hilos.rect.right + 10,self.text_config_hilos.rect.centery), (5,0), 'top', 'white', color_rect_active=(40,40,40), border_radius=0, border_width=-1, toggle_rect=True, func=lambda: self.func_change_hilos('down'))

        self.text_config_idioma = Create_text(self.txts['config-idioma'],16, self.font_mononoki, (20,130), 'left')
        self.text_config_idioma_es = Create_boton('Español',14, self.font_mononoki, (20,160),(20,10), 'left', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda: self.func_change_idioma('español'))
        self.text_config_idioma_en = Create_boton('English',14, self.font_mononoki, (110,160),(20,10), 'left', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=lambda: self.func_change_idioma('ingles'))



        self.list_to_draw = [self.Titulo, self.btn_get_url,self.text_tamaño,self.text_url,self.text_num_hilos,self.barra_progreso,
                             self.text_porcentaje, self.text_estado_general,self.btn_iniciar_cancelar_descarga,self.text_title_hilos,
                             self.text_peso_progreso,self.btn_pausar_y_reanudar_descarga,self.btn_config]
        self.list_to_click = [self.btn_get_url,self.btn_iniciar_cancelar_descarga,self.btn_pausar_y_reanudar_descarga, self.btn_config]

        self.list_to_draw_config = [self.title_config,self.text_config_hilos,self.btn_mas_hilos, self.btn_menos_hilos,self.btn_exit_config,
                                self.text_config_idioma,self.text_config_idioma_es,self.text_config_idioma_en,self.config_version]
        self.list_to_click_config = [self.btn_mas_hilos,self.btn_menos_hilos,self.btn_exit_config,self.text_config_idioma_es,
                                     self.text_config_idioma_en]

    
    def bienvenida(self):
        self.GUI_manager.add(GUI.Info(self.ventana_rect.center, self.txts['GUI-bienvenida_title'], self.txts['GUI-bienvenida_contenido']))


    def format_size(self,size) -> list:
        count = 0
        while size > 1024:
            size /= 1024
            count +=1
        return [count, size]

    def func_to_config(self) -> None:
        self.screen_config_bool = True
        self.screen_main = False
    def func_to_main_from_config(self) -> None:
        self.screen_config_bool = False
        self.screen_main = True

    def func_change_hilos(self, dir):
        if dir == 'up' and self.num_hilos < 32:
            self.num_hilos += 1
        elif dir == 'down' and self.num_hilos > 1:
            self.num_hilos -= 1
        self.text_config_hilos.change_text(self.txts['config-hilos'].format(self.num_hilos))
        self.text_num_hilos.change_text(self.txts['descripcion-numero_hilos'].format(self.num_hilos))
        # match dir:
        #     case 'up':
        #         self.num_hilos += 1
        #     case 'down':
        #         if 
        #         self.num_hilos -= 1

    def func_change_idioma(self,idioma):
        self.idioma = idioma
        self.txts = idiomas[self.idioma]
        self.generate_objs()

    def func_nueva_url(self, result) -> None:
        self.url = result
        self.paused = True
        self.canceled = True
        self.Func_pool.start('descargar detalles del url')

    def func_pausar(self) -> None:
        self.paused = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
    def func_cancelar(self) -> None:
        self.paused = False
        self.canceled = True
        self.downloading = False
        self.can_download = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.btn_iniciar_cancelar_descarga.change_text(self.txts['btn-iniciar'])
        self.btn_iniciar_cancelar_descarga.func = self.start_download
        for num in range(self.num_hilos):
            self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
    def func_reanudar(self) -> None:
        self.paused = False
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

    def func_detalles_archivo(self,tiempo_reanudar = 2) -> None:
        self.can_download = False
        self.paused = True
        self.canceled = True

        title = self.url.split('/')[-1].replace('%20',' ').replace('%28','(').replace('%29',')').replace('%5B',
        '[').replace('%5D',']').replace('%21','!')
        if len(title) > 40: title = title[:40]

        self.Titulo.change_text(f'{title}')
        self.text_url.change_text(self.url if len(self.url) < 40 else self.url[:40] + '...')
        self.text_estado_general.change_text(self.txts['descripcion-state[conectando]'])
        self.peso_total = 1
        self.peso_descargado = 0
        self.barra_progreso.set_volumen(.0)
        try:
            response = requests.get(self.url, stream=True, allow_redirects=True, timeout=15)
            self.prepared_request = response.request
            response = self.prepared_session.send(self.prepared_request,stream=True, allow_redirects=True, timeout=15)
            print(response.headers)
            tipo = response.headers.get('Content-Type',False).split(';')
            if 'text/plain' in tipo or 'text/html' in tipo: 
                raise My_Execption('Trajo un texto')
            tiempo_reanudar = 2
            peso = int(response.headers.get('content-length', 1))
            peso_formateado = self.format_size(peso)
            self.peso_total = peso
            self.peso_total_formateado = self.format_size(self.peso_total)
            self.text_tamaño.change_text(self.txts['descripcion-peso'].format(f'{peso_formateado[1]:.2f}{self.nomenclaturas[peso_formateado[0]]}'))
            try:
                if (a := response.headers.get('Content-Disposition', False)):
                    self.Titulo.change_text(a.split('filename=')[1].replace('"',''))
            except Exception as e:
                pass
            self.text_estado_general.change_text(self.txts['descripcion-state[disponible]'])
            self.can_download = True
            self.file_name = self.Titulo.get_text()
            return 1
        except My_Execption as err:
            self.text_estado_general.change_text(self.txts['descripcion-state[error]'])
            return 4
        except requests.URLRequired as err:
            return 2
        except requests.exceptions.MissingSchema as err:
            self.text_estado_general.change_text(self.txts['descripcion-state[url invalida]'])
            return 3
        except requests.exceptions.InvalidSchema as err:
            self.text_estado_general.change_text(self.txts['descripcion-state[url invalida]'])
            return 3
        except requests.exceptions.ReadTimeout as err:
            self.text_estado_general.change_text(self.txts['descripcion-state[tiempo agotado]'])
            return 3
        except requests.exceptions.ConnectTimeout:
            self.text_estado_general.change_text(self.txts['descripcion-state[reintentando]'])
            time.sleep((tiempo_reanudar*2) if tiempo_reanudar < 30 else tiempo_reanudar)
            return self.func_detalles_archivo()
        except requests.exceptions.ConnectionError as err:
            self.text_estado_general.change_text(self.txts['descripcion-state[error internet]'])
            return 3
        except Exception as err:
            print(err)
            print(type(err))
            self.text_estado_general.change_text(self.txts['descripcion-state[error]'])
            return 0

    def start_download(self) -> None:
        if not self.can_download: return 0
        if self.downloading: return 0
        self.paused = False
        self.canceled = False
        self.downloading = True
        self.hilos_listos = 0
        self.peso_descargado = 0
        self.division = self.peso_total // self.num_hilos
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar

        self.lista_hilos.clear()
        self.lista_status_hilos.clear()
        for x in range(self.num_hilos):
            try:
                os.remove(carpeta_cache.joinpath(f'./parte{x}.tmp'))
            except:
                pass
                
            self.lista_status_hilos.append(Create_text(self.txts['status_hilo[iniciando]'].format(x), 16, self.font_mononoki, (50,40*x +50), 'left'))
            if x == self.num_hilos-1:
                self.surf_h_max = self.lista_status_hilos[-1].rect.bottom
            self.lista_status_hilos_text.append(self.txts['status_hilo[iniciando]'].format(x))
            self.lista_hilos.append(
                Thread(
                    target=self.download_thread,
                    args=(x,
                        self.division*x,
                        self.division*x + self.division - 1 if x < self.num_hilos - 1 else self.peso_total - 1
                        )
                    )
                )
        for x in self.lista_hilos:
            x.start()
        self.btn_iniciar_cancelar_descarga.change_text(self.txts['btn-cancelar'])
        self.btn_iniciar_cancelar_descarga.func = self.func_cancelar

    def download_thread(self,num, start, end, local_count = 0, tiempo_reset = 2):
        if self.paused:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[pausado]'].format(num)
            while self.paused:
                time.sleep(1)
        if self.canceled:
            os.remove(carpeta_cache.joinpath(f'./parte{num}.tmp'))
            return 0
        self.lista_status_hilos_text[num] = self.txts['status_hilo[iniciando]'].format(num)
        headers = {'Range': f'bytes={start+local_count}-{end}'}
        try:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[conectando]'].format(num)
            re = self.prepared_request.copy()
            re.prepare_headers(headers)
            response = self.prepared_session.send(re,stream=True,allow_redirects=True,timeout=15)

            tipo = response.headers.get('Content-Type','a;text/plain').split(';')
            if 'text/plain' in tipo or 'text/html' in tipo: 
                raise My_Execption('Trajo un texto')
            

            tipo1 = response.headers.get('content-length',False)
            tipo = int(response.headers.get('Content-Length',False)) if not tipo1 else int(tipo1)
            if int(tipo) < 1024//8: 
                raise Exception('Peso muy pequeño')
            
            tiempo_reset = 2
            self.lista_status_hilos_text[num] = self.txts['status_hilo[descargando]'].format(num)
            
            with open(carpeta_cache.joinpath(f'./parte{num}.tmp'),'ab') as file_p:
                for data in response.iter_content(1024//8):
                    if self.paused or self.canceled: raise Exception('')
                    if data:
                        local_count += len(data)
                        self.peso_descargado += len(data)
                        file_p.write(data)


            self.lista_status_hilos_text[num] = self.txts['status_hilo[finalizado]'].format(num)
            self.hilos_listos += 1
            return 0
        except Exception as err:
            print(err)
            print(type(err))


            if self.canceled:
                os.remove(carpeta_cache.joinpath(f'./parte{num}.tmp'))
                return 0
            self.lista_status_hilos_text[num] = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time()-t < tiempo_reset:
                if self.canceled:
                    os.remove(carpeta_cache.joinpath(f'./parte{num}.tmp'))
                    return 0
                time.sleep(.3)
            return self.download_thread(num,start,end,local_count,(tiempo_reset*2) if tiempo_reset < 30 else tiempo_reset)


    def screen_config(self):
        if self.screen_config_bool:
            self.cicletry = 0
            self.button1_mouse_func = None
        while self.screen_config_bool:
            mx,my = pag.mouse.get_pos()
            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)

            for evento in eventos:
                if evento.type == QUIT:
                    self.paused = False
                    self.canceled = True
                    pag.quit()
                    sys.exit()
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx,my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.screen_config_bool = False
                        self.screen_main = True
                        break
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click_config:
                        if x.rect.collidepoint((mx,my)):
                            x.click()
                            self.button1_mouse_func = x.func
                    self.button1_mouse_time = time.time()
                elif evento.type == MOUSEBUTTONUP and evento.button == 1:
                    self.button1_mouse_func = None

            if self.button1_mouse_func and time.time()-self.button1_mouse_time > .5:
                self.button1_mouse_time = time.time()-.45
                self.button1_mouse_func()

            self.ventana.fill((20,20,20))
            for x in self.list_to_draw_config:
                x.draw(self.ventana)
                
            pag.display.flip()
            self.relog.tick(30)


    def main_cycle(self) -> None:
        if self.screen_main:
            self.cicletry = 0
        while self.screen_main:
            self.ventana.fill((20,20,20))
            mx,my = pag.mouse.get_pos()

            eventos = pag.event.get()
            self.GUI_manager.input_update(eventos)

            for evento in eventos:
                if evento.type == QUIT:
                    self.paused = False
                    self.canceled = True
                    pag.quit()
                    sys.exit()
                elif self.GUI_manager.active >= 0:
                    if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                        self.GUI_manager.pop()
                    elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                        self.GUI_manager.click((mx,my))
                elif evento.type == KEYDOWN:
                    if evento.key == K_ESCAPE:
                        self.paused = False
                        self.canceled = True
                        pag.quit()
                        sys.exit()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                    for x in self.list_to_click:
                        if x.rect.collidepoint((mx,my)):
                            x.click()
                elif evento.type == MOUSEBUTTONDOWN and evento.button == 3:
                    self.idioma = 'ingles'
                    self.txts = idiomas[self.idioma]
                    self.generate_objs()
                elif evento.type == MOUSEWHEEL and mx > self.ventana_rect.centerx:
                    if -(self.ventana_rect.h-70-self.surf_h_max) < self.surf_h_diff + evento.y*20 < 0:
                        self.surf_h_diff += evento.y*20
                        for x in self.lista_status_hilos:
                            x.move_rel((0,evento.y*20))


            if self.peso_total > 0:
                progreso = (self.peso_descargado/self.peso_total)
                self.text_porcentaje.change_text(f'{progreso*100:.2f}%')
                descargado = self.format_size(self.peso_descargado)
                self.text_peso_progreso.change_text(f'{descargado[1]:.2f}{self.nomenclaturas[descargado[0]]} - {self.peso_total_formateado[1]:.2f}{self.nomenclaturas[self.peso_total_formateado[0]]}')
                self.barra_progreso.set_volumen(progreso)

            if self.hilos_listos == self.num_hilos:
                self.downloading = False
                
                with open(user_downloads_dir()+'/'+self.file_name,'wb') as file:
                    for x in range(self.num_hilos):
                        with open(carpeta_cache.joinpath(f'./parte{x}.tmp'),'rb') as parte:
                            file.write(parte.read())
                        os.remove(carpeta_cache.joinpath(f'./parte{x}.tmp'))
                    file.close()
                for x in self.lista_hilos:
                    x.join()
                self.can_download = True
                self.hilos_listos = 0
                self.peso_descargado = 0
                self.text_estado_general.change_text(self.txts['descripcion-state[finalizado]'])
                self.GUI_manager.add(
                    GUI.Desicion(self.ventana_rect.center, 'Enhorabuena', 'La descarga ah finalizado\n\nDesea ir a la carpeta de las descargas?'),
                    lambda _: os.startfile(user_downloads_dir())
                )

            for x in self.list_to_draw:
                x.draw(self.ventana)

            
            self.surface_hilos.fill((20,20,20))
            for i,x in enumerate(self.lista_status_hilos):
                # if self.lista_status_hilos_text[i] != x.get_text():
                x.change_text(self.lista_status_hilos_text[i])
                x.draw(self.surface_hilos)
            self.ventana.blit(self.surface_hilos,(self.ventana_rect.centerx,70))
            for x in self.lineas_para_separar:
                pag.draw.line(self.ventana, 'black', x[0],x[1], width=3)

            self.GUI_manager.draw(self.ventana,(mx,my))

            pag.display.flip()
            self.relog.tick(60)

if __name__=='__main__':
    clase = Download_manager()