<template>
  <div class="recorder-container">
    <div v-if="isRecording" class="recording-indicator">
      <span class="dot"></span>
      Recording
    </div>
  </div>
</template>

<script>

export default {
  data() {
    return {
      isRecording: false,
      mediaRecorder: null,
      stream: null,
      audioChunks: [],
      currentSize: 0
    };
  },
  mounted() {
    this.requestMicrophonePermission();
  },
  methods: {
    async requestMicrophonePermission() {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            channelCount: 1,
            sampleRate: 16000
          } 
        });
      } catch (error) {
        console.error('Error accessing microphone:', error);
      }
    },
    async startRecording() {
      try {
        if (!this.stream) {
          await this.requestMicrophonePermission();
        }

        // Only create a new MediaRecorder if we don't have one or it's inactive
        if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
          this.resetRecording();
          
          this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
          });

          this.mediaRecorder.addEventListener('dataavailable', async (event) => {
            if (event.data.size > 0) {
              this.audioChunks.push(event.data);
              this.currentSize += event.data.size;
              
              // If we're approaching size limit, emit current chunks
              const CHUNK_SIZE_LIMIT = 0.25 * 1024 * 1024;
              console.log('Current size:', this.currentSize);
              if (this.currentSize >= CHUNK_SIZE_LIMIT) {
                await this.emitCurrentChunks();
              }
            }
          });

          this.mediaRecorder.addEventListener('stop', async () => {
            // Emit any remaining audio when stopped
            if (this.audioChunks.length > 0) {
              await this.emitCurrentChunks();
            }
            this.isRecording = false;
          });

          // Start recording with 1-second chunks
          this.mediaRecorder.start(1000);
          this.isRecording = true;
        } else {
          console.warn('MediaRecorder is in state:', this.mediaRecorder.state);
        }
      } catch (error) {
        console.error('Error starting recording:', error);
        this.isRecording = false;
      }
    },
    async stopRecording() {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
      }
    },
    resetRecording() {
      this.audioChunks = [];
      this.currentSize = 0;
    },
    async emitCurrentChunks() {
      if (this.audioChunks.length === 0) return;

      const blob = new Blob(this.audioChunks, { 
        type: 'audio/webm;codecs=opus' 
      });
      
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64Data = reader.result.split(',')[1];
          this.$emit('audio_ready', { 
            audioBlobBase64: base64Data,
            mimeType: 'audio/webm;codecs=opus'
          });
          resolve();
        };
        reader.readAsDataURL(blob);
      }).finally(() => {
        // Reset for next chunk only after emitting
        this.resetRecording();
        
        // If still recording, ensure we're capturing new data
        if (this.isRecording && this.mediaRecorder.state === 'inactive') {
          this.mediaRecorder.start(1000);
        }
      });
    }
  }
};
</script>

<style scoped>
.recorder-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
}

/* Recording indicator styles */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc3545;
  font-weight: bold;
}

.dot {
  width: 12px;
  height: 12px;
  background-color: #dc3545;
  border-radius: 50%;
  animation: blink 1s infinite;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}
</style>
