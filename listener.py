import json
import os
import traceback
import requests
import shutil
import multiprocessing
import datetime
import time
import socket as sk

from multiprocessing import Process
from DB import Data_Base
from pathlib import Path
from threading import Thread
from platformdirs import user_log_path

from constants import DICT_CONFIG_DEFAULT, TITLE, VERSION, CONFIG_DIR, CACHE_DIR, Config, DICT_CONFIG_DEFAULT_TYPES

from flask import Flask, Response, request, jsonify, g
from flask_cors import CORS, cross_origin

from Utilidades import win32_tools, Logger, check_update

from main import Downloads_manager
from Downloader import Downloader
from my_warnings import TrajoHTML
from ventana_actualizar import Ventana_actualizar
from ventana_cola_finalizada import Ventana_cola_finalizada
from ventana_detener_apago_automatico import Ventana_detener_apago_automatico

os.chdir(Path(__file__).parent)
app = Flask("Acelerador de descargas(API)")
CORS(app)


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

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    l = g.pop("logger", None)
    if l is not None:
        l.close()

def get_all_conf():
    try:
        configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
    except Exception:
        configs = DICT_CONFIG_DEFAULT
    return configs

def get_conf(key: str):
    try:
        configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
    except Exception:
        configs = DICT_CONFIG_DEFAULT
    return configs.get(key, DICT_CONFIG_DEFAULT.get(key))
def set_conf(key: str, value: str):
    configs: dict = json.load(open(CONFIG_DIR.joinpath('./configs.json')))
    configs[key] = value
    json.dump(configs, open(CONFIG_DIR.joinpath('./configs.json'), 'w'))


lista_descargas = []
descargas_process: dict[int,Process] = {}
cola: list[int] = []
cola_iniciada = False
program_opened = False
program_thread = None
last_update = time.time()
last_update_type = 0
last_download_changed = 0

request_session = requests.Session()
request_session.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
}


def update_last_update():
    global last_update, last_update_type
    last_update = float(time.time())
    last_update_type = 2
def update_last_download_update(download_id):
    global last_update, last_update_type, last_download_changed
    last_update = float(time.time())
    if last_update_type < 1:
        last_update_type = 1
    last_download_changed = download_id


@app.route("/check", methods=["GET"])
@cross_origin()
def hello_world():
    return jsonify({ "message": "Hello World", "status": "ok" }), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/api_close", methods=["GET"])
def close():
    if program_thread and program_thread.is_alive():
        program_thread.join(.1)

    for i,key in sorted(enumerate(lista_descargas), reverse = True):
        try:
            lista_descargas.remove(key)
            descargas_process[key].kill()
        except Exception as err:
            print(type(err))
            print(err)
            pass
    icon.stop()
    os._exit(0)
    raise Exception('adadad')
# --------------------------------------- Programa --------------------------------------- #

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
        return jsonify({"message": "Programa ya iniciado", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}

def open_program_thread():
    global program_opened
    program_opened = True
    Downloads_manager(Config(resolution=(800, 550), min_resolution=(600,450)))
    program_opened = False

@app.route("/extencion/check/<name>")
def check_extencion(name: str):
    return jsonify({"message": "busqueda de extension", "code":0, 'status':'ok', "respuesta":name in get_conf('extenciones')}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/get_configurations")
def get_configurations():
    return jsonify(get_all_conf()), 200, {'Access-Control-Allow-Origin':'*'}
@app.route("/configuration/<key>")
def get_configuration(key: str):
    return jsonify(get_conf(key)), 200, {'Access-Control-Allow-Origin':'*'}
@app.route("/set_configuration", methods=["POST"])
def set_configuration():
    if request.is_json:
        response = request.get_json()
    else:
        response = request.form
    print(response)
    try:
        if not isinstance(DICT_CONFIG_DEFAULT_TYPES[response['key']](response['value']), DICT_CONFIG_DEFAULT_TYPES[response['key']]):
            raise TypeError('Troliado mi pana')
        set_conf(response['key'], DICT_CONFIG_DEFAULT_TYPES[response['key']](response['value']))
        get_logger().write(f"Logger: Configuracion {response['key']} cambaiada a '{response['value']}'")
        return jsonify({"message": "Configuracion actualizada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}
    except TypeError as err:
        print(err)
        get_logger().write(f'Logger: Error al actualizar la configuracion {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        get_logger().write(type(err))
        get_logger().write('No es el tipo que necesita')
        get_logger().write(err)
        return jsonify({"message": "Valor de tipo invalido", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    except Exception as err:
        print(err)
        get_logger().write(f'Logger: Error al actualizar la configuracion {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        get_logger().write(type(err))
        get_logger().write(err)
        return jsonify({"message": "Error al actualizar la configuracion", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}


def get_sockets_clients():
    socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
    socket.bind(('127.0.0.1', 5001))
    socket.listen(5)
    while True:
        time.sleep(1)
        client, address = socket.accept()
        print(f"Connection from {address}")
        Thread(target=__comunicacion, args=(client,)).start()

        
def __comunicacion(client: sk.socket):
    try:
        while True:
            message = json.dumps({'status': 'idle', 'last_update':last_update, 'last_update_type': last_update_type, 'last_download_changed': last_download_changed}).encode()
            client.send(message)
            time.sleep(.2)
            client.recv(1024).decode()
    except Exception as err:
        print(err)
    finally:
        client.close()


# --------------------------------------- Downloads --------------------------------------- #

@app.route('/descargas/check/<int:id>', methods=["GET"])
def check_download(id: int):
    return jsonify({'status': 'ok', 'code':0, 'downloading':id in lista_descargas, 'cola': id in cola}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/get/<int:id>", methods=["GET"])
def read_item(id: int):
    return jsonify(get_db().buscar_descarga(id)), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/get_all", methods=["GET"])
def read_items():
    return jsonify({'cola':cola,'lista':get_db().buscar_descargas()}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/url/<int:id>/<url>", methods=["GET"])
def update_url(id:int, url: str):
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    get_db().actualizar_url(id, url)
    return jsonify({"message": "URL actualizada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/estado/<int:id>/<estado>", methods=["GET"])
def update_estado(id:int, estado: str) -> Response:
    get_db().update_estado(id, estado)
    update_last_download_update(id)
    return jsonify({"message": "estado actualizado", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/nombre/<int:id>/<nombre>", methods=["GET"])
def update_name(id:int, nombre: str):
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    get_db().update_nombre(id, nombre)
    update_last_download_update(id)
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

def init_download(id):
    global cola, cola_iniciada
    lista_descargas.append(id)
    get_logger().write(f'Logger: Iniciando descarga {id} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    descargas_process[id] = Process(name=f'Descarga {id} - Download Manager by Edouard Sandoval',target=Downloader,args=(Config(window_resize=False,resolution=(700, 300)),id,'2' if id in cola else '0'),daemon=True)
    descargas_process[id].start()
    descargas_process[id].join()
    # c = Downloader(id,'2' if id in cola else '0')
    print(f"Termino {id} -> {descargas_process[id].exitcode}")

    if id in cola and descargas_process[id].exitcode == 3:
        cola.remove(id)
        update_last_update()

        if len(cola) > 0:
            lista_descargas.remove(id)
            del descargas_process[id]
            return init_download(cola[0])

        cola_iniciada = False
        if get_conf('apagar al finalizar cola'):
            get_logger().write(f'Logger: Apagando el sistema por finalizar la cola de descargas {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")} \n')
            os.system('shutdown /s /t 30 /c "Ah finalizado la cola de descarga - Download Manager by Edouard Sandoval"')
            Process(target=Ventana_detener_apago_automatico, args=(Config(window_resize=False, resolution=(400, 130)),), daemon=True).start()
        else:
            Process(target=Ventana_cola_finalizada, args=(Config(window_resize=False, resolution=(350, 130)),), daemon=True).start()
    del descargas_process[id]
    lista_descargas.remove(id)
    
@app.route("/descargas/add_from_program" , methods=["GET"])
def add_descarga_program():# nombre: str, tipo:str, url: str, size: int, hilos:int
    response = request.args.to_dict()
    get_db().añadir_descarga(response['nombre'],response['tipo'],response['size'],response['url'],response['hilos'])
    update_last_update()
    get_logger().write(f'Logger: Descarga añadida exitosamente: {response["nombre"]} - {response["size"]} - {response["url"]} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    return jsonify({"message": "Descarga añadida exitosamente", "code":0, 'status':'ok'})

@app.route("/descargas/add_web", methods=["POST"])
def add_descarga_web():
    if request.is_json:
        response1 = request.get_json()
    else:
        response1 = request.args.to_dict()
    print(response1)
    
    get_logger().write(response1)
    get_logger().write("Obteniendo informacion de \n" + response1['nombre'] + "\n" + response1['url'])

    try:
        icon.show_notification(f"Obteniendo informacion de \n{response1['nombre']}\n{response1['url'][:70]}...", "Acelerador de descargas")

        response = func_probar_link(response1['url'])
        if not response:
            response = func_probar_link(response1['url'])
        if not response:
            raise Exception('No se pudo obtener la informacion')
        # response = request_session.get(response1['url'], stream=True, timeout=30)
        print(response.headers)
        tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
        peso = int(response.headers.get('content-length', 1))
        hilos = get_conf('hilos') if 'bytes' in response.headers.get('Accept-Ranges', '') else 1
        
        if tipo in ['text/plain', 'text/html']:
            with open(CACHE_DIR.joinpath(f'./last_download_error{response1["nombre"]}.html'), 'w') as f:
                f.write(response.text)
            raise TrajoHTML('No paginas')
    except Exception as err:
        print(err)
        get_logger().write(type(err))
        get_logger().write(err)
        icon.show_notification(f"Error al Obtener informacion de \n\n{response1['nombre']}",'Descargar')
        return jsonify({"message": "Error al obtener la descarga", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}

    
    index = get_db().añadir_descarga(response1['nombre'], tipo, peso, response1['url'], hilos)
    update_last_update()
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

# --------------------------------------- Cola --------------------------------------- #}
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


def func_probar_link(url):
    try:
        response = request_session.get(url, stream=True, timeout=15)
        print(response.headers)
        tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
        if tipo in ['text/plain', 'text/html']:
            with open(CACHE_DIR.joinpath(f'./last_download_error{url}.html'), 'w') as f:
                f.write(response.text)
            raise TrajoHTML('No paginas')
    except Exception as err:
        print(err)
        print(traceback.format_exc())
        return False
    return response

def func_open_program():
    if not program_opened:
        Thread(target=open_program_thread).start()
    else:
        win32_tools.front(TITLE)

def buscar_actualizacion(confirm=False):
    try:
        sera = check_update('acelerador de descargas', VERSION, 'last')
        if sera:
            Process(target=Ventana_actualizar,args=(Config(window_resize=False, resolution=(300, 130)), sera['url'],), daemon=True).start()
        elif confirm:
            icon.show_notification(f"No hay actualizaciones disponibles", "Acelerador de descargas")
    except:
        if confirm:
            icon.show_notification(f"Error al buscar actualizaciones", "Acelerador de descargas")

def borrar_carpetas_vacias():
    cosas = os.listdir(CACHE_DIR)
    for i in cosas:
        if os.path.isdir(CACHE_DIR / i) and len(os.listdir(CACHE_DIR / i)) == 0:
            shutil.rmtree(CACHE_DIR / i)
            print(f"Se ha eliminado {CACHE_DIR / i}")

def borrar_logs_vacios():
    path = user_log_path('Acelerador de descargas', 'Edouard Sandoval')
    cosas = os.listdir(path)
    r = False
    for i in cosas:
        if os.path.isfile and (path/i).stat().st_size == 0:
            os.remove(path/i)
            print(f"'{path/i}' Eliminado")
            r = True

    if r:
        print("logs vacios eliminados")


def init():
    icon.run()
    # icon.show_notification("Acelerador de descargas", "Acelerador de descargas abierto", 5)

    # time.sleep(2)
    # requests.get('http://127.0.0.1:5000/open_program')
    

if __name__ == '__main__':
    multiprocessing.freeze_support()

    try:
        requests.get('http://127.0.0.1:5000/open_program')
        os._exit(0)
    except requests.exceptions.ConnectionError:
        pass
    except Exception as err:
        print(err)
        get_logger().write(f'Logger: Error al iniciar el programa {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
        get_logger().write(type(err))
        get_logger().write(err)


    icon = win32_tools.Win32TrayIcon(
        "descargas.ico",
        "Acelerador de descargas",
        [
            ("Abrir programa", func_open_program),
            ("Buscar actualizaciones", lambda: buscar_actualizacion(confirm=True)),
            ("Open logs", lambda: get_logger().open_folder()),
            ("Salir", lambda: requests.get("http://127.0.0.1:5000/api_close")),
        ],
        func_open_program
    )

    

    Thread(target=buscar_actualizacion).start()
    Thread(target=borrar_carpetas_vacias).start()
    Thread(target=get_sockets_clients).start()
    Thread(target=borrar_logs_vacios).start()
    Thread(target=init).start()
    
    # app.run('0.0.0.0', 5000, debug=True)
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
    icon.stop()
