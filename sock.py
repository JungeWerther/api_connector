from typing_extensions import Unpack
from pydantic import BaseModel, ConfigDict

class Endpoint():
    """
    Endpoint class
    """
    html: str = None
    
    def __init__(self, html: str = None) -> None:
        self.html = html or self.get_html()

    def get_html(self):
        with open("./Connect/socket.html", "r") as f:
            return f.read()

class Socket():
    """
    Socket class
    """
    def __init__(self, ) -> None:
        pass