from nicegui import ui, run
from nicegui.element import Element
from ds.runpod_api import RunPodAPI
from dotenv import load_dotenv
from typing import Callable, Optional
from openai import OpenAI
import os
import base64
import tempfile
from pydub import AudioSegment
import io

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

class AudioTranscriber:
    def __init__(self):
        self.openai = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1"
        )

    async def transcribe(self, audio_blob_base64):
        try:
            # Decode base64 to binary
            audio_data = base64.b64decode(audio_blob_base64)
            
            # Create WAV audio segment from binary data
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Convert to OGG format (reduces file size)
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                audio.export(temp_ogg.name, format='ogg', parameters=["-q:a", "4"])
                
                # Check file size
                file_size = os.path.getsize(temp_ogg.name)
                if file_size > 25 * 1024 * 1024:  # 25 MB in bytes
                    os.unlink(temp_ogg.name)
                    raise ValueError("Audio file too large (>25MB)")
                
                # Transcribe with Whisper API
                with open(temp_ogg.name, 'rb') as audio_file:
                    transcript = self.openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                # Clean up temp file
                os.unlink(temp_ogg.name)
                
                return transcript.text
                
        except Exception as e:
            print(f"Error in transcription: {e}")
            return None

class MyContextBuffer:
    def __init__(self):
        self.context = ""
        self.full_enough = 250
        self.openai = OpenAI(api_key=OPENAI_API_KEY)

    def add_to_context(self, text):
        if text:
            self.context += f" {text.strip()}"

    def is_full_enough(self):
        return len(self.context) > self.full_enough

    def generate_image_prompt(self):
        if not self.context:
            return None
            
        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative assistant that generates detailed image prompts based on conversations. Focus on the key themes, emotions, and visual elements that would make an interesting image."},
                {"role": "user", "content": f"Generate a detailed image prompt based on this conversation excerpt: {self.context}"}
            ]
        )
        
        return response.choices[0].message.content

    def clear(self):
        self.context = ""

class ImageGenerator:
    def __init__(self, endpoint_id=None):
        if endpoint_id is None:
            self.endpoint_id = os.environ.get("RUNPOD_ENDPOINT")
        else:
            self.endpoint_id = endpoint_id

    def generate_image(self, context):
        api_key = os.environ.get("RUNPOD_API_KEY")
        endpoint_id = self.endpoint_id

        runpod_api = RunPodAPI(api_key)
        start_response = runpod_api.start_job(endpoint_id, context)
        job_status_id = start_response.get("id")

        if job_status_id:
            base64_image = runpod_api.get_results(endpoint_id, job_status_id, remove_prefix=False)
            if base64_image:
                print("Successfully extracted base64 image")
                return base64_image
        else:
            print("Failed to start the job.")
        return "Failed"

async def on_audio_ready(data):
    print("Audio data received")
    base64_audio = data.args['audioBlobBase64']
    if not base64_audio:
        print("No audio data received")
        return

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
            image_prompt = context_buffer.generate_image_prompt()
            if image_prompt:
                update_image(interactive_image, image_prompt)
                context_buffer.clear()

def update_image(interactive_image, prompt):
    ig = ImageGenerator(endpoint_id=RUNPOD_SDXL_ENDPOINT_ID)
    image = ig.generate_image(prompt)
    if image == "Failed":
        print("Failed to generate image")
    else:
        print("Successfully generated image")
        interactive_image.set_source(image)
        interactive_image.force_reload()

# Global variables for UI elements
context_buffer = MyContextBuffer()
interactive_image = None
transcription_display = None

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

ui.run(host="0.0.0.0", port=8080)
