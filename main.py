import src.config
from src.server import start_server_thread
from src.ui import demo

if __name__ == "__main__":
    start_server_thread()
    demo.launch()
