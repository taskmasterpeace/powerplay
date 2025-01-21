import pyaudio
import wave
import io
from pydub import AudioSegment
import threading
import time
import numpy as np
from typing import Optional, Callable

class AudioRecorder:
    """Handles real-time audio recording with MP3 conversion"""
    
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=44100, chunk=1024, mp3_bitrate='128k'):
        self.recent_frames = []  # Keep recent frames for level monitoring
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.mp3_bitrate = mp3_bitrate
        
        self.frames = []
        self.is_recording = False
        self.audio = pyaudio.PyAudio()
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        
    def start(self, callback: Optional[Callable] = None):
        """Start recording audio"""
        self.is_recording = True
        self._stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        def record():
            while self.is_recording:
                data = self._stream.read(self.chunk)
                self.frames.append(data)
                if callback:
                    callback(data)
                    
        self._thread = threading.Thread(target=record)
        self._thread.start()
        
    def get_audio_level(self) -> float:
        """Get current audio level (RMS)"""
        if not self.recent_frames:
            return 0.0
        try:
            # Convert recent audio data to numpy array
            audio_data = np.frombuffer(b''.join(self.recent_frames), dtype=np.int16)
            # Calculate RMS
            rms = np.sqrt(np.mean(np.square(audio_data)))
            # Normalize to 0-1
            return min(1.0, rms / 32767)
        except:
            return 0.0

    def stop(self) -> bytes:
        """Stop recording and return MP3 data"""
        self.is_recording = False
        if self._thread:
            self._thread.join()
            
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            
        self.audio.terminate()
        
        # Convert to MP3
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            
        wav_buffer.seek(0)
        audio_segment = AudioSegment.from_wav(wav_buffer)
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format='mp3', bitrate=self.mp3_bitrate)
        
        return mp3_buffer.getvalue()
