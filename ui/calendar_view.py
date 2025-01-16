import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
import os

class CalendarView(ttk.Frame):
    """
    CALENDAR VIEW COMPONENT:
    Provides date-based organization and visualization of audio files
    
    STATE:
    - audio_files: Dict[date_str, List[file_paths]]
    - transcripts: Dict[file_path, transcript_data]
    
    DISPLAY:
    - Tree structure with dates as parents, files as children
    - Color coding for processing status
    """
    
    def __init__(self, master):
        super().__init__(master)
        self.audio_files = {}
        self.transcripts = {}
        
        # Create treeview calendar
        self.calendar = ttk.Treeview(self, selectmode='browse')
        self.calendar.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.calendar.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.calendar.configure(yscrollcommand=scrollbar.set)
        
        # Configure tags for status colors
        self.calendar.tag_configure('not_transcribed', background='red')
        self.calendar.tag_configure('transcribed', background='yellow')
        self.calendar.tag_configure('chapterized', background='green')
        
        # Bind selection event
        self.calendar.bind('<<TreeviewSelect>>', self.on_file_select)
        
        # Add load files button
        self.load_button = ttk.Button(self, text="Load Audio Files", 
                                    command=self.load_audio_files)
        self.load_button.pack(pady=5)
        
    def load_audio_files(self):
        """Load and organize audio files by date"""
        file_paths = filedialog.askopenfilenames(
            filetypes=[("Audio files", "*.mp3 *.mp4")]
        )
        
        for file_path in file_paths:
            # Get the creation time of the file
            creation_time = os.path.getctime(file_path)
            # Format the date and time
            date_str = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Store in the audio_files dictionary
            if date_str not in self.audio_files:
                self.audio_files[date_str] = []
            self.audio_files[date_str].append(file_path)
        
        # Update calendar display
        self.populate_calendar()
        
    def populate_calendar(self):
        """Update calendar display with audio files"""
        # Clear existing items
        for item in self.calendar.get_children():
            self.calendar.delete(item)
            
        # Add dates and files to the calendar
        for date, files in self.audio_files.items():
            # Create a parent node for each date
            date_id = self.calendar.insert('', 'end', text=date)
            
            # Add files under their date
            for file_path in files:
                status = self.get_transcription_status(file_path)
                file_name = os.path.basename(file_path)
                self.calendar.insert(date_id, 'end', text=file_name, 
                                  tags=(status,))
                
    def get_transcription_status(self, file_path):
        """Get the processing status of a file"""
        if file_path in self.transcripts:
            transcript_data = self.transcripts[file_path]
            if 'chapters' in transcript_data:
                return 'chapterized'
            else:
                return 'transcribed'
        else:
            return 'not_transcribed'
            
    def on_file_select(self, event):
        """Handle file selection in calendar"""
        selected_item = self.calendar.focus()
        item_text = self.calendar.item(selected_item, 'text')
        parent_item = self.calendar.parent(selected_item)
        
        if parent_item:  # If it's a file (not a date)
            date = self.calendar.item(parent_item, 'text')
            file_path = next((fp for fp in self.audio_files[date] 
                            if os.path.basename(fp) == item_text), None)
            if file_path:
                self.display_audio_details(file_path)
                
    def display_audio_details(self, file_path):
        """Display details for selected audio file"""
        # This will be implemented later to show waveform and transcript
        print(f"Selected file: {file_path}")
