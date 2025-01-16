import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from datetime import datetime
import os
import platform
import subprocess

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
                               showweeknumbers=False)
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
            self.current_folder = folder_path
            self.folder_path.set(folder_path)
            self.load_files_from_folder(folder_path)
            
    def load_files_from_folder(self, folder_path):
        """Load all audio files from selected folder"""
        self.audio_files.clear()
        self.file_listbox.delete(0, tk.END)
        
        # Use FileHandler to get files
        mp3_files, transcript_status = self.app.file_handler.get_mp3_files(folder_path)
        
        for file_name in mp3_files:
            file_path = os.path.join(folder_path, file_name)
            # Get creation date
            creation_date = self.app.file_handler.get_creation_date(file_path)
            date_str = creation_date.strftime('%Y-%m-%d')
            
            # Store in audio_files dictionary
            if date_str not in self.audio_files:
                self.audio_files[date_str] = []
            self.audio_files[date_str].append(file_path)
            
        # Update calendar display
        self.mark_dates_with_files()
        
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
