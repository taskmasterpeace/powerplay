import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from services.openai_service import OpenAITranscriptionService
from services.assemblyai_service import AssemblyAITranscriptionService
from ui.main_window import MainWindow
from utils.file_handler import FileHandler

class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        self.master.title("MASSY - Multi-Service Audio Transcription")
        self.master.geometry("1200x800")
        
        # Initialize services
        self.openai_service = OpenAITranscriptionService()
        self.assemblyai_service = AssemblyAITranscriptionService()
        
        # Initialize UI
        self.main_window = MainWindow(master, self)
        
        # Initialize file handler
        self.file_handler = FileHandler()
        
        # State variables
        self.stop_event = threading.Event()
        self.current_service = None
        
    def run(self):
        self.master.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    app.run()
