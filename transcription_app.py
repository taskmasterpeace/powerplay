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
        
    def start_transcription(self):
        # Get API keys
        openai_key = self.main_window.api_frame.openai_key.get()
        assemblyai_key = self.main_window.api_frame.assemblyai_key.get()
        
        # Get selected service
        service = self.main_window.model_frame.service_var.get()
        
        # Get folder path
        folder_path = self.main_window.file_frame.folder_path.get()
        
        if not folder_path:
            messagebox.showerror("Error", "Please select a folder first.")
            return
            
        # Setup appropriate service
        try:
            if service == "openai":
                if not openai_key:
                    messagebox.showerror("Error", "Please enter OpenAI API key.")
                    return
                self.current_service = self.openai_service
                self.current_service.setup(openai_key)
            else:
                if not assemblyai_key:
                    messagebox.showerror("Error", "Please enter AssemblyAI API key.")
                    return
                self.current_service = self.assemblyai_service
                self.current_service.setup(assemblyai_key)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize service: {str(e)}")
            return
            
        # Disable start button, enable stop button
        self.main_window.file_frame.start_button.config(state=tk.DISABLED)
        self.main_window.file_frame.stop_button.config(state=tk.NORMAL)
        
        # Clear stop event
        self.stop_event.clear()
        
        # Start transcription thread
        threading.Thread(target=self.process_files, daemon=True).start()
        
    def process_files(self):
        folder_path = self.main_window.file_frame.folder_path.get()
        mp3_files = self.file_handler.get_mp3_files(folder_path)
        
        for file_name in mp3_files:
            if self.stop_event.is_set():
                break
                
            file_path = os.path.join(folder_path, file_name)
            try:
                # Get transcription config
                config = {
                    'speaker_labels': self.main_window.model_frame.speaker_var.get()
                }
                
                # Transcribe file
                transcript = self.current_service.transcribe(file_path, config)
                
                # Save transcript
                # TODO: Implement transcript saving
                
            except Exception as e:
                self.file_handler.skipped_files.append((file_name, str(e)))
                continue
                
            self.file_handler.processed_files.append(file_name)
            
        # Re-enable start button, disable stop button
        self.main_window.file_frame.start_button.config(state=tk.NORMAL)
        self.main_window.file_frame.stop_button.config(state=tk.DISABLED)
        
    def stop_transcription(self):
        self.stop_event.set()
        
    def run(self):
        self.master.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    app.run()
