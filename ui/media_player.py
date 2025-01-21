import os
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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

    def load(self, file_path):
        """Load an audio file using pydub."""
        self.audio_segment = AudioSegment.from_file(file_path)
        self.duration = len(self.audio_segment) / 1000  # Convert to seconds

    def play(self):
        """Play or resume playback."""
        if self.audio_segment:
            with self.lock:
                if self.playback and not self.playback.is_playing():
                    self.playback = None
                if not self.playback:
                    start_ms = int(self.paused_position * 1000)
                    audio_to_play = self.audio_segment[start_ms:]
                    self.playback = _play_with_simpleaudio(audio_to_play)
                    self.start_time = time.time() - self.paused_position
                    self.playing = True

    def pause(self):
        """Pause playback."""
        if self.playback and self.playback.is_playing():
            with self.lock:
                self.playback.stop()
                self.paused_position = self.get_position()
                self.playing = False

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
        if self.audio_segment:
            self.audio_segment = self.audio_segment.apply_gain(20 * np.log10(max(volume, 0.0001)))

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
            # Load audio for playback first
            self.audio_player.load(file_path)
            self.duration = self.audio_player.duration
            
            # Validate duration
            if self.duration <= 0:
                raise ValueError("Invalid audio duration (<= 0 seconds)")
                
            # Load waveform data
            audio_data = self.load_waveform(file_path)
            display_data = self.prepare_waveform_data(audio_data)
            self.plot_waveform(display_data)
            
            # Update UI
            self.filename_var.set(os.path.basename(file_path))
            self.position_slider.set(0)
            self.time_var.set(f"00:00 / {int(self.duration//60):02d}:{int(self.duration%60):02d}")
            
        except Exception as e:
            self.filename_var.set(f"Error loading file: {str(e)}")
            print(f"Error loading audio: {str(e)}")
            
    def load_waveform(self, file_path):
        """Load waveform data from audio file"""
        try:
            audio_segment = AudioSegment.from_file(file_path)
            
            # Validate audio content
            if len(audio_segment) == 0:
                raise ValueError("Empty audio file")
                
            samples = np.array(audio_segment.get_array_of_samples())
            
            # Convert to mono if stereo
            if audio_segment.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize to float between -1 and 1
            samples = samples / (1 << (8 * audio_segment.sample_width - 1))
            
            self.audio_data = samples
            self.sample_rate = audio_segment.frame_rate
            return self.audio_data
            
        except Exception as e:
            print(f"Error loading audio file: {str(e)}")
            raise ValueError(f"Could not load audio file: {str(e)}")
        
    def prepare_waveform_data(self, audio_data):
        """Downsample audio data for visualization with safety checks"""
        try:
            if audio_data is None or len(audio_data) == 0:
                return np.zeros(self.max_waveform_points)

            # Convert to numpy array and ensure float type
            audio_data = np.array(audio_data, dtype=np.float32)
            audio_data = np.nan_to_num(audio_data, nan=0.0)
            
            # Check for valid data
            max_abs_val = np.max(np.abs(audio_data))
            if max_abs_val < 1e-10:
                return np.zeros(self.max_waveform_points)

            # Efficient downsampling using block reduction
            if len(audio_data) > self.max_waveform_points:
                block_size = len(audio_data) // self.max_waveform_points
                audio_data = audio_data[:block_size * self.max_waveform_points]
                audio_data = audio_data.reshape(-1, block_size)
                audio_data = np.max(np.abs(audio_data), axis=1)
                
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
        
        # Handle invalid duration
        if self.duration <= 0 or len(audio_data) == 0:
            self.ax.text(0.5, 0.5, 'Invalid audio file', 
                        horizontalalignment='center',
                        verticalalignment='center')
            self.canvas.draw()
            return
        
        time_axis = np.linspace(0, self.duration, len(audio_data))  # Safer calculation
        self.ax.plot(time_axis, audio_data, color='blue', alpha=0.5)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude')
        
        self.playhead_line = self.ax.axvline(x=0, color='red', linewidth=1, zorder=10)
        self.fig.tight_layout()
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
                # Start playback in a separate thread
                threading.Thread(target=self._play_audio_thread, daemon=True).start()
            except Exception as e:
                print(f"Error playing audio: {e}")
                messagebox.showerror("Playback Error", str(e))

    def _play_audio_thread(self):
        """Handle audio playback in a separate thread"""
        self.audio_player.play()
        self.after(0, lambda: self.play_button.configure(text="Pause"))
        self.after(0, self.start_playback_updates)
            
    def stop_audio(self):
        """Stop audio playback"""
        self.audio_player.stop()
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
                    self.update_id = self.after(100, update)  # Reduced update frequency
            else:
                self.play_button.configure(text="Play")
        self.update_id = self.after(100, update)  # Start with reduced frequency

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
