<template>
  <div class="recorder-container">
    <div class="switch-container">
      <label class="switch">
        <input type="checkbox" v-model="isRecording" @change="toggleRecording">
        <span class="slider round"></span>
      </label>
      <div v-if="isRecording" class="recording-indicator">
        <span class="dot"></span>
        Recording
      </div>
    </div>
  </div>
</template>

<script>
const CHUNK_SIZE_LIMIT = 24 * 1024 * 1024; // 24MB to stay under 25MB limit

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
    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        this.startRecording();
      }
    },
    async startRecording() {
      try {
        if (!this.stream) {
          await this.requestMicrophonePermission();
        }
        this.resetRecording();
        
        this.mediaRecorder = new MediaRecorder(this.stream, {
          mimeType: 'audio/webm;codecs=opus'
        });

        this.mediaRecorder.addEventListener('dataavailable', event => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data);
            this.currentSize += event.data.size;
            
            // If we're approaching size limit, emit current chunks
            if (this.currentSize >= CHUNK_SIZE_LIMIT) {
              this.emitCurrentChunks();
            }
          }
        });

        // Request data every second to maintain stream
        this.mediaRecorder.start(1000);
      } catch (error) {
        console.error('Error starting recording:', error);
        this.isRecording = false;
      }
    },
    stopRecording() {
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
        // Emit any remaining audio
        if (this.audioChunks.length > 0) {
          this.emitCurrentChunks();
        }
      }
      this.isRecording = false;
    },
    resetRecording() {
      this.audioChunks = [];
      this.currentSize = 0;
    },
    emitCurrentChunks() {
      if (this.audioChunks.length === 0) return;

      const blob = new Blob(this.audioChunks, { 
        type: 'audio/webm;codecs=opus' 
      });
      
      const reader = new FileReader();
      reader.onload = () => {
        const base64Data = reader.result.split(',')[1];
        this.$emit('audio_ready', { 
          audioBlobBase64: base64Data,
          mimeType: 'audio/webm;codecs=opus'
        });
      };
      reader.readAsDataURL(blob);
      
      // Reset for next chunk
      this.resetRecording();
      
      // If still recording, start a new MediaRecorder
      if (this.isRecording && this.mediaRecorder) {
        this.mediaRecorder.start(1000);
      }
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

.switch-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Switch styles */
.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
}

input:checked + .slider {
  background-color: #2196F3;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.slider.round {
  border-radius: 34px;
}

.slider.round:before {
  border-radius: 50%;
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
