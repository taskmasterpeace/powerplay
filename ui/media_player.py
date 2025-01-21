import os
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import soundfile as sf
import sounddevice as sd
import numpy as np
import threading
import time
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor

import pygame
from pygame import mixer

class AudioPlayer:
    def __init__(self):
        pygame.init()
        mixer.init()
        self.current_sound = None
        self.paused_position = 0
        self.duration = 0

    def load(self, file_path):
        self.current_sound = mixer.Sound(file_path)
        self.duration = self.current_sound.get_length()

    def play(self):
        if self.current_sound:
            if self.paused_position > 0:
                self.current_sound.play(start=self.paused_position)
            else:
                self.current_sound.play()
            self.paused_position = 0

    def pause(self):
        if self.current_sound and self.is_playing():
            self.paused_position = self.get_position()
            self.current_sound.stop()

    def stop(self):
        if self.current_sound:
            self.current_sound.stop()
            self.paused_position = 0

    def seek(self, position):
        if self.current_sound:
            was_playing = self.is_playing()
            self.paused_position = position
            if was_playing:
                self.play()

    def get_position(self):
        if self.current_sound and self.is_playing():
            return self.current_sound.get_pos() / 1000  # Convert to seconds
        return self.paused_position

    def is_playing(self):
        return mixer.get_busy()

    def set_volume(self, volume):
        if self.current_sound:
            self.current_sound.set_volume(volume)

class MediaPlayerFrame(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Media Player")
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.chunk_size = 100000  # Adjust based on performance
        self.max_waveform_points = 1000  # Maximum points to display
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
        
        # Create matplotlib figure for waveform
        self.fig, self.ax = plt.subplots(figsize=(8, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.top_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add playhead line
        self.playhead_line = self.ax.axvline(x=0, color='red', linewidth=1)
        self.canvas.mpl_connect('button_press_event', self.on_waveform_click)
        
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
        self.playing = False
        self.paused = False
        self.duration = 0
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
        self.show_loading_progress()
        
        # Start async loading
        self.master.after(50, self.load_audio_async, file_path)
        
    def show_loading_progress(self):
        """Show loading progress in the waveform area"""
        # Clear previous plot
        self.ax.clear()
        self.ax.text(0.5, 0.5, 'Loading...', 
                    horizontalalignment='center',
                    verticalalignment='center')
        self.canvas.draw()
        
    def load_audio_async(self, file_path):
        """Load audio file asynchronously"""
        try:
            # Load waveform data in chunks
            audio_data = self.load_waveform(file_path)
            
            # Downsample for visualization
            display_data = self.prepare_waveform_data(audio_data)
            
            # Update waveform display
            self.plot_waveform(display_data)
            
            # Load audio for playback
            try:
                mixer.music.load(file_path)
                self.duration = mixer.Sound(file_path).get_length()
            except Exception as e:
                print(f"Error loading audio for playback: {e}")
                raise
            
            # Update UI
            self.filename_var.set(os.path.basename(file_path))
            self.position_slider.set(0)
            self.time_var.set(f"00:00 / {int(self.duration//60):02d}:{int(self.duration%60):02d}")
            
        except Exception as e:
            self.filename_var.set(f"Error loading file: {str(e)}")
            print(f"Error loading audio: {str(e)}")
            
    def load_waveform(self, file_path):
        """Load waveform in chunks with error handling"""
        try:
            chunks = []
            with sf.SoundFile(file_path) as f:
                self.sample_rate = f.samplerate
                while True:
                    data = f.read(self.chunk_size)
                    if len(data) == 0:
                        break
                    # Convert to mono if needed
                    if len(data.shape) > 1:
                        data = np.mean(data, axis=1)
                    # Check for invalid values
                    if np.any(np.isnan(data)) or np.any(np.isinf(data)):
                        data = np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0)
                    chunks.append(data)
            
            if not chunks:
                raise ValueError("No audio data loaded")
                
            self.audio_data = np.concatenate(chunks)
            # Final safety check on concatenated data
            if np.any(np.isnan(self.audio_data)) or np.any(np.isinf(self.audio_data)):
                self.audio_data = np.nan_to_num(self.audio_data, nan=0.0, posinf=1.0, neginf=-1.0)
            return self.audio_data
            
        except Exception as e:
            print(f"Error in load_waveform: {str(e)}")
            # Try alternate loading method using pygame
            try:
                sound = mixer.Sound(file_path)
                array_data = pygame.sndarray.array(sound)
                if len(array_data.shape) > 1:
                    array_data = np.mean(array_data, axis=1)
                self.audio_data = array_data.astype(np.float32) / 32767.0
                self.sample_rate = mixer.get_init()[0]
                return self.audio_data
            except Exception as e2:
                print(f"Fallback loading failed: {str(e2)}")
                raise ValueError(f"Could not load audio file: {str(e)} / {str(e2)}")
        
    def prepare_waveform_data(self, audio_data):
        """Downsample audio data for visualization with safety checks"""
        try:
            if audio_data is None or len(audio_data) == 0:
                print("Warning: Empty audio data")
                return np.zeros(self.max_waveform_points)

            # Convert to numpy array if not already and ensure float type
            audio_data = np.array(audio_data, dtype=np.float64)
            
            # Replace any invalid values
            audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # Early check for all-zero or very small data
            max_abs_val = np.max(np.abs(audio_data))
            if max_abs_val < 1e-10:  # Check if essentially zero
                print("Warning: Audio data is too quiet or empty")
                return np.zeros(self.max_waveform_points)

            # Normalize amplitude first since we know we have valid data
            audio_data = audio_data / max_abs_val
                
            if len(audio_data) > self.max_waveform_points:
                try:
                    # Calculate reduction factor
                    reduction = max(1, len(audio_data) // self.max_waveform_points)
                    
                    # Ensure we don't exceed array bounds
                    valid_length = (len(audio_data) // reduction) * reduction
                    audio_data = audio_data[:valid_length]
                    
                    # Reshape and take mean of chunks
                    audio_data = audio_data.reshape(-1, reduction)
                    audio_data = np.mean(audio_data, axis=1)
                except ValueError as e:
                    print(f"Reshape error: {e}, falling back to decimation")
                    # Fallback to simple decimation
                    audio_data = audio_data[::reduction]
                
            # Final safety checks
            audio_data = np.clip(audio_data, -1.0, 1.0)
            
            # Verify no invalid values remain
            if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
                print("Warning: Invalid values after processing, returning zeros")
                return np.zeros(len(audio_data))
                
            return audio_data
            
        except Exception as e:
            print(f"Error in prepare_waveform_data: {str(e)}")
            # Return simple sine wave as fallback
            t = np.linspace(0, 2*np.pi, self.max_waveform_points)
            return 0.5 * np.sin(t)
        
    def plot_waveform(self, audio_data):
        """Plot the waveform visualization"""
        self.ax.clear()
        
        time_axis = np.arange(len(audio_data)) / (len(audio_data) / self.duration)
        self.ax.plot(time_axis, audio_data, color='blue', alpha=0.5)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude')
        
        # Re-add playhead line
        self.playhead_line = self.ax.axvline(x=0, color='red', linewidth=1, zorder=10)
        
        # Adjust plot layout
        self.fig.tight_layout()
        
        # Update canvas
        self.canvas.draw()
            
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
            
        if self.audio_player.is_playing():
            self.audio_player.pause()
            self.play_button.configure(text="Play")
            if self.update_id:
                self.after_cancel(self.update_id)
        else:
            try:
                self.audio_player.play()
                self.play_button.configure(text="Pause")
                self.start_playback_updates()
            except Exception as e:
                print(f"Error playing audio: {e}")
                messagebox.showerror("Playback Error", str(e))
            
    def stop_audio(self):
        """Stop audio playback"""
        mixer.music.stop()
        self.playing = False
        self.paused = False
        self.play_button.configure(text="Play")
        self.current_position = 0
        self.position_slider.set(0)
        self.update_time_display()
        self.update_playhead()
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
            position = (float(value) / 100) * self.duration
            self.audio_player.seek(position)
            self.current_position = position
            self.update_playhead()
            
    def on_waveform_click(self, event):
        """Handle click on waveform"""
        if event.inaxes == self.ax and hasattr(self, 'audio_data'):
            # Convert x position to time
            click_time = event.xdata
            if click_time < 0:
                click_time = 0
            elif click_time > self.duration:
                click_time = self.duration
                
            # Update position and seek
            self.current_position = click_time
            self.seek_position(str((click_time / self.duration) * 100))
            
    def update_playhead(self):
        """Update playhead position during playback"""
        if self.playing and self.audio_data is not None:
            time_position = self.current_position / self.sample_rate
            self.playhead_line.set_xdata(time_position)
            self.canvas.draw_idle()
            self.update_playhead_id = self.after(50, self.update_playhead)
            
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
            if self.audio_player.is_playing():
                self.current_position = self.audio_player.get_position()
                if self.current_position >= self.duration:
                    self.stop_audio()
                else:
                    self.update_time_display()
                    self.update_playhead()
                    self.update_id = self.after(50, update)
            else:
                self.play_button.configure(text="Play")
        self.update_id = self.after(50, update)

    def update_time_display(self):
        """Update time labels and slider"""
        self.time_var.set(
            f"{int(self.current_position//60):02d}:{int(self.current_position%60):02d} / "
            f"{int(self.duration//60):02d}:{int(self.duration%60):02d}"
        )
        self.position_slider.set((self.current_position / self.duration) * 100)

    def update_playhead(self):
        """Update waveform playhead position"""
        self.playhead_line.set_xdata(self.current_position)
        self.canvas.draw_idle()
    
            
    def _on_playback_complete(self):
        """Handle playback completion"""
        self.playing = False
        self.play_button.configure(text="Play")
        if self.update_timer_id:
            self.after_cancel(self.update_timer_id)
            self.update_timer_id = None
            
    def destroy(self):
        """Cleanup resources before destroying widget"""
        if self.audio_player:
            self.audio_player.stop()
        if self.update_id:
            self.after_cancel(self.update_id)
        super().destroy()
