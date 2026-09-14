import os
import re

def sanitize_filename(filename):
    if not filename:
        return "archivo_descargado"
    
    # 1. Prevenir Directory Traversal (eliminar rutas)
    # Nos quedamos solo con el nombre del archivo, ignorando carpetas
    filename = os.path.basename(filename)
    
    # 2. Reemplazar caracteres ilegales en Windows y Linux/Mac
    # Caracteres prohibidos: \ / : * ? " < > |
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    
    # 3. Eliminar caracteres de control (no imprimibles)
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # 4. Manejar nombres reservados de Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    base_name, ext = os.path.splitext(filename)
    if re.match(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', base_name, re.IGNORECASE):
        filename = "_" + filename
        
    # 5. Limitar la longitud del nombre (255 caracteres es el límite estándar)
    if len(filename) > 255:
        # Truncar el nombre pero mantener la extensión
        base_name, ext = os.path.splitext(filename)
        base_name = base_name[:255 - len(ext)]
        filename = base_name + ext
        
    # 6. Evitar nombres que terminen en espacio o punto (problemático en Windows)
    filename = filename.rstrip(' .')
    
    # Si después de sanear todo queda vacío
    if not filename:
        return "archivo_descargado"
        
    return filename