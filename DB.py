import sqlite3, time

class Data_Base:
    def __init__(self,path) -> None:
        self.path = path
        self.DB = sqlite3.connect(path)
        self.cursor = self.DB.cursor()

        try:
            self.cursor.execute('SELECT * FROM descargas')
        except sqlite3.OperationalError:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS descargas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    tipo TEXT,
                    peso INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    url_page TEXT DEFAULT '',
                    partes INTEGER NOT NULL,
                    fecha TEXT,
                    estado TEXT,
                    cookies TEXT DEFAULT ''
                );
            ''')
            self.DB.commit()
        try:
            self.cursor.execute("INSERT INTO descargas (nombre,peso,url,partes,cookies) VALUES(\"hola\",121221,\"agahgoeiughioeurghoi\",8,'')")
            self.DB.rollback()
            columns = self.cursor.execute("PRAGMA table_info(descargas);").fetchall()
            # uti.debug_print(columns)
            if columns.__len__() != 9:
                raise sqlite3.OperationalError
        except sqlite3.OperationalError:
            self.cursor.execute("PRAGMA table_info(descargas);")
            columns = [x[1] for x in self.cursor.fetchall()]
            
            self.cursor.execute("SELECT * FROM descargas;")
            rows = self.cursor.fetchall()
            
            data = [dict(zip(columns,row)) for row in rows]
            if 'url_page' in columns:
                for x in data:
                    del x['url_page']
            
            self.cursor.execute("DROP TABLE IF EXISTS descargas;")

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS descargas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    tipo TEXT,
                    peso INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    partes INTEGER NOT NULL,
                    fecha TEXT,
                    estado TEXT,
                    cookies TEXT DEFAULT ''
                );
            ''')

            insert_query = f"INSERT INTO descargas ({', '.join(list(data[0].keys()))}) VALUES ({', '.join(['?'] * len(data[0]))})"

            self.cursor.executemany(insert_query, [list(row.values()) for row in data])


            self.DB.commit()
        

    def buscar_descargas(self):
        self.cursor.execute('SELECT * FROM descargas')
        descargas = self.cursor.fetchall()
        return descargas
    
    def buscar_descarga(self,id):
        self.cursor.execute('SELECT * FROM descargas WHERE id=?',[id])
        descarga = self.cursor.fetchone()
        return descarga
    
    def añadir_descarga(self,nombre,tipo,peso,url,partes,tiempo=None, cookies=''):
        self.cursor.execute(
            "INSERT INTO descargas(nombre,tipo,peso,url,partes,fecha,estado,cookies) VALUES(?,?,?,?,?,?,?,?)",
            (nombre,tipo,peso,url,partes,time.time() if not tiempo else tiempo,'esperando', cookies)
        )
        self.DB.commit()
        return self.cursor.lastrowid
        
    def eliminar_descarga(self,id):
        self.cursor.execute("DELETE FROM descargas WHERE id=?",(id,))
        self.DB.commit()
    
    def get_last_insert(self):
        self.cursor.execute("SELECT * FROM descargas WHERE id=?",(self.cursor.lastrowid,))
        return self.cursor.fetchone()

    def update_hilos(self, id, hilos):
        self.cursor.execute('UPDATE descargas SET partes=? WHERE id=?',[hilos, id])
        self.DB.commit()

    def update_estado(self, id, estado):
        self.cursor.execute('UPDATE descargas SET estado=? WHERE id=?',[estado,id])
        self.DB.commit()
        
    def update_url(self, id, url):
        self.cursor.execute('UPDATE descargas SET url=? WHERE id=?',[url, id])
        self.DB.commit()

    def update_nombre(self, id, nombre):
        self.cursor.execute('UPDATE descargas SET nombre=? WHERE id=?',[nombre, id])
        self.DB.commit()
    
    def update_size(self, id, size):
        self.cursor.execute('UPDATE descargas SET peso=? WHERE id=?',[size, id])
        self.DB.commit()

    def borrar_todo(self):
        self.cursor.execute('DELETE FROM descargas WHERE 1')
        self.DB.commit()

    def close(self):
        self.DB.close()