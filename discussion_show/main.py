from nicegui import ui, run, app
from nicegui.element import Element
from ds.image_generator import ImageGenerator  # Updated import
from dotenv import load_dotenv
from typing import Callable, Optional
from openai import OpenAI
import os
import base64
import tempfile
import time
from pydub import AudioSegment, silence
import io
import asyncio
import logging
import sys
from datetime import datetime
import webrtcvad
import wave
import array

# Configure logging
def setup_logger():
    logger = logging.getLogger('discussion_show')
    logger.setLevel(logging.DEBUG)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f'discussion_show_{datetime.now().strftime("%Y%m%d")}.log')
    )
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logger()

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
        self.openai = OpenAI(api_key=OPENAI_API_KEY)
        self.logger = logging.getLogger('discussion_show.transcriber')
        self.vad = webrtcvad.Vad(3)  # Aggressiveness mode 3 (highest)

    def check_voice_activity(self, wav_path):
        """Check if the WAV file contains voice activity."""
        with wave.open(wav_path, 'rb') as wf:
            # WebRTC VAD only accepts 16-bit mono PCM audio
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                return False
            
            # Get raw audio data
            raw_data = wf.readframes(wf.getnframes())
            samples = array.array('h', raw_data)
            
            # Process in 30ms frames (WebRTC VAD requirement)
            frame_duration = 30  # ms
            samples_per_frame = int(wf.getframerate() * frame_duration / 1000)
            voice_frames = 0
            total_frames = 0
            
            for i in range(0, len(samples), samples_per_frame):
                frame = samples[i:i + samples_per_frame]
                if len(frame) == samples_per_frame:
                    is_speech = self.vad.is_speech(frame.tobytes(), wf.getframerate())
                    if is_speech:
                        voice_frames += 1
                    total_frames += 1
            
            if total_frames == 0:
                return False
                
            voice_percentage = (voice_frames / total_frames) * 100
            return voice_percentage > 10  # Consider it speech if more than 10% contains voice

    async def transcribe(self, audio_blob_base64):
        def _process_audio():
            try:
                self.logger.info("Starting audio transcription process")
                # Decode base64 to binary
                audio_data = base64.b64decode(audio_blob_base64)
                self.logger.debug("Successfully decoded base64 audio data")
                
                # Save the WebM audio data to a temporary file
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                    temp_webm.write(audio_data)
                    temp_webm.flush()
                    self.logger.debug(f"Saved temporary WebM file: {temp_webm.name}")
                    
                    # Convert WebM to WAV using pydub
                    audio = AudioSegment.from_file(temp_webm.name, format="webm")
                    self.logger.debug("Successfully converted WebM to AudioSegment")
                    
                    # Save as WAV for VAD check
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                        audio.export(temp_wav.name, format='wav', parameters=[
                            "-acodec", "pcm_s16le",  # 16-bit PCM
                            "-ac", "1",              # mono
                            "-ar", "16000"           # 16kHz sample rate
                        ])
                        
                        # Check for voice activity
                        if not self.check_voice_activity(temp_wav.name):
                            self.logger.info("No significant voice activity detected")
                            os.unlink(temp_wav.name)
                            os.unlink(temp_webm.name)
                            return None
                        
                        os.unlink(temp_wav.name)
                    
                    # Export as OGG for Whisper API
                    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                        audio.export(temp_ogg.name, format='ogg', parameters=["-q:a", "4"])
                        
                        # Check file size
                        file_size = os.path.getsize(temp_ogg.name)
                        if file_size > 25 * 1024 * 1024:  # 25 MB in bytes
                            self.logger.error("Audio file too large (>25MB)")
                            os.unlink(temp_ogg.name)
                            os.unlink(temp_webm.name)
                            raise ValueError("Audio file too large (>25MB)")
                        
                        self.logger.info("Sending audio to Whisper API for transcription")
                        # Transcribe with Whisper API
                        with open(temp_ogg.name, 'rb') as audio_file:
                            transcript = self.openai.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file
                            )
                        
                        # Clean up temp files
                        os.unlink(temp_ogg.name)
                        os.unlink(temp_webm.name)
                        self.logger.debug("Cleaned up temporary files")
                        
                        self.logger.info("Successfully transcribed audio")
                        return transcript.text
                    
            except Exception as e:
                self.logger.error(f"Error in transcription: {str(e)}", exc_info=True)
                return None

        return await run.io_bound(_process_audio)

class MyContextBuffer:
    def __init__(self):
        self.context = ""
        self.full_enough = 50
        self.openai = OpenAI(api_key=OPENAI_API_KEY)
        self.logger = logging.getLogger('discussion_show.context_buffer')

    def add_to_context(self, text):
        if text:
            self.context += f" {text.strip()}"
            self.logger.debug(f"Added text to context. Current length: {len(self.context)}")

    def is_full_enough(self):
        is_full = len(self.context) > self.full_enough
        self.logger.debug(f"Context buffer fullness check: {is_full}")
        return is_full

    def get_fill_percentage(self):
        percentage = min(100, int((len(self.context) / self.full_enough) * 100))
        self.logger.debug(f"Context buffer fill percentage: {percentage}%")
        return percentage

    async def generate_image_prompt(self):
        if not self.context:
            self.logger.warning("Attempted to generate image prompt with empty context")
            return None
        
        def _generate_prompt():
            self.logger.info("Generating image prompt from context")
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a creative assistant that generates concise image prompts based on conversations. Focus on the key themes and emotions."},
                    {"role": "user", "content": f"Generate a short, focused image prompt based on this conversation excerpt: {self.context}"}
                ]
            )
            prompt = response.choices[0].message.content
            self.logger.info(f"Generated image prompt: {prompt}")
            return prompt
            
        return await run.io_bound(_generate_prompt)

    def clear(self):
        self.context = ""
        self.logger.debug("Context buffer cleared")

async def save_base64_image(base64_data):
    logger = logging.getLogger('discussion_show.image_saver')
    
    def _save_image():
        logger.info("Starting image save process")
        # Remove the data URL prefix if present
        if ',' in base64_data:
            base64_data_clean = base64_data.split(',')[1]
        else:
            base64_data_clean = base64_data
        
        # Generate a unique filename
        filename = f"generated_{int(time.time())}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        logger.debug(f"Saving image to: {filepath}")
        
        # Decode and save the image
        image_data = base64.b64decode(base64_data_clean)
        with open(filepath, 'wb') as f:
            f.write(image_data)
            f.flush()
            os.fsync(f.fileno())
        
        logger.info(f"Successfully saved image: {filename}")
        return f"/static/images/{filename}"

    image_url = await run.io_bound(_save_image)
    await asyncio.sleep(0.5)
    return image_url

async def update_image(interactive_image, prompt):
    logger = logging.getLogger('discussion_show.image_updater')
    
    ig = ImageGenerator(endpoint_id=RUNPOD_SDXL_ENDPOINT_ID)
    logger.info("Generating new image")
    base64_image = await ig.generate_image(prompt)
    
    if base64_image:
        logger.info("Saving generated image")
        image_url = await save_base64_image(base64_image)
        logger.debug(f"Image saved at: {image_url}")
        await asyncio.sleep(0.5)
        interactive_image.set_source(image_url)
        logger.info("Successfully updated image in UI")
    else:
        logger.error("Failed to generate image")

# Global variables for UI elements
context_buffer = MyContextBuffer()
interactive_image = None
transcription_display = None
progress_bar = None
progress_label = None
audio_recorder = None

async def handle_recording_toggle(e):
    logger = logging.getLogger('discussion_show.recording_toggle')
    if e.value:  # Switch turned on
        logger.info("Starting recording")
        await audio_recorder.start_recording()
    else:  # Switch turned off
        logger.info("Stopping recording")
        await audio_recorder.stop_recording()

async def on_audio_ready(e):
    logger = logging.getLogger('discussion_show.audio_handler')
    
    base64_audio = e.args['audioBlobBase64']
    if not base64_audio:
        logger.warning("No audio data received")
        return
    
    logger.info("Audio data received, starting transcription")
    transcriber = AudioTranscriber()
    
    transcription = await transcriber.transcribe(base64_audio)
    if transcription:
        logger.info("Successfully transcribed audio")
        context_buffer.add_to_context(transcription)
        
        # Update progress bar
        percentage = context_buffer.get_fill_percentage()
        progress_bar.set_value(percentage / 100)
        progress_label.set_text(f"Context Buffer: {percentage}%")
        
        # Update transcription display with trailing effect
        transcription_display.clear()
        with transcription_display:
            ui.label(transcription).classes('animate-fade-out')
            
        if context_buffer.is_full_enough():
            logger.info("Context buffer full, generating image")
            image_prompt = await context_buffer.generate_image_prompt()
            if image_prompt:
                logger.debug(f"Generated image prompt: {image_prompt}")
                await update_image(interactive_image, image_prompt)
                context_buffer.clear()
                # Reset progress bar after clearing context
                progress_bar.set_value(0)
                progress_label.set_text("Context Buffer: 0%")

@ui.page("/")
async def main():
    global interactive_image, transcription_display, progress_bar, progress_label, context_buffer, audio_recorder
    logger = logging.getLogger('discussion_show.ui')
    logger.info("Initializing main UI page")
    
    with ui.column().classes('w-full items-center'):
        ui.label("AI Discussion Visualizer").classes('text-2xl mb-4')
        
        # Audio controls row with switch and recorder
        with ui.row().classes('mb-4 items-center gap-4'):
            # Add recording switch with label
            with ui.row().classes('items-center gap-2'):
                ui.switch('Record', on_change=handle_recording_toggle).classes('text-lg')
            # Add recorder component
            audio_recorder = AudioRecorder(on_audio_ready=on_audio_ready)
        
        # Progress bar and label
        with ui.column().classes('w-full max-w-2xl mb-4'):
            progress_label = ui.label("Context Buffer: 0%").classes('text-sm mb-1')
            progress_bar = ui.linear_progress(value=0).classes('w-full')
        
        # Transcription display area with fade-out animation
        transcription_display = ui.column().classes('w-full max-w-2xl mb-4 min-h-[100px] p-4 bg-gray-100 rounded')
        
        # Image display
        interactive_image = ui.interactive_image().classes('w-full max-w-2xl')
    
    logger.info("Main UI page initialized")

    ui.add_head_html('''
    <style>
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    .animate-fade-out {
        animation: fadeOut 15s forwards;
    }
    </style>
    ''')

def startup():
    logger = logging.getLogger('discussion_show.startup')
    logger.info("Application starting up")
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.05
    logger.info("Event loop configured")

app.on_startup(startup)

# Configure static file serving
app.add_static_files("/static", STATIC_DIR)

if __name__ in {"__main__", "__mp_main__"}:  # Modified to support multiprocessing
    logger.info("Starting Discussion Show application")
    ui.run(port=8080)
