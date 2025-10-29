#!/usr/bin/env python3
"""
Simple Blur UI - Focused on core functionality
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import json
import os
from blur_engine import BlurEngine, BlurRegion, BlurType, PIIType

class SimpleBlurUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PII Blur Tool - Simple Interface")
        self.root.geometry("1200x800")
        
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
        self.pending_rectangle = None  # Rectangle waiting to be confirmed
        
        # UI variables
        self.opacity_var = tk.IntVar(value=70)  # 10-100 range for intensity
        self.blur_type_var = tk.StringVar(value="gaussian")
        self.duration_var = tk.IntVar(value=1)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the simple user interface"""
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top section - File controls
        file_frame = tk.LabelFrame(main_frame, text="File Controls", font=("Arial", 12, "bold"))
        file_frame.pack(fill="x", pady=(0, 10))
        
        tk.Button(file_frame, text="Load Video", command=self.load_video, 
                 font=("Arial", 10, "bold"), bg="lightblue", fg="black").pack(side="left", padx=10, pady=10)
        
        self.file_label = tk.Label(file_frame, text="No video loaded", font=("Arial", 10))
        self.file_label.pack(side="left", padx=10)
        
        # Middle section - Controls and video
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(fill="both", expand=True)
        
        # Left panel - Controls with scrollbar
        controls_container = tk.Frame(middle_frame)
        controls_container.pack(side="left", fill="y", padx=(0, 10))
        controls_container.configure(width=350)  # Increased width
        
        # Create canvas and scrollbar for controls
        controls_canvas = tk.Canvas(controls_container, width=350)
        controls_scrollbar = tk.Scrollbar(controls_container, orient="vertical", command=controls_canvas.yview)
        controls_frame = tk.Frame(controls_canvas)
        
        controls_frame.bind(
            "<Configure>",
            lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all"))
        )
        
        controls_canvas.create_window((0, 0), window=controls_frame, anchor="nw")
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)
        
        controls_canvas.pack(side="left", fill="both", expand=True)
        controls_scrollbar.pack(side="right", fill="y")
        
        # Add title label
        title_label = tk.Label(controls_frame, text="Controls", font=("Arial", 12, "bold"))
        title_label.pack(pady=5)
        
        # Frame navigation
        nav_frame = tk.LabelFrame(controls_frame, text="Frame Navigation", font=("Arial", 10, "bold"))
        nav_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(nav_frame, text="Current Second:").pack()
        self.current_second_label = tk.Label(nav_frame, text="0", font=("Arial", 14, "bold"))
        self.current_second_label.pack()
        
        tk.Label(nav_frame, text="Jump to Second:").pack()
        self.frame_scale = tk.Scale(nav_frame, from_=0, to=1, orient="horizontal", 
                                   command=self.on_frame_change)
        self.frame_scale.pack(fill="x", padx=5, pady=5)
        
        # Navigation buttons
        nav_buttons = tk.Frame(nav_frame)
        nav_buttons.pack(fill="x", padx=5, pady=5)
        
        tk.Button(nav_buttons, text="⏮", command=self.first_frame, width=5, bg="lightgray", fg="black").pack(side="left", padx=2)
        tk.Button(nav_buttons, text="⏪", command=self.prev_frame, width=5, bg="lightgray", fg="black").pack(side="left", padx=2)
        tk.Button(nav_buttons, text="⏩", command=self.next_frame, width=5, bg="lightgray", fg="black").pack(side="left", padx=2)
        tk.Button(nav_buttons, text="⏭", command=self.last_frame, width=5, bg="lightgray", fg="black").pack(side="left", padx=2)
        
        # Blur settings
        blur_frame = tk.LabelFrame(controls_frame, text="Blur Settings", font=("Arial", 10, "bold"))
        blur_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(blur_frame, text="Blur Type:").pack(anchor="w")
        blur_combo = ttk.Combobox(blur_frame, textvariable=self.blur_type_var, 
                                 values=["gaussian", "pixelate", "black_box", "white_box"])
        blur_combo.pack(fill="x", padx=5, pady=2)
        
        opacity_label_frame = tk.Frame(blur_frame)
        opacity_label_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(opacity_label_frame, text="Opacity:").pack(side="left")
        tk.Label(opacity_label_frame, text="Lighter", font=("Arial", 8)).pack(side="left", padx=(20, 0))
        tk.Label(opacity_label_frame, text="Darker", font=("Arial", 8)).pack(side="right")
        
        self.opacity_scale = tk.Scale(blur_frame, from_=10, to=100, resolution=5, 
                                     orient="horizontal", variable=self.opacity_var)
        self.opacity_scale.pack(fill="x", padx=5, pady=2)
        
        # Timer settings
        timer_frame = tk.LabelFrame(controls_frame, text="Timer Settings", font=("Arial", 10, "bold"))
        timer_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(timer_frame, text="Duration (seconds):").pack(anchor="w")
        self.duration_scale = tk.Scale(timer_frame, from_=1, to=10, orient="horizontal", 
                                      variable=self.duration_var)
        self.duration_scale.pack(fill="x", padx=5, pady=2)
        
        self.duration_label = tk.Label(timer_frame, text="1 second")
        self.duration_label.pack()
        
        # Rectangle management
        rect_frame = tk.LabelFrame(controls_frame, text="Rectangle Management", font=("Arial", 10, "bold"))
        rect_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Confirm rectangle button
        tk.Button(rect_frame, text="✅ Confirm Rectangle", command=self.confirm_rectangle,
                 bg="green", fg="black", font=("Arial", 10, "bold")).pack(fill="x", padx=5, pady=5)
        
        self.rect_listbox = tk.Listbox(rect_frame, height=4)
        self.rect_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Rectangle action buttons
        rect_buttons = tk.Frame(rect_frame)
        rect_buttons.pack(fill="x", padx=5, pady=5)
        
        tk.Button(rect_buttons, text="Delete Selected", command=self.delete_selected_rectangle,
                 bg="red", fg="black", width=12).pack(side="left", padx=2)
        tk.Button(rect_buttons, text="Clear All", command=self.clear_all_rectangles,
                 bg="red", fg="black", width=12).pack(side="left", padx=2)
        
        # Right panel - Video display
        video_frame = tk.LabelFrame(middle_frame, text="Video Preview", font=("Arial", 12, "bold"))
        video_frame.pack(side="right", fill="both", expand=True)
        
        self.canvas = tk.Canvas(video_frame, bg="black", cursor="arrow")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bottom section - Actions
        actions_frame = tk.LabelFrame(main_frame, text="Actions", font=("Arial", 12, "bold"))
        actions_frame.pack(fill="x", pady=(10, 0))
        
        # First row of action buttons
        action_buttons1 = tk.Frame(actions_frame)
        action_buttons1.pack(fill="x", padx=10, pady=5)
        
        tk.Button(action_buttons1, text="Save Regions", command=self.save_regions,
                 bg="green", fg="black", width=12).pack(side="left", padx=2)
        tk.Button(action_buttons1, text="Load Regions", command=self.load_regions,
                 bg="lightgray", fg="black", width=12).pack(side="left", padx=2)
        tk.Button(action_buttons1, text="Process Video", command=self.process_video,
                 bg="blue", fg="black", width=12).pack(side="left", padx=2)
        
        # Second row of action buttons
        action_buttons2 = tk.Frame(actions_frame)
        action_buttons2.pack(fill="x", padx=10, pady=5)
        
        tk.Button(action_buttons2, text="👁️ Preview", command=self.preview_video,
                 bg="orange", fg="black", width=12).pack(side="left", padx=2)
        tk.Button(action_buttons2, text="💾 Export Video", command=self.export_summary,
                 bg="purple", fg="black", width=12).pack(side="left", padx=2)
        
        # Third row of action buttons
        action_buttons3 = tk.Frame(actions_frame)
        action_buttons3.pack(pady=2)
        tk.Button(action_buttons3, text="📄 Export Text", command=self.export_text_summary,
                 bg="gray", fg="black", width=12).pack(side="left", padx=2)
        
        # Status bar
        self.status_label = tk.Label(main_frame, text="Ready - Load a video to start", 
                                    font=("Arial", 10, "bold"), relief="sunken")
        self.status_label.pack(fill="x", pady=(10, 0))
        
        # Bind duration change
        self.duration_var.trace_add("write", self.on_duration_change)
        
        # Bind window resize
        self.root.bind("<Configure>", self.on_window_resize)
        
    def on_duration_change(self, *args):
        """Handle duration change"""
        duration = self.duration_var.get()
        self.duration_label.configure(text=f"{duration} second{'s' if duration != 1 else ''}")
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # Update display when window is resized
            self.root.after(100, self.update_display)  # Delay to avoid excessive updates
    
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
            self.file_label.configure(text=os.path.basename(file_path))
            
            # Update frame scale
            max_seconds = int(self.video_info['duration_seconds'])
            self.frame_scale.configure(to=max_seconds)
            
            self.status_label.configure(text=f"Video loaded: {self.video_info['duration_seconds']:.1f}s, {self.video_info['fps']} FPS")
            
            # Load first frame
            self.current_second = 0
            self.update_display()
    
    def on_frame_change(self, value):
        """Handle frame slider change"""
        self.current_second = int(float(value))
        self.update_display()
    
    def first_frame(self):
        """Go to first frame"""
        self.current_second = 0
        self.frame_scale.set(0)
        self.update_display()
    
    def prev_frame(self):
        """Go to previous frame"""
        if self.current_second > 0:
            self.current_second -= 1
            self.frame_scale.set(self.current_second)
            self.update_display()
    
    def next_frame(self):
        """Go to next frame"""
        if self.current_second < self.video_info.get('duration_seconds', 0) - 1:
            self.current_second += 1
            self.frame_scale.set(self.current_second)
            self.update_display()
    
    def last_frame(self):
        """Go to last frame"""
        max_seconds = int(self.video_info.get('duration_seconds', 0)) - 1
        self.current_second = max_seconds
        self.frame_scale.set(self.current_second)
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
        
        # Convert to PhotoImage
        display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
        
        # Redraw pending rectangle if exists
        if self.pending_rectangle:
            self.redraw_pending_rectangle()
        
        # Update current second label
        self.current_second_label.configure(text=str(self.current_second))
    
    def redraw_rectangles(self):
        """Redraw all rectangles on the canvas"""
        if not self.video_info or not hasattr(self, 'photo'):
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Get the actual photo dimensions
        photo_width = self.photo.width()
        photo_height = self.photo.height()
        
        # Calculate offset to center the image
        offset_x = (canvas_width - photo_width) // 2
        offset_y = (canvas_height - photo_height) // 2
        
        for i, rect in enumerate(self.regions):
            # Check if rectangle applies to current second
            start_second = rect['start_frame'] // self.video_info['fps']
            end_second = rect['end_frame'] // self.video_info['fps']
            
            if start_second <= self.current_second <= end_second:
                # Convert video coordinates to canvas coordinates
                scale_x = photo_width / self.video_info['width']
                scale_y = photo_height / self.video_info['height']
                
                canvas_x = rect['x'] * scale_x + offset_x
                canvas_y = rect['y'] * scale_y + offset_y
                canvas_width_rect = rect['width'] * scale_x
                canvas_height_rect = rect['height'] * scale_y
                
                # Draw rectangle on canvas (no text labels)
                self.canvas.create_rectangle(
                    canvas_x, canvas_y, 
                    canvas_x + canvas_width_rect, canvas_y + canvas_height_rect,
                    outline="lime", width=2, tags=f"rect_{i}"
                )
    
    def redraw_pending_rectangle(self):
        """Redraw the pending rectangle"""
        if not self.pending_rectangle or not self.video_info or not hasattr(self, 'photo'):
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Get the actual photo dimensions
        photo_width = self.photo.width()
        photo_height = self.photo.height()
        
        # Calculate offset to center the image
        offset_x = (canvas_width - photo_width) // 2
        offset_y = (canvas_height - photo_height) // 2
        
        # Convert video coordinates to canvas coordinates
        scale_x = photo_width / self.video_info['width']
        scale_y = photo_height / self.video_info['height']
        
        canvas_x = self.pending_rectangle['x'] * scale_x + offset_x
        canvas_y = self.pending_rectangle['y'] * scale_y + offset_y
        canvas_width_rect = self.pending_rectangle['width'] * scale_x
        canvas_height_rect = self.pending_rectangle['height'] * scale_y
        
        # Draw pending rectangle in yellow
        self.canvas.create_rectangle(
            canvas_x, canvas_y, 
            canvas_x + canvas_width_rect, canvas_y + canvas_height_rect,
            outline="yellow", width=3, tags="pending_rect"
        )
    
    def on_mouse_down(self, event):
        """Handle mouse down event"""
        self.drawing = True
        self.start_point = (event.x, event.y)
        self.canvas.configure(cursor="crosshair")
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if self.drawing and self.start_point:
            # Draw temporary rectangle
            self.canvas.delete("temp_rect")
            self.canvas.create_rectangle(
                self.start_point[0], self.start_point[1], 
                event.x, event.y, 
                outline="red", width=2, tags="temp_rect"
            )
    
    def on_mouse_up(self, event):
        """Handle mouse up event"""
        if self.drawing and self.start_point:
            # Calculate rectangle coordinates
            x1, y1 = self.start_point
            x2, y2 = event.x, event.y
            
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            # Only create pending rectangle if it has reasonable size
            if width > 10 and height > 10:
                # Get the actual displayed image dimensions
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                # Calculate the actual image display area (centered)
                if hasattr(self, 'photo'):
                    # Get the actual photo dimensions
                    photo_width = self.photo.width()
                    photo_height = self.photo.height()
                    
                    # Calculate offset to center the image
                    offset_x = (canvas_width - photo_width) // 2
                    offset_y = (canvas_height - photo_height) // 2
                    
                    # Adjust coordinates relative to the actual image
                    img_x = x - offset_x
                    img_y = y - offset_y
                    
                    # Convert to video coordinates
                    video_x = int(img_x * self.video_info['width'] / photo_width)
                    video_y = int(img_y * self.video_info['height'] / photo_height)
                    video_width = int(width * self.video_info['width'] / photo_width)
                    video_height = int(height * self.video_info['height'] / photo_height)
                else:
                    # Fallback to canvas-based conversion
                    video_x = int(x * self.video_info['width'] / canvas_width)
                    video_y = int(y * self.video_info['height'] / canvas_height)
                    video_width = int(width * self.video_info['width'] / canvas_width)
                    video_height = int(height * self.video_info['height'] / canvas_height)
                
                # Calculate frame range
                start_second = self.current_second
                end_second = start_second + self.duration_var.get()
                
                self.pending_rectangle = {
                    'x': video_x,
                    'y': video_y,
                    'width': video_width,
                    'height': video_height,
                    'blur_type': self.blur_type_var.get(),
                    'intensity': self.opacity_var.get(),  # Use intensity directly
                    'pii_type': 'custom_text',  # Fixed to custom_text
                    'start_frame': int(start_second * self.video_info['fps']),
                    'end_frame': int(end_second * self.video_info['fps'])
                }
                
                # Draw pending rectangle in yellow
                self.canvas.delete("pending_rect")
                self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    outline="yellow", width=3, tags="pending_rect"
                )
                
                duration_text = f" for {self.duration_var.get()} second{'s' if self.duration_var.get() != 1 else ''}"
                self.status_label.configure(text=f"Rectangle drawn: {video_width}x{video_height}{duration_text} - Click 'Confirm Rectangle' to add")
            
            self.drawing = False
            self.start_point = None
            self.canvas.delete("temp_rect")
            self.canvas.configure(cursor="arrow")
    
    def confirm_rectangle(self):
        """Confirm and add the pending rectangle"""
        if self.pending_rectangle:
            self.regions.append(self.pending_rectangle)
            print(f"DEBUG: Confirmed rectangle {len(self.regions)}: {self.pending_rectangle}")
            
            # Clear pending rectangle
            self.canvas.delete("pending_rect")
            self.pending_rectangle = None
            
            # Update display and list
            self.update_rectangle_list()
            self.update_display()
            
            # Automatically show preview
            self.auto_preview()
            
            self.status_label.configure(text=f"Rectangle confirmed and added! Total: {len(self.regions)} - Preview shown")
        else:
            self.status_label.configure(text="No rectangle to confirm - draw one first")
    
    def update_rectangle_list(self):
        """Update rectangle listbox"""
        self.rect_listbox.delete(0, tk.END)
        for i, rect in enumerate(self.regions):
            start_sec = rect['start_frame'] // self.video_info['fps']
            end_sec = rect['end_frame'] // self.video_info['fps']
            duration = end_sec - start_sec
            intensity = rect.get('intensity', 70)
            label = f"{i+1}: {rect['width']}x{rect['height']} at ({rect['x']},{rect['y']}) - {rect['blur_type']} ({intensity}%) [{start_sec}-{end_sec}s, {duration}s]"
            self.rect_listbox.insert(tk.END, label)
    
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
    
    def auto_preview(self):
        """Automatically show preview when rectangle is confirmed"""
        if not self.video_path or not self.regions:
            return
        
        # Create a temporary preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Auto Preview - Blur Effects")
        preview_window.geometry("600x450")
        
        # Add close button
        close_button = tk.Button(preview_window, text="Close Preview", 
                               command=preview_window.destroy,
                               bg="red", fg="white", font=("Arial", 10, "bold"))
        close_button.pack(pady=5)
        
        # Create canvas for preview
        preview_canvas = tk.Canvas(preview_window, bg="black")
        preview_canvas.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Get current frame and apply blur effects
        frame_number = self.current_second * self.video_info['fps']
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            # Apply blur effects to frame
            preview_frame = self.apply_blur_effects(frame)
            
            # Convert to PhotoImage
            preview_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(preview_frame)
            
            # Resize to fit preview window
            canvas_width = 580
            canvas_height = 380
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
            
            # Display preview
            preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            preview_canvas.image = photo  # Keep reference
            
            # Add info label
            info_label = tk.Label(preview_window, text=f"Auto Preview - Frame {self.current_second}s - {len(self.regions)} blur region(s)", 
                                font=("Arial", 10, "bold"))
            info_label.pack(pady=5)
            
            # Auto-close after 5 seconds (increased time)
            preview_window.after(5000, preview_window.destroy)
    
    def preview_video(self):
        """Manual preview video with blur effects applied"""
        if not self.video_path:
            messagebox.showerror("Error", "No video loaded")
            return
        
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to preview")
            return
        
        # Create a temporary preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Manual Preview - Blur Effects")
        preview_window.geometry("800x600")
        
        # Create canvas for preview
        preview_canvas = tk.Canvas(preview_window, bg="black")
        preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Get current frame and apply blur effects
        frame_number = self.current_second * self.video_info['fps']
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            # Apply blur effects to frame
            preview_frame = self.apply_blur_effects(frame)
            
            # Convert to PhotoImage
            preview_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(preview_frame)
            
            # Resize to fit preview window
            canvas_width = 780
            canvas_height = 580
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
            
            # Display preview
            preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            preview_canvas.image = photo  # Keep reference
            
            # Add info label
            info_label = tk.Label(preview_window, text=f"Manual Preview - Frame {self.current_second}s with {len(self.regions)} blur regions", 
                                font=("Arial", 12, "bold"))
            info_label.pack(pady=5)
            
            self.status_label.configure(text=f"Manual preview window opened - showing frame at {self.current_second}s")
        else:
            messagebox.showerror("Error", "Could not read frame for preview")
    
    def apply_blur_effects(self, frame):
        """Apply blur effects to a frame"""
        result_frame = frame.copy()
        
        for rect in self.regions:
            # Check if rectangle applies to current frame
            current_frame_num = self.current_second * self.video_info['fps']
            if rect['start_frame'] <= current_frame_num <= rect['end_frame']:
                x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
                
                # Ensure coordinates are within frame bounds
                x = max(0, min(x, frame.shape[1] - 1))
                y = max(0, min(y, frame.shape[0] - 1))
                w = max(1, min(w, frame.shape[1] - x))
                h = max(1, min(h, frame.shape[0] - y))
                
                # Extract region of interest
                roi = result_frame[y:y+h, x:x+w]
                
                if roi.size > 0:
                    # Get intensity and convert to opacity (0.1-1.0 range)
                    intensity = rect.get('intensity', 70)  # Default to 70 if not set
                    opacity = max(0.1, min(1.0, intensity / 100.0))
                    
                    # Apply blur based on type
                    if rect['blur_type'] == 'gaussian':
                        # Calculate kernel size based on opacity (3-51 range)
                        kernel_size = int(3 + (opacity * 48))
                        if kernel_size % 2 == 0:
                            kernel_size += 1
                        blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                    elif rect['blur_type'] == 'pixelate':
                        # Calculate pixelation level based on opacity (2-20 range)
                        pixel_size = max(2, int(2 + (opacity * 18)))
                        small = cv2.resize(roi, (max(1, w//pixel_size), max(1, h//pixel_size)))
                        blurred_roi = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
                    elif rect['blur_type'] == 'black_box':
                        blurred_roi = np.zeros_like(roi)
                    elif rect['blur_type'] == 'white_box':
                        blurred_roi = np.full_like(roi, 255)
                    else:
                        blurred_roi = roi
                    
                    # Apply opacity blending
                    result_frame[y:y+h, x:x+w] = cv2.addWeighted(roi, 1-opacity, blurred_roi, opacity, 0)
        
        return result_frame
    
    def export_summary(self):
        """Export video with blur effects applied"""
        if not self.video_path:
            messagebox.showerror("Error", "No video loaded")
            return
            
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to export")
            return
        
        # Ask for output video file
        file_path = filedialog.asksaveasfilename(
            title="Export Blurred Video",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("AVI files", "*.avi"), ("MOV files", "*.mov"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.status_label.configure(text="Processing video with blur effects... This may take a while.")
                self.root.update()
                
                # Convert dictionary regions to BlurRegion objects
                from blur_engine import BlurRegion, BlurType, PIIType
                
                blur_regions = []
                for rect in self.regions:
                    blur_region = BlurRegion(
                        x=rect['x'],
                        y=rect['y'],
                        width=rect['width'],
                        height=rect['height'],
                        blur_type=BlurType(rect['blur_type']),
                        intensity=rect.get('intensity', 70),
                        pii_type=PIIType(rect.get('pii_type', 'custom_text')),
                        start_frame=rect['start_frame'],
                        end_frame=rect['end_frame']
                    )
                    blur_regions.append(blur_region)
                
                # Use the blur engine to process the video
                results = self.blur_engine.process_video(
                    input_path=self.video_path,
                    output_path=file_path,
                    blur_regions=blur_regions,
                    auto_detect=False  # Use only manual regions
                )
                
                output_path = file_path if results['processing_successful'] else None
                
                if results['processing_successful'] and os.path.exists(file_path):
                    self.status_label.configure(text=f"Video exported successfully to {os.path.basename(file_path)}")
                    messagebox.showinfo("Success", f"Blurred video exported to:\n{file_path}")
                else:
                    error_msg = results.get('error', 'Unknown error occurred')
                    self.status_label.configure(text=f"Export failed: {error_msg}")
                    messagebox.showerror("Error", f"Failed to export video:\n{error_msg}")
                    
            except Exception as e:
                self.status_label.configure(text=f"Export error: {str(e)}")
                messagebox.showerror("Error", f"Export failed:\n{str(e)}")
                print(f"Export error: {e}")
    
    def export_text_summary(self):
        """Export regions summary as text file"""
        if not self.regions:
            messagebox.showwarning("Warning", "No rectangles to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Text Summary",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write("BLUR REGIONS SUMMARY\n")
                f.write("=" * 50 + "\n")
                f.write(f"Video: {os.path.basename(self.video_path)}\n")
                f.write(f"Total Rectangles: {len(self.regions)}\n")
                f.write(f"Video Duration: {self.video_info['duration_seconds']:.1f} seconds\n")
                f.write(f"Resolution: {self.video_info['width']}x{self.video_info['height']}\n")
                f.write(f"FPS: {self.video_info['fps']}\n\n")
                
                for i, rect in enumerate(self.regions, 1):
                    start_sec = rect['start_frame'] // self.video_info['fps']
                    end_sec = rect['end_frame'] // self.video_info['fps']
                    f.write(f"Rectangle {i}:\n")
                    f.write(f"  Position: ({rect['x']}, {rect['y']})\n")
                    f.write(f"  Size: {rect['width']}x{rect['height']}\n")
                    f.write(f"  Blur Type: {rect['blur_type']}\n")
                    intensity = rect.get('intensity', 70)
                    f.write(f"  Intensity: {intensity}%\n")
                    f.write(f"  Frame Range: {start_sec}-{end_sec} seconds\n")
                    f.write(f"  Frame Numbers: {rect['start_frame']}-{rect['end_frame']}\n\n")
            
            self.status_label.configure(text=f"Exported text summary to {os.path.basename(file_path)}")
            messagebox.showinfo("Success", f"Text summary exported to:\n{file_path}")
    
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
            # Convert to the format expected by blur engine
            regions_data = []
            for rect in self.regions:
                region = {
                    "x": rect['x'],
                    "y": rect['y'],
                    "width": rect['width'],
                    "height": rect['height'],
                    "blur_type": rect['blur_type'],
                    "intensity": rect.get('intensity', 70),
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
                        'intensity': region_data.get('intensity', 70),
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
        
        # Choose output file
        output_path = filedialog.asksaveasfilename(
            title="Save Processed Video",
            defaultextension=".mov",
            filetypes=[("Video files", "*.mov *.mp4"), ("All files", "*.*")]
        )
        
        if output_path:
            self.status_label.configure(text="Processing video...")
            self.root.update()
            
            try:
                # Convert to BlurRegion objects
                blur_regions = []
                for rect in self.regions:
                    region = BlurRegion(
                        x=rect['x'],
                        y=rect['y'],
                        width=rect['width'],
                        height=rect['height'],
                        blur_type=BlurType(rect['blur_type']),
                        intensity=rect.get('intensity', 70),
                        pii_type=PIIType(rect.get('pii_type', 'custom_text')),
                        start_frame=rect['start_frame'],
                        end_frame=rect['end_frame']
                    )
                    blur_regions.append(region)
                
                # Process video (no auto-detection, only manual regions)
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

def main():
    root = tk.Tk()
    app = SimpleBlurUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
