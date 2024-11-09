from nicegui import ui, run
from nicegui.element import Element

from ds.runpod_api import RunPodAPI

from dotenv import load_dotenv
load_dotenv()

from typing import Callable, Optional

from openai import OpenAI
import os

# Taken from https://github.com/CVxTz/LLM-Voice/blob/master/llm_voice/audio_recorder.py
class AudioRecorder(Element, component="audio_recorder.vue"):
    def __init__(self, *, on_audio_ready: Optional[Callable] = None) -> None:
        super().__init__()
        self.on("audio_ready", on_audio_ready)

    async def start_recording(self) -> None:
        self.run_method("startRecording")

    async def stop_recording(self) -> None:
        self.run_method("stopRecording")

    async def play_recorded_audio(self) -> None:
        self.run_method("playRecordedAudio")

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
RUNPOD_API_KEY=os.getenv("RUNPOD_API_KEY")
RUNPOD_MODEL_NAME=os.getenv("MODEL_NAME")
RUNPOD_ENDPOINT_ID=os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_SDXL_ENDPOINT_ID=os.getenv("RUNPOD_SDXL_ENDPOINT_ID")

class AudioTranscriber:
    def __init__(self):
        self.whisper = None
        self.openai = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1"
        )

    async def transcribe(self, audio_blob):
        # Check size < 25 MB
        # Check filetype
        pass

class MyContextBuffer:
    def __init__(self):
        self.context = ""
        self.full_enough = 250

    def add_to_context(self, text):
        self.context += text

    def is_full_enough(self):
        if len(self.context) > self.full_enough:
            return True
        else:
            return False

class ImageGenerator:
    def __init__(self, endpoint_id=None):
        if endpoint_id is None:
            self.endpoint_id = os.environ.get("RUNPOD_ENDPOINT")
        else:
            self.endpoint_id = endpoint_id

    def generate_image(self, context):
        # Example usage:
        api_key = os.environ.get("RUNPOD_API_KEY")
        endpoint_id = self.endpoint_id

        runpod_api = RunPodAPI(api_key)
        start_response = runpod_api.start_job(endpoint_id, context)
        job_status_id = start_response.get("id")

        # Checking the job status and retrieving the base64 content
        if job_status_id:
            base64_image = runpod_api.get_results(endpoint_id, job_status_id, remove_prefix=False)
            if base64_image:
                print("Successfully extracted base64 image")
                return base64_image
        else:
            print("Failed to start the job.")
        return "Failed"

async def on_audio_ready(base64_audio):
    transcriber = AudioTranscriber()
    print(f"Transcribing audio")

    transcription = await transcriber.transcribe(base64_audio)
    print(f"Transcription: {transcription}")
    my_context_buffer = MyContextBuffer()
    my_context_buffer.add_to_context(transcription)

def update_image(interactive_image, context):
    ig = ImageGenerator(endpoint_id=RUNPOD_SDXL_ENDPOINT_ID)
    image = ig.generate_image(context)
    if image == "Failed":
        print("Failed to generate image")
    else:
        print("Successfully generated image")
        print(image[:32])
        interactive_image.set_source(image)
        interactive_image.force_reload()

def complete_cycle(audio_transcriber, my_context_buffer, interactive_image):
    print("Beginning cycle")
    # When audio is ready, transcribe it
    # Add the transcription to the context
    # When the context is full enough, generate an image
    # Update the image
    update_image(interactive_image, "Hello World")

@ui.page("/")
async def main():
    ui.label("Hello World")
    AudioRecorder(on_audio_ready=on_audio_ready)
    my_context_buffer = MyContextBuffer()
    the_show = ui.interactive_image()
    ui.timer(interval=60_000, callback=lambda: complete_cycle( my_context_buffer, the_show))

ui.run(port=8080)