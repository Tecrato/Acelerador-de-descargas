import sys
import os
import subprocess
import requests
import json

from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from platformdirs import user_config_path
from threading import Thread, Lock, Condition
from tkinter.messagebox import askyesno, showinfo
from urllib.parse import urlparse, unquote

from DB import Data_Base as db

os.chdir(Path(__file__).parent)

app = Flask("listener")
CORS(app)


carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
carpeta_config.mkdir(parents=True, exist_ok=True)


def descargar_archivo(url, name):
    try:
        response = requests.get(url, stream=True, timeout=20)
        tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
        if tipo in ['text/plain', 'text/html']:
            raise Exception()

        peso = int(response.headers.get('content-length', 1))
        partes = json.load(open(carpeta_config.joinpath('./configs.json'))).get('hilos', 8)

        if not name:
            title: str = urlparse(url).path
            title: str = title.split('/')[-1]
            title: str = title.split('?')[0]
            title: str = title.replace('+', ' ')
            title: str = unquote(title)
            name = title
            if a := response.headers.get('content-disposition', False):
                name = a.split(';')
                for x in name:
                    if 'filename=' in x:
                        name = x[10:].replace('"', '')
                        break

        Data_Base = db(carpeta_config.joinpath('./downloads.sqlite3'))
        Data_Base.añadir_descarga(name, tipo, peso, url, partes)

        archivo = json.load(open(Path(__file__).parent.joinpath('./paths.json'),'r'))['downloader']
        subprocess.Popen([f'{archivo} "{Data_Base.get_last_insert()[0]}" "0"'])
    except Exception as err:
        showinfo('Error', f'Error al capturar los detalles para la descarga.\n{err}')


@app.route('/add_download', methods=['POST'])
def descargar():
    data = request.get_json()
    url_file = data['fileUrl']
    filename = data.get('name', None)
    print(data)
    if askyesno('Descargar archivo', f'¿Desea descargar el archivo?:\n{filename}'):
        Thread(target=descargar_archivo, args=(url_file, filename)).start()

    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/open_program',methods=['POST'])
def open_program():
    print('hola')
    archivo = json.load(open(Path(__file__).parent.joinpath('./paths.json'),'r'))['main']
    subprocess.Popen([archivo],shell=True)

    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/check',methods=['POST'])
def check():
    response = jsonify({"status": "success", "version": 1.})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/exit',methods=['POST'])
def exit():
    try:
        sys.exit()
    finally:
        response = jsonify({"status": "success"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
