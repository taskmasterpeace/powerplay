import os
import datetime
import re

class FileHandler:
    def __init__(self):
        self.processed_files = []
        self.skipped_files = []
        
    def get_mp3_files(self, folder_path):
        """Return list of MP3 files in the folder"""
        return [f for f in os.listdir(folder_path) 
                if f.lower().endswith('.mp3')]
    
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
