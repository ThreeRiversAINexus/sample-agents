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
export default {
  data() {
    return {
      CHUNK_SIZE_LIMIT: 0.01 * 1024 * 1024,
      isRecording: false,
      mediaRecorder: null,
      stream: null,
      audioChunks: [],
      currentSize: 0,
      chunkCount: 0,
      isProcessingChunk: false
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
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true
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

        if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
          this.resetRecording();
          
          // Test available MIME types
          const mimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg'
          ];
          
          let selectedType = null;
          for (const type of mimeTypes) {
            if (MediaRecorder.isTypeSupported(type)) {
              selectedType = type;
              console.log(`Using MIME type: ${type}`);
              break;
            }
          }
          
          if (!selectedType) {
            throw new Error('No supported MIME type found');
          }

          const options = {
            mimeType: selectedType,
            audioBitsPerSecond: 16000
          };

          console.log('Creating new MediaRecorder with options:', options);
          this.mediaRecorder = new MediaRecorder(this.stream, options);

          this.mediaRecorder.addEventListener('dataavailable', async (event) => {
            if (event.data.size > 0) {
              console.log(`Chunk ${++this.chunkCount} received: ${event.data.size} bytes`);
              this.audioChunks.push(event.data);
              this.currentSize += event.data.size;
              
              console.log(`Current total size: ${this.currentSize} bytes (limit: ${this.CHUNK_SIZE_LIMIT} bytes)`);
              if (this.currentSize >= this.CHUNK_SIZE_LIMIT && !this.isProcessingChunk) {
                console.log('Size limit reached, stopping current recording...');
                this.isProcessingChunk = true;
                this.mediaRecorder.stop();
              }
            }
          });

          this.mediaRecorder.addEventListener('start', () => {
            console.log('MediaRecorder started');
            this.isRecording = true;
            this.isProcessingChunk = false;
          });

          this.mediaRecorder.addEventListener('stop', async () => {
            console.log('MediaRecorder stopped');
            if (this.audioChunks.length > 0) {
              console.log('Processing chunks...');
              await this.processChunks();
            }
            
            // If still recording, start a new recorder
            if (this.isRecording) {
              console.log('Starting new recording segment...');
              this.startRecording();
            } else {
              this.isRecording = false;
            }
          });

          this.mediaRecorder.addEventListener('error', (error) => {
            console.error('MediaRecorder error:', error);
            this.isRecording = false;
          });

          // Start recording with 1-second chunks
          console.log('Starting MediaRecorder...');
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
      this.isRecording = false;
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
      }
    },
    resetRecording() {
      console.log('Resetting recording state...');
      this.audioChunks = [];
      this.currentSize = 0;
      this.chunkCount = 0;
      this.isProcessingChunk = false;
    },
    async processChunks() {
      if (this.audioChunks.length === 0) {
        console.log('No chunks to process');
        return;
      }

      console.log(`Creating blob from ${this.audioChunks.length} chunks...`);
      const blob = new Blob(this.audioChunks, { 
        type: this.mediaRecorder.mimeType 
      });
      console.log(`Blob created, size: ${blob.size} bytes, type: ${blob.type}`);
      
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64Data = reader.result.split(',')[1];
          console.log('Emitting audio_ready event...');
          this.$emit('audio_ready', { 
            audioBlobBase64: base64Data,
            mimeType: this.mediaRecorder.mimeType
          });
          resolve();
        };
        reader.readAsDataURL(blob);
      }).finally(() => {
        this.resetRecording();
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
