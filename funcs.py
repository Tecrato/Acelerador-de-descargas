import pyperclip, datetime, time, subprocess, shutil
from threading import Thread
from pygame import Vector2

from Utilidades import GUI, mini_GUI

from textos import idiomas


def format_size(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return [count, size]


class Other_funcs:
    def func_select_box(self, respuesta):
        if not self.cached_list_DB: return 0

        if respuesta['index'] == 0:
            self.descargas_adyacentes.append(
                Thread(target=subprocess.run,
                       args=(f'Downloader.exe "{self.cached_list_DB[respuesta['obj']['index']][0]}" 0',))
            )
            #     Thread(target=subprocess.run,
            #            args=(f'python Downloader.py "{self.cached_list_DB[respuesta['obj']['index']][0]}" 0',))
            # )
            self.descargas_adyacentes[-1].start()
        elif respuesta['index'] == 1:
            # GUI para confirmar borrar el elemento
            self.GUI_manager.add(
                GUI.Desicion(self.ventana_rect.center, self.txts['confirmar'], self.txts['gui-desea borrar el elemento']),
                lambda r: (self.del_download_DB(
                    *self.cached_list_DB[respuesta['obj']['index']][:2]) if r == 'aceptar' else None)
            )

        elif respuesta['index'] == 2:
            self.actualizar_url = True
            self.new_url_id = self.cached_list_DB[respuesta['obj']['index']][0]
            self.screen_new_download()
        elif respuesta['index'] == 3:
            pyperclip.copy(self.cached_list_DB[respuesta['obj']['index']][4])
            self.Mini_GUI_manager.add(
                mini_GUI.simple_popup(Vector2(self.ventana_rect.bottomright) - (10, 10), 'botomright', 'Copiado',
                                      self.txts['copiado al portapapeles'])
            )

    def del_download_DB(self, id, nombre):
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
            self.actualizar_url = False
        else:
            datos = [self.new_filename, self.new_file_type, self.new_file_size, self.url, self.threads, time.time(),
                     'en espera']
            self.DB_cursor.execute('INSERT INTO descargas VALUES(null,?,?,?,?,?,?,?)', datos)
            self.DB.commit()

        self.reload_lista_descargas()
        self.screen_new_download_bool = False

    def reload_lista_descargas(self, cursor = None):
        if cursor:
            cursor = cursor
        else:
            cursor = self.DB_cursor
        self.lista_descargas.clear()
        cursor.execute('SELECT * FROM descargas')
        self.cached_list_DB = cursor.fetchall()

        if not self.cached_list_DB:
            self.lista_descargas.append((None, None, None))
            return 0

        for row in self.cached_list_DB:
            nombre = row[1]
            tipo = row[2].split('/')[0]
            peso_formateado = format_size(row[3])
            peso = f'{peso_formateado[1]:.2f}{self.nomenclaturas[peso_formateado[0]]}'
            hilos = row[5]
            fecha = datetime.datetime.fromtimestamp(float(row[6]))
            # txt_fecha = f'{fecha.hour}:{fecha.minute}:{fecha.second} - {fecha.day}/{fecha.month}/{fecha.year}'
            txt_fecha = f'{fecha.day}/{fecha.month}/{fecha.year}'
            estado = row[7]
            self.lista_descargas.append([nombre, tipo, hilos, peso, estado, txt_fecha])
        # self.lista_descargas = sorted(self.lista_descargas, key=lambda x: x[5], reverse=True)

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
        self.text_config_hilos.change_text(self.txts['config-hilos'].format(self.threads))


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
