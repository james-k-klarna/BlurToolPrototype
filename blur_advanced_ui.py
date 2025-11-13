#!/usr/bin/env python3
"""
Advanced Blur UI - Professional interface with enhanced blur controls
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import json
import os
from blur_engine_advanced import BlurEngine, BlurRegion, BlurType, PIIType

class AdvancedBlurUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PII Blur Tool - Professional")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)  # Set minimum window size
        
        # Professional color scheme
        self.colors = {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'accent': '#4a90e2',
            'accent_hover': '#5ba0f2',
            'panel': '#363636',
            'button': '#4a90e2',
            'button_hover': '#5ba0f2',
            'success': '#5cb85c',
            'danger': '#d9534f',
            'warning': '#f0ad4e',
            'text_secondary': '#b0b0b0'
        }
        
        # Configure root style
        self.root.configure(bg=self.colors['bg'])
        
        # Initialize blur engine
        self.blur_engine = BlurEngine()
        
        # Video data
        self.video_path = None
        self.cap = None
        self.video_info = {}
        
        # Current state
        self.current_frame = 0
        self.current_second = 0
        self.regions = []
        self.drawing = False
        self.start_point = None
        self.pending_rectangle = None
        
        # UI variables - Default to 90% for gaussian blur
        self.opacity_var = tk.IntVar(value=90)  # Default 90%
        self.blur_type_var = tk.StringVar(value="gaussian")
        self.duration_var = tk.IntVar(value=1)
        self.start_second_var = tk.StringVar(value="")
        self.end_second_var = tk.StringVar(value="")
        
        # For draggable divider - start at 1/3 of screen
        self.divider_width = 0  # Will be calculated as 1/3 of window
        self.divider_dragging = False
        
        # Hold state for rectangle locking
        self.rectangle_held = False
        self.held_rectangle = None
        
        self.setup_ui()
        
    def create_button(self, parent, text, command, bg=None, fg=None, width=None, font=None):
        """Create a styled button"""
        if bg is None:
            bg = self.colors['button']
        
        # Determine text color: black for gray/light backgrounds, white for dark/colored backgrounds
        if fg is None:
            # Check if background is gray or light colored - use black bold text
            if bg in [self.colors['panel'], '#363636', '#4a4a4a'] or bg == self.colors['bg']:
                fg = '#000000'  # Black text for gray/light backgrounds
                font = ("Helvetica", 10, "bold")  # Ensure bold for gray buttons
            else:
                fg = self.colors['fg']  # White for dark/colored backgrounds
                if font is None:
                    font = ("Helvetica", 10, "bold")
        else:
            if font is None:
                font = ("Helvetica", 10, "bold")
        
        # Determine active background
        if bg in [self.colors['panel'], '#363636', '#4a4a4a']:
            active_bg = '#4a4a4a'
        else:
            active_bg = self.colors['button_hover']
        
        btn = tk.Button(
            parent, 
            text=text, 
            command=command,
            bg=bg,
            fg=fg,
            font=font,
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground=active_bg,
            activeforeground=fg
        )
        if width:
            btn.config(width=width)
        return btn
    
    def create_label_frame(self, parent, text):
        """Create a styled label frame"""
        frame = tk.LabelFrame(
            parent,
            text=text,
            font=("Helvetica", 11, "bold"),
            bg=self.colors['panel'],
            fg=self.colors['fg'],
            relief="flat",
            padx=10,
            pady=10
        )
        return frame
    
    def setup_ui(self):
        """Setup the professional user interface"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = tk.Frame(main_container, bg=self.colors['bg'])
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_label = tk.Label(
            header_frame,
            text="PII Blur Tool",
            font=("Helvetica", 24, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['fg']
        )
        title_label.pack(side="left")
        
        # File controls in header
        file_controls = tk.Frame(header_frame, bg=self.colors['bg'])
        file_controls.pack(side="right", padx=10)
        
        self.create_button(
            file_controls,
            "📁 Load Video",
            self.load_video,
            bg=self.colors['panel'],
            width=15
        ).pack(side="left", padx=5)
        
        self.create_button(
            file_controls,
            "🗑️ Remove Video",
            self.remove_video,
            bg=self.colors['panel'],
            width=15
        ).pack(side="left", padx=5)
        
        self.file_label = tk.Label(
            file_controls,
            text="No video loaded",
            font=("Helvetica", 10),
            bg=self.colors['bg'],
            fg=self.colors['text_secondary']
        )
        self.file_label.pack(side="left", padx=10)
        
        # Main content area with draggable divider
        self.content_paned = tk.PanedWindow(
            main_container,
            orient="horizontal",
            bg=self.colors['bg'],
            sashwidth=8,
            sashrelief="flat",
            sashpad=2
        )
        self.content_paned.pack(fill="both", expand=True)
        
        # Calculate slightly more than 1/3 of window width for left panel (use default, will update after window renders)
        # Default window width is 1400, so ~38% is ~532 (more than 1/3 to fit better)
        left_panel_width = 532
        
        # Left panel - Controls (starts at 1/3 of screen)
        left_panel = tk.Frame(self.content_paned, bg=self.colors['bg'], width=left_panel_width)
        left_panel.pack_propagate(False)
        self.content_paned.add(left_panel, minsize=300, width=left_panel_width)
        
        # Update panel size after window is rendered
        self.root.after(100, self.update_panel_size)
        
        # Create scrollable controls
        controls_canvas = tk.Canvas(
            left_panel,
            bg=self.colors['panel'],
            highlightthickness=0,
            width=380
        )
        controls_scrollbar = tk.Scrollbar(
            left_panel,
            orient="vertical",
            command=controls_canvas.yview,
            bg=self.colors['panel']
        )
        controls_frame = tk.Frame(controls_canvas, bg=self.colors['panel'])
        
        controls_frame.bind(
            "<Configure>",
            lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all"))
        )
        
        controls_canvas.create_window((0, 0), window=controls_frame, anchor="nw")
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)
        
        controls_canvas.pack(side="left", fill="both", expand=True)
        controls_scrollbar.pack(side="right", fill="y")
        
        # Frame Navigation Section
        nav_frame = self.create_label_frame(controls_frame, "Frame Navigation")
        nav_frame.pack(fill="x", padx=10, pady=10)
        
        time_display = tk.Frame(nav_frame, bg=self.colors['panel'])
        time_display.pack(fill="x", padx=5, pady=5)
        
        tk.Label(
            time_display,
            text="Current Time:",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['text_secondary']
        ).pack(side="left")
        
        self.current_second_label = tk.Label(
            time_display,
            text="0s",
            font=("Helvetica", 16, "bold"),
            bg=self.colors['panel'],
            fg=self.colors['accent']
        )
        self.current_second_label.pack(side="right")
        
        self.frame_scale = tk.Scale(
            nav_frame,
            from_=0,
            to=1,
            orient="horizontal",
            command=self.on_frame_change,
            bg=self.colors['panel'],
            fg=self.colors['fg'],
            troughcolor=self.colors['bg'],
            activebackground=self.colors['accent'],
            font=("Helvetica", 9)
        )
        self.frame_scale.pack(fill="x", padx=5, pady=5)
        
        # Navigation buttons
        nav_buttons = tk.Frame(nav_frame, bg=self.colors['panel'])
        nav_buttons.pack(fill="x", padx=5, pady=5)
        
        # Gray buttons with black bold text
        self.create_button(nav_buttons, "⏮", self.first_frame, bg=self.colors['panel'], width=5).pack(side="left", padx=2)
        self.create_button(nav_buttons, "⏪", self.prev_frame, bg=self.colors['panel'], width=5).pack(side="left", padx=2)
        self.create_button(nav_buttons, "⏩", self.next_frame, bg=self.colors['panel'], width=5).pack(side="left", padx=2)
        self.create_button(nav_buttons, "⏭", self.last_frame, bg=self.colors['panel'], width=5).pack(side="left", padx=2)
        
        # Blur Settings Section
        blur_frame = self.create_label_frame(controls_frame, "Blur Settings")
        blur_frame.pack(fill="x", padx=10, pady=10)
        
        blur_type_label_frame = tk.Frame(blur_frame, bg=self.colors['panel'])
        blur_type_label_frame.pack(fill="x", padx=5, pady=(5, 2))
        
        tk.Label(
            blur_type_label_frame,
            text="Blur Type:",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(side="left")
        
        blur_combo = ttk.Combobox(
            blur_type_label_frame,
            textvariable=self.blur_type_var,
            values=["gaussian", "pixelate", "black_box", "white_box"],
            state="readonly",
            font=("Helvetica", 10),
            width=15
        )
        blur_combo.pack(side="left", padx=(5, 2), fill="x", expand=True)
        
        # Lock button for blur type (darker for visibility)
        self.blur_type_lock_button = self.create_button(
            blur_type_label_frame,
            "✓",
            self.lock_blur_type,
            bg='#2b2b2b',  # Darker background
            fg='#228b22',  # Dark green checkmark (forest green)
            width=3
        )
        self.blur_type_lock_button.pack(side="left", padx=2)
        
        # Bind combobox selection event
        blur_combo.bind("<<ComboboxSelected>>", self.on_blur_type_change)
        
        # Intensity control
        intensity_label_frame = tk.Frame(blur_frame, bg=self.colors['panel'])
        intensity_label_frame.pack(fill="x", padx=5, pady=(10, 2))
        
        tk.Label(
            intensity_label_frame,
            text="Intensity:",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(side="left")
        
        self.intensity_value_label = tk.Label(
            intensity_label_frame,
            text="90%",
            font=("Helvetica", 11, "bold"),
            bg=self.colors['panel'],
            fg=self.colors['accent']
        )
        self.intensity_value_label.pack(side="right")
        
        self.opacity_scale = tk.Scale(
            blur_frame,
            from_=10,
            to=100,
            resolution=5,
            orient="horizontal",
            variable=self.opacity_var,
            command=self.on_intensity_change,
            bg=self.colors['panel'],
            fg=self.colors['fg'],
            troughcolor=self.colors['bg'],
            activebackground=self.colors['accent'],
            font=("Helvetica", 9),
            length=320
        )
        self.opacity_scale.pack(fill="x", padx=5, pady=5)
        
        intensity_labels = tk.Frame(blur_frame, bg=self.colors['panel'])
        intensity_labels.pack(fill="x", padx=5)
        
        tk.Label(
            intensity_labels,
            text="Light",
            font=("Helvetica", 8),
            bg=self.colors['panel'],
            fg=self.colors['text_secondary']
        ).pack(side="left")
        
        tk.Label(
            intensity_labels,
            text="Strong",
            font=("Helvetica", 8),
            bg=self.colors['panel'],
            fg=self.colors['text_secondary']
        ).pack(side="right")
        
        # Timer Settings
        timer_frame = self.create_label_frame(controls_frame, "Time Range Settings")
        timer_frame.pack(fill="x", padx=10, pady=10)
        
        # Start/Stop time entry boxes
        time_entry_frame = tk.Frame(timer_frame, bg=self.colors['panel'])
        time_entry_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        tk.Label(
            time_entry_frame,
            text="Start (sec):",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(side="left", padx=(0, 5))
        
        start_entry = tk.Entry(
            time_entry_frame,
            textvariable=self.start_second_var,
            font=("Helvetica", 10),
            bg='#2b2b2b',
            fg=self.colors['fg'],
            relief="flat",
            insertbackground=self.colors['fg'],
            width=10
        )
        start_entry.pack(side="left", padx=5)
        
        tk.Label(
            time_entry_frame,
            text="End (sec):",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(side="left", padx=(10, 5))
        
        end_entry = tk.Entry(
            time_entry_frame,
            textvariable=self.end_second_var,
            font=("Helvetica", 10),
            bg='#2b2b2b',
            fg=self.colors['fg'],
            relief="flat",
            insertbackground=self.colors['fg'],
            width=10
        )
        end_entry.pack(side="left", padx=5)
        
        # Calculate duration button
        calc_button = self.create_button(
            time_entry_frame,
            "Calculate",
            self.calculate_duration,
            bg=self.colors['panel'],
            width=8
        )
        calc_button.pack(side="left", padx=5)
        
        # Duration slider (increased limit to 300 seconds)
        tk.Label(
            timer_frame,
            text="Duration (seconds):",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(anchor="w", padx=5, pady=(10, 2))
        
        self.duration_scale = tk.Scale(
            timer_frame,
            from_=1,
            to=300,  # Increased from 10 to 300
            orient="horizontal",
            variable=self.duration_var,
            command=self.on_duration_change,
            bg=self.colors['panel'],
            fg=self.colors['fg'],
            troughcolor=self.colors['bg'],
            activebackground=self.colors['accent'],
            font=("Helvetica", 9),
            length=320
        )
        self.duration_scale.pack(fill="x", padx=5, pady=5)
        
        self.duration_label = tk.Label(
            timer_frame,
            text="1 second",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['text_secondary']
        )
        self.duration_label.pack()
        
        # Rectangle Management
        rect_frame = self.create_label_frame(controls_frame, "Rectangle Management")
        rect_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Hold, Confirm, and Preview buttons
        hold_confirm_frame = tk.Frame(rect_frame, bg=self.colors['panel'])
        hold_confirm_frame.pack(fill="x", padx=5, pady=5)
        
        self.hold_button = self.create_button(
            hold_confirm_frame,
            "🔒 Hold",
            self.hold_rectangle,
            bg=self.colors['panel'],
            width=10
        )
        self.hold_button.pack(side="left", padx=2)
        
        self.create_button(
            hold_confirm_frame,
            "✅ Confirm",
            self.confirm_rectangle,
            bg=self.colors['panel'],
            width=10
        ).pack(side="left", padx=2)
        
        self.create_button(
            hold_confirm_frame,
            "👁️ Preview",
            self.preview_video,
            bg=self.colors['panel'],
            width=10
        ).pack(side="left", padx=2)
        
        # Rectangle list
        list_container = tk.Frame(rect_frame, bg=self.colors['panel'])
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        tk.Label(
            list_container,
            text="Active Regions:",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        ).pack(anchor="w", pady=(0, 5))
        
        self.rect_listbox = tk.Listbox(
            list_container,
            height=4,
            bg='#2b2b2b',
            fg=self.colors['fg'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['fg'],
            font=("Helvetica", 9),
            relief="flat"
        )
        self.rect_listbox.pack(fill="both", expand=True)
        
        # Rectangle action buttons
        rect_buttons = tk.Frame(rect_frame, bg=self.colors['panel'])
        rect_buttons.pack(fill="x", padx=5, pady=5)
        
        self.create_button(
            rect_buttons,
            "Delete",
            self.delete_selected_rectangle,
            bg=self.colors['panel'],
            width=12
        ).pack(side="left", padx=2)
        
        self.create_button(
            rect_buttons,
            "Clear All",
            self.clear_all_rectangles,
            bg=self.colors['panel'],
            width=12
        ).pack(side="left", padx=2)
        
        # Right panel - Video display
        right_panel = tk.Frame(self.content_paned, bg=self.colors['bg'])
        self.content_paned.add(right_panel, minsize=500)
        
        video_frame = self.create_label_frame(right_panel, "Video Preview")
        video_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(
            video_frame,
            bg="#1a1a1a",
            cursor="crosshair",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        # Video progress bar with timing indicators
        progress_frame = tk.Frame(video_frame, bg=self.colors['panel'])
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Time labels
        time_labels = tk.Frame(progress_frame, bg=self.colors['panel'])
        time_labels.pack(fill="x", padx=5, pady=(5, 0))
        
        self.progress_start_label = tk.Label(
            time_labels,
            text="0:00",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        )
        self.progress_start_label.pack(side="left")
        
        self.progress_current_label = tk.Label(
            time_labels,
            text="0:00",
            font=("Helvetica", 10, "bold"),
            bg=self.colors['panel'],
            fg=self.colors['accent']
        )
        self.progress_current_label.pack(side="left", expand=True)
        
        self.progress_end_label = tk.Label(
            time_labels,
            text="0:00",
            font=("Helvetica", 9),
            bg=self.colors['panel'],
            fg=self.colors['fg']
        )
        self.progress_end_label.pack(side="right")
        
        # Progress bar (interactive)
        self.progress_canvas = tk.Canvas(
            progress_frame,
            height=20,
            bg=self.colors['bg'],
            highlightthickness=0,
            cursor="hand2"
        )
        self.progress_canvas.pack(fill="x", padx=5, pady=5)
        
        # Bind mouse events for progress bar navigation
        self.progress_canvas.bind("<Button-1>", self.on_progress_click)
        self.progress_canvas.bind("<B1-Motion>", self.on_progress_drag)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bottom action bar
        action_bar = tk.Frame(main_container, bg=self.colors['bg'])
        action_bar.pack(fill="x", pady=(15, 0))
        
        action_buttons = tk.Frame(action_bar, bg=self.colors['bg'])
        action_buttons.pack()
        
        # Gray buttons with black bold text
        self.create_button(action_buttons, "💾 Save Regions", self.save_regions, bg=self.colors['panel'], width=15).pack(side="left", padx=5)
        self.create_button(action_buttons, "📂 Load Regions", self.load_regions, bg=self.colors['panel'], width=15).pack(side="left", padx=5)
        self.create_button(action_buttons, "🎬 Process Video", self.process_video, bg=self.colors['panel'], width=15).pack(side="left", padx=5)
        self.create_button(action_buttons, "🎞️ Export as GIF", self.export_as_gif, bg=self.colors['panel'], width=15).pack(side="left", padx=5)
        
        # Clear All Settings button with warning (dark black text)
        clear_settings_btn = self.create_button(action_buttons, "🗑️ Clear All Settings", self.clear_all_settings, bg=self.colors['danger'], width=18)
        clear_settings_btn.configure(fg='#000000', font=("Helvetica", 10, "bold"))  # Dark black bold text
        clear_settings_btn.pack(side="left", padx=5)
        
        # Status bar
        self.status_label = tk.Label(
            main_container,
            text="Ready - Load a video to start",
            font=("Helvetica", 10),
            bg=self.colors['panel'],
            fg=self.colors['fg'],
            relief="flat",
            padx=15,
            pady=8,
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(10, 0))
        
        # Bind duration change
        self.duration_var.trace_add("write", self.on_duration_change)
        
        # Bind window resize
        self.root.bind("<Configure>", self.on_window_resize)
    
    def update_panel_size(self):
        """Update left panel to slightly more than 1/3 of window width after window renders"""
        try:
            window_width = self.root.winfo_width()
            if window_width > 100:  # Only update if window is actually rendered
                left_panel_width = int(window_width * 0.38)  # ~38% instead of 33% for better fit
                # Update paned window sash position
                self.content_paned.sash_place(0, left_panel_width, 0)
        except:
            pass  # Ignore errors during window setup
    
    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    def on_progress_click(self, event):
        """Handle click on progress bar to jump to position"""
        if not self.video_info or not self.video_info.get('success'):
            return
        
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width < 10:
            return
        
        duration = self.video_info.get('duration_seconds', 0)
        if duration == 0:
            return
        
        # Calculate clicked position as percentage
        click_x = event.x
        progress = max(0.0, min(1.0, click_x / canvas_width))
        new_second = int(progress * duration)
        
        # Update current second and frame
        self.current_second = new_second
        self.frame_scale.set(new_second)
        # Auto-update start time to match current position
        self.update_start_time_from_current()
        self.update_display()
    
    def on_progress_drag(self, event):
        """Handle drag on progress bar"""
        self.on_progress_click(event)  # Same behavior as click
    
    def update_progress_bar(self):
        """Update video progress bar with timing indicators"""
        if not self.video_info or not self.video_info.get('success'):
            return
        
        duration = self.video_info.get('duration_seconds', 0)
        if duration == 0:
            return
        
        # Update time labels
        self.progress_start_label.configure(text=self.format_time(0))
        self.progress_current_label.configure(text=self.format_time(self.current_second))
        self.progress_end_label.configure(text=self.format_time(duration))
        
        # Draw progress bar
        self.progress_canvas.delete("all")
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width < 10:
            return
        
        # Calculate progress percentage
        progress = min(1.0, self.current_second / duration) if duration > 0 else 0
        progress_width = int(canvas_width * progress)
        
        # Draw background
        self.progress_canvas.create_rectangle(
            0, 0, canvas_width, 20,
            fill=self.colors['bg'],
            outline=""
        )
        
        # Draw progress fill
        if progress_width > 0:
            self.progress_canvas.create_rectangle(
                0, 0, progress_width, 20,
                fill=self.colors['accent'],
                outline=""
            )
        
        # Draw current position indicator
        if progress_width > 0:
            self.progress_canvas.create_rectangle(
                progress_width - 2, 0, progress_width + 2, 20,
                fill=self.colors['fg'],
                outline=""
            )
    
    def on_intensity_change(self, value):
        """Handle intensity slider change"""
        intensity = int(float(value))
        self.intensity_value_label.configure(text=f"{intensity}%")
    
    def calculate_duration(self):
        """Calculate duration from start/stop times"""
        try:
            start = float(self.start_second_var.get() or 0)
            end = float(self.end_second_var.get() or 0)
            
            if end > start:
                duration = int(end - start)
                self.duration_var.set(max(1, duration))
                self.duration_label.configure(text=f"{duration} second{'s' if duration != 1 else ''}")
                self.status_label.configure(text=f"Calculated duration: {duration} seconds (from {start}s to {end}s)")
            else:
                messagebox.showwarning("Warning", "End time must be greater than start time")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for start and end times")
    
    def on_duration_change(self, *args):
        """Handle duration change"""
        duration = self.duration_var.get()
        self.duration_label.configure(text=f"{duration} second{'s' if duration != 1 else ''}")
        
        # Auto-calculate end time if start time is set
        if self.start_second_var.get():
            try:
                start = float(self.start_second_var.get())
                end = start + duration
                self.end_second_var.set(str(int(end)))
            except ValueError:
                pass
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            self.root.after(100, self.update_display)
            self.root.after(150, self.update_progress_bar)
    
    def load_video(self):
        """Load video file"""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mov *.mp4 *.avi *.mkv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.video_path = file_path
            self.cap = cv2.VideoCapture(file_path)
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Could not open video file")
                return
            
            # Get video info
            self.video_info = self.blur_engine.get_video_info(file_path)
            
            if not self.video_info['success']:
                messagebox.showerror("Error", "Could not read video information")
                return
            
            # Update UI
            self.file_label.configure(text=os.path.basename(file_path), fg=self.colors['fg'])
            
            # Update frame scale
            max_seconds = int(self.video_info['duration_seconds'])
            self.frame_scale.configure(to=max_seconds)
            
            # Limit duration slider to video length
            self.duration_scale.configure(to=min(300, max_seconds))
            
            # Update progress bar
            self.update_progress_bar()
            
            self.status_label.configure(text=f"Video loaded: {self.video_info['duration_seconds']:.1f}s, {self.video_info['fps']} FPS")
            
            # Load first frame
            self.current_second = 0
            self.update_start_time_from_current()
            self.update_display()
    
    def remove_video(self):
        """Remove current video with warning"""
        if not self.video_path:
            messagebox.showinfo("Info", "No video loaded to remove")
            return
        
        # Warning dialog
        result = messagebox.askyesno(
            "Remove Video",
            "Are you sure you want to remove the current video?\n\n"
            "This will:\n"
            "- Close the current video\n"
            "- Clear all rectangles and settings\n"
            "- Reset the interface\n\n"
            "This action cannot be undone.",
            icon="warning"
        )
        
        if result:
            # Close video capture
            if self.cap:
                self.cap.release()
            
            # Clear all data
            self.video_path = None
            self.cap = None
            self.video_info = {}
            self.regions.clear()
            self.pending_rectangle = None
            self.rectangle_held = False
            self.held_rectangle = None
            
            # Reset UI
            self.file_label.configure(text="No video loaded", fg=self.colors['text_secondary'])
            self.frame_scale.configure(to=1)
            self.duration_scale.configure(to=300)
            self.current_second = 0
            self.frame_scale.set(0)
            self.start_second_var.set("")
            self.end_second_var.set("")
            
            # Clear canvas
            self.canvas.delete("all")
            
            # Update lists
            self.update_rectangle_list()
            self.update_progress_bar()
            
            self.status_label.configure(text="Video removed - all settings cleared")
    
    def update_start_time_from_current(self):
        """Update start time entry to match current video position"""
        # Always update start time to match current video position
        # User can still manually override by typing in the field
        self.start_second_var.set(str(self.current_second))
    
    def on_frame_change(self, value):
        """Handle frame slider change"""
        self.current_second = int(float(value))
        # Auto-update start time to match current position
        self.update_start_time_from_current()
        self.update_display()
    
    def first_frame(self):
        """Go to first frame"""
        self.current_second = 0
        self.frame_scale.set(0)
        self.update_start_time_from_current()
        self.update_display()
    
    def prev_frame(self):
        """Go to previous frame"""
        if self.current_second > 0:
            self.current_second -= 1
            self.frame_scale.set(self.current_second)
            self.update_start_time_from_current()
            self.update_display()
    
    def next_frame(self):
        """Go to next frame"""
        if self.current_second < self.video_info.get('duration_seconds', 0) - 1:
            self.current_second += 1
            self.frame_scale.set(self.current_second)
            self.update_start_time_from_current()
            self.update_display()
    
    def last_frame(self):
        """Go to last frame"""
        max_seconds = int(self.video_info.get('duration_seconds', 0)) - 1
        self.current_second = max_seconds
        self.frame_scale.set(self.current_second)
        self.update_start_time_from_current()
        self.update_display()
    
    def update_display(self):
        """Update video display"""
        if not self.cap:
            return
        
        # Get frame at current second
        frame_number = self.current_second * self.video_info['fps']
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if not ret:
            return
        
        # Convert to PhotoImage - ensure proper color conversion
        # Make sure frame is contiguous and properly formatted
        if frame is None or frame.size == 0:
            return
        
        # Ensure frame is contiguous array and in BGR format (OpenCV default) before converting to RGB
        frame = np.ascontiguousarray(frame)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            # Convert BGR to RGB for display
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            display_frame = frame
        
        # Ensure display_frame is contiguous and uint8
        display_frame = np.ascontiguousarray(display_frame, dtype=np.uint8)
        pil_image = Image.fromarray(display_frame)
        
        # Resize to fit canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            # Calculate aspect ratio
            img_width, img_height = pil_image.size
            aspect_ratio = img_width / img_height
            
            if canvas_width / canvas_height > aspect_ratio:
                new_height = canvas_height
                new_width = int(canvas_height * aspect_ratio)
            else:
                new_width = canvas_width
                new_height = int(canvas_width / aspect_ratio)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.photo = ImageTk.PhotoImage(pil_image)
        
        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo)
        
        # Redraw rectangles
        self.redraw_rectangles()
        
        # Redraw pending rectangle if exists (only if not held)
        if self.pending_rectangle and not self.rectangle_held:
            self.redraw_pending_rectangle()
        
        # Redraw held rectangle if exists
        if self.rectangle_held and self.held_rectangle:
            self.redraw_held_rectangle()
        
        # Update current second label with formatted time
        self.current_second_label.configure(text=self.format_time(self.current_second))
        
        # Update progress bar
        self.update_progress_bar()
    
    def redraw_rectangles(self):
        """Redraw all rectangles on the canvas"""
        if not self.video_info or not hasattr(self, 'photo'):
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        photo_width = self.photo.width()
        photo_height = self.photo.height()
        
        offset_x = (canvas_width - photo_width) // 2
        offset_y = (canvas_height - photo_height) // 2
        
        for i, rect in enumerate(self.regions):
            start_frame = rect['start_frame']
            end_frame = rect['end_frame']
            current_frame = int(self.current_second * self.video_info['fps'])
            
            # Only show rectangle if within the frame range (inclusive of end frame)
            if start_frame <= current_frame <= end_frame:
                scale_x = photo_width / self.video_info['width']
                scale_y = photo_height / self.video_info['height']
                
                canvas_x = rect['x'] * scale_x + offset_x
                canvas_y = rect['y'] * scale_y + offset_y
                canvas_width_rect = rect['width'] * scale_x
                canvas_height_rect = rect['height'] * scale_y
                
                # Green rectangle for confirmed rectangles
                self.canvas.create_rectangle(
                    canvas_x, canvas_y, 
                    canvas_x + canvas_width_rect, canvas_y + canvas_height_rect,
                    outline="#00ff00", width=2, tags=f"rect_{i}"  # Green
                )
    
    def redraw_pending_rectangle(self):
        """Redraw the pending rectangle"""
        if not self.pending_rectangle or not self.video_info or not hasattr(self, 'photo'):
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        photo_width = self.photo.width()
        photo_height = self.photo.height()
        
        offset_x = (canvas_width - photo_width) // 2
        offset_y = (canvas_height - photo_height) // 2
        
        scale_x = photo_width / self.video_info['width']
        scale_y = photo_height / self.video_info['height']
        
        canvas_x = self.pending_rectangle['x'] * scale_x + offset_x
        canvas_y = self.pending_rectangle['y'] * scale_y + offset_y
        canvas_width_rect = self.pending_rectangle['width'] * scale_x
        canvas_height_rect = self.pending_rectangle['height'] * scale_y
        
        # Check if pending rectangle applies to current frame (using current duration slider)
        start_second = self.pending_rectangle.get('start_second', self.current_second)
        current_duration = self.duration_var.get()
        end_second = start_second + current_duration
        current_frame = int(self.current_second * self.video_info['fps'])
        start_frame = int(start_second * self.video_info['fps'])
        end_frame = int(end_second * self.video_info['fps'])
        
        # Only show if within the time interval
        if start_frame <= current_frame <= end_frame:
            # Dark yellow border for pending rectangle
            self.canvas.create_rectangle(
                canvas_x, canvas_y, 
                canvas_x + canvas_width_rect, canvas_y + canvas_height_rect,
                outline="#b8860b", width=3, tags="pending_rect"  # Dark yellow
            )
    
    def redraw_held_rectangle(self):
        """Redraw the held rectangle"""
        if not self.held_rectangle or not self.video_info or not hasattr(self, 'photo'):
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        photo_width = self.photo.width()
        photo_height = self.photo.height()
        
        offset_x = (canvas_width - photo_width) // 2
        offset_y = (canvas_height - photo_height) // 2
        
        scale_x = photo_width / self.video_info['width']
        scale_y = photo_height / self.video_info['height']
        
        # Check if held rectangle applies to current frame
        start_frame = self.held_rectangle['start_frame']
        end_frame = self.held_rectangle['end_frame']
        current_frame = int(self.current_second * self.video_info['fps'])
        
        # Only show if within the frame range (inclusive of end frame)
        if start_frame <= current_frame <= end_frame:
            canvas_x = self.held_rectangle['x'] * scale_x + offset_x
            canvas_y = self.held_rectangle['y'] * scale_y + offset_y
            canvas_width_rect = self.held_rectangle['width'] * scale_x
            canvas_height_rect = self.held_rectangle['height'] * scale_y
            
            # Orange rectangle for held rectangle
            self.canvas.create_rectangle(
                canvas_x, canvas_y, 
                canvas_x + canvas_width_rect, canvas_y + canvas_height_rect,
                outline="#ff8c00", width=3, tags="held_rect"  # Orange
            )
    
    def on_mouse_down(self, event):
        """Handle mouse down event"""
        self.drawing = True
        self.start_point = (event.x, event.y)
        self.canvas.configure(cursor="crosshair")
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if self.drawing and self.start_point:
            self.canvas.delete("temp_rect")
            self.canvas.create_rectangle(
                self.start_point[0], self.start_point[1], 
                event.x, event.y, 
                outline=self.colors['danger'], width=2, tags="temp_rect"
            )
    
    def on_mouse_up(self, event):
        """Handle mouse up event"""
        if self.drawing and self.start_point:
            x1, y1 = self.start_point
            x2, y2 = event.x, event.y
            
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            if width > 10 and height > 10:
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if hasattr(self, 'photo'):
                    photo_width = self.photo.width()
                    photo_height = self.photo.height()
                    
                    offset_x = (canvas_width - photo_width) // 2
                    offset_y = (canvas_height - photo_height) // 2
                    
                    img_x = x - offset_x
                    img_y = y - offset_y
                    
                    video_x = int(img_x * self.video_info['width'] / photo_width)
                    video_y = int(img_y * self.video_info['height'] / photo_height)
                    video_width = int(width * self.video_info['width'] / photo_width)
                    video_height = int(height * self.video_info['height'] / photo_height)
                else:
                    video_x = int(x * self.video_info['width'] / canvas_width)
                    video_y = int(y * self.video_info['height'] / canvas_height)
                    video_width = int(width * self.video_info['width'] / canvas_width)
                    video_height = int(height * self.video_info['height'] / canvas_height)
                
                # Store rectangle position - duration will be calculated when Hold/Confirm is pressed
                # Use start time from entry or current position
                if self.start_second_var.get():
                    try:
                        start_second = int(float(self.start_second_var.get()))
                    except ValueError:
                        start_second = self.current_second
                else:
                    start_second = self.current_second
                
                # Store pending rectangle without final duration - will be calculated on Hold/Confirm
                self.pending_rectangle = {
                    'x': video_x,
                    'y': video_y,
                    'width': video_width,
                    'height': video_height,
                    'blur_type': self.blur_type_var.get(),
                    'intensity': self.opacity_var.get(),
                    'pii_type': 'custom_text',
                    'start_second': start_second,  # Store as seconds, will convert to frames later
                    'start_frame': int(start_second * self.video_info['fps']),  # Temporary for display
                    'end_frame': int((start_second + self.duration_var.get()) * self.video_info['fps'])  # Temporary for display
                }
                
                # Show preview with current duration slider value
                current_duration = self.duration_var.get()
                duration_text = f" for {current_duration} second{'s' if current_duration != 1 else ''}"
                self.status_label.configure(
                    text=f"Rectangle drawn: {video_width}x{video_height}{duration_text} - Adjust duration slider, then click 'Hold' or 'Confirm' to finalize"
                )
                
                self.canvas.delete("pending_rect")
                self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    outline="#b8860b", width=3, tags="pending_rect"  # Dark yellow
                )
            
            self.drawing = False
            self.start_point = None
            self.canvas.delete("temp_rect")
            self.canvas.configure(cursor="arrow")
    
    def on_blur_type_change(self, event=None):
        """Handle blur type combobox change"""
        # Update the lock button to show selection is active (keep dark with dark green checkmark)
        self.blur_type_lock_button.configure(bg='#2b2b2b', fg='#228b22')
    
    def lock_blur_type(self):
        """Lock in the blur type selection"""
        # Visual feedback - flash green then return to dark
        self.blur_type_lock_button.configure(bg='#228b22', fg='#ffffff')
        self.root.after(500, lambda: self.blur_type_lock_button.configure(bg='#2b2b2b', fg='#228b22'))
        # Force focus away from combobox
        self.root.focus()
    
    def hold_rectangle(self):
        """Hold/lock the rectangle at current start time and duration"""
        if self.rectangle_held and self.held_rectangle:
            # Release the hold - restore pending rectangle if it exists
            self.rectangle_held = False
            self.held_rectangle = None
            self.hold_button.configure(text="🔒 Hold", bg=self.colors['panel'])
            self.status_label.configure(text="Rectangle hold released - you can modify and hold again")
            # Update rectangle list to remove hold status
            self.update_rectangle_list()
            # Redraw to show pending rectangle again
            self.update_display()
        elif self.pending_rectangle:
            # Calculate duration from current duration slider value (not when rectangle was drawn)
            start_second = self.pending_rectangle.get('start_second', self.current_second)
            if self.start_second_var.get():
                try:
                    start_second = int(float(self.start_second_var.get()))
                except ValueError:
                    start_second = self.pending_rectangle.get('start_second', self.current_second)
            
            # Use current duration slider value (this is the key fix)
            current_duration = self.duration_var.get()
            end_second = start_second + current_duration
            
            # Recalculate frames with current duration
            start_frame = int(start_second * self.video_info['fps'])
            end_frame = int(end_second * self.video_info['fps'])
            
            # Create held rectangle with current settings
            self.held_rectangle = {
                'x': self.pending_rectangle['x'],
                'y': self.pending_rectangle['y'],
                'width': self.pending_rectangle['width'],
                'height': self.pending_rectangle['height'],
                'blur_type': self.blur_type_var.get(),  # Use current blur type
                'intensity': self.opacity_var.get(),  # Use current intensity
                'pii_type': 'custom_text',
                'start_frame': start_frame,
                'end_frame': end_frame
            }
            
            self.rectangle_held = True
            
            # Update button to show it's held
            self.hold_button.configure(text="🔓 Release", bg=self.colors['accent'])
            
            # Update status with detailed info
            start_sec = self.held_rectangle['start_frame'] // self.video_info['fps']
            end_sec = self.held_rectangle['end_frame'] // self.video_info['fps']
            duration = end_sec - start_sec
            
            # Verify duration calculation
            frame_duration = end_frame - start_frame
            calculated_duration = frame_duration / self.video_info['fps']
            
            self.status_label.configure(
                text=f"Rectangle HELD: Grid({self.held_rectangle['x']},{self.held_rectangle['y']}) Size({self.held_rectangle['width']}x{self.held_rectangle['height']}) - Time: {start_sec}s-{end_sec}s ({duration}s) - Frames: {start_frame}-{end_frame} ({frame_duration} frames, {calculated_duration:.2f}s)"
            )
            
            # Update rectangle list to show hold status
            self.update_rectangle_list()
            
            # Redraw to show held rectangle
            self.update_display()
        else:
            self.status_label.configure(text="No rectangle to hold - draw one first")
    
    def confirm_rectangle(self):
        """Confirm and add the pending or held rectangle"""
        rect_to_confirm = None
        
        if self.rectangle_held and self.held_rectangle:
            # Use held rectangle
            rect_to_confirm = self.held_rectangle
            self.rectangle_held = False
            self.held_rectangle = None
            self.hold_button.configure(text="🔒 Hold", bg=self.colors['panel'])
        elif self.pending_rectangle:
            # Calculate duration from current duration slider value (not when rectangle was drawn)
            start_second = self.pending_rectangle.get('start_second', self.current_second)
            if self.start_second_var.get():
                try:
                    start_second = int(float(self.start_second_var.get()))
                except ValueError:
                    start_second = self.pending_rectangle.get('start_second', self.current_second)
            
            # Use current duration slider value
            current_duration = self.duration_var.get()
            end_second = start_second + current_duration
            
            # Calculate frames with current duration
            start_frame = int(start_second * self.video_info['fps'])
            end_frame = int(end_second * self.video_info['fps'])
            
            # Create confirmed rectangle with current settings
            rect_to_confirm = {
                'x': self.pending_rectangle['x'],
                'y': self.pending_rectangle['y'],
                'width': self.pending_rectangle['width'],
                'height': self.pending_rectangle['height'],
                'blur_type': self.blur_type_var.get(),  # Use current blur type
                'intensity': self.opacity_var.get(),  # Use current intensity
                'pii_type': 'custom_text',
                'start_frame': start_frame,
                'end_frame': end_frame
            }
        
        if rect_to_confirm:
            self.regions.append(rect_to_confirm)
            
            self.canvas.delete("pending_rect")
            self.pending_rectangle = None
            
            self.update_rectangle_list()
            self.update_display()
            self.auto_preview()
            
            self.status_label.configure(text=f"Rectangle confirmed and added! Total: {len(self.regions)} - Preview shown")
        else:
            self.status_label.configure(text="No rectangle to confirm - draw one first")
    
    def update_rectangle_list(self):
        """Update rectangle listbox with confirmed and held rectangles"""
        self.rect_listbox.delete(0, tk.END)
        
        # Show confirmed rectangles
        for i, rect in enumerate(self.regions):
            start_sec = rect['start_frame'] // self.video_info['fps']
            end_sec = rect['end_frame'] // self.video_info['fps']
            duration = end_sec - start_sec
            intensity = rect.get('intensity', 90)
            label = f"{i+1}: {rect['width']}x{rect['height']} at ({rect['x']},{rect['y']}) - {rect['blur_type']} ({intensity}%) [{start_sec}-{end_sec}s, {duration}s]"
            self.rect_listbox.insert(tk.END, label)
        
        # Show held rectangle with detailed status
        if self.rectangle_held and self.held_rectangle:
            start_sec = self.held_rectangle['start_frame'] // self.video_info['fps']
            end_sec = self.held_rectangle['end_frame'] // self.video_info['fps']
            duration = end_sec - start_sec
            intensity = self.held_rectangle.get('intensity', 90)
            
            # Detailed hold status with grid regions and time
            start_frame = self.held_rectangle['start_frame']
            end_frame = self.held_rectangle['end_frame']
            frame_duration = end_frame - start_frame
            calculated_duration = frame_duration / self.video_info['fps']
            
            hold_label = f"🔒 HOLD: Grid({self.held_rectangle['x']},{self.held_rectangle['y']}) Size({self.held_rectangle['width']}x{self.held_rectangle['height']}) - {self.held_rectangle['blur_type']} ({intensity}%) - Time: {start_sec}s to {end_sec}s ({duration}s) - Frames: {start_frame}-{end_frame} ({frame_duration} frames, {calculated_duration:.2f}s calc)"
            hold_index = self.rect_listbox.size()
            self.rect_listbox.insert(tk.END, hold_label)
            # Highlight the held rectangle entry
            try:
                self.rect_listbox.itemconfig(hold_index, {'bg': '#4a4a4a', 'fg': '#ff8c00'})
            except:
                pass  # Some systems don't support itemconfig
    
    def delete_selected_rectangle(self):
        """Delete selected rectangle"""
        selection = self.rect_listbox.curselection()
        if selection:
            index = selection[0]
            del self.regions[index]
            self.update_rectangle_list()
            self.update_display()
            self.status_label.configure(text="Rectangle deleted")
        else:
            messagebox.showwarning("Warning", "Please select a rectangle to delete")
    
    def clear_all_rectangles(self):
        """Clear all rectangles"""
        if self.regions:
            count = len(self.regions)
            self.regions.clear()
            self.update_rectangle_list()
            self.update_display()
            self.status_label.configure(text=f"Cleared all {count} rectangles")
        else:
            messagebox.showinfo("Info", "No rectangles to clear")
    
    def clear_all_settings(self):
        """Clear all settings and reset to defaults (keeps video)"""
        if not self.video_path:
            messagebox.showinfo("Info", "No video loaded - nothing to clear")
            return
        
        # Warning dialog
        result = messagebox.askyesno(
            "Clear All Settings",
            "Are you sure you want to clear all settings?\n\n"
            "This will:\n"
            "- Remove all rectangles\n"
            "- Reset all sliders to defaults\n"
            "- Clear pending/held rectangles\n\n"
            "The video will remain loaded.\n\n"
            "This action cannot be undone.",
            icon="warning"
        )
        
        if result:
            # Clear rectangles
            count = len(self.regions)
            self.regions.clear()
            self.pending_rectangle = None
            self.rectangle_held = False
            self.held_rectangle = None
            
            # Reset sliders to defaults
            self.opacity_var.set(90)  # Default 90%
            self.blur_type_var.set("gaussian")
            self.duration_var.set(1)
            self.start_second_var.set("")
            self.end_second_var.set("")
            
            # Reset to first frame
            self.current_second = 0
            self.frame_scale.set(0)
            self.update_start_time_from_current()
            
            # Update UI
            self.update_rectangle_list()
            self.update_display()
            self.update_progress_bar()
            
            self.status_label.configure(text=f"All settings cleared - {count} rectangle(s) removed, sliders reset to defaults")
    
    def auto_preview(self):
        """Automatically show preview when rectangle is confirmed"""
        if not self.video_path or not self.regions:
            return
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Auto Preview - Blur Effects")
        preview_window.geometry("700x550")
        preview_window.configure(bg=self.colors['bg'])
        
        close_button = self.create_button(
            preview_window,
            "Close Preview",
            preview_window.destroy,
            bg=self.colors['danger']
        )
        close_button.pack(pady=10)
        
        preview_canvas = tk.Canvas(preview_window, bg="#1a1a1a", highlightthickness=0)
        preview_canvas.pack(fill="both", expand=True, padx=10, pady=5)
        
        frame_number = self.current_second * self.video_info['fps']
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            preview_frame = self.apply_blur_effects(frame)
            
            # Ensure proper color conversion
            preview_frame = np.ascontiguousarray(preview_frame)
            if len(preview_frame.shape) == 3 and preview_frame.shape[2] == 3:
                preview_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            preview_frame = np.ascontiguousarray(preview_frame, dtype=np.uint8)
            pil_image = Image.fromarray(preview_frame)
            
            canvas_width = 680
            canvas_height = 450
            img_width, img_height = pil_image.size
            aspect_ratio = img_width / img_height
            
            if canvas_width / canvas_height > aspect_ratio:
                new_height = canvas_height
                new_width = int(canvas_height * aspect_ratio)
            else:
                new_width = canvas_width
                new_height = int(canvas_width / aspect_ratio)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_image)
            
            preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            preview_canvas.image = photo
            
            info_label = tk.Label(
                preview_window,
                text=f"Auto Preview - Frame {self.current_second}s - {len(self.regions)} blur region(s)",
                font=("Helvetica", 10, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']
            )
            info_label.pack(pady=5)
            
            preview_window.after(5000, preview_window.destroy)
    
    def preview_video(self):
        """Manual preview video with blur effects applied (works with confirmed and held rectangles)"""
        if not self.video_path:
            messagebox.showerror("Error", "No video loaded")
            return
        
        # Check if there are rectangles to preview (confirmed or held)
        has_rectangles = len(self.regions) > 0
        has_held = self.rectangle_held and self.held_rectangle
        
        if not has_rectangles and not has_held:
            messagebox.showwarning("Warning", "No rectangles to preview - draw and hold/confirm a rectangle first")
            return
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Manual Preview - Blur Effects")
        preview_window.geometry("900x700")
        preview_window.configure(bg=self.colors['bg'])
        
        preview_canvas = tk.Canvas(preview_window, bg="#1a1a1a", highlightthickness=0)
        preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame_number = self.current_second * self.video_info['fps']
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            preview_frame = self.apply_blur_effects(frame)
            
            # Ensure proper color conversion
            preview_frame = np.ascontiguousarray(preview_frame)
            if len(preview_frame.shape) == 3 and preview_frame.shape[2] == 3:
                preview_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            preview_frame = np.ascontiguousarray(preview_frame, dtype=np.uint8)
            pil_image = Image.fromarray(preview_frame)
            
            canvas_width = 880
            canvas_height = 650
            img_width, img_height = pil_image.size
            aspect_ratio = img_width / img_height
            
            if canvas_width / canvas_height > aspect_ratio:
                new_height = canvas_height
                new_width = int(canvas_height * aspect_ratio)
            else:
                new_width = canvas_width
                new_height = int(canvas_width / aspect_ratio)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_image)
            
            preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            preview_canvas.image = photo
            
            region_count = len(self.regions)
            if self.rectangle_held and self.held_rectangle:
                region_count += 1
            
            info_label = tk.Label(
                preview_window,
                text=f"Manual Preview - Frame {self.current_second}s with {region_count} blur region(s)",
                font=("Helvetica", 12, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']
            )
            info_label.pack(pady=5)
            
            self.status_label.configure(text=f"Manual preview window opened - showing frame at {self.current_second}s")
        else:
            messagebox.showerror("Error", "Could not read frame for preview")
    
    def apply_blur_effects(self, frame):
        """Apply blur effects to a frame using advanced engine (includes confirmed and held rectangles)"""
        # Use current frame number from video position
        current_frame_num = int(self.current_second * self.video_info['fps'])
        return self.apply_blur_effects_for_frame(frame, current_frame_num)
    
    def apply_blur_effects_for_frame(self, frame, frame_number):
        """Apply blur effects to a frame for a specific frame number"""
        result_frame = frame.copy()
        
        # Combine confirmed regions and held rectangle for preview
        regions_to_apply = list(self.regions)
        if self.rectangle_held and self.held_rectangle:
            regions_to_apply.append(self.held_rectangle)
        
        for rect in regions_to_apply:
            if rect['start_frame'] <= frame_number <= rect['end_frame']:
                x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
                
                x = max(0, min(x, frame.shape[1] - 1))
                y = max(0, min(y, frame.shape[0] - 1))
                w = max(1, min(w, frame.shape[1] - x))
                h = max(1, min(h, frame.shape[0] - y))
                
                roi = result_frame[y:y+h, x:x+w]
                
                if roi.size > 0:
                    intensity = rect.get('intensity', 90)
                    opacity = max(0.1, min(1.0, intensity / 100.0))
                    
                    if rect['blur_type'] == 'gaussian':
                        kernel_size = int(15 + (opacity * 86))
                        if kernel_size % 2 == 0:
                            kernel_size += 1
                        blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                        if opacity > 0.7:
                            blurred_roi = cv2.GaussianBlur(blurred_roi, (kernel_size, kernel_size), 0)
                        if opacity > 0.9:
                            blurred_roi = cv2.GaussianBlur(blurred_roi, (kernel_size, kernel_size), 0)
                    elif rect['blur_type'] == 'pixelate':
                        pixel_size = max(3, int(3 + (opacity * 27)))
                        small = cv2.resize(roi, (max(1, w//pixel_size), max(1, h//pixel_size)))
                        blurred_roi = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
                    elif rect['blur_type'] == 'black_box':
                        blurred_roi = np.zeros_like(roi)
                    elif rect['blur_type'] == 'white_box':
                        blurred_roi = np.full_like(roi, 255)
                    else:
                        blurred_roi = roi
                    
                    if opacity >= 0.95:
                        result_frame[y:y+h, x:x+w] = blurred_roi
                    else:
                        blur_weight = opacity * 1.2
                        blur_weight = min(1.0, blur_weight)
                        original_weight = 1.0 - blur_weight
                        result_frame[y:y+h, x:x+w] = cv2.addWeighted(roi, original_weight, blurred_roi, blur_weight, 0)
        
        return result_frame
    
    def save_regions(self):
        """Save regions to file"""
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Regions",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            regions_data = []
            for rect in self.regions:
                region = {
                    "x": rect['x'],
                    "y": rect['y'],
                    "width": rect['width'],
                    "height": rect['height'],
                    "blur_type": rect['blur_type'],
                    "intensity": rect.get('intensity', 90),
                    "pii_type": rect.get('pii_type', 'custom_text'),
                    "start_frame": rect['start_frame'],
                    "end_frame": rect['end_frame']
                }
                regions_data.append(region)
            
            data = {"regions": regions_data}
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.status_label.configure(text=f"Saved {len(regions_data)} regions to {os.path.basename(file_path)}")
    
    def load_regions(self):
        """Load regions from file"""
        file_path = filedialog.askopenfilename(
            title="Load Regions",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                regions_data = data.get('regions', [])
                self.regions.clear()
                
                for region_data in regions_data:
                    rect = {
                        'x': region_data['x'],
                        'y': region_data['y'],
                        'width': region_data['width'],
                        'height': region_data['height'],
                        'blur_type': region_data['blur_type'],
                        'intensity': region_data.get('intensity', 90),
                        'pii_type': region_data.get('pii_type', 'custom_text'),
                        'start_frame': region_data['start_frame'],
                        'end_frame': region_data['end_frame']
                    }
                    self.regions.append(rect)
                
                self.update_rectangle_list()
                self.update_display()
                self.status_label.configure(text=f"Loaded {len(regions_data)} regions from {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not load regions: {str(e)}")
    
    def process_video(self):
        """Process video with current regions"""
        if not self.video_path:
            messagebox.showerror("Error", "No video loaded")
            return
        
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to process")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save Processed Video",
            defaultextension=".mov",
            filetypes=[("Video files", "*.mov *.mp4"), ("All files", "*.*")]
        )
        
        if output_path:
            self.status_label.configure(text="Processing video...")
            self.root.update()
            
            try:
                blur_regions = []
                for rect in self.regions:
                    region = BlurRegion(
                        x=rect['x'],
                        y=rect['y'],
                        width=rect['width'],
                        height=rect['height'],
                        blur_type=BlurType(rect['blur_type']),
                        intensity=rect.get('intensity', 90),
                        pii_type=PIIType(rect.get('pii_type', 'custom_text')),
                        start_frame=rect['start_frame'],
                        end_frame=rect['end_frame']
                    )
                    blur_regions.append(region)
                
                results = self.blur_engine.process_video(self.video_path, output_path, blur_regions, auto_detect=False)
                
                if results['processing_successful']:
                    self.status_label.configure(text=f"Video processed successfully! Saved to {os.path.basename(output_path)}")
                    messagebox.showinfo("Success", f"Video processed successfully!\nSaved to: {output_path}")
                else:
                    self.status_label.configure(text="Video processing failed")
                    messagebox.showerror("Error", f"Video processing failed: {results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.status_label.configure(text="Video processing failed")
                messagebox.showerror("Error", f"Video processing failed: {str(e)}")
    
    def export_as_gif(self):
        """Export processed video as a looping GIF"""
        if not self.video_path:
            messagebox.showerror("Error", "No video loaded")
            return
        
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to process")
            return
        
        # Ask user for frame rate quality with custom dialog
        quality_dialog = tk.Toplevel(self.root)
        quality_dialog.title("GIF Quality")
        quality_dialog.geometry("400x300")
        quality_dialog.configure(bg=self.colors['bg'])
        quality_dialog.transient(self.root)
        quality_dialog.grab_set()
        
        # Center the dialog
        quality_dialog.update_idletasks()
        x = (quality_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (quality_dialog.winfo_screenheight() // 2) - (300 // 2)
        quality_dialog.geometry(f"400x300+{x}+{y}")
        
        quality_choice = [None]  # Use list to store result from nested function
        
        tk.Label(
            quality_dialog,
            text="Choose GIF Quality:",
            font=("Helvetica", 14, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['fg']
        ).pack(pady=20)
        
        tk.Label(
            quality_dialog,
            text="High Frame Rate\n"
                 "- More frames (~60 frames)\n"
                 "- Smoother animation\n"
                 "- Larger file size",
            font=("Helvetica", 10),
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            justify="left"
        ).pack(pady=10)
        
        tk.Label(
            quality_dialog,
            text="Low Frame Rate\n"
                 "- Fewer frames (~15 frames)\n"
                 "- Smaller file size\n"
                 "- Faster processing",
            font=("Helvetica", 10),
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            justify="left"
        ).pack(pady=10)
        
        button_frame = tk.Frame(quality_dialog, bg=self.colors['bg'])
        button_frame.pack(pady=20)
        
        def choose_high():
            quality_choice[0] = True
            quality_dialog.destroy()
        
        def choose_low():
            quality_choice[0] = False
            quality_dialog.destroy()
        
        high_btn = self.create_button(button_frame, "High", choose_high, bg=self.colors['accent'], width=12)
        high_btn.pack(side="left", padx=10)
        
        low_btn = self.create_button(button_frame, "Low", choose_low, bg=self.colors['panel'], width=12)
        low_btn.pack(side="left", padx=10)
        
        # Wait for dialog to close
        quality_dialog.wait_window()
        
        # Check if user closed dialog without selecting
        if quality_choice[0] is None:
            return  # User cancelled
        
        # Set frame sampling based on choice
        if quality_choice[0]:
            # High frame rate: target ~60 frames
            target_frames = 60
            quality_text = "High"
        else:
            # Low frame rate: target ~15 frames
            target_frames = 15
            quality_text = "Low"
        
        output_path = filedialog.asksaveasfilename(
            title="Save as GIF",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")]
        )
        
        if output_path:
            self.status_label.configure(text="Processing video and creating GIF...")
            self.root.update()
            
            try:
                # Open video
                cap = cv2.VideoCapture(self.video_path)
                if not cap.isOpened():
                    messagebox.showerror("Error", "Could not open video file")
                    return
                
                fps = self.video_info['fps']
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Limit GIF size for reasonable file size (max 800px width)
                max_width = 800
                if width > max_width:
                    scale = max_width / width
                    new_width = max_width
                    new_height = int(height * scale)
                else:
                    new_width = width
                    new_height = height
                
                # Sample frames for GIF based on user's quality choice
                frame_skip = max(1, total_frames // target_frames)
                
                frames = []
                frame_count = 0
                processed_count = 0
                
                estimated_frames = total_frames // frame_skip
                self.status_label.configure(text=f"Processing GIF ({quality_text} quality)... (0/{estimated_frames} frames)")
                self.root.update()
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Only process every Nth frame
                    if frame_count % frame_skip == 0:
                        # Apply blur effects for this specific frame
                        processed_frame = self.apply_blur_effects_for_frame(frame, frame_count)
                        
                        # Resize if needed
                        if new_width != width or new_height != height:
                            processed_frame = cv2.resize(processed_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                        
                        # Convert BGR to RGB for PIL
                        processed_frame = np.ascontiguousarray(processed_frame)
                        if len(processed_frame.shape) == 3 and processed_frame.shape[2] == 3:
                            processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                        processed_frame = np.ascontiguousarray(processed_frame, dtype=np.uint8)
                        
                        # Convert to PIL Image
                        pil_frame = Image.fromarray(processed_frame)
                        frames.append(pil_frame)
                        
                        processed_count += 1
                        if processed_count % 5 == 0:
                            estimated_frames = total_frames // frame_skip
                            self.status_label.configure(text=f"Processing GIF ({quality_text} quality)... ({processed_count}/{estimated_frames} frames)")
                            self.root.update()
                    
                    frame_count += 1
                
                cap.release()
                
                if not frames:
                    messagebox.showerror("Error", "No frames processed for GIF")
                    return
                
                self.status_label.configure(text="Saving GIF...")
                self.root.update()
                
                # Save as animated GIF with loop
                # Duration per frame in milliseconds (100ms = ~10fps for GIF)
                duration_ms = int(1000 / (fps / frame_skip))
                
                frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=duration_ms,
                    loop=0,  # 0 means infinite loop
                    optimize=False
                )
                
                self.status_label.configure(text=f"GIF exported successfully! ({quality_text} quality) - {os.path.basename(output_path)}")
                messagebox.showinfo("Success", f"GIF exported successfully!\n\nSaved to: {output_path}\n\nQuality: {quality_text}\nFrames: {len(frames)}\nSize: {new_width}x{new_height}\nLoop: Infinite")
                
            except Exception as e:
                self.status_label.configure(text="GIF export failed")
                messagebox.showerror("Error", f"GIF export failed: {str(e)}")

def main():
    root = tk.Tk()
    app = AdvancedBlurUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
