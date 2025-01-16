import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
import time
from moviepy.editor import VideoFileClip
from utils.audio_recorder import AudioRecorder

class AudioSourceFrame(ttk.LabelFrame):
    def __init__(self, master, app):
        super().__init__(master, text="Audio Sources")
        self.app = app
        
        # Create notebook for different input methods
        self.source_notebook = ttk.Notebook(self)
        self.source_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Batch folder tab
        self.folder_frame = FolderFrame(self.source_notebook, app)
        self.source_notebook.add(self.folder_frame, text="Folder")
        
        # Single file tab
        self.file_frame = SingleFileFrame(self.source_notebook, app)
        self.source_notebook.add(self.file_frame, text="Single File")
        
        # Recording tab
        self.recording_frame = RecordingFrame(self.source_notebook, app)
        self.source_notebook.add(self.recording_frame, text="Record")

class FolderFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        
        self.folder_path = tk.StringVar()
        ttk.Button(self, text="Select Folder", 
                  command=self.select_folder).pack(pady=5)
        ttk.Label(self, textvariable=self.folder_path).pack(pady=5)
        
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)
            self.app.file_handler.load_files_from_folder(folder_path)

class SingleFileFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        
        ttk.Button(
            self, 
            text="Import Audio/Video File",
            command=self.import_file
        ).pack(pady=10)
        
        self.file_label = ttk.Label(self, text="No file selected")
        self.file_label.pack(pady=5)
        
    def import_file(self):
        file_types = [
            ("Audio/Video files", "*.mp3 *.mp4 *.wav *.m4a"),
            ("All files", "*.*")
        ]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if file_path:
            if file_path.lower().endswith('.mp4'):
                self.convert_to_mp3(file_path)
            else:
                self.process_audio_file(file_path)
                
    def convert_to_mp3(self, video_path):
        try:
            video = VideoFileClip(video_path)
            audio = video.audio
            
            # Generate output path in imports folder
            output_path = self.app.file_handler.generate_output_filename(
                video_path, "mp3", "imports")
                
            # Export as 128kbps MP3
            audio.write_audiofile(
                output_path,
                bitrate="128k",
                fps=44100
            )
            video.close()
            
            self.process_audio_file(output_path)
            
        except Exception as e:
            messagebox.showerror("Conversion Error", str(e))
            
    def process_audio_file(self, file_path):
        self.file_label.config(text=os.path.basename(file_path))
        # Add to processing queue or start transcription

class RecordingFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.recording = False
        
        # Controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.record_btn = ttk.Button(
            self.controls_frame,
            text="Start Recording",
            command=self.toggle_recording
        )
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.time_label = ttk.Label(self.controls_frame, text="00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # Live preview
        self.preview_frame = ttk.LabelFrame(self, text="Live Preview")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_text = tk.Text(self.preview_frame, height=10)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        self.recorder = AudioRecorder(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            chunk=1024,
            mp3_bitrate='128k'
        )
        self.recording = True
        self.record_btn.configure(text="Stop Recording")
        self.start_time = time.time()
        self.update_timer()
        self.recorder.start()
        
    def stop_recording(self):
        if hasattr(self, 'recorder'):
            audio_data = self.recorder.stop()
            filename = f"recording_{datetime.now().strftime('%H%M%S')}"
            saved_path = self.app.file_handler.save_recording(audio_data, filename)
            self.preview_text.insert('end', f"Recording saved: {saved_path}\n")
            
        self.recording = False
        self.record_btn.configure(text="Start Recording")
        
    def update_timer(self):
        if self.recording:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.time_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.after(1000, self.update_timer)
