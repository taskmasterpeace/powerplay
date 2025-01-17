import os
from dotenv import load_dotenv

class TranscriptionService:
    def __init__(self):
        load_dotenv()
        pass
        
    def setup(self, api_key):
        raise NotImplementedError
        
    def transcribe(self, file_path, config=None):
        raise NotImplementedError
