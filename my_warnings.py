class MyException(Exception):
    def __init__(self, mensaje) -> None:
        super().__init__(mensaje)


class DifferentTypeError(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)


class LowSizeError(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)


class TrajoHTML(Exception):
    def __int__(self, mensaje):
        super().__init__(mensaje)


class LinkCaido(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        
class DifferentSizeError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)