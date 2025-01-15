from openai import OpenAI
from .base_service import TranscriptionService

class OpenAITranscriptionService(TranscriptionService):
    def __init__(self):
        super().__init__()
        self.client = None
        self.model = "whisper-1"
        
    def setup(self, api_key):
        self.client = OpenAI(api_key=api_key)
        
    def transcribe(self, file_path, config=None):
        if not self.client:
            raise ValueError("OpenAI client not initialized")
            
        with open(file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format="srt"
            )
        return response
