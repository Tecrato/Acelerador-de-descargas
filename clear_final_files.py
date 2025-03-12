import os
from pathlib import Path
import shutil

import Utilidades as uti

os.chdir(Path(__file__).parent)



def borrar_carpetas_dist_info(path):
    cosas = os.listdir(path)
    for i in cosas:
        if os.path.isdir(path/i) and i.endswith("dist-info"):
            shutil.rmtree(path / i)
            uti.debug_print(f"Se ha eliminado {path / i}")
        elif os.path.isdir(path/i):
            borrar_carpetas_dist_info(path/i)


def borrar_dlls_sobrantes(path, lista):
    cosas = os.listdir(path)
    r = False
    for i in cosas:
        if os.path.isfile(path/i) and i in lista:
            try:
                os.remove(path/i)
                uti.debug_print(f"'{path/i}' Eliminado")
            except:
                pass

    
if __name__ == "__main__":
    here = Path("./dist/Download Manager")
    lista_dlls = [
        "freetype.dll",
        "libjpeg-9.dll",
        "libmodplug-1.dll",
        "zlib1.dll",
        "libogg-0.dll",
        "libvorbis-0.dll",
        "libvorbisfile-3.dll",
        "libpng16-16.dll",
        "libwebp-7.dll",
        "portmidi.dll",
        "SDL2.dll",
        "SDL2_mixer.dll",
        "SDL2_ttf.dll",
        "SDL2_image.dll",
        "libopus-0.dll",
    ]
    borrar_carpetas_dist_info(here)
    borrar_dlls_sobrantes(here, lista_dlls)

    uti.debug_print("Finalizado")