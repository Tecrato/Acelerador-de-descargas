class MyException(Exception):
    """Trajo un texto"""

    def __init__(self, mensaje) -> None:
        super().__init__(mensaje)


class DifferentTypeError(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)


class LowSizeError(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)