"""Browser acceptance server: reject all outbound socket connections."""
import socket
import uvicorn

original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex

def guarded(original):
    def connect(self, address):
        # Windows asyncio creates an internal loopback socket pair.
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
            return original(self, address)
        raise AssertionError('API browsing attempted an outbound connection')
    return connect

socket.socket.connect = guarded(original_connect)
socket.socket.connect_ex = guarded(original_connect_ex)
uvicorn.run('pokelab.api:app', host='127.0.0.1', port=8001)
