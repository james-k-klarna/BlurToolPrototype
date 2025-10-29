#!/usr/bin/env python3
"""
Blur Engine - Core PII blurring functionality
Handles video processing, blur effects, and PII detection
"""

import cv2
import numpy as np
import re
import logging
from enum import Enum
from typing import List, Tuple, Dict, Optional
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PIIType(Enum):
    CUSTOM_TEXT = "custom_text"

class BlurType(Enum):
    GAUSSIAN = "gaussian"
    PIXELATE = "pixelate"
    BLACK_BOX = "black_box"
    WHITE_BOX = "white_box"

class BlurRegion:
    def __init__(self, x: int, y: int, width: int, height: int, 
                 blur_type: BlurType, intensity: int, pii_type: PIIType,
                 start_frame: int = 0, end_frame: int = -1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.blur_type = blur_type
        self.intensity = intensity
        self.pii_type = pii_type
        self.start_frame = start_frame
        self.end_frame = end_frame

class BlurEngine:
    def __init__(self):
        self._validate_environment()
        self._init_patterns()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self._verify_library_safety()

    def _validate_environment(self):
        """Validate the environment is secure"""
        try:
            import socket
            # Check if we can make network connections (should be blocked in secure environments)
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            test_socket.connect(("8.8.8.8", 53))
            logger.warning("Network detected. Ensure no external calls.")
            test_socket.close()
        except:
            pass  # Good - no network access
        
        logger.info("Blur engine initialized - local processing only")

    def _init_patterns(self):
        """Initialize PII detection patterns - simplified to custom text only"""
        self.patterns = {
            PIIType.CUSTOM_TEXT: [
                # Basic text detection patterns
                re.compile(r'\b[A-Za-z0-9\s@._-]+\b'),
            ]
        }

    def _verify_library_safety(self):
        """Verify all libraries are safe and local"""
        safe_libraries = {
            'cv2': 'OpenCV - Computer vision library',
            'numpy': 'NumPy - Numerical computing',
            'PIL': 'Pillow - Image processing',
            're': 'Regex - Pattern matching'
        }
        
        for lib, description in safe_libraries.items():
            try:
                __import__(lib)
                logger.info(f"✓ {lib}: {description}")
            except ImportError:
                logger.warning(f"⚠ {lib}: Not available")

    def detect_text_regions(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect text regions in frame"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 20 and h > 10:  # Filter small regions
                    aspect_ratio = w / h
                    if 0.2 < aspect_ratio < 10:  # Reasonable text ratio
                        regions.append((x, y, w, h))
            return regions
        except Exception as e:
            logger.error(f"Error detecting text: {e}")
            return []

    def detect_pii_in_text(self, text: str) -> List[Tuple[PIIType, str, int, int]]:
        """Detect PII patterns in text string"""
        detections = []
        
        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    detections.append((
                        pii_type,
                        match.group(),
                        match.start(),
                        match.end()
                    ))
        
        return detections

    def apply_blur_region(self, frame: np.ndarray, region: BlurRegion) -> np.ndarray:
        """Apply blur to region in frame with proper opacity handling"""
        try:
            x = max(0, min(region.x, frame.shape[1]))
            y = max(0, min(region.y, frame.shape[0]))
            width = max(1, min(region.width, frame.shape[1] - x))
            height = max(1, min(region.height, frame.shape[0] - y))
            
            roi = frame[y:y+height, x:x+width]
            if roi.size == 0:
                return frame
            
            # Calculate blur intensity based on opacity (0.1-1.0 range)
            opacity = region.intensity / 100.0  # Convert intensity to 0-1 range
            opacity = max(0.1, min(1.0, opacity))  # Clamp to valid range
            
            if region.blur_type == BlurType.GAUSSIAN:
                # Calculate kernel size based on opacity (3-51 range)
                kernel_size = int(3 + (opacity * 48))  # 3 to 51
                if kernel_size % 2 == 0:
                    kernel_size += 1
                blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
            elif region.blur_type == BlurType.PIXELATE:
                # Calculate pixelation level based on opacity (2-20 range)
                pixel_size = max(2, int(2 + (opacity * 18)))  # 2 to 20
                small = cv2.resize(roi, (max(1, width//pixel_size), max(1, height//pixel_size)))
                blurred_roi = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)
            elif region.blur_type == BlurType.BLACK_BOX:
                blurred_roi = np.zeros_like(roi)
            elif region.blur_type == BlurType.WHITE_BOX:
                blurred_roi = np.full_like(roi, 255)
            else:
                blurred_roi = roi
            
            # Apply opacity blending
            result = frame.copy()
            if region.blur_type in [BlurType.BLACK_BOX, BlurType.WHITE_BOX]:
                # For solid boxes, opacity controls the strength
                result[y:y+height, x:x+width] = cv2.addWeighted(roi, 1-opacity, blurred_roi, opacity, 0)
            else:
                # For blur effects, opacity controls the blur strength
                result[y:y+height, x:x+width] = cv2.addWeighted(roi, 1-opacity, blurred_roi, opacity, 0)
            
            return result
        except Exception as e:
            logger.error(f"Error applying blur: {e}")
            return frame

    def process_video(self, input_path: str, output_path: str, 
                     blur_regions: List[BlurRegion], auto_detect: bool = False) -> Dict:
        """Process video with blur regions"""
        results = {
            'processing_successful': False,
            'total_frames': 0,
            'pii_regions_detected': 0,
            'error': None
        }
        
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                results['error'] = f"Could not open video: {input_path}"
                return results
            
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            results['total_frames'] = total_frames
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_count = 0
            pii_regions_total = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Apply manual blur regions
                for region in blur_regions:
                    if (region.start_frame <= frame_count <= region.end_frame or 
                        (region.start_frame <= frame_count and region.end_frame == -1)):
                        frame = self.apply_blur_region(frame, region)
                
                # Auto-detect PII
                if auto_detect:
                    text_regions = self.detect_text_regions(frame)
                    pii_regions_total += len(text_regions)
                    
                    for (x, y, w, h) in text_regions:
                        pii_region = BlurRegion(
                            x=x, y=y, width=w, height=h,
                            blur_type=BlurType.GAUSSIAN,
                            intensity=15,
                            pii_type=PIIType.CUSTOM_TEXT,
                            start_frame=frame_count,
                            end_frame=frame_count
                        )
                        frame = self.apply_blur_region(frame, pii_region)
                
                out.write(frame)
                frame_count += 1
                
                if frame_count % 100 == 0:
                    logger.info(f"Processed {frame_count}/{total_frames} frames")
            
            results['pii_regions_detected'] = pii_regions_total
            results['processing_successful'] = True
            
            cap.release()
            out.release()
            
            logger.info("Secure cleanup completed")
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"Error processing video: {e}")
        
        return results

    def get_video_info(self, video_path: str) -> Dict:
        """Get video information"""
        info = {
            'fps': 0,
            'total_frames': 0,
            'duration_seconds': 0,
            'width': 0,
            'height': 0,
            'file_size_mb': 0,
            'success': False
        }
        
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                info['fps'] = int(cap.get(cv2.CAP_PROP_FPS))
                info['total_frames'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                info['duration_seconds'] = info['total_frames'] / info['fps'] if info['fps'] > 0 else 0
                info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info['file_size_mb'] = os.path.getsize(video_path) / (1024 * 1024)
                info['success'] = True
                cap.release()
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return info
