import tkinter as tk
from tkinter import ttk

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
                       variable=self.service_var).pack(pady=5)
        ttk.Radiobutton(self, text="AssemblyAI", value="assemblyai", 
                       variable=self.service_var).pack(pady=5)
        
        # Speaker Detection (AssemblyAI only)
        self.speaker_var = tk.BooleanVar(value=False)
        self.speaker_check = ttk.Checkbutton(self, text="Enable Speaker Detection", 
                                           variable=self.speaker_var)
        self.speaker_check.pack(pady=5)

class FileSelectionFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="File Selection")
        
        self.folder_path = tk.StringVar()
        ttk.Button(self, text="Select Folder", 
                  command=self.select_folder).pack(pady=5)
        ttk.Label(self, textvariable=self.folder_path).pack(pady=5)
        
    def select_folder(self):
        # Implement folder selection logic
        pass

class ProgressFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Progress")
        
        # Overall progress
        self.overall_progress = ttk.Progressbar(self, mode='determinate')
        self.overall_progress.pack(fill=tk.X, padx=5, pady=5)
        
        # Scrollable frame for individual file progress
        self.create_scrollable_frame()
        
    def create_scrollable_frame(self):
        # Create scrollable frame for file progress
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", 
                                command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
