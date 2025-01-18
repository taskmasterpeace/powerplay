import assemblyai as aai
import queue
from typing import Optional, Dict, Any, Callable

class AssemblyAIRealTimeTranscription:
    """Handles real-time transcription using AssemblyAI's SDK"""
    
    def __init__(self, api_key: str, sample_rate: int = 16000,
                 on_data: Optional[Callable] = None,
                 on_error: Optional[Callable] = None):
        aai.settings.api_key = api_key
        self.sample_rate = sample_rate
        self.transcript_queue = queue.Queue()
        self.is_running = False
        self._audio_data = bytearray()
        
        # Configure callbacks
        self.on_data = on_data
        self.on_error = on_error
        
        # Initialize transcriber
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=sample_rate,
            on_data=self._handle_transcript,
            on_error=self._handle_error,
        )
        
    def _handle_transcript(self, transcript: aai.RealtimeTranscript):
        """Internal handler for transcripts"""
        if not transcript.text:
            return
            
        result = {
            'text': transcript.text,
            'is_final': isinstance(transcript, aai.RealtimeFinalTranscript),
            'timestamp': None  # AssemblyAI SDK doesn't provide timestamps in the same way
        }
        
        self.transcript_queue.put(result)
        
        if self.on_data:
            self.on_data(result)
        
    def _handle_error(self, error: aai.RealtimeError):
        """Internal handler for errors"""
        if self.on_error:
            self.on_error(error)
        
        
    def start(self):
        """Start real-time transcription"""
        self.is_running = True
        self.transcriber.connect()
                
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
