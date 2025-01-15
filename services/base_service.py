class TranscriptionService:
    def __init__(self):
        pass
        
    def setup(self, api_key):
        raise NotImplementedError
        
    def transcribe(self, file_path, config=None):
        raise NotImplementedError
