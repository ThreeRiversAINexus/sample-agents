from interpreter import interpreter
import os
from dotenv import load_dotenv

load_dotenv()

MY_MODEL_NAME = os.getenv("MY_MODEL_NAME")
MY_API_BASE = os.getenv("MY_API_BASE")
MY_API_KEY = os.getenv("MY_API_KEY")

interpreter.offline = True
interpreter.llm.model = MY_MODEL_NAME
interpreter.llm.api_base = MY_API_BASE
interpreter.llm.api_key = MY_API_KEY
interpreter.auto_run = True
interpreter.max_budget = 5.0
interpreter.llm.context_window = 8192
interpreter.llm.max_tokens = 4096
interpreter.loop = True

def handle_disk_space():
    interpreter.chat("Tell me about the size of the disk space on this VM.")

def maintain_system():
    interpreter.chat("Please maintain the system.")

print("hello")
# handle_disk_space()
maintain_system()