import subprocess, requests, json, time, sys, pygame as pag
import os
from threading import Thread, Lock, Condition
from flask import Flask, request, jsonify
from flask_cors import CORS
from platformdirs import user_config_path
from urllib.parse import urlparse, unquote
from pathlib import Path

from Utilidades import Funcs_pool, Button, Text
from Utilidades.win32_tools import topmost
from DB import Data_Base as db

os.chdir(Path(__file__).parent)


class Administrador_de_ventanas:
    def __init__(self,count,limit) -> None:
        self.count = count
        self.limit = limit
        self.lock = Lock()
        self.condition_v = Condition(self.lock)

        self.list_m = []

    def acquire(self):
        with self.lock:
            while self.count <= 0:
                self.condition_v.wait()
            self.count -= 1

    def release(self):
        with self.lock:
            self.count += 1
            self.condition_v.notify()

def descargar_archivo(url,name,num):
    try:
        response = requests.get(url, stream=True, timeout=20)
        tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
        if tipo in ['text/plain', 'text/html']:
            raise Exception('a')
        peso = int(response.headers.get('content-length', 1))
        partes = json.load(open(carpeta_config.joinpath('./configs.json'))).get('hilos',8)

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
                        name = x[10:].replace('"','')
                        break


        Data_Base = db(carpeta_config.joinpath('./downloads.sqlite3'))
        Data_Base.añadir_descarga(name,tipo,peso,url,partes)

        subprocess.Popen(['Downloader.exe', f"{Data_Base.get_last_insert()[0]}", '0'],shell=True)
        down_winds.remove(num)
    except:
        errors.append(num)
    # archivo = json.load(open(Path(__file__).parent.joinpath('./paths.json'),'r'))['downloader']
    # subprocess.Popen([f'{archivo} "{Data_Base.get_last_insert()[0]}" "0"'])

def download_window(num,text):
    wins.acquire()

    pag.init()
    
    v = pag.display.set_mode((250,120), pag.NOFRAME)
    pag.display.set_icon(pag.image.load('descargas.png'))
    pag.display.set_caption("Listener")
    run = True
    err = False
    r = pag.time.Clock()

    texto = Text('Obteniendo informacion de:',24,None,(125,30),with_rect=True,color='white',color_rect=(20,20,20))
    texto2 = Text((text if len(text) < 37 else (text[:40] + "...")),16,None,(125,60),padding=(1,5),with_rect=True,color='white',color_rect=(20,20,20))
    boton = Button('Aceptar',20,None,(125,95),(20, 10), 'center', 'black','purple', 'cyan', 0, 0, 20, 0, 0, 20, -1)


    topmost(pag.display.get_wm_info()['window'])

    while run:
        r.tick(30)
        for e in pag.event.get():
            if e.type == pag.QUIT:
                pag.quit()
                run = False
            elif e.type == pag.MOUSEBUTTONDOWN and e.button == 1 and boton.click(e.pos):
                if num in errors:
                    errors.remove(num)
                pag.quit()
                run = False
        if num in errors:
            if not err:
                texto.text = 'Error...'
                err = True
            pass
        elif not num in down_winds:
            pag.quit()
            run = False
        if run:
            v.fill((20,20,20))
            pag.draw.rect(v,(100,100,100),[0,0,250,120],5)
            pag.draw.rect(v,(200,200,200),[0,0,250,120],3)
            pag.draw.rect(v,(255,255,255),[0,0,250,120],1)
            texto.draw(v)
            texto2.draw(v)
            boton.draw(v)
            pag.display.flip()
    wins.release()

            

wins = Administrador_de_ventanas(1,1)
id = 0
down_winds = []
errors = []
app = Flask("listener")
CORS(app)

carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
carpeta_config.mkdir(parents=True, exist_ok=True)

pool_descargas = Funcs_pool()

@app.route('/add_download',methods=['POST'])
def descargar():
    global id
    data = request.get_json()
    url_file = data['fileUrl']
    filename = data.get('name',None)
    print(data)
    t = time.time()
    down_winds.append(f'{t}')
    try:
        configs: dict = json.load(open(carpeta_config.joinpath('./configs.json')))
    except Exception:
        configs = {}
    if configs.get('mini_ventana_captar_extencion',True):
        Thread(target=download_window,args=(f'{t}',filename if filename else url_file)).start()
    Thread(target=descargar_archivo,args=(url_file,filename,f'{t}')).start()
    
    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/open_program',methods=['POST'])
def open_program():
    # archivo = json.load(open(Path(__file__).parent.joinpath('./paths.json'),'r'))['main']
    # subprocess.Popen([archivo],shell=True)
    subprocess.Popen(['Download Manager.exe'],shell=True)

    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
@app.route('/check',methods=['POST'])
def check():
    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
@app.route('/exit',methods=['POST'])
def exit():
    sys.exit()
    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__=='__main__':
    # app.run(port=5000)
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
