import pyperclip, datetime, subprocess, shutil, pygame as pag, sys
from threading import Thread
from pygame import Vector2
from tkinter.filedialog import askdirectory
from tkinter.simpledialog import askstring

from Utilidades import GUI, mini_GUI
from Utilidades import win32_tools

from textos import idiomas
from DB import Data_Base

def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


class Other_funcs:
    def download(self,id,mod) -> None:
        self.descargando.append(id)
        # proceso = subprocess.run(f'python Downloader.py "{id}" "{mod}"', shell=True)
        proceso = subprocess.run(f'Downloader.exe "{id}" "{mod}"', shell=True)
        if proceso.returncode == 1 and id in self.cola:
            self.cola.remove(id)
            if len(self.cola) > 0:
                self.init_download(self.cola[0],2)
                self.descargando.append(self.cola[0])
            elif self.apagar_al_finalizar_cola:
                subprocess.call('shutdown /s /t 10 /c "Ah finalizado la cola de descarga - Download Manager by Edouard Sandoval"', shell=True)
                pag.quit()
                sys.exit()
            else:
                if self.enfoques:
                    win32_tools.front2(pag.display.get_wm_info()['window'])
                self.GUI_manager.add(
                    GUI.Info(self.ventana_rect.center, self.txts['completado'],
                             self.txts['gui-cola de descarga completada'],(400,200)))
        else:
            print('NT Bro')
        self.descargando.remove(id)
        DB = Data_Base(self.carpeta_config.joinpath('./downloads.sqlite3'))
        self.reload_lista_descargas(DB.cursor)
        del DB
    def init_download(self,id,mod=0):
            Thread(target=self.download, args=(id,mod)).start()

    def func_select_box(self, respuesta) -> None:
        if not self.cached_list_DB: return
        if len(respuesta['obj']) > 1:
            for x in respuesta['obj']:
                self.func_select_box({'obj': [x], 'index': respuesta['index']})
            return
        else:
            obj_cached = self.cached_list_DB[respuesta['obj'][0]['index']]

        if respuesta['index'] == 0:
            if win32_tools.check_win(f'Downloader {obj_cached[0]}_{obj_cached[1]}'):
                if self.enfoques:
                    win32_tools.front(f'Downloader {obj_cached[0]}_{obj_cached[1]}')
                return
            if obj_cached[0] in self.descargando:
                return
            else:
                self.init_download(obj_cached[0],2 if obj_cached[0] in self.cola else 0)
        elif respuesta['index'] == 1:
            if self.comprobar_descargando(obj_cached):
                return

            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar el elemento']+f'\n\n"{obj_cached[1]}"'),
                lambda r: (self.del_download_DB(*obj_cached[:2], respuesta['obj'][0]['index']) if r == 'aceptar' else None))

        elif respuesta['index'] == 2:
            if self.comprobar_descargando(obj_cached):
                return

            self.new_url_id = obj_cached[0]
            self.screen_new_download(1)
        elif respuesta['index'] == 3:
            pyperclip.copy(obj_cached[4])
            self.Mini_GUI_manager.clear_group('portapapeles')
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Copiado',
                                      self.txts['copiado al portapapeles']),
                group='portapapeles'
            )
        elif respuesta['index'] == 4:
            if obj_cached[0] in self.cola:
                return
            self.cola.append(obj_cached[0])
            self.lista_descargas[5][respuesta['obj'][0]['index']] = f'[{self.cola.index(obj_cached[0])}]'
            
        elif respuesta['index'] == 5:
            if not obj_cached[0] in self.cola:
                return
            self.cola.remove(obj_cached[0])
            self.reload_lista_descargas()
        elif respuesta['index'] == 6:
            self.cola.clear()
            self.reload_lista_descargas()
        elif respuesta['index'] == 7:
            if self.comprobar_descargando(obj_cached):
                return

            shutil.rmtree(self.carpeta_cache.joinpath(f'./{obj_cached[0]}_{"".join(obj_cached[1].split(".")[:-1])}'), True)
            self.DB.update_estado(obj_cached[0], 'esperando')
            self.lista_descargas[4][respuesta['obj'][0]['index']] = self.txts['esperando'].capitalize()
        elif respuesta['index'] == 8:
            if self.comprobar_descargando(obj_cached):
                return

            nombre = askstring(self.txts['nombre'], self.txts['gui-nombre del archivo'],initialvalue=obj_cached[1])
            if not nombre or nombre == '':
                return

            shutil.rmtree(self.carpeta_cache.joinpath(f'./{obj_cached[0]}_{"".join(obj_cached[1].split(".")[:-1])}'), True)

            self.DB.update_nombre(obj_cached[0], nombre)
            self.lista_descargas[0][respuesta['obj']['index']] = nombre
        self.redraw = True


    def comprobar_descargando(self, obj):
        self.Mini_GUI_manager.clear_group('descarga en curso')
        if obj[0] in self.descargando or win32_tools.check_win(f'Downloader {obj[0]}_{obj[1]}'):
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Error',
                                    self.txts['gui-descarga en curso']),
                group='descarga en curso'
            )
            return True
        elif obj[0] in self.cola:
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'botomright', 'Error',
                                    self.txts['gui-descarga en cola']),
                group='descarga en curso'
            )
            return True
        return False

    def func_select_box_hilos(self, respuesta) -> None:
        self.threads = 2**respuesta['index']

        self.text_config_hilos.text = self.txts['config-hilos'].format(self.threads)
        self.redraw = True

    def func_select_box_hilos_newd(self, respuesta) -> None:
        self.new_threads = 2**respuesta['index']

        self.text_newd_hilos.text = self.txts['config-hilos'].format(self.new_threads)
        self.redraw = True

    def del_download_DB(self, id, nombre, index):
        shutil.rmtree(self.carpeta_cache.joinpath(f'./{id}_{"".join(nombre.split(".")[:-1])}'), True)
        self.DB.eliminar_descarga(id)
        self.reload_lista_descargas()
        # self.cached_list_DB.pop(index)
        # self.lista_descargas.pop(index)


    def func_add_download_to_DB(self):
        'Funcion para agregar los datos de la nueva descarga a la base de datos'

        if not self.can_add_new_download:
            return 0
        if self.actualizar_url:
            self.DB.update_url(self.new_url_id,self.input_newd_url.get_text())
        else:
            datos = [self.new_filename, self.new_file_type, self.new_file_size, self.url, self.new_threads]
            self.DB.añadir_descarga(*datos)

        

        self.reload_lista_descargas()
        self.screen_new_download_bool = False

    def func_preguntar_carpeta(self):
        try:
            ask = askdirectory(initialdir=self.save_dir, title=self.txts['cambiar carpeta'])
            if not ask:
                return
            self.save_dir = ask
            self.save_json()
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(50000,50000), 'bottomright', self.txts['carpeta cambiada'], self.txts['gui-carpeta cambiada con exito'])
            )
        except:
            pass
    
    def reload_lista_descargas(self, cursor = None):
        if not cursor:
            self.cached_list_DB = self.DB.buscar_descargas()
        else:
            cursor.execute('SELECT * FROM descargas')
            self.cached_list_DB = cursor.fetchall()

        if not self.cached_list_DB:
            self.lista_descargas.clear()
            self.lista_descargas.append((None, None, None))
            return 0
        self.lista_descargas.clear()
        for row in self.cached_list_DB:
            nombre = row[1]
            tipo = row[2].split('/')[0]
            peso_formateado = format_size(row[3])
            peso = f'{peso_formateado[1]:.2f}{self.nomenclaturas[peso_formateado[0]]}'
            hilos = row[6]
            fecha = datetime.datetime.fromtimestamp(float(row[7]))
            # txt_fecha = f'{fecha.hour}:{fecha.minute}:{fecha.second} - {fecha.day}/{fecha.month}/{fecha.year}'
            txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
            estado = self.txts[f'{row[8]}'.lower()] if f'{row[8]}'.lower() in self.txts else row[8]
            cola = ' - 'if not row[0] in self.cola else f'[{self.cola.index(row[0])}]'
            self.lista_descargas.append([nombre, tipo, hilos, peso, estado, cola, txt_fecha])

        self.Mini_GUI_manager.clear_group('lista_descargas')
        self.Mini_GUI_manager.add(
            mini_GUI.more_objs.aviso1((50000, 50000), 'bottomright', self.txts['lista actualizada'],self.font_mononoki),
            group='lista_descargas'
        )

    def func_borrar_todas_las_descargas(self):
        shutil.rmtree(self.carpeta_cache)
        self.DB.borrar_todo()
        self.reload_lista_descargas()


    def func_paste_url(self, url=False):
        'Pegar la url en el input'
        if url:
            self.input_newd_url.set(url)
        else:
            self.input_newd_url.set(pyperclip.paste())

    def toggle_apagar_al_finalizar_cola(self):
        self.apagar_al_finalizar_cola = not self.apagar_al_finalizar_cola
        self.btn_config_apagar_al_finalizar_cola.text = ''if self.apagar_al_finalizar_cola else ''

    def toggle_LDM(self):
        self.low_detail_mode = not self.low_detail_mode
        self.btn_config_LDM.text = ''if self.low_detail_mode else ''
        self.lista_descargas.smothscroll = not self.low_detail_mode
    
    def toggle_enfoques(self):
        self.enfoques = not self.enfoques
        self.btn_config_enfoques.text = '' if self.enfoques else ''
    def toggle_detener_5min(self):
        self.detener_5min = not self.detener_5min
        self.btn_config_detener_5min.text = '' if self.detener_5min else ''

    def func_comprobar_url(self):
        self.url = self.input_newd_url.get_text()
        self.thread_new_download = Thread(target=self.comprobar_url, daemon=True)
        self.thread_new_download.start()

    def func_change_idioma(self, idioma):
        self.idioma = idioma
        self.txts = idiomas[self.idioma]
        self.configs['idioma'] = self.idioma

        self.generate_objs()
        self.reload_lista_descargas()
        self.move_objs()
        self.redraw = True

    def func_newd_close(self):
        self.screen_new_download_bool = False
        if self.thread_new_download and self.thread_new_download.is_alive():
            self.thread_new_download.join(.1)

    def func_main_to_config(self):
        self.screen_main_bool = False
        self.screen_configs_bool = True
        self.screen_new_download_bool = False

    def func_exit_configs(self):
        self.screen_configs_bool = False
        self.screen_main_bool = True
        self.screen_new_download_bool = False

        self.save_json()

    def func_extras_to_main(self):
        self.screen_main_bool = True
        self.screen_configs_bool = False
        self.screen_new_download_bool = False
        self.screen_extras_bool = False

    def func_main_to_extras(self):
        self.screen_main_bool = False
        self.screen_configs_bool = False
        self.screen_new_download_bool = False
        self.screen_extras_bool = True
