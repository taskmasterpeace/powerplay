import os
import datetime
import re

class FileHandler:
    def __init__(self):
        self.processed_files = []
        self.skipped_files = []
        self.date_pattern = re.compile(r'^(\d{6})_.*\.mp3$')
        self.strict_naming = False  # New flag to control naming convention enforcement
        
    def get_mp3_files(self, folder_path):
        """Return list of MP3 files in the folder"""
        print(f"Scanning folder: {folder_path}")
        mp3_files = []
        try:
            for f in os.listdir(folder_path):
                print(f"Checking file: {f}")
                if not f.lower().endswith('.mp3'):
                    print(f"Skipping non-MP3 file: {f}")
                    continue
                    
                # If strict naming is enabled, validate the pattern
                if self.strict_naming and not self.date_pattern.match(f):
                    print(f"Warning: File {f} doesn't match YYMMDD_filename.mp3 format")
                    self.skipped_files.append((f, "Doesn't match YYMMDD_filename.mp3 format"))
                    continue
                    
                mp3_files.append(f)
                print(f"Added MP3 file: {f}")
        except Exception as e:
            print(f"Error scanning folder: {str(e)}")
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
