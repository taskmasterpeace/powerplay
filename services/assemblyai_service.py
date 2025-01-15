import assemblyai as aai
from .base_service import TranscriptionService

class AssemblyAITranscriptionService(TranscriptionService):
    def __init__(self):
        super().__init__()
        self.transcriber = None
        
    def setup(self, api_key):
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()
        
    def transcribe(self, file_path, config=None):
        if not self.transcriber:
            raise ValueError("AssemblyAI transcriber not initialized")
            
        transcription_config = aai.TranscriptionConfig(
            speaker_labels=config.get('speaker_labels', False) if config else False
        )
        
        transcript = self.transcriber.transcribe(
            file_path,
            transcription_config
        )
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
            
        # Create a formatted transcript with speaker labels if enabled
        formatted_text = ""
        if config and config.get('speaker_labels'):
            for utterance in transcript.utterances:
                formatted_text += f"Speaker {utterance.speaker}: {utterance.text}\n"
        else:
            formatted_text = transcript.text
            
        return formatted_text
