import Utilidades as uti

class Download:
    __slots__ = ('__id', '__nombre', '__tipo', '__peso', '__url', '__partes', '__fecha', '__estado', '__cookies')
    def __init__(self, id: int, nombre: str, tipo: str, peso: int, url: str, partes: int, fecha: str, estado: str, cookies: str):
        self.id: int = id
        self.nombre: str = nombre
        self.tipo: str = tipo
        self.peso: int = peso
        self.url: str = url
        self.partes: int = partes
        self.fecha: str = fecha
        self.estado: str = estado
        self.cookies: str = cookies

    def __eq__(self, other: 'Download') -> bool:
        return self.id == other.id

    def __getitem__(self, key: str):
        return (self.id,
                self.nombre,
                self.tipo,
                self.peso,
                self.url,
                self.partes,
                self.fecha,
                self.estado,
                self.cookies)[key]

    @property
    def id(self) -> int:
        return self.__id
    @id.setter
    def id(self, id: int):
        self.__id = int(id)

    @property
    def nombre(self) -> str:
        return self.__nombre
    @nombre.setter
    def nombre(self, nombre: str):
        self.__nombre = str(nombre)

    @property
    def tipo(self) -> str:
        return self.__tipo
    @tipo.setter
    def tipo(self, tipo: str):
        self.__tipo = str(tipo)
    
    @property
    def peso(self) -> int:
        return self.__peso
    @peso.setter
    def peso(self, peso: int):
        self.__peso = int(peso)
    
    @property
    def url(self) -> str:
        return self.__url
    @url.setter
    def url(self, url: str):
        self.__url = str(url)
    
    @property
    def partes(self) -> int:
        return self.__partes
    @partes.setter
    def partes(self, partes: int):
        self.__partes = int(partes)
    
    @property
    def fecha(self) -> str:
        return self.__fecha
    @fecha.setter
    def fecha(self, fecha: str):
        self.__fecha = str(fecha)
    
    @property
    def estado(self) -> str:
        return self.__estado
    @estado.setter
    def estado(self, estado: str):
        self.__estado = str(estado)
    
    @property
    def cookies(self) -> str:
        return self.__cookies
    @cookies.setter
    def cookies(self, cookies: str):
        self.__cookies = str(cookies)
    
    def __str__(self) -> str:
        return f"Download {self.id} - {self.nombre} - {self.tipo} - {self.peso} - {self.url} - {self.partes} - {self.fecha} - {self.estado}"
    def __repr__(self) -> str:
        return f"Download {self.id} - {self.nombre} - {self.tipo} - {self.peso} - {self.url} - {self.partes} - {self.fecha} - {self.estado} - {self.cookies}"