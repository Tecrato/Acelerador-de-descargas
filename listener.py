import json
import os
import requests
import shutil
import multiprocessing
import notifypy
import pystray
import datetime


from PIL import Image
from DB import Data_Base
from pathlib import Path
from subprocess import Popen
from threading import Thread
from platformdirs import user_config_path, user_cache_path, user_log_path

from constants import DICT_CONFIG_DEFAULT, TITLE

from flask import Flask, request, jsonify, g
from flask_cors import CORS, cross_origin

from Utilidades import win32_tools, Logger


os.chdir(Path(__file__).parent)
carpeta_config = Path(user_config_path('Acelerador de descargas', 'Edouard Sandoval'))
carpeta_config.mkdir(parents=True, exist_ok=True)
carpeta_cache = Path(user_cache_path('Acelerador de descargas', 'Edouard Sandoval'))
carpeta_cache.mkdir(parents=True, exist_ok=True)

app = Flask("Acelerador de descargas(API)")
CORS(app)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = Data_Base(carpeta_config.joinpath('./downloads.sqlite3'))
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

def get_conf(key: str):
    try:
        configs: dict = json.load(open(carpeta_config.joinpath('./configs.json')))
    except Exception:
        configs = {}
    return configs.get(key, DICT_CONFIG_DEFAULT.get(key))

lista_descargas = []
cola: list[int] = []
cola_iniciada = False
program_opened = False
program_thread = None

get_logger().write(f'Logger: Acelerador de descargas iniciado {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')


@app.route("/check", methods=["GET"])
@cross_origin()
def hello_world():
    return jsonify({ "message": "Hello World", "status": "ok" }), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/api_close", methods=["GET"])
def close():
    if program_thread and program_thread.is_alive():
        program_thread.join(.1)
    if lista_descargas:
        notifypy.Notify('Cerrar', f"Cierre todas las descargas antes de continuar", "Acelerador de descargas", 'normal', "./descargas.ico").send(False)
        return
    get_logger().write(f'Logger: Cerrando el programa {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    icon.stop()
    os._exit(0)
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
    Popen(['Download Manager.exe','--run'],shell=True).wait()
    # Popen(['main.py','--run'],shell=True).wait()
    program_opened = False

@app.route("/extencion/check/<name>")
def check_extencion(name: str):
    return jsonify({"message": "busqueda de extension", "code":0, 'status':'ok', "respuesta":name in get_conf('extenciones')}), 200, {'Access-Control-Allow-Origin':'*'}


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
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    get_db().actualizar_url(id, url)
    return jsonify({"message": "URL actualizada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/update/estado/<int:id>/<estado>", methods=["GET"])
def update_estado(id:int, estado: str):
    get_db().update_estado(id, estado)
    return jsonify({"message": "estado actualizado", "code":0, 'status':'ok'})

@app.route("/descargas/update/nombre/<int:id>/<nombre>", methods=["GET"])
def update_name(id:int, nombre: str):
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    get_db().update_nombre(id, nombre)
    return jsonify({"message": "nombre actualizado", "code":0, 'status':'ok'})

@app.route("/descargas/download/<int:id>", methods=["GET"])
def download(id: int):
    global cola, cola_iniciada
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":1, 'status':'error'})
    
    if id in cola and cola_iniciada == True:
        return jsonify({"message": "Descarga en cola", "code":2, 'status':'error'})
    elif id in cola:
        cola_iniciada = True
    Thread(target=init_download,args=(id,),daemon=True).start()
    return jsonify({"message": "Descarga iniciada", "code":0, 'status':'ok'})

def init_download(id):
    global cola, cola_iniciada
    lista_descargas.append(id)
    get_logger().write(f'Logger: Iniciando descarga {id} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    proceso = Popen(['Downloader.exe',f'{id}','2' if id in cola else '0'],shell=True)
    proceso.wait()

    if id in cola and proceso.returncode == 1:
        cola.remove(id)

        if len(cola) > 0:
            lista_descargas.remove(id)
            return init_download(cola[0])

        cola_iniciada = False
        if get_conf('apagar al finalizar cola'):
            get_logger().write(f'Logger: Apagando el sistema por finalizar la cola de descargas {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")} \n')
            os.system('shutdown /s /t 30 /c "Ah finalizado la cola de descarga - Download Manager by Edouard Sandoval"')
    lista_descargas.remove(id)
    
@app.route("/descargas/add_from_program" , methods=["GET"])
def add_descarga_program():# nombre: str, tipo:str, url: str, size: int, hilos:int
    response = request.args.to_dict()
    get_db().añadir_descarga(response['nombre'],response['tipo'],response['size'],response['url'],response['hilos'])
    get_logger().write(f'Logger: Descarga añadida exitosamente: {response["nombre"]} - {response["size"]} - {response["url"]} {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')
    return jsonify({"message": "Descarga añadida exitosamente", "code":0, 'status':'ok'})

@app.route("/descargas/add_web", methods=["GET"])
def add_descarga_web():
    response1 = request.args.to_dict()
    
    get_logger().write(response1)
    get_logger().write("Obteniendo informacion de \n" + response1['nombre'] + "\n" + response1['url'])

    try:
        notifypy.Notify('Descargar', f"Obteniendo informacion de \n{response1['nombre']}\n{response1['url'][:70]}...", "Acelerador de descargas", 'normal', "./descargas.ico").send(False)

        response = requests.get(response1['url'], stream=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'}, timeout=30)

        tipo = response.headers.get('Content-Type', 'unknown/Nose').split(';')[0]
        peso = int(response.headers.get('content-length', 1))
        if 'bytes' in response.headers.get('Accept-Ranges', ''):
            hilos = get_conf('hilos')
        else:
            hilos = 1

        if tipo in ['text/plain', 'text/html'] or peso < 128 * hilos:
            notifypy.Notify('Descargar', f"Error al Obtener informacion de \n\n{response1['nombre']}", "Acelerador de descargas", 'normal', "./descargas.ico").send(False)
            return jsonify({"message": "Error al obtener la descarga", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    except Exception as err:
        print(err)
        get_logger().write(type(err))
        get_logger().write(err)
        notifypy.Notify('Descargar', f"Error al Obtener informacion de \n\n{response1['nombre']}", "Acelerador de descargas", 'normal', "./descargas.ico").send(False)
        return jsonify({"message": "Error al obtener la descarga", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}


    index = get_db().añadir_descarga(response1['nombre'], tipo, peso, response1['url'], hilos)
    Thread(target=init_download,args=(index,)).start()
    return jsonify({"message": "Descarga iniciada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}


@app.route("/descargas/delete/<int:id>" , methods=["GET"])
def delete_descarga(id: int):
    if id in lista_descargas or id in cola:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'}), 200, {'Access-Control-Allow-Origin':'*'}
    else:
        get_db().eliminar_descarga(id)
        shutil.rmtree(carpeta_cache.joinpath(f'./{id}'), True)
        return jsonify({"message": "Descarga eliminada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

@app.route("/descargas/delete_all", methods=["GET"])
def delete_all():
    if lista_descargas or cola:
        return jsonify({"message": "descargas o colas en proceso", "code":1, 'status':'error'})
    shutil.rmtree(carpeta_cache)
    os.remove(carpeta_config.joinpath('./downloads.sqlite3'))
    setattr(g, '_database', Data_Base(carpeta_config.joinpath('./downloads.sqlite3')))

    get_logger().write(f'Logger: todas las descargas eliminadas {datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")}')

    return jsonify({"message": "Descargas eliminadas", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}

# --------------------------------------- Cola --------------------------------------- #
@app.route("/cola/add/<int:id>", methods=["GET"])
def add_cola(id: int):
    if id in cola:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'})
    cola.append(id)
    return jsonify({"message": "Descarga añadida a la cola", "code":0, 'status':'ok'})

@app.route("/cola/delete/<int:id>", methods=["GET"])
def delete_cola(id: int):
    if id in lista_descargas:
        return jsonify({"message": "Descarga en progreso", "code":2, 'status':'error'})
    elif id not in cola:
        return jsonify({"message": "Descarga no esta en la cola", "code":2, 'status':'error'})
    
    cola.remove(id)
    return jsonify({"message": "Descarga eliminada de la cola", "code":0, 'status':'ok'})

@app.route("/cola/clear", methods=["GET"])
def clear_cola():
    cola.clear()
    return jsonify({"message": "Cola limpiada", "code":0, 'status':'ok'}), 200, {'Access-Control-Allow-Origin':'*'}


image = Image.open("descargas.png")


def after_click(icon, query):
    global app, program_opened
    if str(query) == "Abrir programa":
        if not program_opened:
            Thread(target=open_program_thread).start()
        else:
            win32_tools.front(TITLE)
    elif str(query) == "Salir":
        icon.stop()
        requests.get("http://127.0.0.1:5000/api_close")

        raise Exception('adadad')
    elif str(query) == "Open log":
        get_logger().open()




icon = pystray.Icon("AdD", image, "Acelerador de descargas",
                    menu=pystray.Menu(
                        pystray.MenuItem("Abrir programa", after_click),
                        pystray.MenuItem("Open log", after_click),
                        pystray.MenuItem("Salir", after_click),
                    )
)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    try:
        requests.get('http://127.0.0.1:5000/check')
        os._exit(0)
    except requests.exceptions.ConnectionError:
        pass

    icon.run_detached()
    
    # app.run('0.0.0.0', 5000, debug=True)
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
    icon.stop()
