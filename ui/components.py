import tkinter as tk
from tkinter import ttk, filedialog

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
        
        # Add control buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(self.button_frame, text="Start Transcription",
                                     command=lambda: master.master.app.start_transcription())
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(self.button_frame, text="Stop",
                                    command=lambda: master.master.app.stop_transcription(),
                                    state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)
            
        # Add control buttons
        if not hasattr(self, 'button_frame'):
            self.button_frame = ttk.Frame(self)
            self.button_frame.pack(fill=tk.X, pady=5)
            
            self.start_button = ttk.Button(self.button_frame, text="Start Transcription")
            self.start_button.pack(side=tk.LEFT, padx=5)
            
            self.stop_button = ttk.Button(self.button_frame, text="Stop", state=tk.DISABLED)
            self.stop_button.pack(side=tk.LEFT, padx=5)

class ProgressFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Progress")
        
        # Overall progress
        self.overall_progress = ttk.Progressbar(self, mode='determinate')
        self.overall_progress.pack(fill=tk.X, padx=5, pady=5)
        
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
