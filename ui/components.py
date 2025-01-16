import tkinter as tk
from tkinter import ttk, filedialog
import datetime
import os
import platform
import subprocess

class APIKeyFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="API Keys")
        
        # OpenAI API Key
        ttk.Label(self, text="OpenAI API Key:").pack(pady=5)
        self.openai_key = ttk.Entry(self, show="*")
        self.openai_key.pack(fill=tk.X, padx=5)
        
        # AssemblyAI API Key
        ttk.Label(self, text="AssemblyAI API Key:").pack(pady=5)
        self.assemblyai_key = ttk.Entry(self, show="*")
        self.assemblyai_key.pack(fill=tk.X, padx=5)

class ModelSelectionFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Transcription Settings")
        
        # Service Selection
        self.service_var = tk.StringVar(value="openai")
        ttk.Radiobutton(self, text="OpenAI Whisper", value="openai", 
                       variable=self.service_var,
                       command=self.toggle_assemblyai_features).pack(pady=5)
        ttk.Radiobutton(self, text="AssemblyAI", value="assemblyai", 
                       variable=self.service_var,
                       command=self.toggle_assemblyai_features).pack(pady=5)
        
        # Create AssemblyAI features frame
        self.assemblyai_frame = ttk.LabelFrame(self, text="AssemblyAI Features")
        
        # Speaker Detection
        self.speaker_var = tk.BooleanVar(value=False)
        self.speaker_check = ttk.Checkbutton(self.assemblyai_frame, 
                                           text="Enable Speaker Detection", 
                                           variable=self.speaker_var)
        self.speaker_check.pack(pady=2)
        
        # Auto Chapters
        self.chapters_var = tk.BooleanVar(value=False)
        self.chapters_check = ttk.Checkbutton(self.assemblyai_frame, 
                                            text="Generate Auto Chapters", 
                                            variable=self.chapters_var)
        self.chapters_check.pack(pady=2)
        
        # Entity Detection
        self.entity_var = tk.BooleanVar(value=False)
        self.entity_check = ttk.Checkbutton(self.assemblyai_frame, 
                                          text="Enable Entity Detection", 
                                          variable=self.entity_var)
        self.entity_check.pack(pady=2)
        
        # Key Phrases
        self.keyphrases_var = tk.BooleanVar(value=False)
        self.keyphrases_check = ttk.Checkbutton(self.assemblyai_frame, 
                                               text="Extract Key Phrases", 
                                               variable=self.keyphrases_var)
        self.keyphrases_check.pack(pady=2)
        
        # Summarization
        self.summary_var = tk.BooleanVar(value=False)
        self.summary_check = ttk.Checkbutton(self.assemblyai_frame, 
                                           text="Generate Summary", 
                                           variable=self.summary_var)
        self.summary_check.pack(pady=2)
        
        # Pack AssemblyAI frame
        self.assemblyai_frame.pack(fill=tk.X, pady=5, padx=5)
        self.toggle_assemblyai_features()
        
    def toggle_assemblyai_features(self):
        """Enable/disable AssemblyAI specific features based on service selection"""
        if self.service_var.get() == "assemblyai":
            for child in self.assemblyai_frame.winfo_children():
                child.configure(state=tk.NORMAL)
        else:
            for child in self.assemblyai_frame.winfo_children():
                child.configure(state=tk.DISABLED)

class FileSelectionFrame(ttk.LabelFrame):
    def __init__(self, master, app):
        super().__init__(master, text="File Selection")
        self.app = app
        
        self.folder_path = tk.StringVar()
        ttk.Button(self, text="Select Folder", 
                  command=self.select_folder).pack(pady=5)
        ttk.Label(self, textvariable=self.folder_path).pack(pady=5)
        
        # Add control buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(self.button_frame, text="Start Transcription",
                                     command=self.app.start_transcription)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(self.button_frame, text="Stop",
                                    command=self.app.stop_transcription,
                                    state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)

class ProgressFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Progress")
        self.folder_path = None  # Store folder path
        
        # Add completion time label
        self.completion_var = tk.StringVar()
        self.completion_label = ttk.Label(self, textvariable=self.completion_var)
        self.completion_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Overall progress
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.progress_label = ttk.Label(self.progress_frame, text="0%")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        self.overall_progress = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.overall_progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Current file label
        self.current_file_var = tk.StringVar()
        self.current_file_label = ttk.Label(self, textvariable=self.current_file_var)
        self.current_file_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Scrollable frame for individual file progress
        self.create_scrollable_frame()
        
    def create_scrollable_frame(self):
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", 
                                     command=self.canvas.yview)
        
        # Create inner frame for content
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window inside canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack everything
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure canvas scrolling
        self.canvas.bind("<Enter>", self._bind_mouse_scroll)
        self.canvas.bind("<Leave>", self._unbind_mouse_scroll)
        
    def _bind_mouse_scroll(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        
    def _unbind_mouse_scroll(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def update_progress(self, current_file, processed_count, total_count):
        # Get and store folder path from FileSelectionFrame if not already set
        if not self.folder_path:
            for widget in self.master.winfo_children():
                if isinstance(widget, FileSelectionFrame):
                    self.folder_path = widget.folder_path.get()
                    print(f"Setting folder path: {self.folder_path}")  # Debug print
                    break
        
        self.status_var.set(f"Processing: {processed_count}/{total_count} files")
        self.current_file_var.set(f"Current file: {current_file}")
        progress = (processed_count / total_count * 100) if total_count > 0 else 0
        self.overall_progress['value'] = progress
        self.progress_label.config(text=f"{progress:.1f}%")
        
    def mark_completion(self, start_time):
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        
        self.completion_var.set(
            f"Completed at {end_time.strftime('%H:%M:%S')} "
            f"(Duration: {minutes}m {seconds}s)"
        )
        
        # Ensure progress bar shows 100%
        self.overall_progress['value'] = 100
        self.progress_label.config(text="100%")
        
    def add_file_result(self, filename, status):
        result_frame = ttk.Frame(self.scrollable_frame)
        result_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Update status colors
        status_color = {
            "Success": "green",
            "Skipped (Transcript Exists)": "blue",
            "Failed": "red"
        }.get(status, "black")
        
        ttk.Label(result_frame, text=filename).pack(side=tk.LEFT)
        status_label = ttk.Label(result_frame, text=status, 
                               foreground=status_color)
        status_label.pack(side=tk.RIGHT)
        
        # Add View button for existing transcripts
        if status == "Skipped (Transcript Exists)":
            view_btn = ttk.Button(result_frame, text="View",
                                command=lambda: self.view_transcript(filename))
            view_btn.pack(side=tk.RIGHT, padx=5)
            
    def view_transcript(self, filename):
        """Open transcript file in default text editor"""
        if not self.folder_path:
            # Try to get folder path from FileSelectionFrame
            for widget in self.master.winfo_children():
                if isinstance(widget, FileSelectionFrame):
                    self.folder_path = widget.folder_path.get()
                    print(f"Retrieved folder path: {self.folder_path}")  # Debug print
                    break
            
            if not self.folder_path:
                print("Could not find folder path")
                return
                
        base_name = os.path.splitext(filename)[0]
        transcript_path = os.path.join(self.folder_path, f"{base_name}_transcript.txt")
        print(f"Attempting to open: {transcript_path}")  # Debug print
        
        if os.path.exists(transcript_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(transcript_path)
                else:
                    subprocess.call(["xdg-open", transcript_path])
            except Exception as e:
                print(f"Error opening transcript: {str(e)}")
