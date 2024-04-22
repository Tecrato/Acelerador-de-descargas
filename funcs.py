import pyperclip, datetime, time, subprocess, shutil, sqlite3, pygame as pag, sys
from threading import Thread
from pygame import Vector2
from tkinter.filedialog import askdirectory

from Utilidades import GUI, mini_GUI, Create_boton
from Utilidades import win32_tools

from textos import idiomas


def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


class Other_funcs:
    def download(self,id,mod) -> None:
            # proceso = subprocess.run(f'python Downloader.py "{id}" "{mod}"', shell=True)
            proceso = subprocess.run(f'Downloader.exe "{id}" "{mod}"', shell=True)
            if proceso.returncode == 1 and id in self.cola:
                self.cola.remove(id)
                if len(self.cola) > 0:
                    self.init_download(self.cola[0],2)
                elif self.apagar_al_finalizar_cola:
                    subprocess.call('shutdown /s /t 10 /c "Ah finalizado la cola de descarga - Download Manager by Edouard Sandoval"', shell=True)
                    
                    DB = sqlite3.connect(self.carpeta_config.joinpath('./downloads.sqlite3'))
                    DB_cursor = DB.cursor()
                    self.reload_lista_descargas(DB_cursor)
                    pag.quit()
                    sys.exit()
                else:
                    win32_tools.front('Download Manager by Edouard Sandoval')
            else:
                print('NT Bro')
            DB = sqlite3.connect(self.carpeta_config.joinpath('./downloads.sqlite3'))
            DB_cursor = DB.cursor()
            self.reload_lista_descargas(DB_cursor)
    def init_download(self,id,mod=0):
            Thread(target=self.download, args=(id,mod)).start()

    def func_select_box(self, respuesta) -> None:
        if not self.cached_list_DB: return
        obj_cached = self.cached_list_DB[respuesta['obj']['index']]

        if respuesta['index'] == 0:
            if win32_tools.check_win(f'Downloader {obj_cached[0]}_{obj_cached[1]}'):
                win32_tools.front(f'Downloader {obj_cached[0]}_{obj_cached[1]}')
                return
            self.init_download(obj_cached[0],2 if obj_cached[0] in self.cola else 0)
        elif respuesta['index'] == 1:
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar el elemento']),
                lambda r: (self.del_download_DB(
                    *obj_cached[:2]) if r == 'aceptar' else None)
            )

        elif respuesta['index'] == 2:
            self.new_url_id = obj_cached[0]
            self.screen_new_download(1)
        elif respuesta['index'] == 3:
            pyperclip.copy(obj_cached[4])
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(self.ventana_rect.bottomright) - (10, 10), 'botomright', 'Copiado',
                                      self.txts['copiado al portapapeles'])
            )
        elif respuesta['index'] == 4:
            if obj_cached[0] in self.cola:
                return
            self.cola.append(obj_cached[0])
            self.reload_lista_descargas()
        elif respuesta['index'] == 5:
            if not obj_cached[0] in self.cola:
                return
            self.cola.remove(obj_cached[0])
            self.reload_lista_descargas()
        elif respuesta['index'] == 6:
            self.cola.clear()
            self.reload_lista_descargas()

    def del_download_DB(self, id, nombre):
        if win32_tools.check_win(f'Downloader {id}_{nombre}'):
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(self.ventana_rect.bottomright) - (10, 10), 'botomright', 'Error',
                                      self.txts['gui-descarga en curso'])
            )
            return
        shutil.rmtree(self.carpeta_cache.joinpath(f'./{id}_{''.join(nombre.split('.')[:-1])}'), True)
        self.DB_cursor.execute('DELETE FROM descargas WHERE id=?', [id])
        self.DB.commit()
        self.reload_lista_descargas()

    def func_add_download_to_DB(self):
        'Funcion para agregar los datos de la nueva descarga a la base de datos'

        if not self.can_add_new_download:
            return 0
        if self.actualizar_url:
            url = self.input_newd_url.get_text()

            self.DB_cursor.execute('UPDATE descargas SET url=? WHERE id=?', [url, self.new_url_id])
            self.DB.commit()
        else:
            datos = [self.new_filename, self.new_file_type, self.new_file_size, self.url, self.threads, time.time(),
                     'esperando']
            self.DB_cursor.execute('INSERT INTO descargas VALUES(null,?,?,?,?,?,?,?)', datos)
            self.DB.commit()

        self.reload_lista_descargas()
        self.screen_new_download_bool = False

    def func_preguntar_carpeta(self):
        try:
            self.save_dir = askdirectory(initialdir=self.save_dir, title='Select dir')
            if not self.save_dir: 
                return
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', self.txts['carpeta cambiada'], self.txts['gui-carpeta cambiada con exito'])
            )
            self.save_json()
        except:
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(self.ventana_rect.bottomright, 'bottomright', 'Error', self.txts['gui-carpeta cambiada con exito'])
            )
    
    def reload_lista_descargas(self, cursor = None):
        if not cursor:
            cursor = self.DB_cursor
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
            hilos = row[5]
            fecha = datetime.datetime.fromtimestamp(float(row[6]))
            # txt_fecha = f'{fecha.hour}:{fecha.minute}:{fecha.second} - {fecha.day}/{fecha.month}/{fecha.year}'
            txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
            estado = self.txts[f'{row[7]}'.lower()] if f'{row[7]}'.lower() in self.txts else row[7]
            cola = ' - 'if not row[0] in self.cola else f'[{self.cola.index(row[0])}]'
            self.lista_descargas.append([nombre, tipo, hilos, peso, estado, cola, txt_fecha])

    def func_paste_url(self, url=False):
        'Pegar la url en el input'
        if url:
            self.input_newd_url.set(url)
        else:
            self.input_newd_url.set(pyperclip.paste())

    def func_change_hilos(self, dir):
        if dir == 'up' and self.threads < 32:
            self.threads += 1
        elif dir == 'down' and self.threads > 1:
            self.threads -= 1
        elif isinstance(dir, int):
            self.threads = dir
        self.text_config_hilos.text = self.txts['config-hilos'].format(self.threads)
        self.ventana.fill((20, 20, 20))
        for x in self.list_to_draw_config:
            if isinstance(x, Create_boton):
                x.draw(self.ventana, (-500,-500))
            else:
                x.draw(self.ventana)

    def toggle_apagar_al_finalizar_cola(self):
        self.apagar_al_finalizar_cola = not self.apagar_al_finalizar_cola
        self.btn_config_apagar_al_finalizar_cola.text = ''if self.apagar_al_finalizar_cola else ''
    def toggle_LDM(self):
        self.low_detail_mode = not self.low_detail_mode
        self.btn_config_LDM.text = ''if self.low_detail_mode else ''
        self.framerate = 60 if not self.low_detail_mode else 30
        self.lista_descargas.smothscroll = not self.low_detail_mode

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
        self.ventana.fill((20, 20, 20))
        for x in self.list_to_draw_config:
            if isinstance(x, Create_boton):
                x.draw(self.ventana, (-500,-500))
            else:
                x.draw(self.ventana)

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
