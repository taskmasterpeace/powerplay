import os
from pathlib import Path

# Base directories
ROOT_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
AUDIO_FILES_DIR = ROOT_DIR / "audio_files"

# Source-specific directories
RECORDINGS_DIR = AUDIO_FILES_DIR / "recordings"
IMPORTS_DIR = AUDIO_FILES_DIR / "imports"
BATCH_DIR = AUDIO_FILES_DIR / "batch"

# Ensure all directories exist
for directory in [AUDIO_FILES_DIR, RECORDINGS_DIR, IMPORTS_DIR, BATCH_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
