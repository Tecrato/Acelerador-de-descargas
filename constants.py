from platformdirs import user_downloads_path, user_pictures_path, user_config_path, user_cache_path

DICT_CONFIG_DEFAULT = {
    'hilos': 8,  # Número de hilos para la descarga
    'enfoques': True,  # Permitira al programa venir al frente por encima de las demás aplicaciones en ciertos momentos.
    'detener_5min': True,  # Detener la descarga después de 5 minutos de no haber descargado nada.
    'ldm': False,  # Desactiva el smothscroll de la lista de descargas y algún otro efecto en la aplicacion ´para que consuma menos CPU.
    'idioma': 'español',  # Idioma de la interfaz gráfica, opciones: 'español', 'inglés'.
    'save_dir': user_downloads_path(), # Directorio por defecto donde se guardarán los archivos descargados. Puedes cambiarlo a cualquier ruta que desees.
    'apagar al finalizar cola': False, # Si se establece en True, el sistema se apagará automáticamente una vez que se haya procesado toda la cola de descargas.
    'extenciones': ['whl','exe','msi','iso','cia','apk','zip','rar','jar','tar','gz','iso','mp3','mp4','mkv','flv','avi'], # Lista de extensiones de archivo que se permitirán descargar. Puedes agregar o eliminar extensiones según tus necesidades.
    'velocidad_limite': 0, # Límite de velocidad en kb/s para las descargas. Si se establece en 0, no se aplicará ningún límite.
    'particulas': True, # Particulas de la interfaz.
}

TITLE = 'Download Manager by Edouard Sandoval'
VERSION = '3.7'
SCREENSHOTS_DIR  = user_pictures_path().joinpath('./Edouard Sandoval/Acelerador_de_descargas')
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = user_config_path('Acelerador de descargas', 'Edouard Sandoval')
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = user_cache_path('Acelerador de descargas', 'Edouard Sandoval')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FONT_MONONOKI = "./Assets/fuentes/mononoki Bold Nerd Font Complete Mono.ttf"
FONT_SIMBOLS = "./Assets/fuentes/Symbols.ttf"

# FONT_MONONOKI = "C:/Users/Edouard/Documents/fuentes/mononoki Bold Nerd Font Complete Mono.ttf"
# FONT_SIMBOLS = "C:/Users/Edouard/Documents/fuentes/Symbols.ttf"