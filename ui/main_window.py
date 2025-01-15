import tkinter as tk
from tkinter import ttk
from .components import (
    APIKeyFrame,
    ModelSelectionFrame,
    FileSelectionFrame,
    ProgressFrame
)

class MainWindow:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        
        # Create main frames
        self.create_frames()
        
    def create_frames(self):
        # API Keys Section
        self.api_frame = APIKeyFrame(self.master)
        self.api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Model Selection
        self.model_frame = ModelSelectionFrame(self.master)
        self.model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # File Selection
        self.file_frame = FileSelectionFrame(self.master)
        self.file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Progress Display
        self.progress_frame = ProgressFrame(self.master)
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
