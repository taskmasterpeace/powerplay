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

import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AudioPlayer:
    """Handles audio playback with proper resource management"""
    
    def __init__(self):
        self.logger = logging.getLogger('AudioPlayer')
        self.audio_segment = None
        self.playback = None
        self.duration = 0
        self._volume = 1.0
        self._position = 0
        self._playback_lock = threading.RLock()  # Reentrant lock for playback operations
        self._state_lock = threading.Lock()      # Separate lock for state changes
        self._state = PlaybackState.IDLE
        self._error_message = ""
        self._playback_start_time = 0
        self._playback_start_position = 0

    def load(self, file_path):
        """Load an audio file using pydub."""
        self.logger.info(f"Loading audio file: {file_path}")
        try:
            self.audio_segment = AudioSegment.from_file(file_path)
            self.duration = len(self.audio_segment) / 1000  # Convert to seconds
            self._state = PlaybackState.LOADED
            self._error_message = ""
            self.logger.info(f"Successfully loaded audio file. Duration: {self.duration}s")
        except Exception as e:
            self._state = PlaybackState.ERROR
            self._error_message = str(e)
            self.logger.error(f"Failed to load audio file: {str(e)}", exc_info=True)
            raise

    def play(self):
        """Play or resume playback with proper resource management"""
        self.logger.debug(f"Play requested. Current state: {self._state}")
        
        with self._state_lock:
            if self._state == PlaybackState.IDLE or not self.audio_segment:
                self.logger.warning("Cannot play: No audio loaded or player idle")
                return False
                
            if self._state == PlaybackState.PLAYING:
                self.logger.debug("Already playing, ignoring play request")
                return True  # Already playing is not an error
                
            if self._state not in [PlaybackState.LOADED, PlaybackState.PAUSED]:
                self.logger.error(f"Invalid state for playback: {self._state}")
                return False
                
            try:
                with self._playback_lock:
                    # Calculate remaining audio
                    start_ms = int(self._position * 1000)
                    if start_ms >= len(self.audio_segment):
                        self.logger.debug("At end of audio, cannot play")
                        return False
                        
                    # Prepare audio segment
                    audio_to_play = self.audio_segment[start_ms:]
                    if self._volume != 1.0:
                        audio_to_play = audio_to_play.apply_gain(20 * np.log10(max(self._volume, 0.0001)))
                    
                    # Create playback object
                    new_playback = _play_with_simpleaudio(audio_to_play)
                    if not new_playback or not new_playback.is_playing():
                        self.logger.error("Failed to create playing playback object")
                        return False
                        
                    # Only after successful playback creation, update state and references
                    self.playback = new_playback
                    self._playback_start_time = time.time()
                    self._playback_start_position = self._position
                    self._state = PlaybackState.PLAYING
                    
                    # Verify playback is still active
                    if not self.playback.is_playing():
                        self.logger.error("Playback stopped immediately after starting")
                        self._cleanup_playback()
                        return False
                        
                    self.logger.debug(f"Playback successfully started, state: {self._state}")
                    return True
                
            except Exception as e:
                print(f"Playback error: {e}")
                self._cleanup_playback()
                return False

    def pause(self):
        """Pause playback with proper cleanup"""
        with self._state_lock:
            if self._state != PlaybackState.PLAYING:
                return False
            
            try:
                with self._playback_lock:
                    self._position = self.get_position()
                    self._cleanup_playback()
                    return True
            except Exception as e:
                self.logger.error(f"Pause error: {e}")
                self._cleanup_playback()
                return False

    def stop(self):
        """Stop playback and reset state"""
        with self._state_lock:
            with self._playback_lock:
                self._cleanup_playback()
                self._position = 0

    def seek(self, position):
        """Seek to a specific position in seconds."""
        if not self.audio_segment:
            return False
            
        with self._state_lock:
            try:
                # Validate position
                new_position = max(0, min(position, self.duration))
                if abs(new_position - self._position) < 0.1:  # Avoid tiny seeks
                    return True
                    
                # Store playback state
                was_playing = self._state == PlaybackState.PLAYING
                
                with self._playback_lock:
                    # Update position and cleanup
                    self._cleanup_playback()
                    self._position = new_position
                    self._playback_start_position = new_position
                    self._playback_start_time = time.time()
                    
                    # Resume if was playing
                    if was_playing:
                        return self.play()
                    
                    self._state = PlaybackState.PAUSED
                    return True
                    
            except Exception as e:
                self.logger.error(f"Seek error: {e}")
                self._state = PlaybackState.ERROR
                self._error_message = str(e)
                return False

    def _cleanup_playback(self, preserve_state=False):
        """Clean up playback resources"""
        with self._playback_lock:
            current_state = self._state
            self.logger.debug(f"Cleanup starting. Current state: {current_state}, preserve_state: {preserve_state}")
            
            if self.playback:
                try:
                    self.playback.stop()
                    self.playback = None
                    self.logger.debug("Playback stopped and cleared")
                except Exception as e:
                    self.logger.error(f"Cleanup error: {e}")
                    self._state = PlaybackState.ERROR
                    self._error_message = str(e)
                    return
            
            # Only change state if we're not preserving it and not in error
            if not preserve_state:
                if self._state == PlaybackState.PLAYING:
                    new_state = PlaybackState.PAUSED
                elif self._state == PlaybackState.ERROR:
                    return  # Keep error state
                else:
                    new_state = PlaybackState.PAUSED if self._position > 0 else PlaybackState.LOADED
                self.logger.debug(f"Setting new state to: {new_state}")
                self._state = new_state
            else:
                self.logger.debug(f"Preserving state as: {current_state}")
                self._state = current_state
    
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
        with self._state_lock:
            try:
                self._volume = max(0.0, min(1.0, volume))
                if self._state == PlaybackState.PLAYING:
                    with self._playback_lock:
                        current_pos = self.get_position()
                        self._cleanup_playback()
                        self._position = current_pos
                        return self.play()
                return True
            except Exception as e:
                self.logger.error(f"Volume error: {e}")
                return False

class MediaPlayerFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Media Player")
        self.logger = logging.getLogger('MediaPlayerFrame')
        self.audio_player = AudioPlayer()
        self.seek_update_time = 0
        self.duration = 0  # Initialize duration
        self.auto_play = tk.BooleanVar(value=False)  # Add auto-play option
        
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
        
        # Add drag tracking to slider
        self.position_slider.bind('<Button-1>', lambda e: setattr(self.position_slider, '_dragging', True))
        self.position_slider.bind('<ButtonRelease-1>', lambda e: setattr(self.position_slider, '_dragging', False))
        
        # Playback options frame
        self.options_frame = ttk.Frame(self.controls_frame)
        self.options_frame.pack(side=tk.RIGHT, padx=5)
        
        # Auto-play checkbox
        self.auto_play_check = ttk.Checkbutton(
            self.options_frame, 
            text="Auto-play next",
            variable=self.auto_play
        )
        self.auto_play_check.pack(side=tk.LEFT, padx=5)
        
        # Volume control
        self.volume_frame = ttk.Frame(self.options_frame)
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
        self.logger.info("Play audio requested")
        if not self.audio_player:
            self.logger.error("No audio player initialized")
            messagebox.showerror("Error", "No audio player initialized")
            return
            
        try:
            current_state = self.audio_player.get_state()
            self.logger.debug(f"Current player state: {current_state}")
            
            if current_state == PlaybackState.PLAYING:
                # Handle pause
                self.logger.info("Pausing playback")
                if self.audio_player.pause():
                    self.play_button.configure(text="Play")
                    self.cancel_updates()
                    self.logger.info("Playback paused successfully")
                return
                
            # Handle play
            self.logger.info("Starting playback")
            if self.audio_player.play():
                # Verify state changed
                if self.audio_player.get_state() == PlaybackState.PLAYING:
                    self.play_button.configure(text="Pause")
                    self.start_playback_updates()
                    self.logger.info("Playback started successfully")
                else:
                    raise RuntimeError("Failed to enter playing state")
            else:
                raise RuntimeError("Failed to start playback")
                
        except Exception as e:
            self.logger.error(f"Playback error: {str(e)}", exc_info=True)
            self.audio_player._cleanup_playback()
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
                self.seek_update_time = now
                self.audio_player.seek(position)
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
                        # Check for auto-play
                        if self.auto_play.get():
                            self.master.after(1000, self.play_next)  # Wait 1s before next
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
        
        # Only update slider if not being dragged
        if not hasattr(self.position_slider, '_dragging'):
            self.position_slider.set((position / self.duration) * 100)

            
    def _on_playback_complete(self):
        """Handle playback completion"""
        # Reset playback state
        self.audio_player._cleanup_playback()
        self.play_button.configure(text="Play")
        self.cancel_updates()
        
        # Reset position to start
        self.position_slider.set(0)
        self.audio_player._position = 0
        self.update_time_display()
        
        # Emit completion event
        self.event_generate('<<PlaybackComplete>>')
            
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
            
    def play_next(self):
        """Play the next file in the playlist if available"""
        # Generate event for parent to handle
        self.event_generate('<<RequestNextFile>>')
        
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
