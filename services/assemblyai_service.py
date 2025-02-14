import os
import assemblyai as aai
from .base_service import TranscriptionService

class AssemblyAITranscriptionService(TranscriptionService):
    def __init__(self):
        super().__init__()
        self.transcriber = None
        
    def setup(self, api_key=None):
        aai.settings.api_key = api_key or os.getenv('ASSEMBLYAI_API_KEY')
        self.transcriber = aai.Transcriber()
        
    def transcribe(self, file_path, config=None):
        print(f"AssemblyAI: Starting transcription for {file_path}")
        if not self.transcriber:
            raise ValueError("AssemblyAI transcriber not initialized")
            
        try:
            # Configure enabled features
            config_params = {
                'speech_model': (aai.SpeechModel.best 
                               if config.get('model') == 'best' 
                               else aai.SpeechModel.nano)
            }
            print(f"AssemblyAI: Using config params: {config_params}")
            
            if config:
                if config.get('speaker_labels'):
                    config_params['speaker_labels'] = True
                if config.get('chapters'):
                    config_params['auto_chapters'] = True
                if config.get('entity'):
                    config_params['entity_detection'] = True
                if config.get('keyphrases'):
                    config_params['auto_highlights'] = True
                if config.get('summary'):
                    config_params['summarization'] = True
                    
            transcription_config = aai.TranscriptionConfig(**config_params)
            
            transcript = self.transcriber.transcribe(
                file_path,
                transcription_config
            )
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
                
            # Build formatted output
            formatted_transcript = self.format_transcript(transcript, config)
            print(f"Generated transcript length: {len(formatted_transcript)} chars")
            return formatted_transcript
            
        except Exception as e:
            print(f"AssemblyAI: Error during transcription: {str(e)}")
            raise
            
    def format_transcript(self, transcript, config):
        """Format the transcript with all enabled features"""
        formatted_text = []
            
        def format_timestamp(ms):
            """Convert milliseconds to HH:MM:SS format"""
            seconds = int(ms / 1000)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
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
                if config.get('timestamps'):
                    start_time = format_timestamp(utterance.start)
                    formatted_text.append(f"[{start_time}] Speaker {utterance.speaker}: {utterance.text}")
                else:
                    formatted_text.append(f"Speaker {utterance.speaker}: {utterance.text}")
        else:
            if config.get('timestamps'):
                # Get sentences with timestamps
                for sentence in transcript.get_sentences():
                    start_time = format_timestamp(sentence.start)
                    formatted_text.append(f"[{start_time}] {sentence.text}")
            else:
                formatted_text.append(transcript.text)
            
        return "\n".join(formatted_text)
