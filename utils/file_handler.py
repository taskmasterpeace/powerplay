import datetime
import re
import platform
from pathlib import Path
from typing import Tuple, List, Dict, Optional

class FileHandler:
    """Handles file operations for audio transcription files.
    
    Manages MP3 files and their corresponding transcripts, including file naming
    conventions and status tracking.
    """
    
    def __init__(self):
        self.processed_files: List[str] = []
        self.skipped_files: List[Tuple[str, str]] = []
        self.date_pattern = re.compile(r'^(\d{6})_.*\.mp3$')
        self.strict_naming = True
        
    def get_creation_date(self, file_path: str | Path) -> datetime.datetime:
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

    def get_mp3_files(self, folder_path):
        """Return list of MP3 files with transcript status"""
        print(f"Scanning folder: {folder_path}")
        mp3_files = []
        renamed_files = []  # Track files needing rename
        transcript_status = {}  # Track transcript status
        
        try:
            # First pass - check existing files and transcripts
            for f in os.listdir(folder_path):
                if not f.lower().endswith('.mp3'):
                    print(f"Skipping non-MP3 file: {f}")
                    continue
                
                file_path = os.path.join(folder_path, f)
                has_transcript = self.check_transcript_exists(file_path)
                transcript_status[f] = has_transcript
                
                if not self.date_pattern.match(f):
                    print(f"File {f} doesn't match YYMMDD_ convention")
                    print(f"Original creation date: {self.get_creation_date(file_path)}")
                    renamed_files.append(file_path)
                else:
                    mp3_files.append(f)
            
            # Second pass - perform renames
            for file_path in renamed_files:
                new_filename = self.rename_to_convention(file_path)
                if new_filename:
                    mp3_files.append(new_filename)
                    # Transfer transcript status to new filename
                    old_name = os.path.basename(file_path)
                    transcript_status[new_filename] = transcript_status.pop(old_name)
                else:
                    original_name = os.path.basename(file_path)
                    self.skipped_files.append((original_name, "Failed to rename file"))
            
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
    
    def generate_output_filename(self, input_file, output_type):
        """Generate output filename maintaining convention"""
        base_name = os.path.splitext(input_file)[0]
        return f"{base_name}_transcript.{output_type}"
