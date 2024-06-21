import json
import requests
import shutil
from platformdirs import user_config_path
from pathlib import Path

class Version_error(Exception):
    def __init__(self):
        super().__init__('Pues si')


carpeta_config = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
carpeta_config.mkdir(parents=True, exist_ok=True)

try:
    print('empezando')
    response = requests.post('http://127.0.0.1:5000/check', timeout=5).json()
    print('request hecho')
    if not int(response.get('version', 0)) == 1.1:
        raise Version_error()
except Version_error:
    try:
        requests.post('http://127.0.0.1:5000/exit', timeout=5)
    except:
        pass
    shutil.copy('./listener.exe', carpeta_config.joinpath('./listener.exe'))
except Exception as err:
    print(err)
    shutil.copy('./listener.exe', carpeta_config.joinpath('./listener.exe'))
finally:
    json.dump(
        {
            'main': f'{Path(__file__).parent.joinpath('./Download Manager.exe')}',
            'downloader': f'{Path(__file__).parent.joinpath('./Downloader.exe')}'
        },
        open(carpeta_config.joinpath('./paths.json'), 'w')
    )