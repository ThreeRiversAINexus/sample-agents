<template>
  <div class="recorder-container">
    <div v-if="isRecording" class="recording-indicator">
      <span class="dot"></span>
      Recording
    </div>
    <div class="debug-info" v-if="isRecording">
      {{ (currentSize / 1024).toFixed(2) }}KB / {{ (CHUNK_SIZE_LIMIT / 1024).toFixed(2) }}KB
    </div>
  </div>
</template>

<script>
const CHUNK_SIZE_LIMIT = 0.25 * 1024 * 1024; // 256KB

export default {
  data() {
    return {
      isRecording: false,
      mediaRecorder: null,
      stream: null,
      audioChunks: [],
      currentSize: 0,
      chunkCount: 0
    };
  },
  mounted() {
    this.requestMicrophonePermission();
  },
  methods: {
    async requestMicrophonePermission() {
      try {
        console.log('Requesting microphone permission...');
        this.stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            channelCount: 1,
            sampleRate: 16000
          } 
        });
        console.log('Microphone permission granted');
      } catch (error) {
        console.error('Error accessing microphone:', error);
      }
    },
    async startRecording() {
      try {
        console.log('Starting recording...');
        if (!this.stream) {
          console.log('No stream, requesting microphone permission...');
          await this.requestMicrophonePermission();
        }

        // Only create a new MediaRecorder if we don't have one or it's inactive
        if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
          this.resetRecording();
          
          console.log('Creating new MediaRecorder...');
          this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
          });

          this.mediaRecorder.addEventListener('dataavailable', async (event) => {
            if (event.data.size > 0) {
              console.log(`Chunk ${++this.chunkCount} received: ${event.data.size} bytes`);
              this.audioChunks.push(event.data);
              this.currentSize += event.data.size;
              
              console.log(`Current total size: ${this.currentSize} bytes (limit: ${CHUNK_SIZE_LIMIT} bytes)`);
              if (this.currentSize >= CHUNK_SIZE_LIMIT) {
                console.log('Size limit reached, emitting chunks...');
                await this.emitCurrentChunks();
              }
            }
          });

          this.mediaRecorder.addEventListener('start', () => {
            console.log('MediaRecorder started');
            this.isRecording = true;
          });

          this.mediaRecorder.addEventListener('stop', async () => {
            console.log('MediaRecorder stopped');
            if (this.audioChunks.length > 0) {
              console.log('Emitting remaining chunks...');
              await this.emitCurrentChunks();
            }
            this.isRecording = false;
          });

          this.mediaRecorder.addEventListener('error', (error) => {
            console.error('MediaRecorder error:', error);
            this.isRecording = false;
          });

          // Start recording with 1-second chunks
          console.log('Starting MediaRecorder with 1-second chunks...');
          this.mediaRecorder.start(1000);
        } else {
          console.warn('MediaRecorder is in state:', this.mediaRecorder.state);
        }
      } catch (error) {
        console.error('Error starting recording:', error);
        this.isRecording = false;
      }
    },
    async stopRecording() {
      console.log('Stopping recording...');
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
      } else {
        console.warn('MediaRecorder is not in recording state:', this.mediaRecorder?.state);
      }
    },
    resetRecording() {
      console.log('Resetting recording state...');
      this.audioChunks = [];
      this.currentSize = 0;
      this.chunkCount = 0;
    },
    async emitCurrentChunks() {
      if (this.audioChunks.length === 0) {
        console.log('No chunks to emit');
        return;
      }

      console.log(`Creating blob from ${this.audioChunks.length} chunks...`);
      const blob = new Blob(this.audioChunks, { 
        type: 'audio/webm;codecs=opus' 
      });
      console.log(`Blob created, size: ${blob.size} bytes`);
      
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64Data = reader.result.split(',')[1];
          console.log('Emitting audio_ready event...');
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
        
        // If still recording and in inactive state, restart
        if (this.isRecording && (!this.mediaRecorder || this.mediaRecorder.state === 'inactive')) {
          console.log('Restarting MediaRecorder for next chunk...');
          this.startRecording();
        }
      });
    }
  }
};
</script>

<style scoped>
.recorder-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 1rem;
  gap: 0.5rem;
}

/* Recording indicator styles */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc3545;
  font-weight: bold;
}

.debug-info {
  font-size: 0.8rem;
  color: #666;
  font-family: monospace;
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
