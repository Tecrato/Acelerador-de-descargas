import pygame as pag, sys, os, time, requests, json, sqlite3
from platformdirs import user_downloads_dir, user_cache_path, user_config_path
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pygame.locals import MOUSEBUTTONDOWN, K_ESCAPE, QUIT, SCALED, KEYDOWN, MOUSEWHEEL


import Utilidades

from Utilidades import Create_text,Create_boton, Barra_de_progreso
from Utilidades import GUI
from Utilidades import multithread
from textos import idiomas

pag.init()


class My_Execption(Exception):
    """Trajo un texto"""
    def __init__(self, mensaje) -> None:
        super().__init__(mensaje)
    

class Downloader:
    def __init__(self,id) -> None:

        self.ventana = pag.display.set_mode((800,400), SCALED)
        self.ventana_rect = self.ventana.get_rect()
        pag.display.set_icon(pag.image.load('./descargas.png'))

        
        self.carpeta_cache = user_cache_path('Acelerador de descargas','Edouard Sandoval')
        self.carpeta_cache.mkdir(parents=True, exist_ok=True)
        self.carpeta_config = user_config_path('Acelerador de descargas','Edouard Sandoval')
        self.carpeta_config.mkdir(parents=True, exist_ok=True)


        self.Database = sqlite3.Connection(self.carpeta_config.joinpath('./downloads.sqlite3'))
        self.DB_cursor = self.Database.cursor()
        self.DB_cursor.execute('SELECT * FROM descargas WHERE id=?',[id])
        self.raw_data = self.DB_cursor.fetchone()

        self.id:int = self.raw_data[0]
        self.file_name:str = self.raw_data[1]
        self.type:str = self.raw_data[2]
        self.peso_total:int = self.raw_data[3]
        self.url:str = self.raw_data[4]
        self.num_hilos:int = self.raw_data[5]
        self.tiempo:float = float(self.raw_data[6])
        self.estado:str = self.raw_data[7]

        self.pool_hilos = ThreadPoolExecutor(self.num_hilos,'downloader')

        self.division = self.peso_total // self.num_hilos
        self.peso_total_formateado = self.format_size(self.peso_total)
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
        self.surface_hilos = pag.Surface((self.ventana_rect.w//2,self.ventana_rect.h-70))
        self.surface_hilos.fill((20,20,20))
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


        self.prepared_request = requests.Request('GET','https://www.google.com').prepare()
        self.prepared_session = requests.session()
        

        self.cargar_configs()

        self.idioma = 'español'
        self.txts = idiomas[self.idioma]
        self.font_mononoki = 'C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf'
        self.font_simbols = 'C:/Users/Edouard/Documents/fuentes/Symbols.ttf'


        self.generate_objs()
        self.Func_pool.start('descargar')

        self.ciclo_general = [self.main_cycle]
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

        # self.Func_pool.add('descargar detalles del url', self.func_detalles_archivo)
        self.Func_pool.add('descargar', self.crear_conexion,self.start_download)

        self.lineas_para_separar = [
            ((self.ventana_rect.centerx,0),(self.ventana_rect.centerx,self.ventana_rect.h)),
            ((0,self.ventana_rect.centery),self.ventana_rect.center)]

        # ------------------------------------------- Textos y botones -----------------------------------

        self.Titulo = Create_text(self.file_name, 16, self.font_mononoki, (30,100), 'left')
        self.text_tamaño = Create_text(self.txts['descripcion-peso'].format(f'{self.peso_total_formateado[1]:.2f}{self.nomenclaturas[self.peso_total_formateado[0]]}'), 12, self.font_mononoki, (30,120), 'left')
        self.text_url = Create_text(f'url: {self.url}', 12, self.font_mononoki, (30,140), 'left')
        self.text_num_hilos = Create_text(self.txts['descripcion-numero_hilos'].format(self.num_hilos), 12, self.font_mononoki, (30,160), 'left')
        self.text_estado_general = Create_text(self.txts['descripcion-state[esperando]'], 12, self.font_mononoki, (30,180), 'left')

        self.text_porcentaje = Create_text('0.00%', 16, self.font_mononoki, (200,self.ventana_rect.bottom-90), 'center')
        self.text_peso_progreso = Create_text('0 - 0b', 16, self.font_mononoki, (200,self.ventana_rect.bottom-70), 'center')
        self.text_title_hilos = Create_text(self.txts['title_hilos'], 20, self.font_mononoki, (600, 30), 'center')


        self.btn_cancelar_descarga = Create_boton(self.txts['btn-cancelar'], 20, self.font_mononoki, ((800/2)/3,60), (20,10), 'center', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.func_cancelar)
        
        self.btn_pausar_y_reanudar_descarga = Create_boton(self.txts['btn-reanudar'], 20, self.font_mononoki, (((800/2)/3)*2,60), (20,10), 'center', 'black', 
                                        'purple', 'cyan', 0, 0, 20, 0, 0, 20, -1, func=self.func_reanudar)
    
        #   Barra de progreso
        self.barra_progreso = Barra_de_progreso((20, self.ventana_rect.bottom-50), (360,20), 'horizontal')
        self.barra_progreso.set_volumen(.0)


        self.list_to_draw = [self.Titulo,self.text_tamaño,self.text_url,self.text_num_hilos,self.barra_progreso,
                             self.text_porcentaje, self.text_estado_general,self.btn_cancelar_descarga,self.text_title_hilos,
                             self.text_peso_progreso,self.btn_pausar_y_reanudar_descarga]
        self.list_to_click = [self.btn_cancelar_descarga,self.btn_pausar_y_reanudar_descarga]


    def cargar_configs(self):
        
        progreso = (self.peso_descargado/self.peso_total)
        self.estado = f'{progreso*100:.2f}%'
        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?',[f'{progreso*100:.2f}%',self.id])
        self.Database.commit()

        try:
            self.configs:dict = json.load(open(self.carpeta_config.joinpath('./configs.json')))
        except:
            self.configs = {}
        self.idioma = self.configs.get('idioma','español')
    
    
    def format_size(self,size) -> list:
        count = 0
        while size > 1024:
            size /= 1024
            count +=1
        return [count, size]

    def func_pausar(self) -> None:
        self.paused = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        progreso = (self.peso_descargado/self.peso_total)
        self.estado = f'{progreso*100:.2f}%'
        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?',[f'{progreso*100:.2f}%',self.id])
        self.Database.commit()
    def func_cancelar(self) -> None:
        if not self.downloading:
            return 0
        self.paused = False
        self.canceled = True
        self.downloading = False
        self.can_download = True
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-reanudar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
        progreso = (self.peso_descargado/self.peso_total)
        self.estado = f'{progreso*100:.2f}%'
        self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?',[f'{progreso*100:.2f}%',self.id])
        self.Database.commit()
        for num in range(self.num_hilos):
            self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
        self.GUI_manager.add(
            GUI.Desicion(self.ventana_rect.center,'Cerrar', 'Desea cerrar la ventana de descarga?\nLa descarga se podra reanudar luego.'),
            self.cerrar_todo
        )
        
    def func_abrir_carpeta_antes_de_salir(self,resultado):
        if resultado == 'aceptar':
            os.startfile(user_downloads_dir())
        self.cerrar_todo('a')

    def cerrar_todo(self,result):
        if result == 'cancelar': return 0
        self.paused = False
        self.canceled = True
        pag.quit()
        sys.exit()
    def func_reanudar(self) -> None:
        if not self.can_download: return 0
        self.paused = False
        self.canceled = False
        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        self.reanudar_bool = True
        self.start_download()

    def crear_conexion(self):
        self.text_estado_general.change_text(self.txts['descripcion-state[conectando]'])
        try:
            response = requests.get(self.url, stream=True, allow_redirects=True, timeout=15)
            self.prepared_request = response.request
            response = self.prepared_session.send(self.prepared_request,stream=True, allow_redirects=True, timeout=15)

            self.can_download = True
        except requests.exceptions.ConnectionError:
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, 'Error', 'A ocurrido un error al conectar con el servidor\n\nDesea volver a intentarlo?'),
                self.Func_pool.start('descargar')
            )
        except Exception as err:
            # print(err)
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, 'Error', 'A ocurrido un error inesperado\n\nDesea volver a intentarlo?'),
                self.Func_pool.start('descargar')
            )
        


    def start_download(self) -> None:
        if not self.can_download: return 0
        if self.downloading: return 0
        self.paused = False
        self.canceled = False
        self.downloading = True
        self.hilos_listos = 0
        self.peso_descargado = 0

        # self.lista_hilos.clear()
        self.lista_status_hilos.clear()
        for x in range(self.num_hilos):
            if not self.reanudar_bool:
                try:
                    os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
                except:
                    pass
                
            self.lista_status_hilos.append(Create_text(self.txts['status_hilo[iniciando]'].format(x), 16, self.font_mononoki, (50,40*x +50), 'left'))
            if x == self.num_hilos-1:
                self.surf_h_max = self.lista_status_hilos[-1].rect.bottom
            self.lista_status_hilos_text.append(self.txts['status_hilo[iniciando]'].format(x))

            self.pool_hilos.submit(self.download_thread, x,
                        self.division*x,
                        self.division*x + self.division - 1 if x < self.num_hilos - 1 else self.peso_total - 1
                        )

        self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-pausar'])
        self.btn_pausar_y_reanudar_descarga.func = self.func_pausar
        
        self.text_estado_general.change_text(self.txts['descripcion-state[descargando]'])

    def download_thread(self,num, start, end, local_count = 0, tiempo_reset = 2):
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
            if local_count >= end-start-10:
                self.hilos_listos += 1
                self.lista_status_hilos_text[num] = self.txts['status_hilo[finalizado]'].format(num)
                return 0
        headers = {'Range': f'bytes={start+local_count}-{end}'}
        try:
            self.lista_status_hilos_text[num] = self.txts['status_hilo[conectando]'].format(num)
            re = self.prepared_request.copy()
            re.prepare_headers(headers)
            response = self.prepared_session.send(re,stream=True,allow_redirects=True,timeout=15)

            tipo = response.headers.get('Content-Type','text/plain;a').split(';')[0]
            if tipo != self.type:
                # print(tipo,self.type, response.headers)
                raise My_Execption('Trajo un texto')

            

            tipo = response.headers.get('content-length',False)
            if int(tipo) < 1024//8: 
                raise Exception('Peso muy pequeño')
            
            tiempo_reset = 2
            self.lista_status_hilos_text[num] = self.txts['status_hilo[descargando]'].format(num)
            
            with open(self.carpeta_cache.joinpath(f'./parte{num}.tmp'),'ab') as file_p:
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
            # print(err)
            # print(type(err))


            if self.canceled:
                self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
                return 0
            self.lista_status_hilos_text[num] = self.txts['status_hilo[reconectando]'].format(num)
            t = time.time()
            while time.time()-t < tiempo_reset:
                if self.canceled:
                    self.lista_status_hilos_text[num] = self.txts['status_hilo[cancelado]'].format(num)
                    return 0
                time.sleep(.3)
            return self.download_thread(num,start,end,local_count,(tiempo_reset*2) if tiempo_reset < 30 else tiempo_reset)


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
                        x.click((mx,my))
                elif evento.type == MOUSEWHEEL and mx > self.ventana_rect.centerx:
                    if -self.surf_h_max + 300 < self.surf_h_diff + evento.y*20 < 0:
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
                        with open(self.carpeta_cache.joinpath(f'./parte{x}.tmp'),'rb') as parte:
                            file.write(parte.read())
                        os.remove(self.carpeta_cache.joinpath(f'./parte{x}.tmp'))
                    file.close()
                os.rmdir(self.carpeta_cache)
                
                self.pool_hilos.shutdown()
                
                self.can_download = True
                self.hilos_listos = 0
                self.peso_descargado = 0
                self.text_estado_general.change_text(self.txts['descripcion-state[finalizado]'])
                self.btn_pausar_y_reanudar_descarga.change_text(self.txts['btn-reanudar'])
                self.btn_pausar_y_reanudar_descarga.func = self.func_reanudar
                
                self.DB_cursor.execute('UPDATE descargas SET estado=? WHERE id=?',['Completado',self.id])
                self.Database.commit()

                if self.apagar_al_finalizar:
                    self.paused = False
                    self.canceled = True
                    self.screen_main = False
                    os.system('shutdown /s /t 10')
                    pag.quit()
                    sys.exit()
                else:
                    self.GUI_manager.add(
                        GUI.Desicion(self.ventana_rect.center, 'Enhorabuena', 'La descarga ah finalizado\n\nDesea ir a la carpeta de las descargas?'),
                        self.func_abrir_carpeta_antes_de_salir
                    )
                    

            for x in self.list_to_draw:
                x.draw(self.ventana)

            
            self.surface_hilos.fill((20,20,20))
            for i,x in enumerate(self.lista_status_hilos):
                x.change_text(self.lista_status_hilos_text[i])
                x.draw(self.surface_hilos)
            self.ventana.blit(self.surface_hilos,(self.ventana_rect.centerx,70))
            for x in self.lineas_para_separar:
                pag.draw.line(self.ventana, 'black', x[0],x[1], width=3)

            self.GUI_manager.draw(self.ventana,(mx,my))

            pag.display.flip()
            self.relog.tick(60)

if __name__=='__main__':
    clase = Downloader(*sys.argv[1:])