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
        print("Starting transcription...")
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
        total_files = len(mp3_files)
        processed_count = 0
        
        # Reset progress display
        self.main_window.progress_frame.status_var.set(f"Starting transcription of {total_files} files...")
        self.main_window.progress_frame.overall_progress['value'] = 0
        
        for file_name in mp3_files:
            if self.stop_event.is_set():
                self.main_window.progress_frame.status_var.set("Transcription stopped by user")
                break
                
            file_path = os.path.join(folder_path, file_name)
            self.main_window.progress_frame.update_progress(file_name, processed_count, total_files)
            
            try:
                # Get transcription config
                config = {
                    'speaker_labels': self.main_window.model_frame.speaker_var.get(),
                    'chapters': self.main_window.model_frame.chapters_var.get(),
                    'entity': self.main_window.model_frame.entity_var.get(),
                    'keyphrases': self.main_window.model_frame.keyphrases_var.get(),
                    'summary': self.main_window.model_frame.summary_var.get()
                }
                
                # Transcribe file
                transcript = self.current_service.transcribe(file_path, config)
                
                # Save transcript
                output_file = self.file_handler.generate_output_filename(file_name, "txt")
                output_path = os.path.join(folder_path, output_file)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
                
                self.file_handler.processed_files.append(file_name)
                self.main_window.progress_frame.add_file_result(file_name, "Success")
                
            except Exception as e:
                self.file_handler.skipped_files.append((file_name, str(e)))
                self.main_window.progress_frame.add_file_result(file_name, f"Failed: {str(e)}")
                continue
            
            processed_count += 1
            
        # Update final status
        final_status = f"Completed: {processed_count}/{total_files} files processed"
        if self.stop_event.is_set():
            final_status += " (Stopped by user)"
        self.main_window.progress_frame.status_var.set(final_status)
            
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
