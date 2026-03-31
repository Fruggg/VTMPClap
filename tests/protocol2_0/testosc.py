from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import time


def handle_value(address, *args):
    print(f"received on {address}: {args}")


dispatcher = Dispatcher()
dispatcher.map("/value", handle_value)

server = ThreadingOSCUDPServer(("127.0.0.1", 9001), dispatcher)
print("Listening for OSC on 127.0.0.1:9001")

server_thread = __import__("threading").Thread(
    target=server.serve_forever,
    daemon=True
)
server_thread.start()

try:
    while True:
        print("python still running...")
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down.")
    server.shutdown()
    server.server_close()