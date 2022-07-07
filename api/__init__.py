import requests


class PetHome(object):

    def __init__(self, username: str, password: str, addr: str, port: str):
        self.addr = addr
        self.port = port
        self.protocol = 'http'
        self.token = self.auth(username, password)
        # self.url = f"{self.protocol}://{self.addr}:{self.port}"

    def auth(self, username: str, password: str) -> str: ...

    def create_ad(self, data: dict) -> int: ...

    def delete_ad(self, id: int): ...

    def get_own_advertisements(self, page: int) -> list: ...

    def get_other_advertisements(self, page: int) -> list: ...

    def get_advertisement_by(self, id: int) -> dict: ...

    def _get_advertisements(self, pov: str, page: int, size: int = 4) -> list: ...
