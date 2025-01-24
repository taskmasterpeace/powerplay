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
from ui.components import DualPurposeIndicator

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

class FolderFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        
        self.folder_path = tk.StringVar()
        ttk.Button(self, text="Select Folder", 
                  command=self.select_folder).pack(pady=5)
        ttk.Label(self, textvariable=self.folder_path).pack(pady=5)
        
        # Add control buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(pady=5)
        
        self.start_button = ttk.Button(
            self.button_frame,
            text="Start Transcription",
            command=self.app.start_transcription,
            state=tk.NORMAL
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            self.button_frame,
            text="Stop",
            command=self.app.stop_transcription,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
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
        
        # Add control buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(pady=5)
        
        self.start_button = ttk.Button(
            self.button_frame,
            text="Start Transcription",
            command=self.app.start_transcription,
            state=tk.NORMAL
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            self.button_frame,
            text="Stop",
            command=self.app.stop_transcription,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.current_file = None  # Track selected file
        
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
        self.current_file = file_path  # Store selected file path

class RecordingFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.recording = False
        self.transcribing = False
        self.current_transcript = ""
        self.markers = []  # Store markers with timestamps
        
        # State variables for interval processing
        self.last_process_time = 0  # Tracks when we last processed text
        self.accumulated_text = ""   # Holds text between processing intervals
        self.recent_frames = []      # Store recent audio frames for level monitoring
        
        # Meeting Configuration Frame
        self.config_frame = ttk.LabelFrame(self, text="Meeting Configuration")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Interval Selection Frame for processing chunks
        self.interval_frame = ttk.Frame(self.config_frame)
        self.interval_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(self.interval_frame, text="Processing Interval:").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="10s")
        self.interval_combo = ttk.Combobox(
            self.interval_frame,
            textvariable=self.interval_var,
            values=["Manual", "10s", "45s", "5m", "10m"],
            width=12,
            state="readonly"
        )
        self.interval_combo.pack(side=tk.LEFT, padx=5)
        self.interval_combo.bind('<<ComboboxSelected>>', self.on_interval_change)
        
        # Hotkey hint label
        ttk.Label(self.interval_frame, text="(F12 for instant process)").pack(side=tk.LEFT, padx=5)
        
        # Bind F12 for instant processing
        self.master.bind('<F12>', self.trigger_instant_processing)
        self.bind_all('<F12>', self.trigger_instant_processing)  # Bind to all widgets
        
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
        
        # Add dual-purpose indicator
        self.dual_indicator = DualPurposeIndicator(self.controls_frame)
        self.dual_indicator.pack(side=tk.LEFT, padx=5)
        
        self.time_label = ttk.Label(self.controls_frame, text="00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # Display Options
        self.display_frame = ttk.Frame(self.controls_frame)
        self.display_frame.pack(side=tk.RIGHT, padx=5)
        
        self.show_timestamps = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.display_frame, text="Show Timestamps", 
                       variable=self.show_timestamps,
                       command=self.refresh_display).pack(side=tk.RIGHT)
        
        # Split View Frame with Template Selection
        self.split_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.split_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side: Transcript Frame (smaller)
        self.transcript_frame = ttk.LabelFrame(self.split_frame, text="Live Transcription")
        self.split_frame.add(self.transcript_frame, weight=1)
        
        self.transcript_text = tk.Text(self.transcript_frame, 
                                     wrap=tk.WORD,
                                     background='#f0f0f0',  # Light gray background
                                     font=('Courier', 9))   # Smaller font
        self.transcript_text.pack(fill=tk.BOTH, expand=True)
        self.transcript_scroll = ttk.Scrollbar(self.transcript_frame, 
                                             command=self.transcript_text.yview)
        self.transcript_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.transcript_text.configure(yscrollcommand=self.transcript_scroll.set)
        
        # Right side: LLM Response Frame (larger)
        self.response_frame = ttk.LabelFrame(self.split_frame, text="AI Insights")
        self.split_frame.add(self.response_frame, weight=2)  # Give more space to responses
        
        # Template selection frame
        self.template_frame = ttk.Frame(self.response_frame)
        self.template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.template_frame, text="Analysis Template:").pack(side=tk.LEFT, padx=5)
        self.template_var = tk.StringVar(value="Meeting Summary")
        self.template_combo = ttk.Combobox(
            self.template_frame,
            textvariable=self.template_var,
            values=["Meeting Summary", "Action Items", "Decision Tracking"],
            width=20,
            state="readonly"
        )
        self.template_combo.pack(side=tk.LEFT, padx=5)
        
        # Response text area
        self.response_text = tk.Text(self.response_frame,
                                   wrap=tk.WORD,
                                   background='white',
                                   font=('Arial', 11))      # Larger, more readable font
        self.response_text.pack(fill=tk.BOTH, expand=True)
        self.response_scroll = ttk.Scrollbar(self.response_frame, 
                                           command=self.response_text.yview)
        self.response_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_text.configure(yscrollcommand=self.response_scroll.set)
        
        # Configure text tags for chunk status
        self.transcript_text.tag_configure("processing", background="#FFFFD0")  # Light yellow
        self.transcript_text.tag_configure("processed", background="#E8F5E9")   # Light green
        self.transcript_text.tag_configure("context", background="#E3F2FD")     # Light blue
        
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
                sample_rate=16000
            )
            
            # Start transcription session
            self.assemblyai_session.start()
            
            # Initialize audio recorder with matching sample rate
            self.recorder = AudioRecorder(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,  # Match AssemblyAI's expected sample rate
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
            
            # Start indicator updates
            self.update_dual_indicator()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            self.stop_recording()
        
    def process_audio_chunk(self, audio_chunk):
        """Process audio chunks for live transcription"""
        if self.transcribing:
            try:
                self.assemblyai_session.process_audio_chunk(audio_chunk)
                # Keep last 10 frames for level monitoring
                self.recent_frames.append(audio_chunk)
                if len(self.recent_frames) > 10:
                    self.recent_frames.pop(0)
            except Exception as e:
                print(f"Transcription error: {e}")
        
    def stop_recording(self):
        """Stop recording and cleanup resources"""
        try:
            # Disable UI elements first
            self.record_btn.configure(state=tk.DISABLED)
            self.update()  # Force UI update
            
            # Set flags to stop processing
            self.transcribing = False
            self.recording = False
            
            # Stop audio recording first
            audio_data = None
            if hasattr(self, 'recorder'):
                try:
                    audio_data = self.recorder.stop()
                    delattr(self, 'recorder')
                except Exception as e:
                    print(f"Error stopping recorder: {e}")
            
            # Stop AssemblyAI session with timeout
            if hasattr(self, 'assemblyai_session'):
                try:
                    stop_thread = threading.Thread(
                        target=self._stop_assemblyai_session,
                        daemon=True
                    )
                    stop_thread.start()
                    stop_thread.join(timeout=2.0)  # Wait up to 2 seconds
                except Exception as e:
                    print(f"Error in AssemblyAI cleanup: {e}")
                finally:
                    if hasattr(self, 'assemblyai_session'):
                        delattr(self, 'assemblyai_session')
            
        # Update metadata with markers
        if hasattr(self, 'metadata'):
            self.metadata["hotkey_markers"] = [
                {
                    "timestamp": f"{int(m['timestamp'] // 60):02d}:{int(m['timestamp'] % 60):02d}",
                    "key": m['key']
                } for m in self.markers
            ]
            
            # Save recording with standardized naming
            current_time = datetime.now()
            filename = f"{current_time.strftime('%y%m%d_%H%M')}_{self.meeting_name.get()}"
            saved_path = self.app.file_handler.save_recording(
                audio_data, 
                filename,
                metadata=self.metadata
            )
            
            # Get the full transcript from the text widget
            full_transcript = self.transcript_text.get('1.0', tk.END)
            
            # Generate and save transcript file next to the MP3
            transcript_path = os.path.splitext(saved_path)[0] + '_transcript.txt'
            try:
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(full_transcript)
                self.transcript_text.insert('end', f"\n\nTranscript saved: {transcript_path}\n")
            except Exception as e:
                self.transcript_text.insert('end', f"\n\nError saving transcript: {str(e)}\n")
                
            self.transcript_text.insert('end', f"\nRecording saved: {saved_path}\n")
            
        # Re-enable and update UI
        self.record_btn.configure(
            text="Start Recording",
            state=tk.NORMAL
        )
        self.update()  # Force final UI update
        
    def update_timer(self):
        if self.recording:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.time_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.after(1000, self.update_timer)
            
    def _stop_assemblyai_session(self):
        """Helper method to stop AssemblyAI session in a separate thread"""
        try:
            if hasattr(self, 'assemblyai_session'):
                self.assemblyai_session.stop()
        except Exception as e:
            print(f"Error stopping AssemblyAI session: {e}")
            
    def update_dual_indicator(self):
        """Update the dual-purpose indicator during recording"""
        if self.recording:
            # Calculate chunk progress
            interval = self.get_current_interval()
            if interval != float('inf'):
                elapsed = time.time() - self.last_process_time
                # Ensure progress doesn't exceed 100%
                chunk_progress = min((elapsed / interval) * 100, 100)
                # Calculate actual seconds remaining
                seconds_remaining = max(interval - elapsed, 0)
            else:
                chunk_progress = 0
                seconds_remaining = 0
            
            # Get audio level
            audio_level = self.recorder.get_audio_level() * 100 if hasattr(self, 'recorder') else 0
            
            # Update the indicator with actual seconds remaining
            self.dual_indicator.update(chunk_progress, audio_level, seconds_remaining)
            
            # Schedule next update
            self.after(50, self.update_dual_indicator)
            
    def get_current_interval(self):
        """Convert interval string to seconds"""
        interval = self.interval_var.get()
        if interval == "Manual":
            return float('inf')
        # Convert time formats to seconds
        value = interval[:-1]  # Remove last character
        unit = interval[-1]    # Get last character
        try:
            value = int(value)
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            else:
                return float('inf')
        except ValueError:
            return float('inf')
        
    def on_interval_change(self, event=None):
        """Handle interval change and process if needed"""
        new_interval = self.get_current_interval()
        current_time = time.time()
        time_since_last = current_time - self.last_process_time
        
        # If we've accumulated more time than the new interval, process immediately
        if time_since_last >= new_interval and self.accumulated_text:
            self.process_text_chunk(self.accumulated_text)
            self.accumulated_text = ""
            self.last_process_time = current_time
        
    def trigger_instant_processing(self, event=None):
        """Handle F12 key press for instant processing"""
        if not self.recording:
            return
            
        if not hasattr(self, 'accumulated_text'):
            return
            
        # Flash the indicator to show chunk processing
        self.dual_indicator.create_oval(5, 5, self.dual_indicator.size-5, 
                                      self.dual_indicator.size-5, 
                                      fill='yellow', tags="flash")
        self.after(100, lambda: self.dual_indicator.delete("flash"))
            
        # Force immediate processing
        current_time = time.time()
        text_to_process = self.accumulated_text.strip()
        
        if text_to_process:
            print(f"Processing chunk: {text_to_process}")  # Debug print
            self.process_text_chunk(text_to_process)
            self.accumulated_text = ""
            self.last_process_time = current_time
            
            # Reset the visual indicator
            audio_level = self.recorder.get_audio_level() * 100 if hasattr(self, 'recorder') else 0
            self.dual_indicator.update(0, audio_level, self.get_current_interval())
            
            # Force UI update
            self.update()
        else:
            print("No text to process")  # Debug print
            
    def process_text_chunk(self, text):
        """
        Process accumulated text chunk using LangChain service
        """
        if not text or not text.strip():
            print("Empty text chunk, skipping processing")
            return
            
        current_time = datetime.now().strftime('%H:%M:%S')
        elapsed_since_last = time.time() - self.last_process_time
        chunk_header = (
            f"\n\n=== New Chunk ({current_time}) ===\n"
            f"Time since last chunk: {elapsed_since_last:.1f}s\n"
        )
        
        try:
            # Add chunk header and text
            self.transcript_text.insert(tk.END, chunk_header)
            chunk_start = self.transcript_text.index(tk.END)
            self.transcript_text.insert(tk.END, text)
            chunk_end = self.transcript_text.index(tk.END)
            self.transcript_text.see(tk.END)
            
            # Mark this chunk as being processed
            self.transcript_text.tag_add("processing", chunk_start, chunk_end)
            
            # Process with LangChain placeholder
            template = {
                "name": self.template_var.get(),
                "system": "You are an AI assistant analyzing meeting transcripts.",
                "user": f"Analyze this meeting segment: {text}"
            }
            
            response = f"[AI Analysis ({self.template_var.get()})]\n"
            response += "This is a placeholder for LangChain processing.\n"
            response += f"Template: {template['name']}\n"
            response += f"Chunk length: {len(text)} characters\n\n"
            
            self.response_text.insert(tk.END, response)
            self.response_text.see(tk.END)
            
            # Update chunk color to show it's been processed
            chunk_ranges = self.transcript_text.tag_ranges("processing")
            if chunk_ranges:
                start, end = chunk_ranges[-2:]  # Get the last chunk's range
                self.transcript_text.tag_remove("processing", start, end)
                self.transcript_text.tag_add("processed", start, end)
                
                # Mark previous chunks as context
                if len(chunk_ranges) > 2:
                    for i in range(0, len(chunk_ranges)-2, 2):
                        self.transcript_text.tag_remove("processed", chunk_ranges[i], chunk_ranges[i+1])
                        self.transcript_text.tag_add("context", chunk_ranges[i], chunk_ranges[i+1])
            
            print(f"Processed chunk at {current_time}")  # Debug print
        except Exception as e:
            print(f"Error processing text chunk: {e}")  # Debug print
            
    def process_transcriptions(self):
        """Process incoming transcriptions with interval-based chunking"""
        self.last_process_time = time.time()
        self.accumulated_text = ""

        while self.recording and hasattr(self, 'assemblyai_session'):
            try:
                packet = self.assemblyai_session.get_next_transcription()
                if packet:
                    formatted_transcript = self.format_transcript(packet)
                    self.master.after(0, self.update_transcript_display, formatted_transcript)
                    
                    # Accumulate text
                    self.accumulated_text += formatted_transcript
                    
                    current_time = time.time()
                    interval = self.get_current_interval()
                    
                    # Process if interval has elapsed or we're in instant mode
                    if interval != float('inf'):
                        time_since_last = current_time - self.last_process_time
                        if time_since_last >= interval and self.accumulated_text.strip():
                            self.process_text_chunk(self.accumulated_text)
                            self.accumulated_text = ""
                            self.last_process_time = current_time
                    
                    # Update metadata
                    if packet.get('speaker') and packet['speaker'] not in self.metadata['speakers']:
                        self.metadata['speakers'].append(packet['speaker'])
                        
            except Exception as e:
                print(f"Transcription processing error: {e}")
                time.sleep(0.1)
                
    def format_transcript(self, packet):
        """Format transcript with timestamp and speaker"""
        # Use recording start time to calculate relative timestamp
        current_time = time.time() - self.start_time
        minutes = int(current_time // 60)
        seconds = int(current_time % 60)
        timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
            
        speaker = packet.get('speaker', 'Speaker 1')
        text = packet.get('text', '')
        
        return f"{timestamp_str} {speaker}: {text}\n"
        
    def update_transcript_display(self, text):
        """Update transcript display with new text"""
        # Just add the raw text without any coloring
        self.transcript_text.insert(tk.END, text)
        self.transcript_text.see(tk.END)
        
    def on_closing(self):
        """Handle window closing"""
        if self.recording:
            self.stop_recording()
        self.master.destroy()
