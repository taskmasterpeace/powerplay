import os
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto

class PlaybackState(Enum):
    """Enum representing possible playback states"""
    IDLE = auto()      # No audio loaded
    LOADED = auto()    # Audio loaded but not playing
    PLAYING = auto()   # Audio is currently playing
    PAUSED = auto()    # Audio is paused
    ERROR = auto()     # Error state

class AudioPlayer:
    """Handles audio playback with proper resource management"""
    
    def __init__(self):
        self.audio_segment = None
        self.playback = None
        self.duration = 0
        self._volume = 1.0
        self._position = 0
        self._lock = threading.Lock()
        self._state = PlaybackState.IDLE
        self._error_message = ""
        self._playback_start_time = 0
        self._playback_start_position = 0

    def load(self, file_path):
        """Load an audio file using pydub."""
        try:
            self.audio_segment = AudioSegment.from_file(file_path)
            self.duration = len(self.audio_segment) / 1000  # Convert to seconds
            self._state = PlaybackState.LOADED
            self._error_message = ""
        except Exception as e:
            self._state = PlaybackState.ERROR
            self._error_message = str(e)
            raise

    def play(self):
        """Play or resume playback with proper resource management"""
        if self._state == PlaybackState.IDLE or not self.audio_segment:
            return False

        with self._lock:
            if self._state == PlaybackState.PLAYING:
                return False
                
            try:
                # Clean up any existing playback
                self._cleanup_playback()
                
                # Calculate remaining audio
                start_ms = int(self._position * 1000)
                if start_ms >= len(self.audio_segment):
                    return False
                    
                # Prepare audio segment
                audio_to_play = self.audio_segment[start_ms:]
                if self._volume != 1.0:
                    audio_to_play = audio_to_play.apply_gain(20 * np.log10(max(self._volume, 0.0001)))
                
                # Start playback
                self.playback = _play_with_simpleaudio(audio_to_play)
                if not self.playback:
                    return False
                
                # Record start time and position
                self._playback_start_time = time.time()
                self._playback_start_position = self._position
                self._state = PlaybackState.PLAYING
                return True
                
            except Exception as e:
                print(f"Playback error: {e}")
                self._cleanup_playback()
                return False

    def pause(self):
        """Pause playback with proper cleanup"""
        with self._lock:
            if self._state != PlaybackState.PLAYING:
                return False
                
            try:
                self._position = self.get_position()
                self._cleanup_playback()
                return True
            except Exception as e:
                print(f"Pause error: {e}")
                self._cleanup_playback()
                return False

    def stop(self):
        """Stop playback and reset state"""
        with self._lock:
            self._cleanup_playback()
            self._position = 0

    def seek(self, position):
        """Seek to a specific position in seconds."""
        if not self.audio_segment:
            return False
            
        with self._lock:
            try:
                was_playing = self._state == PlaybackState.PLAYING
                self._cleanup_playback()
                self._position = max(0, min(position, self.duration))
                if was_playing:
                    return self.play()
                return True
            except Exception as e:
                print(f"Seek error: {e}")
                return False

    def _cleanup_playback(self):
        """Clean up playback resources"""
        if self.playback:
            try:
                self.playback.stop()
            except Exception as e:
                print(f"Cleanup error: {e}")
                self._state = PlaybackState.ERROR
                self._error_message = str(e)
            finally:
                self.playback = None
                if self._state != PlaybackState.ERROR:
                    self._state = PlaybackState.PAUSED if self._position > 0 else PlaybackState.LOADED
    
    def get_position(self):
        """Get current playback position in seconds"""
        if self._state != PlaybackState.PLAYING:
            return self._position
            
        try:
            if self.playback and self.playback.is_playing():
                # Calculate position based on elapsed time
                elapsed = time.time() - self._playback_start_time
                current_pos = self._playback_start_position + elapsed
                
                # Ensure we don't exceed duration
                return min(current_pos, self.duration)
                
            # If playback stopped, update stored position
            self._position = min(self._position, self.duration)
            return self._position
            
        except Exception as e:
            print(f"Position error: {e}")
            return self._position

    def is_playing(self):
        """Check if audio is currently playing."""
        return self._state == PlaybackState.PLAYING

    def get_state(self):
        """Get current playback state."""
        return self._state

    def get_error(self):
        """Get last error message if in error state."""
        return self._error_message if self._state == PlaybackState.ERROR else ""

    def set_volume(self, volume):
        """Set playback volume (0.0 to 1.0)."""
        with self._lock:
            try:
                self._volume = max(0.0, min(1.0, volume))
                if self._state == PlaybackState.PLAYING:
                    current_pos = self.get_position()
                    self._cleanup_playback()
                    self._position = current_pos
                    return self.play()
                return True
            except Exception as e:
                print(f"Volume error: {e}")
                return False

class MediaPlayerFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Media Player")
        self.audio_player = AudioPlayer()
        self.seek_update_time = 0
        self.duration = 0  # Initialize duration
        
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
        
        # Volume control
        self.volume_frame = ttk.Frame(self.controls_frame)
        self.volume_frame.pack(side=tk.RIGHT, padx=5)
        
        self.volume_label = ttk.Label(self.volume_frame, text="Volume:")
        self.volume_label.pack(side=tk.LEFT)
        
        self.volume_slider = ttk.Scale(self.volume_frame, from_=0, to=100,
                                     orient=tk.HORIZONTAL, length=100,
                                     command=self.set_volume)
        self.volume_slider.set(100)
        self.volume_slider.pack(side=tk.LEFT, padx=5)
        
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
        if not file_path or not os.path.exists(file_path):
            self.filename_var.set("Invalid file path")
            return
            
        try:
            # Stop any current playback
            self.stop_audio()
            
            # Reset state
            self.audio_file = file_path
            self.filename_var.set("Loading...")
            self.position_slider.set(0)
            self.time_var.set("00:00 / 00:00")
            
            # Start async loading
            self.master.after(50, self.load_audio_async, file_path)
            
        except Exception as e:
            self.filename_var.set(f"Error: {str(e)}")
            self.audio_file = None
        
    def load_audio_async(self, file_path):
        """Load audio file asynchronously"""
        try:
            # Validate file type
            ext = os.path.splitext(file_path)[1].lower()
            supported_types = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.wma'}
            if ext not in supported_types:
                raise ValueError(f"Unsupported file type. Supported: {', '.join(supported_types)}")
            
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
            self.audio_file = None
            self.duration = 0
            
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
        if not self.audio_file:
            return
            
        self.audio_player.stop()
        self.play_button.configure(text="Play")
        self.position_slider.set(0)
        self.update_time_display()
        self.cancel_updates()
        
    def seek_position(self, value):
        """Handle seeking in audio"""
        if not self.audio_file:
            return
            
        now = time.time()
        if now - self.seek_update_time > 0.1:  # 100ms throttle
            try:
                position = (float(value) / 100) * self.audio_player.duration
                if self.audio_player.seek(position):
                    self.update_time_display()
                self.seek_update_time = now
            except Exception as e:
                print(f"Seek error: {e}")
            
            
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
            if not self.audio_player:
                return
                
            try:
                if self.audio_player.is_playing():
                    position = self.audio_player.get_position()
                    if position >= self.audio_player.duration:
                        self.master.after_idle(self._on_playback_complete)
                        return
                    self.update_time_display()
                    progress = (position / self.audio_player.duration) * 100
                    self.position_slider.set(progress)
                    self.update_id = self.master.after(50, update)
                else:
                    self._on_playback_complete()
            except Exception as e:
                print(f"Update error: {e}")
                self._on_playback_complete()
                
        self.cancel_updates()
        self.update_id = self.master.after(50, update)

    def update_time_display(self):
        """Update time labels and slider"""
        if self.duration <= 0:
            self.time_var.set("00:00 / 00:00")
            self.position_slider.set(0)
            return
        
        position = self.audio_player.get_position()
        current_time = f"{int(position//60):02d}:{int(position%60):02d}"
        total_time = f"{int(self.duration//60):02d}:{int(self.duration%60):02d}"
        self.time_var.set(f"{current_time} / {total_time}")
        self.position_slider.set((position / self.duration) * 100)

            
    def _on_playback_complete(self):
        """Handle playback completion"""
        self.audio_player._cleanup_playback()
        self.play_button.configure(text="Play")
        self.cancel_updates()
            
    def cancel_updates(self):
        """Cancel any pending updates"""
        if self.update_id:
            self.after_cancel(self.update_id)
            self.update_id = None

    def set_volume(self, value):
        """Set audio volume"""
        if self.audio_player:
            volume = float(value) / 100.0
            self.audio_player.set_volume(volume)
            
    def destroy(self):
        """Cleanup resources before destroying widget"""
        try:
            # Cancel all pending updates
            self.cancel_updates()
            
            # Stop audio playback
            if self.audio_player:
                self.audio_player.stop()
                self.audio_player = None
            
            # Clear text widgets
            if hasattr(self, 'transcript_text'):
                self.transcript_text.delete('1.0', tk.END)
            
            # Reset variables
            self.duration = 0
            self.audio_file = None
            
            # Clear any remaining state
            if hasattr(self, 'filename_var'):
                self.filename_var.set("No file loaded")
            if hasattr(self, 'time_var'):
                self.time_var.set("00:00 / 00:00")
            if hasattr(self, 'position_slider'):
                self.position_slider.set(0)
            
        except Exception as e:
            print(f"Cleanup error during destroy: {e}")
        finally:
            super().destroy()
