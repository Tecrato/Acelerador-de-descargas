import os
import time
import json
import shutil
import datetime
import socket as sk
import multiprocessing
import Utilidades as uti

from DB import Data_Base
from pathlib import Path
from threading import Thread, Lock
from multiprocessing import Process
from platformdirs import user_log_path

from constants import DICT_CONFIG_DEFAULT, TITLE, VERSION, CONFIG_DIR, CACHE_DIR, Config, DICT_CONFIG_DEFAULT_TYPES
from textos import idiomas

from flask import Flask, Response, request, jsonify, g
from flask_cors import CORS, cross_origin

from Utilidades import win32_tools, Logger, check_update


from my_warnings import TrajoHTML
from ventanas.V_principal import Downloads_manager
from ventanas.V_download import Downloader
from ventanas.V_actualizar import Ventana_actualizar
from ventanas.V_cola_finalizada import Ventana_cola_finalizada
from ventanas.V_detener_apago_automatico import Ventana_detener_apago_automatico
from ventanas.V_actualizar_url import Ventana_actualizar_url


os.chdir(Path(__file__).parent)
app = Flask("Acelerador de descargas(API)")
CORS(app)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    l = g.pop("logger", None)
    if l is not None:
        l.close()


#-------------------------------------------------------------------------------------------------

#        ---------------------      Variables       ---------------------------------

#-------------------------------------------------------------------------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = Data_Base(CONFIG_DIR.joinpath('./downloads.sqlite3'))
    return db
def get_logger():
    global app
    ctx = app.app_context().g
    if ctx.get("logger", None) is None:
        ctx.logger = Logger('Acelerador de descargas', user_log_path('Acelerador de descargas', 'Edouard Sandoval'))
    return ctx.logger

def get_text(key: str) -> str:
    return str(idiomas[get_conf('idioma')][key])

def get_all_conf():
    try:
        configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
        for key, value in configs.items():
            configs[key] = DICT_CONFIG_DEFAULT_TYPES[key](value)
    except Exception as err:
        uti.debug_print(f"No se pudo cargar la configuracion {key}", priority=2)
        configs = DICT_CONFIG_DEFAULT
    return configs

def get_conf(key: str):
    try:
        configs: dict = get_all_conf()
    except Exception as err:
        uti.debug_print(f"No se pudo cargar la configuracion {key}", priority=2)
        uti.debug_print(err, priority=2)
        get_logger().write(f"No se pudo cargar la configuracion {key}")
        get_logger().write(err)
        return DICT_CONFIG_DEFAULT.get(key)
    return configs.get(key, DICT_CONFIG_DEFAULT.get(key))
def set_conf(key: str, value: str):
    try:
        configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
    except Exception as err:
        uti.debug_print(f"No se pudo guardar la configuracion {key}", priority=2)
        get_logger().write(f"No se pudo guardar la configuracion {key}")
        get_logger().write(err)
        configs = DICT_CONFIG_DEFAULT
    configs[key] = value
    json.dump(configs, open(CONFIG_DIR.joinpath('./configs.json'), 'w'))


lista_descargas = []
descargas_process: dict[int,Process] = {}
cola: list[int] = []
cola_iniciada = False
program_opened = False
program_thread = None
last_update = time.time()
list_changes_to_sockets = {}
lock = Lock()
timer = uti.multithread.Interval_funcs()

una_session = uti.Http_Session(verify=False)

updating_url = False
updating_id = -1

pv_updating_url = Process()
pv_cola_finalizada = Process()
pv_actualizar_programa = Process()
pv_detener_apago_automatico = Process()




@app.route("/check", methods=["GET"])
@cross_origin()
def hello_world():
    return jsonify({ "message": "Hello World", "status": "ok" }), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/api_close", methods=["GET"])
def close():
    global updating_url, pv_updating_url, pv_cola_finalizada, pv_actualizar_programa, pv_detener_apago_automatico
    if program_thread and program_thread.is_alive():
        program_thread.join(.1)
    
    for i in [pv_updating_url, pv_cola_finalizada, pv_actualizar_programa, pv_detener_apago_automatico]:
        try:
            i.kill()
        except:
            pass

    for i,key in sorted(enumerate(lista_descargas), reverse = True):
        try:
            lista_descargas.remove(key)
            descargas_process[key].kill()
        except Exception as err:
            uti.debug_print(type(err), priority=2)
            uti.debug_print(err, priority=2)
            pass
    icon.stop()
    os._exit(0)
    raise Exception('adadad')

#-------------------------------------------------------------------------------------------------

#        ---------------------      Funciones programas       ---------------------------------

#-------------------------------------------------------------------------------------------------

@app.route("/open_program", methods=["GET"])
@cross_origin()
def open_program():
    global program_opened, program_thread
    if not program_opened:
        program_thread = Thread(target=open_program_thread,daemon=True)
        program_thread.start() 
        return jsonify({"message": "Programa iniciado", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    else:
        win32_tools.front(TITLE)
        return jsonify({"message": "Programa ya iniciado", "code":1, 'status':'error'}), 405, {'Access-Control-Allow-Origin':'*'}

def open_program_thread():
    global program_opened
    program_opened = True
    Downloads_manager(Config(resolution=(800, 550), min_resolution=(600,450)))
    program_opened = False

@app.route("/extencion/check/<name>")
def check_extencion(name: str):
    s = name in get_conf('extenciones')
    return jsonify({"message": "busqueda de extension", "code":0, 'status':'ok', "respuesta":s}), 200 if s else 404, {'Access-Control-Allow-Origin':'*'}

@app.route("/get_configurations")
def get_configurations():
    return jsonify(get_all_conf()), 200, {'Access-Control-Allow-Origin':'*'}
@app.route("/configuration/<key>")
def get_configuration(key: str):
    return jsonify(get_conf(key)), 200, {'Access-Control-Allow-Origin':'*'}
@app.route("/set_configuration", methods=["POST"])
def set_configuration():
    try:
        if request.is_json:
            response = request.get_json()
        else:
            response = request.form.to_dict()
        uti.debug_print(response)


        if not isinstance(DICT_CONFIG_DEFAULT_TYPES[response['key']](response['value']), DICT_CONFIG_DEFAULT_TYPES[response['key']]):
            raise TypeError('Troliado mi pana')
        set_conf(response['key'], response['value'])
        get_logger().write(f"Logger: Configuracion {response['key']} cambaiada a '{response['value']}'")
        return jsonify({"message": "Configuracion actualizada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    except TypeError as err:
        uti.debug_print(err, priority=2)
        get_logger().write(f'Logger: Error al actualizar la configuracion {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        get_logger().write(type(err))
        get_logger().write('No es el tipo que necesita')
        get_logger().write(err)
        return jsonify({"message": "Valor de tipo invalido", "code":2, 'status':'error'}), 400, {'Access-Control-Allow-Origin':'*'}
    except Exception as err:
        uti.debug_print(err, priority=2)
        get_logger().write(f'Logger: Error al actualizar la configuracion {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        get_logger().write(type(err))
        get_logger().write(err)
        return jsonify({"message": "Error al actualizar la configuracion", "code":1, 'status':'error'}), 500, {'Access-Control-Allow-Origin':'*'}


def get_sockets_clients():
    socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
    socket.bind(('127.0.0.1', 5001))
    socket.listen(5)
    while True:
        time.sleep(1)
        client, address = socket.accept()
        uti.debug_print(f"Connection from {address}", priority=1)
        list_changes_to_sockets[address] = {
            'last_downloads_changed': [],
            'last_update_type': 0,
            'last_update': time.time()
        }
        Thread(target=__comunicacion, args=(client,address)).start()
    
def __comunicacion(client: sk.socket, address):
    try:
        while True:
            lock.acquire()
            message = json.dumps({'status': 'idle', 'last_update':last_update, 'last_update_type': list_changes_to_sockets[address]['last_update_type'],'last_downloads_changed': list_changes_to_sockets[address]['last_downloads_changed']}).encode()
            client.sendall(message)
            lock.release()
            r = client.recv(1024).decode()
            if not r:
                continue
            try:
                response = json.loads(r)
            except Exception as err:
                uti.debug_print("updated", priority=2)
                continue
            if response['status'] == 'updated':
                list_changes_to_sockets[address]['last_downloads_changed'] = []
                list_changes_to_sockets[address]['last_update_type'] = 0
                list_changes_to_sockets[address]['last_update'] = time.time()
                continue
            if response['status'] == 'idle' and time.time() - list_changes_to_sockets[address]['last_update'] > .5:
                time.sleep(.3)
            else:
                time.sleep(1/30)
    except Exception as err:
        uti.debug_print(err, priority=1)
    finally:
        try:
            lock.release()
        except:
            pass
        del list_changes_to_sockets[address]
        client.close()


#-------------------------------------------------------------------------------------------------

#        ---------------------      Descargas       ---------------------------------

#-------------------------------------------------------------------------------------------------

@app.route('/descargas/check/<int:id>', methods=["GET"])
def check_download(id: int):
    return jsonify({'status': 'ok', 'code':0, 'downloading':id in lista_descargas, 'cola': id in cola}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/get/<int:id>", methods=["GET"])
def read_item(id: int):
    return jsonify(get_db().buscar_descarga(id)), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/get_all", methods=["GET"])
def read_items():
    return jsonify({'cola':cola,'lista':get_db().buscar_descargas()}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/url/<int:id>", methods=["GET"])
def update_url(id:int):
    global updating_url, pv_updating_url, updating_id
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    if updating_url:
        return jsonify({"message": "Ya se esta actualizando", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    updating_url = True
    updating_id = id
    pv_updating_url = Process(target=Ventana_actualizar_url, args=(Config(window_resize=False, resolution=(400, 125)),id))
    pv_updating_url.start()
    return jsonify({"message": "Cambiando url", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/cancel_update/url", methods=["GET"])
def cancel_update_url():
    global updating_url, pv_updating_url
    if updating_url:
        updating_url = False
        try:
            pv_updating_url.kill()
        except:
            pass
        uti.debug_print("actualizacion de url cancelada", priority=0)
    return jsonify({"message": "actualizacion de url cancelada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/estado/<int:id>/<estado>", methods=["GET"])
def update_estado(id:int, estado: str) -> Response:
    get_db().update_estado(id, estado)
    update_last_download_update(id)
    return jsonify({"message": "estado actualizado", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/size/<int:id>/<size>", methods=["GET"])
def update_size(id:int, size: str) -> Response:
    try:
        get_db().update_size(id, size)
        update_last_download_update(id)
        return jsonify({"message": "tamanio actualizado", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    except Exception as err:
        uti.debug_print(type(err), priority=3)
        return jsonify({"message": "Error al actualizar el tamanio", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/nombre", methods=["POST"])
def update_name():
    try:
        if request.is_json:
            r = request.get_json()
            id_download, nombre = r.get('id'), r.get('nombre')
        else:
            r = request.form.to_dict()
            id_download, nombre = r.get('id'), r.get('nombre')
    except Exception as err:
        uti.debug_print(type(err), priority=3)
        return jsonify({"message": "Error al actualizar el nombre", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    if id_download in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    get_db().update_nombre(id_download, nombre)
    update_last_download_update(id_download)
    return jsonify({"message": "nombre actualizado", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/download/<int:id>", methods=["GET"])
def download(id: int):
    global cola, cola_iniciada
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    
    if id in cola and cola_iniciada:
        return jsonify({"message": "Descarga en cola", "code":2, 'status':'error'})
    elif id in cola:
        cola_iniciada = True
    Thread(target=init_download,args=(id,)).start()
    
    
    return jsonify({"message": "Descarga iniciada", "code":0, 'status':'ok'})

def init_download(id_download):
    global cola, cola_iniciada, pv_cola_finalizada, pv_detener_apago_automatico
    lista_descargas.append(id_download)
    get_logger().write(f'Logger: Iniciando descarga {id_download} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    descargas_process[id_download] = Process(name=f'Descarga {id_download} - Download Manager by Edouard Sandoval',target=Downloader,args=(Config(window_resize=False,resolution=(700, 300)),id_download,'2' if id_download in cola else '0'),daemon=True)
    descargas_process[id_download].start()
    descargas_process[id_download].join()
    exitcode = descargas_process[id_download].exitcode
    # c = Downloader(id,'2' if id in cola else '0')
    uti.debug_print(f"Termino {id_download} -> {exitcode}", priority=1)
    
    if id_download in cola:
        update_last_update()
    else:
        update_last_download_update(id_download)
    
    del descargas_process[id_download]
    lista_descargas.remove(id_download)

    if exitcode == 4:
        # os.system('shutdown /s /t 30 /c "A finalizado la descarga - Download Manager by Edouard Sandoval"')
        Process(target=Ventana_detener_apago_automatico, args=(Config(window_resize=False, resolution=(400, 130)),), daemon=True).start()
        return
    
    if id_download in cola and exitcode == 3:
        cola.remove(id_download)

        if len(cola) > 0:
            return init_download(cola[0])

        cola_iniciada = False
        if get_conf('apagar al finalizar cola'):
            get_logger().write(f'Logger: Apagando el sistema por finalizar la cola de descargas {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")} \n')
            os.system('shutdown /s /t 30 /c "A finalizado la cola de descarga - Download Manager by Edouard Sandoval"')
            if not pv_detener_apago_automatico.is_alive():
                pv_detener_apago_automatico = Process(target=Ventana_detener_apago_automatico, args=(Config(window_resize=False, resolution=(400, 130)),), daemon=True)
                pv_detener_apago_automatico.start()
        else:
            if not pv_cola_finalizada.is_alive():
                pv_cola_finalizada = Process(target=Ventana_cola_finalizada, args=(Config(window_resize=False, resolution=(350, 130)),), daemon=True)
                pv_cola_finalizada.start()


@app.route("/descargas/add_from_program" , methods=["POST"])
def add_descarga_program():
    try:
        if request.is_json:
            response = request.get_json()
        else:
            response = request.form.to_dict()
        get_db().añadir_descarga(response['nombre'],response['tipo'],response['size'],response['url'],response['hilos'],cookies=response.get('cookies', ''))
        update_last_update()
        get_logger().write(f'Logger: Descarga añadida exitosamente: {response["nombre"]} - {response["size"]} - {response["url"]} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        return jsonify({"message": "Descarga añadida exitosamente", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    except Exception as err:
        uti.debug_print(err, 2)
        return jsonify({"message": "Error al añadir la descarga", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/add_web", methods=["POST"])
def add_descarga_web():
    global cola_iniciada
    try:
        global updating_url
        if request.is_json:
            response1 = request.get_json()
        else:
            response1 = request.form.to_dict()
        uti.debug_print(response1, priority=0)
        get_logger().write(response1)

        if response1.get('nombre', '').split('.')[-1].lower() not in get_conf('extenciones'):
            return jsonify({"message": "La extensión no esta permitida", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
        
        get_logger().write(response1)
    except Exception as err:
        uti.debug_print(err, 2)
        return jsonify({"message": "Error al obtener la descarga", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    
    get_logger().write("Obteniendo informacion de \n" + response1['nombre'] + "\n" + response1['url'])

    try:
        icon.show_notification(f"{get_text('gui-buscando informacion de')} \n{response1['nombre']}\n{response1['url'][:70]}...", "Acelerador de descargas")

        response = func_probar_link(response1['url'], response1.get('cookies', None))
        if not response:
            response = func_probar_link(response1['url'], response1.get('cookies', None))
        if not response:
            raise Exception('No se pudo obtener la informacion')
        if updating_url:
            func_update_url_download(updating_id, response1["url"], response1['nombre'])
            return jsonify({"message": "Cambiando url", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

        p = False
        peso = int(response.get('content-length', 0))
        if peso > 0 and 'bytes' in response.get('Accept-Ranges', ''):
            try:
                res = uti.get(response1['url'], headers={'Range': 'bytes=0-1'})
                p = True
            except Exception as err:
                p = False
        uti.debug_print(response, priority=0)
        tipo = response.get('Content-Type', 'unknown/Nose').split(';')[0]
        if peso > 0 and 'bytes' in response.get('Accept-Ranges', '') and p: 
            hilos = get_conf('hilos')
        else:
            hilos = 1
        
        if tipo in ['text/plain', 'text/html']:
            raise TrajoHTML('No paginas')
    except Exception as err:
        uti.debug_print(err, priority=2)
        get_logger().write(type(err))
        get_logger().write(err)
        icon.show_notification(f"{get_text('gui-error al buscar la informacion de')} \n\n{response1['nombre']}",'Descargar')
        return jsonify({"message": "Error al obtener la descarga", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}

    
    index = get_db().añadir_descarga(nombre=response1['nombre'], tipo=tipo,peso=peso, url=response1['url'], partes=hilos, cookies=response1.get('cookies', ''))
    update_last_update()
    if get_conf('agregar a cola automaticamente'):
        if lista_descargas:
            cola.append(lista_descargas[0])
            cola_iniciada = True
        cola.append(index)
        if not cola_iniciada:
            cola_iniciada = True
            Thread(target=init_download,args=(index,)).start()
        return jsonify({"message": "Descarga añadida a la cola", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    
    Thread(target=init_download,args=(index,)).start()
    return jsonify({"message": "Descarga iniciada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}


@app.route("/descargas/delete/<int:id>" , methods=["GET"])
def delete_descarga(id: int):
    if id in lista_descargas or id in cola:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    else:
        shutil.rmtree(CACHE_DIR.joinpath(f'./{id}'), True)
        get_db().eliminar_descarga(id)
        update_last_update()
        return jsonify({"message": "Descarga eliminada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/delete_all", methods=["GET"])
def delete_all():
    if lista_descargas or cola:
        return jsonify({"message": "descargas o colas en proceso", "code":1, 'status':'error'})
    shutil.rmtree(CACHE_DIR)
    os.remove(CONFIG_DIR.joinpath('./downloads.sqlite3'))
    setattr(g, '_database', Data_Base(CONFIG_DIR.joinpath('./downloads.sqlite3')))
    update_last_update()

    get_logger().write(f'Logger: todas las descargas eliminadas {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')

    return jsonify({"message": "Descargas eliminadas", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

#-------------------------------------------------------------------------------------------------

#        ---------------------      Cola       ---------------------------------

#-------------------------------------------------------------------------------------------------
@app.route("/cola/get_all", methods=["GET"])
def get_toda_la_cola():
    return jsonify({"cola": cola, "message": "Descarga añadida a la cola", "code":0, 'status':'ok'})

@app.route("/cola/add/<int:id>", methods=["GET"])
def add_cola(id: int):
    if id in cola:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'})
    cola.append(id)
    update_last_download_update(id)
    return jsonify({"message": "Descarga añadida a la cola", "code":0, 'status':'ok'})

@app.route("/cola/delete/<int:id>", methods=["GET"])
def delete_cola(id: int):
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'})
    elif id not in cola:
        return jsonify({"message": "Descarga no esta en la cola", "code":2, 'status':'error'})
    
    cola.remove(id)
    update_last_download_update(id)
    return jsonify({"message": "Descarga eliminada de la cola", "code":0, 'status':'ok'})

@app.route("/cola/clear", methods=["GET"])
def clear_cola():
    cola.clear()
    update_last_update()
    return jsonify({"message": "Cola limpiada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}


#-------------------------------------------------------------------------------------------------

#        ---------------------      Funciones varias       ---------------------------------

#-------------------------------------------------------------------------------------------------


def update_last_update():
    global last_update, list_changes_to_sockets
    try:
        lock.acquire()
        last_update = float(time.time())
        for i,x in list_changes_to_sockets.items():
            x['last_update_type'] = 2
    except Exception as err:
        uti.debug_print(err, priority=2)
    finally:
        lock.release()
def update_last_download_update(download_id):
    global last_update, list_changes_to_sockets
    try:
        lock.acquire()
        last_update = float(time.time())
        for i,x in list_changes_to_sockets.items():
            if download_id not in x['last_downloads_changed']:
                x['last_downloads_changed'].append(download_id)
        x['last_update_type'] = max(x['last_update_type'], 1)
    except Exception as err:
        uti.debug_print(err, priority=2)
    finally:
        lock.release()


def func_probar_link(url, cookie=None):
    try:
        if cookie:
            una_session.cookies = cookie
        else:
            una_session.cookies = {}
        response = una_session.get(url).headers
        uti.debug_print(response, priority=0)
        tipo = response.get('Content-Type', 'unknown/Nose').split(';')[0]
        if tipo in ['text/plain', 'text/html']:
            raise TrajoHTML('No paginas')
        return response
    except Exception as err:
        uti.debug_print(err, 2)
        return False

def func_update_url_download(download_id, url, nombre):
    global updating_url, pv_updating_url
    get_db().update_url(download_id, url)
    updating_url = False
    try:
        pv_updating_url.kill()
    except:
        pass
    icon.show_notification(f"URL cambiada para \n{download_id} -> {nombre}", 'Acelerador de descargas')
    get_logger().write(f"Logger ({datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')}): URL cambiada para {download_id} -> {nombre}: [{url}]")
    Thread(target=init_download,args=(download_id,)).start()


def func_open_program():
    if not program_opened:
        Thread(target=open_program_thread).start()
    else:
        win32_tools.front(TITLE)

def buscar_actualizacion(confirm=False):
    global pv_actualizar_programa
    try:
        sera = check_update('acelerador de descargas', VERSION, 'last')
        uti.debug_print(sera)
        if sera and not pv_actualizar_programa.is_alive():
            pv_actualizar_programa = Process(target=Ventana_actualizar,args=(Config(window_resize=False, resolution=(300, 130)), sera['url'],), daemon=True)
            pv_actualizar_programa.start()
        elif pv_actualizar_programa.is_alive():
            pass
        elif confirm:
            icon.show_notification(get_text('gui-no hay actualizaciones disponibles'), "Acelerador de descargas")
    except Exception as err:
        uti.debug_print(err, 2)
        if confirm:
            icon.show_notification(get_text('gui-error al buscar actualizaciones'), "Acelerador de descargas")

def borrar_carpetas_vacias():
    cosas = os.listdir(CACHE_DIR)
    for i in cosas:
        if os.path.isdir(CACHE_DIR / i) and len(os.listdir(CACHE_DIR / i)) == 0:
            shutil.rmtree(CACHE_DIR / i)
            uti.debug_print(f"Se ha eliminado {CACHE_DIR / i}")

def borrar_logs_vacios():
    path = user_log_path('Acelerador de descargas', 'Edouard Sandoval')
    cosas = os.listdir(path)
    r = False
    for i in cosas:
        if os.path.isfile and (path/i).stat().st_size == 0:
            os.remove(path/i)
            uti.debug_print(f"'{path/i}' Eliminado")
            r = True

    if r:
        uti.debug_print("logs vacios eliminados")


def init():
    global icon
    try:
        icon = win32_tools.Win32TrayIcon(
            "Assets/img/descargas.ico",
            "Acelerador de descargas",
            [
                ("Abrir programa", func_open_program),
                ("Buscar actualizaciones", lambda: buscar_actualizacion(confirm=True)),
                ("Open logs", lambda: get_logger().open_folder()),
                ("Salir", lambda: uti.get("http://127.0.0.1:5000/api_close").json),
            ],
            func_open_program
        )
    except Exception as err:
        uti.debug_print(err, 2)
        del icon
        os._exit(0)
    try:
        json.load(open(CONFIG_DIR.joinpath('./configs.json')))
    except:
        json.dump(DICT_CONFIG_DEFAULT, open(CONFIG_DIR.joinpath('./configs.json'), 'w'))
    icon.run()
    # icon.show_notification("Acelerador de descargas", "Acelerador de descargas abierto", 5)

    # time.sleep(2)
    # requests.get('http://127.0.0.1:5000/open_program')


#-------------------------------------------------------------------------------------------------

#        ---------------------      Init       ---------------------------------

#-------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    multiprocessing.freeze_support()

    try:
        uti.get('http://127.0.0.1:5000/open_program').json
        os._exit(0)
    except Exception:
        pass

    Thread(target=init).start()
    Thread(target=buscar_actualizacion).start()
    Thread(target=borrar_carpetas_vacias).start()
    Thread(target=get_sockets_clients).start()
    Thread(target=borrar_logs_vacios).start()
    
    try:
        # app.run('0.0.0.0', 5000, debug=True)
        from waitress import serve
        serve(app, host="0.0.0.0", port=5000)
    except Exception as err:
        uti.debug_print(err, 2)
        try:
            icon.stop()
        except:
            pass
        os._exit(0)
        exit()
    icon.stop()
