import os, time
from pathlib import Path
from threading import Thread
from my_warnings import *


class Download_thread:
    def __init__(self,id,url,start,end,path,prepared_request,prepared_session) -> None:
        self.id = id
        self.url = url
        self.local_num = 0
        self.start = start
        self.end = end
        self.status = 'conectando'
        self.path = path
        self.paused = False
        self.canceled = False
        self.tiempo_reset = 2
        self.intentos = 0

        self.prepared_request = prepared_request
        self.prepared_session = prepared_session

        self.thread = Thread
        self.finished_func = None

    def init(self,reanudar=0):
        self.thread = Thread(target=self.__init_hread,args=(reanudar,))

    def __init_hread(self,reanudar):
        while self.status != 'finalizado':
            self.__download(reanudar)

    def __download(self,reanudar):
        if self.local_count == 0 and reanudar and self.path.is_file():
            self.local_count = os.stat(self.path).st_size
            if self.local_count >= self.end - self.start:
                if self.finished_func:
                    self.finished_func()
                self.status = self.txts['status_hilo[finalizado]'].format(id)
                return
        headers = {'Range': f'bytes={self.start + self.local_count}-{self.end}'}
        try:
            self.status = self.txts['status_hilo[conectando]'].format(id)
            re = self.prepared_request.copy()
            re.prepare_headers(headers)
            response = self.prepared_session.send(re, stream=True, allow_redirects=True, timeout=15)

            tipo = response.headers.get('Content-Type', 'text/plain;a').split(';')[0]
            if tipo != self.type:
                raise DifferentTypeError('ay')

            peso = response.headers.get('content-length', False)
            if int(peso) < 1024 // 16:
                raise LowSizeError('Peso muy pequeño')

            tiempo_reset = 2
            self.status = self.txts['status_hilo[descargando]'].format(id)

            with open(self.path, 'ab') as file_p:
                for data in response.iter_content(1024 // 16):
                    if self.paused or self.canceled:
                        raise Exception('')
                    if not data:
                        continue
                    if self.local_count + len(data) > self.end-self.start+1:
                        d = data[:(self.end-self.start)-self.local_count+1]
                        self.local_count += len(d)
                        file_p.write(d)
                        break
                    self.local_count += len(data)
                    file_p.write(data)

            self.status = 'finalizado'
            if self.finished_func:
                self.finished_func()
            return
        except (Exception, LowSizeError) as err:
            print(err)
            print(type(err))

            if self.canceled:
                self.status = self.txts['status_hilo[cancelado]'].format(id)
                return
            self.status = self.txts['status_hilo[reconectando]'].format(id)
            t = time.time()
            while time.time() - t < tiempo_reset:
                if self.canceled:
                    self.status = self.txts['status_hilo[cancelado]'].format(id)
                    return
                time.sleep(.3)
            
            self.intentos += 1
            self.tiempo_reset = (self.tiempo_reset * 2) if self.tiempo_reset < 30 else self.tiempo_reset