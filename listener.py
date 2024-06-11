import subprocess, requests, json, time, os, pygame as pag
import win32gui
import win32con
import win32api
from threading import Thread, Lock, Condition
from flask import Flask, request, jsonify
from flask_cors import CORS
from platformdirs import user_config_path
from urllib.parse import urlparse, unquote
from pathlib import Path

from Utilidades import Funcs_pool, Create_boton, Create_text
from Utilidades.win32_tools import front2
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

    def acquire(self):
        with self.lock:
            self.count += 1
            self.condition_v.notify()
    def add(self,mensaje):
        self.list_m.append(mensaje)
    
def op_pro():
    subprocess.run('"Download Manager.exe"',shell=True)
    # subprocess.run('"C:/ProgramData/anaconda3/envs/nuevo/python.exe" main.py')
def descargar_archivo(url,name,num):

    response = requests.get(url,stream=True,timeout=20)
    tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
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
    
    down_winds.remove(num)
    subprocess.run(f'Downloader.exe "{Data_Base.get_last_insert()[0]}" "0"', shell=True)
    # subprocess.run(f'"C:/ProgramData/anaconda3/envs/nuevo/python.exe" Downloader.py "{Data_Base.get_last_insert()[0]}" "0"', shell=True)

def download_window(num,text):
    pag.init()
    
    v = pag.display.set_mode((250,120), pag.NOFRAME|pag.SRCALPHA)
    pag.display.set_icon(pag.image.load('descargas.png'))
    pag.display.set_caption("Listener")
    # v.fill((255, 0, 128))
    # v.set_colorkey((255, 0, 128))
    run = True
    r = pag.time.Clock()

    texto = Create_text('Obteniendo informacion de:',24,None,(125,30),with_rect=True,color='white',color_rect=(20,20,20))
    texto2 = Create_text((text if len(text) < 37 else (text[:40] + "...")),16,None,(125,60),padding=(1,5),with_rect=True,color='white',color_rect=(20,20,20))
    boton = Create_boton('Aceptar',20,None,(125,95),(20, 10), 'center', 'black','purple', 'cyan', 0, 0, 20, 0, 0, 20, -1)

    # # Create layered window
    # hwnd = pag.display.get_wm_info()["window"]
    # win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
    #                     win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    # win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(255, 0, 128), 0, win32con.LWA_COLORKEY)
    win32gui.SetWindowPos(pag.display.get_wm_info()['window'], win32con.HWND_TOPMOST, 0,0,0,0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    while run:
        r.tick(30)
        for e in pag.event.get():
            if e.type == pag.QUIT:
                pag.quit()
                run = False
            elif e.type == pag.MOUSEBUTTONDOWN and e.button == 1 and boton.click(e.pos):
                pag.quit()
                run = False
        if not num in down_winds:
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

            

id = 0
down_winds = []
app = Flask("listener")
CORS(app)

carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
carpeta_config.mkdir(parents=True, exist_ok=True)

pool_descargas = Funcs_pool()
pool_descargas.add('open_program',op_pro)

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
    pool_descargas.start('open_program')

    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
@app.route('/check',methods=['POST'])
def check():
    response = jsonify({"status": "success"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__=='__main__':
    # app.run(port=5000)
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)