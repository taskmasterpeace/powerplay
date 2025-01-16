import os
import datetime
import re
import platform
from pathlib import Path

class FileHandler:
    def __init__(self):
        self.processed_files = []
        self.skipped_files = []
        self.date_pattern = re.compile(r'^(\d{6})_.*\.mp3$')
        self.strict_naming = True
        
    def get_creation_date(self, file_path):
        """Get file creation date cross-platform compatible"""
        path = Path(file_path)
        
        if platform.system() == 'Windows':
            # Windows - use creation time
            return datetime.datetime.fromtimestamp(path.stat().st_ctime)
        else:
            # Unix-like - try birth time first, fall back to modification time
            try:
                return datetime.datetime.fromtimestamp(path.stat().st_birthtime)
            except AttributeError:
                # Fallback to modification time if birth time is not available
                return datetime.datetime.fromtimestamp(path.stat().st_mtime)

    def rename_to_convention(self, original_path):
        """Rename file to match YYMMDD_ convention using file creation date"""
        try:
            # Get file creation date
            creation_date = self.get_creation_date(original_path)
            date_prefix = creation_date.strftime('%y%m%d')
            
            # Generate new filename
            directory = os.path.dirname(original_path)
            filename = os.path.basename(original_path)
            
            # Remove any existing date prefix if present
            clean_filename = re.sub(r'^\d{6}_', '', filename)
            
            new_filename = f"{date_prefix}_{clean_filename}"
            new_path = os.path.join(directory, new_filename)
            
            print(f"Renaming: {filename} -> {new_filename}")
            
            # Check if target file already exists
            if os.path.exists(new_path):
                print(f"Warning: Target file {new_filename} already exists")
                return None
                
            # Perform the rename
            os.rename(original_path, new_path)
            return new_filename
            
        except Exception as e:
            print(f"Error renaming file {original_path}: {str(e)}")
            return None

    def get_mp3_files(self, folder_path):
        """Return list of MP3 files in the folder"""
        print(f"Scanning folder: {folder_path}")
        mp3_files = []
        renamed_files = []  # Track files needing rename
        
        try:
            # First pass - identify files needing rename
            for f in os.listdir(folder_path):
                if not f.lower().endswith('.mp3'):
                    print(f"Skipping non-MP3 file: {f}")
                    continue
                
                if not self.date_pattern.match(f):
                    original_path = os.path.join(folder_path, f)
                    print(f"File {f} doesn't match YYMMDD_ convention")
                    print(f"Original creation date: {self.get_creation_date(original_path)}")
                    renamed_files.append(original_path)
                else:
                    mp3_files.append(f)
            
            # Second pass - perform renames
            for file_path in renamed_files:
                new_filename = self.rename_to_convention(file_path)
                if new_filename:
                    mp3_files.append(new_filename)
                else:
                    original_name = os.path.basename(file_path)
                    self.skipped_files.append((original_name, "Failed to rename file"))
            
            # Sort the final list
            mp3_files.sort()
            
        except Exception as e:
            print(f"Error scanning folder: {str(e)}")
            
        print(f"Final file list: {mp3_files}")
        return mp3_files
    
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
