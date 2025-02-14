import tkinter as tk
from tkinter import ttk
from .components import (
    APIKeyFrame,
    ModelSelectionFrame,
    ProgressFrame
)
from .audio_sources import AudioSourceFrame
from .recording import RecordingFrame

class MainWindow:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Set up window close protocol
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main frames
        self.create_frames()
        
    def create_frames(self):
        # Batch Processing View
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_frame, text="Batch Processing")
        
        # API Keys Section
        self.api_frame = APIKeyFrame(self.batch_frame)
        self.api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Model Selection
        self.model_frame = ModelSelectionFrame(self.batch_frame)
        self.model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Audio Source Selection
        self.audio_source_frame = AudioSourceFrame(self.batch_frame, self.app)
        self.audio_source_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Progress Display
        self.progress_frame = ProgressFrame(self.batch_frame, self.app)
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Recording View - using local RecordingFrame
        self.recording_frame = RecordingFrame(self.notebook, self.app)
        self.notebook.add(self.recording_frame, text="Record")
        
        # Calendar View
        from .calendar_view import CalendarView
        self.calendar_view = CalendarView(self.notebook, self.app)  # Pass app reference
        self.notebook.add(self.calendar_view, text="Calendar View")
        
        # Media Player View
        from .media_player import MediaPlayerFrame
        self.media_player = MediaPlayerFrame(self.notebook)
        self.notebook.add(self.media_player, text="Media Player")
        
    def on_closing(self):
        """Handle application closing"""
        # Stop any ongoing recording
        if hasattr(self, 'recording_frame'):
            self.recording_frame.stop_recording()
        self.master.destroy()
