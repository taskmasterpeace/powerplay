import websockets
import asyncio
import json
import base64
import audioop
import queue
import threading
from typing import Optional, Dict, Any

class AssemblyAIRealTimeTranscription:
    """Handles real-time transcription using AssemblyAI's WebSocket API"""
    
    def __init__(self, api_key: str, sample_rate: int = 16000, 
                 speaker_detection: bool = False):
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.speaker_detection = speaker_detection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.audio_queue = queue.Queue()
        self.transcript_queue = queue.Queue()
        self.is_running = False
        self._audio_data = bytearray()
        
    async def _connect(self):
        """Establish WebSocket connection with AssemblyAI"""
        url = "wss://api.assemblyai.com/v2/realtime/ws"
        extra_headers = {
            "Authorization": self.api_key,
        }
        
        self.websocket = await websockets.connect(
            url,
            extra_headers=extra_headers,
            ping_interval=None
        )
        
        # Send configuration
        await self.websocket.send(json.dumps({
            "sample_rate": self.sample_rate,
            "speaker_labels": self.speaker_detection,
            "format_text": True
        }))
        
    def _process_audio(self):
        """Process and send audio data"""
        async def sender():
            while self.is_running:
                try:
                    audio_data = self.audio_queue.get(timeout=1)
                    if audio_data and self.websocket:
                        # Convert to base64
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        await self.websocket.send(json.dumps({
                            "audio_data": audio_base64
                        }))
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Error sending audio: {e}")
                    break
                    
        asyncio.run(sender())
        
    def _process_transcripts(self):
        """Receive and process transcription results"""
        async def receiver():
            while self.is_running:
                try:
                    if self.websocket:
                        response = await self.websocket.recv()
                        data = json.loads(response)
                        if data.get("message_type") == "FinalTranscript":
                            self.transcript_queue.put({
                                'text': data['text'],
                                'timestamp': data.get('audio_start'),
                                'speaker': data.get('speaker', 'Speaker 1')
                            })
                except Exception as e:
                    print(f"Error receiving transcript: {e}")
                    break
                    
        asyncio.run(receiver())
        
    def start(self):
        """Start real-time transcription"""
        self.is_running = True
        
        # Start WebSocket connection
        asyncio.run(self._connect())
        
        # Start processing threads
        threading.Thread(target=self._process_audio, daemon=True).start()
        threading.Thread(target=self._process_transcripts, daemon=True).start()
        
    def process_audio_chunk(self, audio_data: bytes):
        """Process incoming audio chunk"""
        if self.is_running:
            # Resample to 16kHz if needed
            if self.sample_rate != 16000:
                audio_data = audioop.ratecv(
                    audio_data, 2, 1, 44100, 16000, None)[0]
            self.audio_queue.put(audio_data)
            self._audio_data.extend(audio_data)
            
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
        """Stop transcription and close connection"""
        self.is_running = False
        if self.websocket:
            asyncio.run(self.websocket.close())
