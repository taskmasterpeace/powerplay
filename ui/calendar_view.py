import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from datetime import datetime
import os
import platform
import subprocess
import re

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
    
    def __init__(self, master, app):  # Add app parameter to access transcription services
        super().__init__(master)
        self.app = app
        self.audio_files = {}
        self.transcripts = {}
        self.current_folder = None
        
        # Create main container
        self.main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Controls and Calendar
        self.left_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.left_frame, weight=1)
        
        # Folder selection
        self.folder_frame = ttk.LabelFrame(self.left_frame, text="Folder Selection")
        self.folder_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.folder_path = tk.StringVar()
        ttk.Button(self.folder_frame, text="Select Folder", 
                  command=self.select_folder).pack(pady=5)
        self.folder_label = ttk.Label(self.folder_frame, textvariable=self.folder_path,
                                    wraplength=200)
        self.folder_label.pack(pady=5)
        
        # Calendar widget
        self.calendar = Calendar(self.left_frame, 
                               selectmode='day',
                               date_pattern='y-mm-dd',
                               showweeknumbers=False,
                               firstweekday='sunday')
        self.calendar.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.calendar.bind('<<CalendarSelected>>', self.on_date_select)
        
        # Right side - File list and controls
        self.right_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.right_frame, weight=2)
        
        # File list frame
        self.files_frame = ttk.LabelFrame(self.right_frame, text="Audio Files")
        self.files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add files label
        self.files_label = ttk.Label(self.files_frame, text="Files for selected date:")
        self.files_label.pack(fill=tk.X, padx=5, pady=5)
        
        # File listbox with scrollbar
        self.file_list_frame = ttk.Frame(self.files_frame)
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
        
        # Transcription controls
        self.control_frame = ttk.Frame(self.right_frame)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.transcribe_btn = ttk.Button(self.control_frame, 
                                       text="Transcribe Selected",
                                       command=self.transcribe_selected)
        self.transcribe_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_transcript_btn = ttk.Button(self.control_frame,
                                            text="View Transcript",
                                            command=self.view_transcript)
        self.view_transcript_btn.pack(side=tk.LEFT, padx=5)
        
    def select_folder(self):
        """Select folder and load all audio files"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            print(f"Selected folder: {folder_path}")  # Debug print
            self.current_folder = folder_path
            self.folder_path.set(folder_path)
            # Get both MP3 files and transcript files
            self.load_files_from_folder(folder_path)
            
    def load_files_from_folder(self, folder_path):
        """Load all audio files from selected folder"""
        self.audio_files.clear()
        self.file_listbox.delete(0, tk.END)
        
        print(f"Loading files from: {folder_path}")  # Debug print
        
        # Use FileHandler to get files
        mp3_files, transcript_status = self.app.file_handler.get_mp3_files(folder_path)
        
        print(f"Found MP3 files: {mp3_files}")  # Debug print
        
        earliest_date = None
        
        # Process each MP3 file
        for file_name in mp3_files:
            file_path = os.path.join(folder_path, file_name)
            
            # Try to get date from filename first
            date_match = re.match(r'^(\d{2})(\d{2})(\d{2})_', os.path.basename(file_path))
            if date_match:
                year, month, day = date_match.groups()
                date_str = f"20{year}-{month}-{day}"
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                print(f"Extracted date from filename: {date_str}")  # Debug print
            else:
                # Fallback to creation date
                creation_date = self.app.file_handler.get_creation_date(file_path)
                date_str = creation_date.strftime('%Y-%m-%d')
                file_date = creation_date.date()
                print(f"Using creation date for {file_name}: {date_str}")  # Debug print
            
            # Track earliest date
            if earliest_date is None or file_date < earliest_date:
                earliest_date = file_date
            
            # Store in audio_files dictionary
            if date_str not in self.audio_files:
                self.audio_files[date_str] = []
            self.audio_files[date_str].append(file_path)
            print(f"Added file to date {date_str}: {file_path}")  # Debug print
            
            # Add to listbox immediately with date prefix
            display_name = f"{date_str}: {os.path.basename(file_path)}"
            self.file_listbox.insert(tk.END, display_name)
            
            # Color code based on transcript status
            has_transcript = self.app.file_handler.check_transcript_exists(file_path)
            color = 'green' if has_transcript else 'red'
            self.file_listbox.itemconfig(tk.END, {'fg': color})
        
        print(f"Final audio_files dictionary: {self.audio_files}")  # Debug print
        
        # Update calendar display
        self.mark_dates_with_files()
        
        # Select earliest date if available, otherwise current date
        if earliest_date:
            self.calendar.selection_set(earliest_date)
            self.calendar.see(earliest_date)
        else:
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.calendar.selection_set(current_date)
        
    def mark_dates_with_files(self):
        """Highlight dates that have audio files"""
        # Reset all dates
        self.calendar.calevent_remove('all')
        
        print(f"Audio files by date: {self.audio_files}")  # Debug print
        print(f"Calendar widget: {self.calendar}")  # Debug print
        
        # Mark dates with files
        for date_str in self.audio_files.keys():
            try:
                # Parse the date string
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                print(f"Marking date: {date}")  # Debug print
                
                # Check if any files on this date have transcripts
                has_transcript = any(
                    self.app.file_handler.check_transcript_exists(file_path)
                    for file_path in self.audio_files[date_str]
                )
                
                # Create event with appropriate tag
                tag = 'has_transcript' if has_transcript else 'no_transcript'
                print(f"Setting calendar date: {date} with tag {tag}")  # Debug print
                
                # Create the calendar event first
                self.calendar.calevent_create(date, tag, 'Files Available')
                
                # Then force calendar to show and select the date
                self.calendar.see(date)
                self.calendar.selection_set(date)
                
                print(f"Created event for {date} with tag {tag}")  # Debug print
                
            except ValueError as e:
                print(f"Error processing date {date_str}: {e}")
                continue
        
        # Configure tags with more visible colors
        self.calendar.tag_config('has_transcript', background='#90EE90')  # Light green
        self.calendar.tag_config('no_transcript', background='#FFB6C6')  # Light pink
        
        # Force calendar update and redraw
        self.calendar.update()
        self.calendar.update_idletasks()
                
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
        
        # Highlight matching files in listbox
        for i in range(self.file_listbox.size()):
            item_text = self.file_listbox.get(i)
            if item_text.startswith(selected_date):
                self.file_listbox.selection_set(i)
                self.file_listbox.see(i)  # Ensure visible
            else:
                self.file_listbox.selection_clear(i)
                
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
                
    def transcribe_selected(self):
        """Transcribe selected file using current service"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to transcribe")
            return
            
        file_name = self.file_listbox.get(selection[0])
        selected_date = self.calendar.get_date()
        
        # Find full file path
        file_path = next((fp for fp in self.audio_files[selected_date] 
                         if os.path.basename(fp) == file_name), None)
                         
        if file_path:
            # Use the app's current transcription service
            try:
                # Get current service and config from app
                service = self.app.current_service
                config = {
                    'model': self.app.main_window.model_frame.model_var.get(),
                    'speaker_labels': self.app.main_window.model_frame.speaker_var.get(),
                    'chapters': self.app.main_window.model_frame.chapters_var.get(),
                    'entity': self.app.main_window.model_frame.entity_var.get(),
                    'keyphrases': self.app.main_window.model_frame.keyphrases_var.get(),
                    'summary': self.app.main_window.model_frame.summary_var.get(),
                    'timestamps': self.app.main_window.model_frame.timestamps_var.get()
                }
                
                transcript = service.transcribe(file_path, config)
                
                # Save transcript
                output_file = self.app.file_handler.generate_output_filename(file_path, "txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(transcript)
                    
                messagebox.showinfo("Success", "Transcription completed successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Transcription failed: {str(e)}")
                
    def view_transcript(self):
        """View transcript for selected file"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to view")
            return
            
        file_name = self.file_listbox.get(selection[0])
        selected_date = self.calendar.get_date()
        
        # Find full file path
        file_path = next((fp for fp in self.audio_files[selected_date] 
                         if os.path.basename(fp) == file_name), None)
                         
        if file_path:
            transcript_path = self.app.file_handler.generate_output_filename(file_path, "txt")
            if os.path.exists(transcript_path):
                if platform.system() == "Windows":
                    os.startfile(transcript_path)
                else:
                    subprocess.call(["xdg-open", transcript_path])
            else:
                messagebox.showinfo("Info", "No transcript found for this file")
