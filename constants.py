from platformdirs import user_downloads_path

DICT_CONFIG_DEFAULT = {
    'hilos': 8,  # Número de hilos para la descarga
    'enfoques': True,  # Permitira al programa venir al frente por encima de las demás aplicaciones en ciertos momentos.
    'detener_5min': True,  # Detener la descarga después de 5 minutos de no haber descargado nada.
    'ldm': False,  # Desactiva el smothscroll de la lista de descargas y algún otro efecto en la aplicacion ´para que consuma menos CPU.
    'idioma': 'español',  # Idioma de la interfaz gráfica, opciones: 'español', 'inglés'.
    'save_dir': user_downloads_path(), # Directorio por defecto donde se guardarán los archivos descargados. Puedes cambiarlo a cualquier ruta que desees.
    'apagar al finalizar cola': False, # Si se establece en True, el sistema se apagará automáticamente una vez que se haya procesado toda la cola de descargas.
    'extenciones': ['whl','exe','msi','iso','cia','apk','zip','rar','jar','tar','gz','iso','mp3','mp4','mkv','flv','avi'], # Lista de extensiones de archivo que se permitirán descargar. Puedes agregar o eliminar extensiones según tus necesidades.
}

TITLE = 'Download Manager by Edouard Sandoval'
RESOLUCION = [800, 550]
MIN_RESOLUTION = [600,450]
VERSION = '3.1'