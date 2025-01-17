import websockets
import asyncio
import json
import base64
import audioop
import queue
import threading
import time
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
        url = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate={self.sample_rate}"
        
        # Configure retry parameters
        retry_count = 0
        max_retries = 3
        retry_delay = 1.0
        
        while retry_count < max_retries:
            try:
                self.websocket = await websockets.connect(
                    url,
                    extra_headers={"Authorization": self.api_key},
                    ping_interval=5,
                    ping_timeout=20
                )
                
                # Wait for and validate session begins message
                response = await self.websocket.recv()
                session_data = json.loads(response)
                
                if session_data.get("message_type") == "SessionBegins":
                    self.session_id = session_data.get("session_id")
                    print(f"Session established: {self.session_id}")
                    return
                elif "error" in session_data:
                    raise Exception(f"Connection failed: {session_data['error']}")
                    
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Failed to connect after {max_retries} attempts: {e}")
                    if self.websocket:
                        await self.websocket.close()
                    raise
                
                wait_time = retry_delay * (2 ** retry_count)
                print(f"Connection attempt {retry_count} failed. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        # Send configuration
        await self.websocket.send(json.dumps({
            "sample_rate": self.sample_rate,
            "speaker_labels": self.speaker_detection,
            "format_text": True
        }))
        
    async def _run_transcription(self):
        """Main async routine for handling transcription"""
        try:
            while self.is_running and self.websocket:
                # Handle audio sending
                try:
                    audio_data = self.audio_queue.get_nowait()
                    if audio_data:
                        # Send raw binary audio data
                        await self.websocket.send(audio_data)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                # Handle receiving transcripts
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=0.1)
                    data = json.loads(response)
                    
                    # Validate message schema
                    if "message_type" not in data:
                        continue
                        
                    msg_type = data["message_type"]
                    
                    if msg_type in ["PartialTranscript", "FinalTranscript"]:
                        if "text" not in data:
                            continue
                            
                        self.transcript_queue.put({
                            'text': data['text'],
                            'is_final': msg_type == "FinalTranscript",
                            'timestamp': data.get('audio_start'),
                            'speaker': data.get('speaker', 'Speaker 1')
                        })
                    elif msg_type == "SessionTerminated":
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error processing transcript: {e}")
                    if "not authorized" in str(e).lower():
                        print("Authorization failed - check API key")
                        break
                    elif "invalid request" in str(e).lower():
                        print("Invalid message format")
                        continue
                        
        except Exception as e:
            print(f"Transcription loop error: {e}")
        finally:
            if self.websocket:
                try:
                    await self.websocket.send(json.dumps({"terminate_session": True}))
                    await self.websocket.close()
                except:
                    pass
        
    def _process_transcripts(self):
        """Receive and process transcription results"""
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def receiver():
                try:
                    while self.is_running and self.websocket:
                        try:
                            response = await self.websocket.recv()
                            data = json.loads(response)
                            if data.get("message_type") == "FinalTranscript":
                                self.transcript_queue.put({
                                    'text': data['text'],
                                    'timestamp': data.get('audio_start'),
                                    'speaker': data.get('speaker', 'Speaker 1')
                                })
                        except Exception as e:
                            print(f"Error receiving transcript data: {e}")
                            break
                finally:
                    if self.websocket:
                        await self.websocket.close()
                        
            if loop.is_running():
                loop.create_task(receiver())
            else:
                loop.run_until_complete(receiver())
        except Exception as e:
            print(f"Error in transcript processing thread: {e}")
        finally:
            if loop and not loop.is_closed():
                loop.close()
        
    def start(self):
        """Start real-time transcription"""
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.is_running = True
                loop.run_until_complete(self._connect())
                loop.run_until_complete(self._run_transcription())
            except Exception as e:
                print(f"Transcription error: {e}")
            finally:
                self.is_running = False
                if not loop.is_closed():
                    loop.close()
        
        self.main_thread = threading.Thread(target=run_async_loop, daemon=True)
        self.main_thread.start()
        
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
        
        # Wait for processing threads to complete
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=1.0)
        if hasattr(self, 'transcript_thread'):
            self.transcript_thread.join(timeout=1.0)
        
        if self.websocket:
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Close websocket connection
                async def close_ws():
                    await self.websocket.close()
                    
                loop.run_until_complete(close_ws())
            except Exception as e:
                print(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
