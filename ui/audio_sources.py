import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
import time
import threading
import pyaudio
from pydub import AudioSegment
from utils.audio_recorder import AudioRecorder
from services.assemblyai_realtime import AssemblyAIRealTimeTranscription

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
            # Load video audio using pydub
            audio = AudioSegment.from_file(video_path)
            
            # Generate output path in imports folder
            output_path = self.app.file_handler.generate_output_filename(
                video_path, "mp3", "imports")
                
            # Export as 128kbps MP3
            audio.export(
                output_path,
                format="mp3",
                bitrate="128k"
            )
            
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
        self.transcribing = False
        self.current_transcript = ""
        self.markers = []  # Store markers with timestamps
        
        # Meeting Configuration Frame
        self.config_frame = ttk.LabelFrame(self, text="Meeting Configuration")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Meeting Name
        ttk.Label(self.config_frame, text="Meeting Name:").pack(pady=2)
        self.meeting_name = ttk.Entry(self.config_frame)
        self.meeting_name.pack(fill=tk.X, padx=5, pady=2)
        
        # Template Selection
        ttk.Label(self.config_frame, text="Template:").pack(pady=2)
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(self.config_frame, 
            textvariable=self.template_var,
            values=["Job Interview", "Technical Meeting", "Project Review", "Custom"])
        self.template_combo.pack(fill=tk.X, padx=5, pady=2)
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_change)
        
        # Custom Prompt
        ttk.Label(self.config_frame, text="Custom Prompt:").pack(pady=2)
        self.prompt_text = tk.Text(self.config_frame, height=3)
        self.prompt_text.pack(fill=tk.X, padx=5, pady=2)
        
        # Controls Frame
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
        
        # Display Options
        self.display_frame = ttk.Frame(self.controls_frame)
        self.display_frame.pack(side=tk.RIGHT, padx=5)
        
        self.show_timestamps = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.display_frame, text="Show Timestamps", 
                       variable=self.show_timestamps,
                       command=self.refresh_display).pack(side=tk.RIGHT)
        
        # Split View Frame
        self.split_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.split_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Transcript Frame
        self.transcript_frame = ttk.LabelFrame(self.split_frame, text="Live Transcription")
        self.split_frame.add(self.transcript_frame, weight=1)
        
        self.transcript_text = tk.Text(self.transcript_frame, wrap=tk.WORD)
        self.transcript_text.pack(fill=tk.BOTH, expand=True)
        self.transcript_scroll = ttk.Scrollbar(self.transcript_frame, 
                                             command=self.transcript_text.yview)
        self.transcript_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.transcript_text.configure(yscrollcommand=self.transcript_scroll.set)
        
        # Future LLM Response Frame (placeholder)
        self.response_frame = ttk.LabelFrame(self.split_frame, text="AI Responses")
        self.split_frame.add(self.response_frame, weight=1)
        
        self.response_text = tk.Text(self.response_frame, wrap=tk.WORD)
        self.response_text.pack(fill=tk.BOTH, expand=True)
        self.response_scroll = ttk.Scrollbar(self.response_frame, 
                                           command=self.response_text.yview)
        self.response_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_text.configure(yscrollcommand=self.response_scroll.set)
        
        # Bind function keys
        for i in range(1, 13):  # F1 through F12
            self.master.bind(f'<F{i}>', self.add_marker)
        
    def add_marker(self, event):
        """Add a marker when function key is pressed"""
        if self.recording:
            timestamp = time.time() - self.start_time
            marker = {
                'timestamp': timestamp,
                'key': event.keysym,
                'position': self.transcript_text.index(tk.INSERT)
            }
            self.markers.append(marker)
            
            # Insert marker emoji
            self.transcript_text.insert(tk.INSERT, " 🚩 ")
            self.transcript_text.see(tk.INSERT)
            
    def on_template_change(self, event):
        """Handle template selection"""
        template = self.template_var.get()
        if template == "Job Interview":
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', 
                "Help me during this interview by analyzing responses and suggesting improvements.")
        elif template == "Technical Meeting":
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0',
                "Track technical terms and concepts discussed in the meeting.")
        elif template == "Project Review":
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0',
                "Track action items, decisions, and key discussion points.")
                
    def refresh_display(self):
        """Refresh the transcript display with current settings"""
        if hasattr(self, 'current_transcript'):
            self.transcript_text.delete('1.0', tk.END)
            self.transcript_text.insert('1.0', self.current_transcript)
            
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        if not self.meeting_name.get():
            messagebox.showerror("Error", "Please enter a meeting name")
            return
            
        try:
            # Initialize AssemblyAI session
            assemblyai_key = self.app.main_window.api_frame.assemblyai_key.get()
            if not assemblyai_key:
                messagebox.showerror("Error", "Please enter AssemblyAI API key")
                return
                
            self.assemblyai_session = AssemblyAIRealTimeTranscription(
                api_key=assemblyai_key,
                sample_rate=16000,
                speaker_detection=True
            )
            
            # Start transcription session
            self.assemblyai_session.start()
            
            # Initialize audio recorder
            self.recorder = AudioRecorder(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                chunk=1024,
                mp3_bitrate='128k'
            )
            
            # Initialize metadata
            self.metadata = {
                "meeting_name": self.meeting_name.get(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "prompt_template": self.template_var.get(),
                "custom_prompt": self.prompt_text.get('1.0', tk.END.strip()),
                "speakers": [],
                "hotkey_markers": []
            }
            
            self.recording = True
            self.transcribing = True
            self.markers = []
            self.record_btn.configure(text="Stop Recording")
            self.start_time = time.time()
            self.update_timer()
            
            # Clear displays
            self.transcript_text.delete('1.0', tk.END)
            self.response_text.delete('1.0', tk.END)
            
            # Start processing threads
            self.recorder.start(callback=self.process_audio_chunk)
            threading.Thread(target=self.process_transcriptions, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            self.stop_recording()
        
    def process_audio_chunk(self, audio_chunk):
        """Process audio chunks for live transcription"""
        if self.transcribing:
            try:
                self.assemblyai_session.process_audio_chunk(audio_chunk)
            except Exception as e:
                print(f"Transcription error: {e}")
        
    def stop_recording(self):
        if hasattr(self, 'recorder'):
            audio_data = self.recorder.stop()
            
            # Update metadata with markers
            self.metadata["hotkey_markers"] = [
                {
                    "timestamp": f"{int(m['timestamp'] // 60):02d}:{int(m['timestamp'] % 60):02d}",
                    "key": m['key']
                } for m in self.markers
            ]
            
            # Save recording with metadata
            filename = f"{self.meeting_name.get()}_{datetime.now().strftime('%H%M%S')}"
            saved_path = self.app.file_handler.save_recording(
                audio_data, 
                filename,
                metadata=self.metadata
            )
            
            self.transcript_text.insert('end', f"\n\nRecording saved: {saved_path}\n")
            
        self.recording = False
        self.transcribing = False
        self.record_btn.configure(text="Start Recording")
        
    def update_timer(self):
        if self.recording:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.time_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.after(1000, self.update_timer)
            
    def process_transcriptions(self):
        """Process incoming transcriptions"""
        while self.recording:
            try:
                packet = self.assemblyai_session.get_next_transcription()
                if packet:
                    # Format transcript with timestamp and speaker
                    formatted_transcript = self.format_transcript(packet)
                    
                    # Update UI (thread-safe)
                    self.master.after(0, self.update_transcript_display, formatted_transcript)
                    
                    # Update metadata
                    if packet.get('speaker') and packet['speaker'] not in self.metadata['speakers']:
                        self.metadata['speakers'].append(packet['speaker'])
                        
            except Exception as e:
                print(f"Transcription processing error: {e}")
                time.sleep(0.1)
