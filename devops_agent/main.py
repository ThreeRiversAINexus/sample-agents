from interpreter import interpreter
import os
import io
from dotenv import load_dotenv

from contextlib import redirect_stdout

load_dotenv()

MY_MODEL_IS_OFFLINE = os.getenv("MY_MODEL_IS_OFFLINE")
MY_MODEL_NAME = os.getenv("MY_MODEL_NAME")
MY_API_BASE = os.getenv("MY_API_BASE")
MY_API_KEY = os.getenv("MY_API_KEY")

# LangFuse integration
# LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
# LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
# LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

interpreter.offline = MY_MODEL_IS_OFFLINE
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
    with redirect_stdout(io.StringIO()) as f:
        interpreter.chat("Please maintain the system.")

    output = print(f.getvalue())
    return output

# TODO
# These are not working for my custom model yet, so I need custom messages or templates probably.
# redirect_stdout won't display the output while running, maybe. I couldn't get output anymore with it.
# We are going to end up blocking and need to run this in a subprocess, maybe?
# We want to merge this with langgraph imo, so we can have a single agent that can do everything.

print("hello")
handle_disk_space()
output = maintain_system()
print("Output: ", output)
print("bye!")