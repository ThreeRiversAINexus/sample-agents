from nicegui import ui, run, app
from nicegui.element import Element
from ds.runpod_api import RunPodAPI
from dotenv import load_dotenv
from typing import Callable, Optional
from openai import OpenAI
import os
import base64
import tempfile
import time
from pydub import AudioSegment
import io
import asyncio

load_dotenv()

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

# Get the absolute path for the images directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

class AudioTranscriber:
    def __init__(self):
        self.openai = OpenAI(
            api_key=OPENAI_API_KEY
        )

    async def transcribe(self, audio_blob_base64):
        def _process_audio():
            try:
                # Decode base64 to binary
                audio_data = base64.b64decode(audio_blob_base64)
                
                # Save the WebM audio data to a temporary file
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                    temp_webm.write(audio_data)
                    temp_webm.flush()
                    
                    # Convert WebM to WAV using pydub
                    audio = AudioSegment.from_file(temp_webm.name, format="webm")
                    
                    # Export as OGG for Whisper API
                    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                        audio.export(temp_ogg.name, format='ogg', parameters=["-q:a", "4"])
                        
                        # Check file size
                        file_size = os.path.getsize(temp_ogg.name)
                        if file_size > 25 * 1024 * 1024:  # 25 MB in bytes
                            os.unlink(temp_ogg.name)
                            os.unlink(temp_webm.name)
                            raise ValueError("Audio file too large (>25MB)")
                        
                        # Transcribe with Whisper API
                        with open(temp_ogg.name, 'rb') as audio_file:
                            transcript = self.openai.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file
                            )
                        
                        # Clean up temp files
                        os.unlink(temp_ogg.name)
                        os.unlink(temp_webm.name)
                        
                        return transcript.text
                    
            except Exception as e:
                print(f"Error in transcription: {e}")
                return None

        return await run.io_bound(_process_audio)

class MyContextBuffer:
    def __init__(self):
        self.context = ""
        self.full_enough = 50
        self.openai = OpenAI(api_key=OPENAI_API_KEY)

    def add_to_context(self, text):
        if text:
            self.context += f" {text.strip()}"

    def is_full_enough(self):
        return len(self.context) > self.full_enough

    async def generate_image_prompt(self):
        if not self.context:
            return None
        
        def _generate_prompt():
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a creative assistant that generates detailed image prompts based on conversations. Focus on the key themes, emotions, and visual elements that would make an interesting image."},
                    {"role": "user", "content": f"Generate a detailed image prompt based on this conversation excerpt: {self.context}"}
                ]
            )
            return response.choices[0].message.content
            
        return await run.io_bound(_generate_prompt)

    def clear(self):
        self.context = ""

class ImageGenerator:
    def __init__(self, endpoint_id=None):
        if endpoint_id is None:
            self.endpoint_id = os.environ.get("RUNPOD_ENDPOINT")
        else:
            self.endpoint_id = endpoint_id
        self.api_key = os.environ.get("RUNPOD_API_KEY")

    async def generate_image(self, context):
        def _start_job():
            url = f"https://api.runpod.ai/v2/{self.endpoint_id}/run"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            # Format input according to SDXL requirements
            data = {
                "input": {
                    "prompt": context,
                    "negative_prompt": "blurry, bad quality, distorted",
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "width": 1024,
                    "height": 1024,
                    "seed": int(time.time()),
                    "num_images": 1,
                    "scheduler": "DDIM"
                }
            }
            import requests
            response = requests.post(url, headers=headers, json=data)
            return response.json()

        def _check_status(job_id):
            url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status/{job_id}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            import requests
            response = requests.get(url, headers=headers)
            return response.json()

        start_response = await run.io_bound(_start_job)
        print(f"RunPod start response: {start_response}")  # Debug print
        job_status_id = start_response.get("id")

        if not job_status_id:
            print("Failed to start the job.")
            return None

        while True:
            status_response = await run.io_bound(lambda: _check_status(job_status_id))
            print(f"RunPod status response: {status_response}")  # Debug print
            if status_response.get("status") in ["COMPLETED", "FAILED", "CANCELLED"]:
                break
            await asyncio.sleep(1)

        if status_response.get("status") == "COMPLETED":
            try:
                # Handle both possible output formats
                output = status_response.get("output", {})
                if isinstance(output, list) and output:
                    base64_image = output[0]  # Get first image if list
                elif isinstance(output, dict):
                    base64_image = output.get("image") or output.get("image_url")
                else:
                    base64_image = output
                
                if base64_image:
                    print("Successfully extracted base64 image")
                    return base64_image
                else:
                    print(f"No image in output: {output}")
                    return None
            except (KeyError, TypeError) as e:
                print(f"Error extracting image: {e}")
                return None
        else:
            print(f"Job failed with status: {status_response.get('status')}")
            return None

async def save_base64_image(base64_data):
    def _save_image():
        # Remove the data URL prefix if present
        if ',' in base64_data:
            base64_data_clean = base64_data.split(',')[1]
        else:
            base64_data_clean = base64_data
        
        # Generate a unique filename
        filename = f"generated_{int(time.time())}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # Decode and save the image
        image_data = base64.b64decode(base64_data_clean)
        with open(filepath, 'wb') as f:
            f.write(image_data)
            f.flush()  # Ensure the file is written to disk
            os.fsync(f.fileno())  # Force the OS to write the file to disk
        
        return f"/static/images/{filename}"

    # Save the image and wait a moment to ensure it's written to disk
    image_url = await run.io_bound(_save_image)
    await asyncio.sleep(0.5)  # Small delay to ensure file is available
    return image_url

async def update_image(interactive_image, prompt):
    ig = ImageGenerator(endpoint_id=RUNPOD_SDXL_ENDPOINT_ID)
    base64_image = await ig.generate_image(prompt)
    
    if base64_image:
        # Save the image and get its URL
        image_url = await save_base64_image(base64_image)
        print(f"Image saved at: {image_url}")
        # Add a small delay before updating the UI
        await asyncio.sleep(0.5)
        interactive_image.set_source(image_url)
    else:
        print("Failed to generate image")

# Global variables for UI elements
context_buffer = MyContextBuffer()
interactive_image = None
transcription_display = None

async def on_audio_ready(e):
    base64_audio = e.args['audioBlobBase64']
    if not base64_audio:
        print("No audio data received")
        return
    
    print("Audio data received")
    transcriber = AudioTranscriber()
    print("Transcribing audio...")
    
    transcription = await transcriber.transcribe(base64_audio)
    if transcription:
        print(f"Transcription: {transcription}")
        context_buffer.add_to_context(transcription)
        
        # Update transcription display with trailing effect
        transcription_display.clear()
        with transcription_display:
            ui.label(transcription).classes('animate-fade-out')
            
        if context_buffer.is_full_enough():
            image_prompt = await context_buffer.generate_image_prompt()
            if image_prompt:
                print(f"Generated image prompt: {image_prompt}")  # Debug print
                await update_image(interactive_image, image_prompt)
                context_buffer.clear()

@ui.page("/")
async def main():
    global interactive_image, transcription_display, context_buffer
    
    with ui.column().classes('w-full items-center'):
        ui.label("AI Discussion Visualizer").classes('text-2xl mb-4')
        
        # Audio controls
        with ui.row().classes('mb-4'):
            AudioRecorder(on_audio_ready=on_audio_ready)
        
        # Transcription display area with fade-out animation
        transcription_display = ui.column().classes('w-full max-w-2xl mb-4 min-h-[100px]')
        
        # Image display
        interactive_image = ui.interactive_image().classes('w-full max-w-2xl')

    ui.add_head_html('''
    <style>
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    .animate-fade-out {
        animation: fadeOut 5s forwards;
    }
    </style>
    ''')

def startup():
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.05

app.on_startup(startup)

# Configure static file serving
app.add_static_files("/static", STATIC_DIR)

ui.run(port=8080)
