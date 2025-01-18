import assemblyai as aai
import queue
from typing import Optional, Dict, Any, Callable

class AssemblyAIRealTimeTranscription:
    """Handles real-time transcription using AssemblyAI's SDK"""
    
    def __init__(self, api_key: str, sample_rate: int = 16000):
        aai.settings.api_key = api_key
        self.sample_rate = sample_rate
        self.transcript_queue = queue.Queue()
        self.is_running = False
        self._audio_data = bytearray()
        
        # Initialize transcriber
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=sample_rate,
            on_data=self._handle_transcript,
            on_error=self._handle_error,
            on_open=self._handle_open,
            on_close=self._handle_close
        )
        
    def _handle_open(self, session_opened: aai.RealtimeSessionOpened):
        """Internal handler for session open"""
        print("Session ID:", session_opened.session_id)
        
    def _handle_close(self):
        """Internal handler for session close"""
        print("Session closed")
        
    def _handle_transcript(self, transcript: aai.RealtimeTranscript):
        """Internal handler for transcripts"""
        if not transcript.text:
            return
            
        result = {
            'text': transcript.text,
            'is_final': isinstance(transcript, aai.RealtimeFinalTranscript),
            'timestamp': None
        }
        
        self.transcript_queue.put(result)
        
    def _handle_error(self, error: aai.RealtimeError):
        """Internal handler for errors"""
        if self.on_error:
            self.on_error(error)
        
        
    def start(self):
        """Start real-time transcription"""
        self.is_running = True
        self.transcriber.connect()
                        
    def process_audio_chunk(self, audio_data: bytes):
        """Process incoming audio chunk"""
        if self.is_running:
            self._audio_data.extend(audio_data)
            self.transcriber.stream(audio_data)
        
    def get_next_transcription(self) -> Optional[Dict[str, Any]]:
        """Get next available transcription result"""
        try:
            return self.transcript_queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_audio_data(self) -> bytes:
        """Get recorded audio data"""
        return bytes(self._audio_data)
        
    def stop(self):
        """Stop transcription"""
        if self.is_running:
            self.is_running = False
            self.transcriber.close()
