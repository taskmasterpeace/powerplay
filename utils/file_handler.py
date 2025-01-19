import re
import os
import json
import platform
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from datetime import datetime, date

class FileStatus:
    """Manages status and metadata for audio files"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.metadata_path = file_path.replace('.mp3', '_metadata.json')
        self.load_metadata()
        
    def load_metadata(self):
        """Load or initialize metadata"""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "status": {
                    "has_audio": True,
                    "has_transcript": False,
                    "processed_by_llm": False,
                    "last_modified": datetime.now().strftime('%y%m%d_%H%M'),
                    "chunks": []
                },
                "summary": None,
                "chapters": [],
                "tags": [],
                "notes": ""
            }
            self.save_metadata()
            
    def update_status(self, **kwargs):
        """Update status fields and save"""
        self.metadata["status"].update(kwargs)
        self.metadata["status"]["last_modified"] = datetime.now().strftime('%y%m%d_%H%M')
        self.save_metadata()
        
    def save_metadata(self):
        """Save metadata to file"""
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

class FileHandler:
    """Handles file operations for audio transcription files.
    
    Manages MP3 files and their corresponding transcripts, including file naming
    conventions and status tracking across different source types (batch, recordings, imports).
    """
    
    def __init__(self):
        from config.constants import RECORDINGS_DIR, IMPORTS_DIR, BATCH_DIR
        self.processed_files: List[str] = []
        self.skipped_files: List[Tuple[str, str]] = []
        self.date_pattern = re.compile(r'^(\d{6})_.*\.mp3$')
        self.strict_naming = True
        
        # Use constants for folder structure
        self.recordings_dir = RECORDINGS_DIR
        self.imports_dir = IMPORTS_DIR 
        self.batch_dir = BATCH_DIR
        self.folders = {
            "recordings": self.recordings_dir,
            "imports": self.imports_dir,
            "batch": self.batch_dir
        }
        
        # Current working folder
        self._current_folder: Optional[str] = None
        self._folder_observers: List[callable] = []
        
    def setup_folders(self):
        """Create necessary folder structure"""
        for folder in self.folders.values():
            os.makedirs(folder, exist_ok=True)
            
    def get_dated_folder(self, base_folder: str) -> str:
        """Get or create a dated folder within the specified base folder"""
        date_str = datetime.datetime.now().strftime('%y%m%d')
        folder_path = os.path.join(self.folders[base_folder], date_str)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
        
    def get_creation_date(self, file_path: str | Path) -> datetime:
        """Gets file creation date in a cross-platform compatible way.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            datetime: The file's creation date.
        """
        path = Path(file_path)
        
        if platform.system() == 'Windows':
            return datetime.datetime.fromtimestamp(path.stat().st_ctime)
            
        try:
            return datetime.datetime.fromtimestamp(path.stat().st_birthtime)
        except AttributeError:
            return datetime.datetime.fromtimestamp(path.stat().st_mtime)

    def rename_to_convention(self, original_path: str | Path) -> Optional[str]:
        """Renames file to match YYMMDD_ convention using file creation date.
        
        Args:
            original_path: Path to the file to be renamed.
            
        Returns:
            str: New filename if successful, None if rename failed.
        """
        try:
            path = Path(original_path)
            creation_date = self.get_creation_date(path)
            date_prefix = creation_date.strftime('%y%m%d')
            
            # Remove any existing date prefix if present
            clean_filename = re.sub(r'^\d{6}_', '', path.name)
            new_filename = f"{date_prefix}_{clean_filename}"
            new_path = path.parent / new_filename
            
            if new_path.exists():
                return None
                
            path.rename(new_path)
            return new_filename
            
        except Exception:
            return None

    def check_transcript_exists(self, file_path: str | Path, output_type: str = "txt") -> bool:
        """Checks if transcript already exists for given file.
        
        Args:
            file_path: Path to the audio file.
            output_type: Expected transcript file extension.
            
        Returns:
            bool: True if transcript exists, False otherwise.
        """
        path = Path(file_path)
        transcript_path = path.parent / f"{path.stem}_transcript.{output_type}"
        return transcript_path.exists()

    def get_mp3_files(self, folder_path: str | Path, include_subfolders: bool = False) -> Tuple[List[str], Dict[str, bool]]:
        """Return list of MP3 files with transcript status.
        
        Args:
            folder_path: Path to folder containing MP3 files.
            include_subfolders: Whether to scan subfolders recursively.
            
        Returns:
            Tuple containing:
                - List of MP3 filenames
                - Dictionary mapping filenames to transcript status
        """
        print(f"Scanning folder: {folder_path}")
        folder = Path(folder_path)
        mp3_files = []
        renamed_files = []  # Track files needing rename
        transcript_status = {}  # Track transcript status
        
        try:
            # Get files based on recursion setting
            pattern = '**/*.mp3' if include_subfolders else '*.mp3'
            for f in folder.glob(pattern):
                print(f"Found MP3 file: {f.name}")  # Debug print
                if not f.name.lower().endswith('.mp3'):
                    print(f"Skipping non-MP3 file: {f.name}")
                    continue
                
                has_transcript = self.check_transcript_exists(f)
                transcript_status[f.name] = has_transcript
                
                # Always add to mp3_files list, whether it matches convention or not
                mp3_files.append(f.name)
                
                if not self.date_pattern.match(f.name):
                    print(f"File {f.name} doesn't match YYMMDD_ convention")
                    print(f"Original creation date: {self.get_creation_date(f)}")
                    renamed_files.append(f)
            
            # Second pass - perform renames
            for file_path in renamed_files:
                new_filename = self.rename_to_convention(file_path)
                if new_filename:
                    mp3_files.append(new_filename)
                    # Transfer transcript status to new filename
                    transcript_status[new_filename] = transcript_status.pop(file_path.name)
                else:
                    self.skipped_files.append((file_path.name, "Failed to rename file"))
            
            # Sort the final list
            mp3_files.sort()
            
        except Exception as e:
            print(f"Error scanning folder: {str(e)}")
            
        print(f"Final file list: {mp3_files}")
        return mp3_files, transcript_status
    
    def extract_date_from_filename(self, filename):
        """Extract date from filename format YYMMDD_*"""
        date_match = re.search(r'(\d{6})_', filename)
        if date_match:
            date_str = date_match.group(1)
            return datetime.datetime.strptime(date_str, '%y%m%d')
        return None
    
    def generate_output_filename(self, input_file: str | Path, output_type: str, source_type: str = "batch") -> str:
        """Generate output filename maintaining convention.
        
        Args:
            input_file: Input audio filename.
            output_type: Desired output file extension.
            source_type: Type of source ("recordings", "imports", or "batch").
            
        Returns:
            str: Generated output filename with transcript suffix.
        """
        path = Path(input_file)
        dated_folder = self.get_dated_folder(source_type)
        return os.path.join(dated_folder, f"{path.stem}_transcript.{output_type}")
        
    def add_folder_observer(self, callback: callable):
        """Add a callback to be notified when the current folder changes"""
        self._folder_observers.append(callback)
        
    def set_current_folder(self, folder_path: str):
        """Set the current working folder and notify observers"""
        self._current_folder = folder_path
        for callback in self._folder_observers:
            callback(folder_path)
            
    def get_current_folder(self) -> Optional[str]:
        """Get the current working folder"""
        return self._current_folder
        
    def load_files_from_folder(self, folder_path: str) -> Tuple[List[str], Dict[str, bool]]:
        """Load audio files from a folder and return their transcript status.
        
        Args:
            folder_path: Path to folder containing audio files
            
        Returns:
            Tuple containing:
                - List of audio filenames
                - Dictionary mapping filenames to transcript status
        """
        self.set_current_folder(folder_path)
        return self.get_mp3_files(folder_path)
        
    def save_recording(self, audio_data: bytes, filename: str, metadata: dict = None) -> str:
        """Save a recording to the recordings folder with standardized naming.
        
        Args:
            audio_data: Raw audio data.
            filename: Base filename (will be standardized).
            metadata: Optional dictionary of metadata to save alongside recording.
            
        Returns:
            str: Full path to saved recording.
        """
        dated_folder = self.get_dated_folder("recordings")
        # Ensure filename follows YYMMDD_HHMM_name convention
        if not re.match(r'^\d{6}_\d{4}_.*$', filename):
            current_time = datetime.datetime.now()
            filename = f"{current_time.strftime('%y%m%d_%H%M')}_{filename}"
        
        output_path = os.path.join(dated_folder, f"{filename}.mp3")
        
        # Save audio file
        with open(output_path, 'wb') as f:
            f.write(audio_data)
            
        # Save metadata if provided
        if metadata:
            metadata_path = output_path.replace('.mp3', '_metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                import json  # Add import at top of file if needed
                json.dump(metadata, f, indent=2)
            
        return output_path
