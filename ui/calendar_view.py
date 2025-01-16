import tkinter as tk
from tkinter import ttk, filedialog
from tkcalendar import Calendar
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
    - Monthly calendar view
    - File list for selected date
    - Color coding for dates with files
    """
    
    def __init__(self, master):
        super().__init__(master)
        self.audio_files = {}
        self.transcripts = {}
        
        # Create main container
        self.main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Calendar
        self.left_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.left_frame, weight=1)
        
        # Calendar widget
        self.calendar = Calendar(self.left_frame, 
                               selectmode='day',
                               date_pattern='y-mm-dd',
                               showweeknumbers=False)
        self.calendar.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.calendar.bind('<<CalendarSelected>>', self.on_date_select)
        
        # Right side - File list
        self.right_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.right_frame, weight=2)
        
        # File list label
        self.files_label = ttk.Label(self.right_frame, text="Files for selected date:")
        self.files_label.pack(fill=tk.X, padx=5, pady=5)
        
        # File listbox with scrollbar
        self.file_list_frame = ttk.Frame(self.right_frame)
        self.file_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(self.file_list_frame)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.file_scrollbar = ttk.Scrollbar(self.file_list_frame, 
                                          orient="vertical",
                                          command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=self.file_scrollbar.set)
        
        # Bind file selection
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        # Load files button
        self.load_button = ttk.Button(self.right_frame, 
                                    text="Load Audio Files",
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
            # Format the date (without time)
            date_str = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d')
            
            # Store in the audio_files dictionary
            if date_str not in self.audio_files:
                self.audio_files[date_str] = []
            self.audio_files[date_str].append(file_path)
        
        # Update calendar display
        self.mark_dates_with_files()
        # Update file list if current date has files
        self.on_date_select(None)
        
    def mark_dates_with_files(self):
        """Highlight dates that have audio files"""
        # Reset all dates
        self.calendar.calevent_remove('all')
        
        # Mark dates with files
        for date_str in self.audio_files.keys():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            self.calendar.calevent_create(date, 'has_files', 'Files Available')
        
        # Configure tag
        self.calendar.tag_config('has_files', background='lightblue')
                
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
            
    def on_date_select(self, event):
        """Handle date selection in calendar"""
        selected_date = self.calendar.get_date()
        self.files_label.config(text=f"Files for {selected_date}:")
        
        # Clear listbox
        self.file_listbox.delete(0, tk.END)
        
        # Add files for selected date
        if selected_date in self.audio_files:
            for file_path in self.audio_files[selected_date]:
                file_name = os.path.basename(file_path)
                status = self.get_transcription_status(file_path)
                self.file_listbox.insert(tk.END, file_name)
                # Color code based on status
                color = {
                    'not_transcribed': 'red',
                    'transcribed': 'orange',
                    'chapterized': 'green'
                }.get(status, 'black')
                self.file_listbox.itemconfig(tk.END, {'fg': color})
                
    def on_file_select(self, event):
        """Handle file selection in listbox"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
            
        selected_date = self.calendar.get_date()
        file_name = self.file_listbox.get(selection[0])
        
        # Find full file path
        file_path = next((fp for fp in self.audio_files[selected_date] 
                         if os.path.basename(fp) == file_name), None)
        if file_path:
            self.display_audio_details(file_path)
                
    def display_audio_details(self, file_path):
        """Display details for selected audio file"""
        # This will be implemented later to show waveform and transcript
        print(f"Selected file: {file_path}")
