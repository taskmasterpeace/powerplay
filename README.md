# MASSY - Multi-Service Audio Transcription System

A Python-based desktop application for transcribing audio files using multiple service providers.

## Features

- Support for OpenAI Whisper and AssemblyAI transcription services
- Real-time audio recording and transcription
- Batch processing of audio files
- Calendar-based organization of recordings
- Media player with transcript viewer
- Customizable processing intervals
- Support for multiple audio formats (MP3, WAV, M4A)

## Requirements

- Python 3.8+
- See requirements.txt for Python package dependencies
- OpenAI API key (for Whisper transcription)
- AssemblyAI API key (for real-time transcription)

## Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file with your API keys:
```
OPENAI_API_KEY=your_key_here
ASSEMBLYAI_API_KEY=your_key_here
```

## Usage

Run the main application:
```bash
python transcription_app.py
```

## License

MIT License - See LICENSE file for details
