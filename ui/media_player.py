import os
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

class AudioPlayer:
    def __init__(self):
        self.audio_segment = None
        self.playback = None
        self.start_time = 0
        self.paused_position = 0
        self.duration = 0
        self.playing = False
        self.lock = threading.Lock()
        self._last_position = 0
        self._volume = 1.0

    def load(self, file_path):
        """Load an audio file using pydub."""
        self.audio_segment = AudioSegment.from_file(file_path)
        self.duration = len(self.audio_segment) / 1000  # Convert to seconds

    def play(self):
        """Play or resume playback."""
        if not self.audio_segment:
            return False

        with self.lock:
            if self.playing and self.playback and self.playback.is_playing():
                return False
                
            try:
                # Ensure clean state
                if self.playback:
                    self._last_position = self.get_position()
                    self.playback.stop()
                    self.playback = None
                else:
                    self._last_position = self.paused_position

                # Calculate start position and create new playback
                start_ms = int(self._last_position * 1000)
                audio_to_play = self.audio_segment[start_ms:]
                
                # Apply current volume
                if self._volume != 1.0:
                    audio_to_play = audio_to_play.apply_gain(20 * np.log10(max(self._volume, 0.0001)))
                
                self.playback = _play_with_simpleaudio(audio_to_play)
                self.start_time = time.time() - self._last_position
                self.playing = bool(self.playback and self.playback.is_playing())
                return self.playing
            except Exception as e:
                print(f"Playback error: {e}")
                self.playing = False
                self.playback = None
                return False

    def pause(self):
        """Pause playback."""
        with self.lock:
            if not self.playing or not self.playback:
                return False
                
            try:
                self.paused_position = self.get_position()
                self.playback.stop()
                self.playback = None
                self.playing = False
                return True
            except Exception as e:
                print(f"Pause error: {e}")
                return False

    def stop(self):
        """Stop playback and reset position."""
        if self.playback:
            with self.lock:
                self.playback.stop()
                self.playback = None
                self.paused_position = 0
                self.playing = False

    def seek(self, position):
        """Seek to a specific position in seconds."""
        if self.audio_segment:
            with self.lock:
                was_playing = self.playing
                self.stop()
                self.paused_position = position
                if was_playing:
                    self.play()

    def get_position(self):
        """Get the current playback position in seconds."""
        if self.playing and self.playback:
            return time.time() - self.start_time
        return self.paused_position

    def is_playing(self):
        """Check if audio is currently playing."""
        return self.playing

    def set_volume(self, volume):
        """Set playback volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if self.playing:
            # Restart playback with new volume
            current_pos = self.get_position()
            self.stop()
            self.paused_position = current_pos
            self.play()

class MediaPlayerFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Media Player")
        self.audio_player = AudioPlayer()
        self.seek_update_time = 0
        
        # Filename display
        self.filename_var = tk.StringVar(value="No file loaded")
        self.filename_label = ttk.Label(self, textvariable=self.filename_var)
        self.filename_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Initialize playback variables
        self.update_timer_id = None
        self.stream = None
        self.play_thread = None

        # Create main container
        self.main_container = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top section - Waveform and controls
        self.top_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.top_frame, weight=1)
        
        # Playback controls
        self.controls_frame = ttk.Frame(self.top_frame)
        self.controls_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        self.play_button = ttk.Button(self.controls_frame, text="Play", command=self.play_audio)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(self.controls_frame, text="Stop", command=self.stop_audio)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Time slider
        self.time_var = tk.StringVar(value="00:00 / 00:00")
        self.time_label = ttk.Label(self.controls_frame, textvariable=self.time_var)
        self.time_label.pack(side=tk.RIGHT, padx=5)
        
        self.position_slider = ttk.Scale(self.controls_frame, from_=0, to=100, 
                                       orient=tk.HORIZONTAL, command=self.seek_position)
        self.position_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Bottom section - Transcript
        self.bottom_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.bottom_frame, weight=1)
        
        # Search frame
        self.search_frame = ttk.Frame(self.bottom_frame)
        self.search_frame.pack(fill=tk.X, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.search_button = ttk.Button(self.search_frame, text="Search", 
                                      command=self.search_transcript)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Transcript text
        self.transcript_text = tk.Text(self.bottom_frame, wrap=tk.WORD)
        self.transcript_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        self.scrollbar = ttk.Scrollbar(self.bottom_frame, orient=tk.VERTICAL, 
                                     command=self.transcript_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.transcript_text.configure(yscrollcommand=self.scrollbar.set)
        
        # Audio playback state
        self.audio_file = None
        self.current_position = 0
        self.update_id = None

        
    def setup_ui(self):
        """Initialize UI components"""
        # Add loading indicator
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(self, textvariable=self.progress_var)
        self.progress_label.pack()
        
        # Rest of your existing UI setup...
        
    def load_audio(self, file_path):
        """Entry point for loading audio"""
        self.audio_file = file_path
        self.filename_var.set("Loading...")
        
        # Start async loading
        self.master.after(50, self.load_audio_async, file_path)
        
    def load_audio_async(self, file_path):
        """Load audio file asynchronously"""
        try:
            self.audio_player.load(file_path)
            self.duration = self.audio_player.duration
            
            if self.duration <= 0:
                raise ValueError("Invalid audio duration")
                
            self.filename_var.set(os.path.basename(file_path))
            self.position_slider.set(0)
            self.time_var.set(f"00:00 / {int(self.duration//60):02d}:{int(self.duration%60):02d}")
            
        except Exception as e:
            self.filename_var.set(f"Error loading file: {str(e)}")
            print(f"Error loading audio: {str(e)}")
            
    def load_transcript(self, transcript_path):
        """Load transcript file"""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            self.transcript_text.delete('1.0', tk.END)
            self.transcript_text.insert('1.0', transcript_text)
        except Exception as e:
            print(f"Error loading transcript: {str(e)}")
            
    def play_audio(self):
        """Toggle play/pause audio playback"""
        if not self.audio_file:
            return

        try:
            if self.audio_player.is_playing():
                if self.audio_player.pause():
                    self.play_button.configure(text="Play")
                    self.cancel_updates()
            else:
                if self.audio_player.play():
                    self.play_button.configure(text="Pause")
                    self.start_playback_updates()
                else:
                    messagebox.showerror("Playback Error", "Failed to start playback")
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))
            

            
    def stop_audio(self):
        """Stop audio playback"""
        self.audio_player.stop()
        self.play_button.configure(text="Play")
        self.current_position = 0
        self.position_slider.set(0)
        self.update_time_display()
        if self.update_id:
            self.after_cancel(self.update_id)
        
    def _throttled_seek(self, value):
        """Throttle seek operations to prevent overload"""
        now = time.time()
        if now - self.seek_update_time > 0.1:  # 100ms throttle
            self.seek_position(value)
            self.seek_update_time = now
            
    def seek_position(self, value):
        """Handle seeking in audio"""
        if self.audio_file:
            now = time.time()
            if now - self.seek_update_time > 0.1:  # 100ms throttle
                position = (float(value) / 100) * self.audio_player.duration
                self.audio_player.seek(position)
                self.current_position = position
                self.seek_update_time = now
            
            
    def search_transcript(self):
        """Search within transcript"""
        search_term = self.search_var.get()
        if not search_term:
            return
            
        # Remove previous search tags
        self.transcript_text.tag_remove('search', '1.0', tk.END)
        
        # Search and highlight matches
        start_pos = '1.0'
        while True:
            start_pos = self.transcript_text.search(search_term, start_pos, tk.END)
            if not start_pos:
                break
                
            end_pos = f"{start_pos}+{len(search_term)}c"
            self.transcript_text.tag_add('search', start_pos, end_pos)
            start_pos = end_pos
            
        self.transcript_text.tag_config('search', background='yellow')
        
    def start_playback_updates(self):
        """Start updating playback position"""
        def update():
            try:
                if self.audio_player.is_playing():
                    self.current_position = self.audio_player.get_position()
                    if self.current_position >= self.audio_player.duration:
                        self.after_idle(self.stop_audio)
                    else:
                        self.update_time_display()
                        progress = (self.current_position / self.audio_player.duration) * 100
                        self.position_slider.set(progress)
                        self.update_id = self.after(50, update)
                else:
                    self.play_button.configure(text="Play")
                    self.cancel_updates()
            except Exception as e:
                print(f"Update error: {e}")
                self.cancel_updates()
                
        self.cancel_updates()
        self.update_id = self.after(50, update)

    def update_time_display(self):
        """Update time labels and slider"""
        if self.duration <= 0:
            self.time_var.set("00:00 / 00:00")
            self.position_slider.set(0)
            return
        
        current_time = f"{int(self.current_position//60):02d}:{int(self.current_position%60):02d}"
        total_time = f"{int(self.duration//60):02d}:{int(self.duration%60):02d}"
        self.time_var.set(f"{current_time} / {total_time}")
        self.position_slider.set((self.current_position / self.duration) * 100)

            
    def _on_playback_complete(self):
        """Handle playback completion"""
        self.playing = False
        self.play_button.configure(text="Play")
        if self.update_timer_id:
            self.after_cancel(self.update_timer_id)
            self.update_timer_id = None
            
    def cancel_updates(self):
        """Cancel any pending updates"""
        if self.update_id:
            self.after_cancel(self.update_id)
            self.update_id = None

    def destroy(self):
        """Cleanup resources before destroying widget"""
        if self.audio_player:
            self.audio_player.stop()
        if self.update_id:
            self.after_cancel(self.update_id)
        super().destroy()
