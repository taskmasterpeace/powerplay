import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from .media_player import MediaPlayerFrame
from datetime import datetime
import os
import platform
import subprocess
import re
from utils.file_handler import FileStatus

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
        self.file_statuses = {}  # Track file statuses
        
        # Configure highlight tag for calendar
        self.highlight_tag = 'highlight'
        
        # Create main container with horizontal split
        self.main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create top section paned window
        self.top_section = ttk.PanedWindow(self.main_container, orient=tk.HORIZONTAL)
        self.main_container.add(self.top_section)

        # Left side - Controls and Calendar
        self.left_frame = ttk.Frame(self.top_section)
        self.top_section.add(self.left_frame, weight=1)
        
        # Folder selection
        self.folder_frame = ttk.LabelFrame(self.left_frame, text="Folder Selection")
        self.folder_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add folder controls frame
        self.folder_controls = ttk.Frame(self.folder_frame)
        self.folder_controls.pack(fill=tk.X, padx=5, pady=2)
        
        self.folder_path = tk.StringVar()
        ttk.Button(self.folder_controls, text="Select Folder", 
                  command=self.select_folder).pack(side=tk.LEFT, pady=5)
                  
        # Add subfolder option
        self.include_subfolders = tk.BooleanVar(value=False)
        self.subfolder_check = ttk.Checkbutton(
            self.folder_controls,
            text="Include Subfolders",
            variable=self.include_subfolders,
            command=self.refresh_files
        )
        self.subfolder_check.pack(side=tk.LEFT, padx=5, pady=5)
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
        self.right_frame = ttk.Frame(self.top_section)
        self.top_section.add(self.right_frame, weight=2)
        
        
        # Create notebook for file views
        self.file_notebook = ttk.Notebook(self.right_frame)
        self.file_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Date view tab
        self.date_frame = ttk.Frame(self.file_notebook)
        self.file_notebook.add(self.date_frame, text="By Date")
        
        # All files tab
        self.all_files_frame = ttk.Frame(self.file_notebook)
        self.file_notebook.add(self.all_files_frame, text="All Files")
        
        # File list frame for date view
        self.files_frame = ttk.LabelFrame(self.date_frame, text="Audio Files")
        self.files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add files label
        self.files_label = ttk.Label(self.files_frame, text="Files for selected date:")
        self.files_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Status indicator frame
        self.status_frame = ttk.Frame(self.files_frame)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Status legend
        ttk.Label(self.status_frame, text="🎵 Audio Only").pack(side=tk.LEFT, padx=2)
        ttk.Label(self.status_frame, text="📝 Has Transcript").pack(side=tk.LEFT, padx=2)
        
        # File listbox with scrollbar for date view
        self.file_list_frame = ttk.Frame(self.files_frame)
        self.file_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(self.file_list_frame)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.file_scrollbar = ttk.Scrollbar(self.file_list_frame, 
                                          orient="vertical",
                                          command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=self.file_scrollbar.set)
        
        # All files list
        self.all_files_label = ttk.Label(self.all_files_frame, text="All Audio Files:")
        self.all_files_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.all_files_frame_inner = ttk.Frame(self.all_files_frame)
        self.all_files_frame_inner.pack(fill=tk.BOTH, expand=True)
        
        self.all_files_listbox = tk.Listbox(self.all_files_frame_inner)
        self.all_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.all_files_scrollbar = ttk.Scrollbar(self.all_files_frame_inner,
                                                orient="vertical",
                                                command=self.all_files_listbox.yview)
        self.all_files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.all_files_listbox.configure(yscrollcommand=self.all_files_scrollbar.set)
        
        # Bind events for all files list
        self.all_files_listbox.bind('<<ListboxSelect>>', self.on_all_files_select)
        self.all_files_listbox.bind('<Button-3>', self.show_context_menu)
        
        # Bind file selection and right-click
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        self.file_listbox.bind('<Button-3>', self.show_context_menu)
        
        # Create context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Play in Media Player", command=self.play_in_media_player)
        self.context_menu.add_command(label="Go to Date", command=self.go_to_date)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Transcript", command=self.view_transcript)
        
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
            
    def refresh_files(self):
        """Refresh files based on current folder and subfolder setting"""
        if self.current_folder:
            self.load_files_from_folder(self.current_folder)
            
    def load_files_from_folder(self, folder_path):
        """Load all audio files from selected folder and optionally subfolders"""
        self.audio_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.all_files_listbox.delete(0, tk.END)
        
        print(f"Loading files from: {folder_path}")  # Debug print
        
        # Use FileHandler to get files with subfolder option
        mp3_files, transcript_status = self.app.file_handler.get_mp3_files(
            folder_path, 
            include_subfolders=self.include_subfolders.get()
        )
        
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
            
            # Add to all files listbox with date prefix and status
            status = self.get_file_status(file_path)
            status_prefix = "📝 " if status["has_transcript"] else "🎵 "
            display_name = f"{date_str}: {os.path.basename(file_path)}"
            self.all_files_listbox.insert(tk.END, f"{status_prefix}{display_name}")
        
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
        # Reset all dates and tags
        self.calendar.calevent_remove('all')
        self.calendar.tag_config(self.highlight_tag, background='yellow')
        
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
        try:
            selected_date = self.calendar.get_date()
            # Validate date format and existence
            datetime.strptime(selected_date, '%Y-%m-%d')
            
            self.files_label.config(text=f"Files for {selected_date}:")
            
            # Clear and repopulate listbox with only files from selected date
            self.file_listbox.delete(0, tk.END)
            
            if selected_date in self.audio_files:
                for file_path in self.audio_files[selected_date]:
                    # Get file status and add to listbox with status indicator
                    status = self.get_file_status(file_path)
                    status_prefix = "📝 " if status["has_transcript"] else "🎵 "
                    display_name = f"{selected_date}: {os.path.basename(file_path)}"
                    self.file_listbox.insert(tk.END, f"{status_prefix}{display_name}")
        except ValueError:
            # Invalid date selected, reset to today
            today = datetime.now().strftime('%Y-%m-%d')
            self.calendar.selection_set(today)
            self.files_label.config(text=f"Files for {today}:")
            self.file_listbox.delete(0, tk.END)
                
    def on_file_select(self, event):
        """Handle file selection in listbox"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
            
        item_text = self.file_listbox.get(selection[0])
        # Remove any status emoji and clean up whitespace
        clean_text = item_text.lstrip("🎵 ").lstrip("📝 ")
        date_str = clean_text.split(": ")[0]  # Extract date from "YYYY-MM-DD: filename"
        file_name = clean_text.split(": ")[1]  # Get filename part
        
        # Find full file path
        if date_str in self.audio_files:
            file_path = next((fp for fp in self.audio_files[date_str] 
                            if os.path.basename(fp) == file_name), None)
            if file_path:
                # Update UI to show file is selected
                has_transcript = self.app.file_handler.check_transcript_exists(file_path)
                self.view_transcript_btn.configure(state='normal' if has_transcript else 'disabled')
                
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
                
    def on_all_files_select(self, event):
        """Handle selection in all files listbox"""
        selection = self.all_files_listbox.curselection()
        if not selection:
            return
            
        item_text = self.all_files_listbox.get(selection[0])
        date_str = item_text.split(": ")[0]  # Extract date from "YYYY-MM-DD: filename"
        file_name = item_text.split(": ")[1]  # Get filename part
        
        # Find full file path
        if date_str in self.audio_files:
            file_path = next((fp for fp in self.audio_files[date_str] 
                            if os.path.basename(fp) == file_name), None)
            if file_path:
                # Update UI to show file is selected
                has_transcript = self.app.file_handler.check_transcript_exists(file_path)
                self.view_transcript_btn.configure(state='normal' if has_transcript else 'disabled')

    def get_file_status(self, file_path: str) -> dict:
        """Get status for a file, loading or creating metadata if needed"""
        if file_path not in self.file_statuses:
            status = FileStatus(file_path)
            self.file_statuses[file_path] = status
            
            # Update transcript status
            has_transcript = self.app.file_handler.check_transcript_exists(file_path)
            if has_transcript != status.metadata["status"]["has_transcript"]:
                status.update_status(has_transcript=has_transcript)
                
        return self.file_statuses[file_path].metadata["status"]
        
    def show_context_menu(self, event):
        """Show context menu on right click"""
        try:
            # Determine which listbox was clicked
            widget = event.widget
            if widget == self.file_listbox or widget == self.all_files_listbox:
                selection = widget.curselection()
                if selection:
                    self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
            
    def play_in_media_player(self):
        """Load selected file in media player and switch to that tab"""
        # Check both listboxes for selection
        selection = self.file_listbox.curselection() or self.all_files_listbox.curselection()
        if not selection:
            return
            
        # Get text from whichever listbox has the selection
        if self.file_listbox.curselection():
            item_text = self.file_listbox.get(selection[0])
        else:
            item_text = self.all_files_listbox.get(selection[0])
        clean_text = item_text.lstrip("🎵 ").lstrip("📝 ")
        date_str = clean_text.split(": ")[0]
        file_name = clean_text.split(": ")[1]
        
        if date_str in self.audio_files:
            file_path = next((fp for fp in self.audio_files[date_str] 
                            if os.path.basename(fp) == file_name), None)
            if file_path:
                # Load audio and transcript in media player and switch to media player tab
                self.app.main_window.media_player.load_audio(file_path)
                if self.app.file_handler.check_transcript_exists(file_path):
                    transcript_path = os.path.splitext(file_path)[0] + '_transcript.txt'
                    self.app.main_window.media_player.load_transcript(transcript_path)
                self.app.main_window.notebook.select(self.app.main_window.media_player)
                
    def go_to_date(self):
        """Navigate to the date of the selected file"""
        # Check both listboxes for selection
        selection = self.file_listbox.curselection() or self.all_files_listbox.curselection()
        if not selection:
            return
            
        # Get text from whichever listbox has the selection
        if self.file_listbox.curselection():
            item_text = self.file_listbox.get(selection[0])
        else:
            item_text = self.all_files_listbox.get(selection[0])
        clean_text = item_text.lstrip("🎵 ").lstrip("📝 ")
        date_str = clean_text.split(": ")[0]
        
        # Switch to date view tab
        self.file_notebook.select(0)
        
        # Jump to date in calendar
        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        self.calendar.selection_set(file_date)
        self.calendar.see(file_date)
        
        # Update file list for selected date
        self.on_date_select(None)
        
    def view_transcript(self):
        """View transcript for selected file and switch to calendar view"""
        # Check both listboxes for selection
        selection = self.file_listbox.curselection() or self.all_files_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to view")
            return
            
        # Get text from whichever listbox has the selection
        if self.file_listbox.curselection():
            item_text = self.file_listbox.get(selection[0])
        else:
            item_text = self.all_files_listbox.get(selection[0])
            
        # Clean up the text and extract components
        clean_text = item_text.lstrip("🎵 ").lstrip("📝 ")
        date_str = clean_text.split(": ")[0].strip()
        file_name = clean_text.split(": ")[1].strip()
        
        # Switch to calendar view and select date
        self.calendar.selection_set(datetime.strptime(date_str, '%Y-%m-%d').date())
        self.calendar.see(datetime.strptime(date_str, '%Y-%m-%d').date())
        self.on_date_select(None)  # Update file list for selected date
        
        # Find and open transcript
        if date_str in self.audio_files:
            file_path = next((fp for fp in self.audio_files[date_str] 
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
