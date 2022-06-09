import requests

from api import PetHome


class PetHomeImpl(PetHome):

    def __init__(self, username: str, password: str, addr: str, port: str):
        super().__init__(username, password, addr, port)

    def auth(self, username: str, password: str) -> str:
        payload = {
            "username": username,
            "password": password
        }
        req = requests.post(f"{self.protocol}://{self.addr}:{self.port}/v1/users/auth", json=payload)
        if req.status_code == 200:
            resp = req.json()
            return resp['token']

        raise Exception('Authorization is failed')

    def get_own_advertisements(self, page: int) -> list:
        return self._get_advertisements('OWNER', page)

    def get_other_advertisements(self, page: int) -> list:
        return self._get_advertisements('VIEWER', page)

    def get_advertisement_by(self, id: int) -> dict:
        req = requests.get(f"{self.protocol}://{self.addr}:{self.port}/v1/advertisements/{id}",
                           headers={'Authorization': f"Bearer {self.token}"})

        resp = req.json()
        return resp

    def _get_advertisements(self, pov: str, page: int, size: int = 4) -> list:
        payload = {
            "pov": pov,
            "paged": {
                "current": page,
                "size": size
            }
        }
        req = requests.get(f"{self.protocol}://{self.addr}:{self.port}/v1/advertisements",
                           json=payload,
                           headers={'Authorization': f"Bearer {self.token}"})

        if req.status_code != 200:
            raise Exception('Cannot get advertisements')

        resp = req.json()
        ids = resp['ids']
        ads = list()
        for id in ids:
            ad = self.get_advertisement_by(id)
            ads.append(ad)
        return ads

    def create_ad(self, data: str) -> int:
        payload = data
        req = requests.post(f"{self.protocol}://{self.addr}:{self.port}/v1/advertisements",
                            json=payload,
                            headers={'Authorization': f"Bearer {self.token}"})

        if req.status_code != 200:
            raise Exception('Could not create advertisement')

        resp = req.json()
        return resp['id']

    def delete_ad(self, id: int):
        requests.delete(f"{self.protocol}://{self.addr}:{self.port}/v1/advertisements/{id}",
                           headers={'Authorization': f"Bearer {self.token}"})
