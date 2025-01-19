import os
from openai import OpenAI
from .base_service import TranscriptionService

class OpenAITranscriptionService(TranscriptionService):
    def __init__(self):
        super().__init__()
        self.client = None
        self.model = "whisper-1"
        
    def setup(self, api_key=None):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        
    def transcribe(self, file_path, config=None):
        print(f"OpenAI: Starting transcription for {file_path}")
        if not self.client:
            raise ValueError("OpenAI client not initialized")
            
        try:
            with open(file_path, "rb") as audio_file:
                print("OpenAI: File opened successfully")
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="srt"
                )
                print("OpenAI: Transcription completed")
                return response
        except Exception as e:
            print(f"OpenAI: Error during transcription: {str(e)}")
            raise
