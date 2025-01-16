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
            
        # Configure enabled features
        transcription_config = aai.TranscriptionConfig(
            speaker_labels=config.get('speaker_labels', False) if config else False,
            auto_chapters=config.get('chapters', False) if config else False,
            entity_detection=config.get('entity', False) if config else False,
            key_phrases=config.get('keyphrases', False) if config else False,
            summarization=config.get('summary', False) if config else False
        )
        
        transcript = self.transcriber.transcribe(
            file_path,
            transcription_config
        )
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
            
        # Build formatted output
        formatted_text = []
        
        # Add summary if enabled
        if config.get('summary') and transcript.summary:
            formatted_text.append("=== Summary ===")
            formatted_text.append(transcript.summary)
            formatted_text.append("\n")
        
        # Add chapters if enabled
        if config.get('chapters') and transcript.chapters:
            formatted_text.append("=== Chapters ===")
            for chapter in transcript.chapters:
                formatted_text.append(f"{chapter.headline}")
                formatted_text.append(f"Start: {chapter.start}ms")
                formatted_text.append(f"Summary: {chapter.summary}")
                formatted_text.append("")
            formatted_text.append("\n")
        
        # Add entities if enabled
        if config.get('entity') and transcript.entities:
            formatted_text.append("=== Entities ===")
            for entity in transcript.entities:
                formatted_text.append(f"{entity.text} ({entity.entity_type})")
            formatted_text.append("\n")
        
        # Add key phrases if enabled
        if config.get('keyphrases') and transcript.key_phrases:
            formatted_text.append("=== Key Phrases ===")
            for phrase in transcript.key_phrases:
                formatted_text.append(phrase)
            formatted_text.append("\n")
        
        # Add main transcript
        formatted_text.append("=== Transcript ===")
        if config.get('speaker_labels'):
            for utterance in transcript.utterances:
                formatted_text.append(f"Speaker {utterance.speaker}: {utterance.text}")
        else:
            formatted_text.append(transcript.text)
        
        return "\n".join(formatted_text)
