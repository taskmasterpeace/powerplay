import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import soundfile as sf
import sounddevice as sd
import numpy as np
import threading
import time
from queue import Queue, Empty

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
        self.audio_data = None
        self.sample_rate = None
        self.playing = False
        self.paused = False
        self.audio_player = AudioPlayer()
        self.after(100, self._check_audio_queue)
        self.current_position = 0
        self.stream = None
        self.play_thread = None
        self.update_playhead_id = None
        
    def load_audio(self, file_path):
        """Load audio file and display waveform"""
        # Update filename display
        self.filename_var.set(file_path.split('/')[-1].split('\\')[-1])
        try:
            # Load audio for waveform visualization
            audio_data, sample_rate = sf.read(file_path, dtype='float32')
            
            # Load audio for playback using pygame
            self.audio_player.load(file_path)
            
            # Clear previous plot
            self.ax.clear()
            
            # Plot waveform using mono for visualization only
            if len(audio_data.shape) > 1:
                audio_mono = np.mean(audio_data, axis=1)
            else:
                audio_mono = audio_data
                
            time_axis = np.arange(len(audio_mono)) / sample_rate
            self.ax.plot(time_axis, audio_mono, color='blue', alpha=0.5)
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Amplitude')
            
            # Re-add playhead line
            self.playhead_line = self.ax.axvline(x=0, color='red', linewidth=1, zorder=10)
            
            # Adjust plot layout
            self.fig.tight_layout()
            
            # Update canvas
            self.canvas.draw()
            
            # Reset controls
            self.position_slider.set(0)
            duration = self.audio_player.duration
            self.time_var.set(f"00:00 / {int(duration//60):02d}:{int(duration%60):02d}")
            
        except Exception as e:
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
        if not self.audio_player.current_sound:
            return
            
        if self.audio_player.is_playing():
            self.audio_player.pause()
            self.play_button.configure(text="Play")
        else:
            self.audio_player.play()
            self.play_button.configure(text="Pause")
            self.start_playback_updates()
            
    def stop_audio(self):
        """Stop audio playback"""
        self.audio_player.stop()
        self.play_button.configure(text="Play")
        self.position_slider.set(0)
        self.update_time_display(0)
        self.update_playhead(0)
        
    def seek_position(self, value):
        """Handle seeking in audio"""
        if self.audio_player.current_sound:
            position = float(value) * self.audio_player.duration / 100
            self.audio_player.seek(position)
            self.update_playhead(position)
            
    def on_waveform_click(self, event):
        """Handle click on waveform"""
        if event.inaxes == self.ax and self.audio_data is not None:
            # Convert x position to samples
            click_time = event.xdata
            self.current_position = int(click_time * self.sample_rate)
            # Update slider
            position_percent = (self.current_position / len(self.audio_data)) * 100
            self.position_slider.set(position_percent)
            # Update playhead
            self.playhead_line.set_xdata(click_time)
            self.canvas.draw_idle()
            
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
        
    def _start_playback(self):
        """Initialize and start audio playback"""
        try:
            def callback(outdata, frames, time, status):
                if status:
                    print("SoundDevice Callback Status:", status)
                
                if not self.playing:
                    raise sd.CallbackStop()
                
                # Calculate remaining frames
                remaining = len(self.audio_data) - self.current_position
                if remaining <= 0:
                    self.after(0, self._on_playback_complete)
                    raise sd.CallbackStop()
                
                # Get chunk of audio data
                chunk = self.audio_data[self.current_position:self.current_position + frames]
                frames_to_write = len(chunk)
                
                # Handle stereo vs mono correctly
                if len(chunk.shape) == 1:
                    chunk = chunk.reshape(-1, 1)
                
                outdata[:frames_to_write] = chunk
                if frames_to_write < len(outdata):
                    outdata[frames_to_write:] = 0
                
                # Update position
                self.current_position += frames_to_write
            
            # Clean up existing stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            # Create new stream with optimized settings
            channels = 2 if len(self.audio_data.shape) > 1 else 1
            self.stream = sd.OutputStream(
                channels=channels,
                samplerate=self.sample_rate,
                dtype='float32',
                callback=callback,
                blocksize=4096,  # Increased from 2048 to 4096
                latency='high'   # Changed from 'low' to 'high'
            )
            
            # Start playback
            self.stream.start()
            
        except Exception as e:
            print(f"Error starting playback: {str(e)}")
            self._on_playback_complete()
    def _update_playback_position(self):
        """Update slider and time display from the main thread"""
        if not self.playing:
            return
            
        # Update slider position
        position_percent = (self.current_position / len(self.audio_data)) * 100
        self.position_slider.set(position_percent)
        
        # Update time display
        current_time = self.current_position / self.sample_rate
        total_time = len(self.audio_data) / self.sample_rate
        self.time_var.set(
            f"{int(current_time//60):02d}:{int(current_time%60):02d} / "
            f"{int(total_time//60):02d}:{int(total_time%60):02d}"
        )
    def start_playback_updates(self):
        """Start periodic updates during playback"""
        def update():
            if self.audio_player.is_playing():
                current_pos = self.audio_player.get_position()
                self.update_time_display(current_pos)
                self.update_playhead(current_pos)
                self.update_id = self.after(50, update)
        self.update_id = self.after(50, update)

    def update_time_display(self, current_pos):
        """Update time display and slider position"""
        total_time = self.audio_player.duration
        self.time_var.set(
            f"{int(current_pos//60):02d}:{int(current_pos%60):02d} / "
            f"{int(total_time//60):02d}:{int(total_time%60):02d}"
        )
        self.position_slider.set((current_pos / total_time) * 100)

    def update_playhead(self, position):
        """Update playhead position in waveform"""
        self.playhead_line.set_xdata(position)
        self.canvas.draw_idle()
    
    def _update_position(self):
        """Update UI elements showing playback position"""
        if self.playing:
            # Update slider and time less frequently
            if (self.current_position % 2048) == 0:  # Only update every 2048 samples
                # Update slider
                position_percent = (self.current_position / len(self.audio_data)) * 100
                self.position_slider.set(position_percent)
                
                # Update time display
                current_time = self.current_position / self.sample_rate
                total_time = len(self.audio_data) / self.sample_rate
                self.time_var.set(
                    f"{int(current_time//60):02d}:{int(current_time%60):02d} / "
                    f"{int(total_time//60):02d}:{int(total_time%60):02d}"
                )
            
            # Update playhead even less frequently
            if (self.current_position % 8192) == 0:  # Only update every 8192 samples
                current_time = self.current_position / self.sample_rate
                self.playhead_line.set_xdata(current_time)
                self.canvas.draw_idle()
            
            # Schedule next update with longer interval
            self.update_timer_id = self.after(200, self._update_position)  # Increased from 150 to 200ms
            
    def _on_playback_complete(self):
        """Handle playback completion"""
        self.playing = False
        self.play_button.configure(text="Play")
        if self.update_timer_id:
            self.after_cancel(self.update_timer_id)
            self.update_timer_id = None
