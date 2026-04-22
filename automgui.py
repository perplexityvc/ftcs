import pyautogui
import cv2
import numpy as np
import time
import os
import json
import threading
import subprocess
import sys
from datetime import datetime
from skimage.metrics import structural_similarity as ssim
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

try:
    import pygetwindow as gw
except Exception:
    gw = None

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration class for automation settings."""
    
    # Directories
    SAVE_DIR = os.path.join(os.getcwd(), "captured_screens")
    CONFIG_FILE = "automation_config.json"
    TARGET_WINDOW_TITLE = ""
    
    # Timing
    SCROLL_DELAY = 1.0
    INITIAL_DELAY = 5.0
    ADAPTIVE_WAIT_CHECKS = 3
    ADAPTIVE_WAIT_INTERVAL = 0.3
    
    # Image comparison
    SSIM_TOLERANCE = 0.97
    
    # Safety limits
    MAX_PAGES_PER_SECTION = 100
    MAX_SECTIONS = 50
    MAX_CONSECUTIVE_IDENTICAL = 3

    # Stop condition for section switching
    TOP_REGION_RATIO = 0.33
    TOP_CHANGE_STOP_THRESHOLD = 0.20

    # Feature toggles
    REQUIRE_WINDOW_TITLE = True
    ENABLE_ADAPTIVE_WAIT = True
    ENABLE_UNCHANGED_SCREEN_STOP = True
    ENABLE_TOP_CHANGE_GUARD = True
    ENABLE_POST_PROCESSING = True
    ENABLE_IMAGE_PREPROCESSING = True
    DISABLE_PROCESSING = False
    
    @classmethod
    def load_from_file(cls):
        """Load configuration from JSON file if it exists."""
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                    for key, value in config_data.items():
                        if hasattr(cls, key.upper()):
                            setattr(cls, key.upper(), value)
            except Exception:
                pass
    
    @classmethod
    def save_to_file(cls):
        """Save current configuration to JSON file."""
        config_data = {
            'save_dir': cls.SAVE_DIR,
            'target_window_title': cls.TARGET_WINDOW_TITLE,
            'scroll_delay': cls.SCROLL_DELAY,
            'initial_delay': cls.INITIAL_DELAY,
            'ssim_tolerance': cls.SSIM_TOLERANCE,
            'max_pages_per_section': cls.MAX_PAGES_PER_SECTION,
            'max_sections': cls.MAX_SECTIONS,
            'max_consecutive_identical': cls.MAX_CONSECUTIVE_IDENTICAL,
            'adaptive_wait_checks': cls.ADAPTIVE_WAIT_CHECKS,
            'adaptive_wait_interval': cls.ADAPTIVE_WAIT_INTERVAL,
            'top_region_ratio': cls.TOP_REGION_RATIO,
            'top_change_stop_threshold': cls.TOP_CHANGE_STOP_THRESHOLD,
            'require_window_title': cls.REQUIRE_WINDOW_TITLE,
            'enable_adaptive_wait': cls.ENABLE_ADAPTIVE_WAIT,
            'enable_unchanged_screen_stop': cls.ENABLE_UNCHANGED_SCREEN_STOP,
            'enable_top_change_guard': cls.ENABLE_TOP_CHANGE_GUARD,
            'enable_post_processing': cls.ENABLE_POST_PROCESSING,
            'enable_image_preprocessing': cls.ENABLE_IMAGE_PREPROCESSING,
            'disable_processing': cls.DISABLE_PROCESSING,
        }
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

class ImageComparator:
    """Handles image comparison with multiple strategies."""
    
    def __init__(self, tolerance=0.97):
        self.tolerance = tolerance
        self.comparison_count = 0
    
    def compare(self, img1, img2):
        """Compare two images using pixel-perfect and SSIM checks."""
        self.comparison_count += 1
        
        if img1.shape != img2.shape:
            return False, "dimension_check", 0.0
        
        if np.array_equal(img1, img2):
            return True, "pixel_perfect", 1.0
        
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        score, _ = ssim(gray1, gray2, full=True, data_range=255)
        is_similar = score >= self.tolerance
        
        return is_similar, "ssim", score


class ScreenCapture:
    """Handles screenshot capture and saving."""
    
    def __init__(self, save_dir, target_window_title=""):
        self.save_dir = save_dir
        self.target_window_title = target_window_title or ""
        self.ensure_directory()
    
    def ensure_directory(self):
        """Create save directory if it doesn't exist."""
        os.makedirs(self.save_dir, exist_ok=True)
    
    def capture(self):
        """Take a screenshot and return as OpenCV image."""
        region = self.get_capture_region()
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def get_capture_region(self):
        """Get screenshot region for selected window."""
        window_title = (self.target_window_title or "").strip()
        if not window_title:
            return None

        if gw is None:
            raise RuntimeError("pygetwindow is required for window-only capture")

        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            raise RuntimeError(f"Target window not found: {window_title}")

        selected = None
        for win in windows:
            if getattr(win, 'isMinimized', False):
                continue
            width = int(getattr(win, 'width', 0))
            height = int(getattr(win, 'height', 0))
            if width > 0 and height > 0:
                selected = win
                break

        if selected is None:
            raise RuntimeError(f"Target window is minimized or invalid: {window_title}")

        left = int(getattr(selected, 'left', 0))
        top = int(getattr(selected, 'top', 0))
        width = int(getattr(selected, 'width', 0))
        height = int(getattr(selected, 'height', 0))

        if width <= 0 or height <= 0:
            raise RuntimeError(f"Target window has invalid bounds: {window_title}")

        screen_width, screen_height = pyautogui.size()
        right = min(left + width, screen_width)
        bottom = min(top + height, screen_height)
        left = max(left, 0)
        top = max(top, 0)
        width = max(1, right - left)
        height = max(1, bottom - top)

        return (left, top, width, height)
    
    def save(self, image, filename):
        """Save image to disk with verification."""
        filepath = os.path.join(self.save_dir, filename)
        
        try:
            success = cv2.imwrite(filepath, image)
            if success and os.path.exists(filepath):
                return True, os.path.getsize(filepath)
            return False, 0
        except Exception:
            return False, 0
    
    def wait_for_screen_stability(self, delay=0.5, checks=3):
        """Wait for screen to stabilize."""
        prev_img = self.capture()
        stable_count = 0
        
        for _ in range(checks):
            time.sleep(delay)
            new_img = self.capture()
            
            if np.array_equal(prev_img, new_img):
                stable_count += 1
            else:
                stable_count = 0
            
            prev_img = new_img
            
            if stable_count >= 2:
                return True
        
        return True


# ============================================================================
# AUTOMATION ENGINE
# ============================================================================

class AutomationEngine:
    """Main automation engine for screen capture."""
    
    def __init__(self, config, log_callback=None):
        self.config = config
        self.log_callback = log_callback
        self.capture = ScreenCapture(config.SAVE_DIR, config.TARGET_WINDOW_TITLE)
        self.comparator = ImageComparator(tolerance=config.SSIM_TOLERANCE)
        
        self.section_count = 0
        self.is_running = False
        self.should_stop = False
        
        self.stats = {
            'start_time': None,
            'sections': 0,
            'pages': 0,
            'comparisons': 0
        }
    
    def log(self, message, level="INFO"):
        """Log message through callback if available."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        
        if self.log_callback:
            self.log_callback(formatted_msg)
        else:
            print(formatted_msg)
    
    def initialize(self):
        """Initialize automation with countdown."""
        self.log("=" * 60)
        self.log("SCREEN CAPTURE AUTOMATION STARTED")
        self.log("=" * 60)
        self.log(f"Save directory: {self.config.SAVE_DIR}")
        if getattr(self.config, 'TARGET_WINDOW_TITLE', '').strip():
            self.log(f"Target window: {self.config.TARGET_WINDOW_TITLE}")
        else:
            self.log("Target window: FULL SCREEN")
        self.log(f"SSIM tolerance: {self.config.SSIM_TOLERANCE}")
        self.log(f"Max pages/section: {self.config.MAX_PAGES_PER_SECTION}")
        self.log(f"Max sections: {self.config.MAX_SECTIONS}")
        self.log("")
        self.log("PLEASE FOCUS THE TARGET WINDOW NOW!")
        
        for i in range(int(self.config.INITIAL_DELAY), 0, -1):
            if self.should_stop:
                return False
            self.log(f"Starting in {i} seconds...")
            time.sleep(1)
        
        self.log("Starting automation NOW!")
        return True
    
    def simulate_key_and_wait(self, key):
        """Simulate key press and wait for screen to stabilize."""
        pyautogui.press(key)
        time.sleep(self.config.SCROLL_DELAY)
        
        if (
            not getattr(self.config, 'DISABLE_PROCESSING', False)
            and getattr(self.config, 'ENABLE_ADAPTIVE_WAIT', True)
            and self.config.ADAPTIVE_WAIT_CHECKS > 0
        ):
            self.capture.wait_for_screen_stability(
                delay=self.config.ADAPTIVE_WAIT_INTERVAL,
                checks=self.config.ADAPTIVE_WAIT_CHECKS
            )
    
    def process_section(self):
        """Process a single section by paging through it."""
        self.section_count += 1
        page_count = 1
        consecutive_identical = 0
        
        self.log("")
        self.log(f"{'='*60}")
        self.log(f"SECTION {self.section_count}")
        self.log(f"{'='*60}")
        
        # Capture first page
        current_img = self.capture.capture()
        filename = f"section_{self.section_count:03d}_page_{page_count:03d}.png"
        
        success, size = self.capture.save(current_img, filename)
        if not success:
            self.log("Failed to save first page, aborting section", "ERROR")
            return False
        
        self.log(f"Saved: {filename} ({size} bytes)")
        self.stats['pages'] += 1
        last_page_img = current_img
        
        # Page through section
        while page_count < self.config.MAX_PAGES_PER_SECTION and not self.should_stop:
            # Simulate PageDown
            self.simulate_key_and_wait('pagedown')
            
            # Capture new screen
            new_img = self.capture.capture()
            
            if not getattr(self.config, 'DISABLE_PROCESSING', False):
                # Compare images
                is_equal, method, score = self.comparator.compare(last_page_img, new_img)
                self.stats['comparisons'] += 1

                if is_equal and getattr(self.config, 'ENABLE_UNCHANGED_SCREEN_STOP', True):
                    consecutive_identical += 1
                    self.log(f"Screen unchanged ({consecutive_identical}/"
                           f"{self.config.MAX_CONSECUTIVE_IDENTICAL})")

                    if consecutive_identical >= self.config.MAX_CONSECUTIVE_IDENTICAL:
                        self.log("End of section detected (screen stopped changing)")
                        break
                else:
                    consecutive_identical = 0
                    page_count += 1
                    self.stats['pages'] += 1

                    filename = f"section_{self.section_count:03d}_page_{page_count:03d}.png"
                    success, size = self.capture.save(new_img, filename)

                    if success:
                        self.log(f"Saved: {filename} ({size} bytes)")
                    else:
                        self.log(f"Failed to save {filename}", "WARNING")

                    last_page_img = new_img
            else:
                page_count += 1
                self.stats['pages'] += 1

                filename = f"section_{self.section_count:03d}_page_{page_count:03d}.png"
                success, size = self.capture.save(new_img, filename)

                if success:
                    self.log(f"Saved: {filename} ({size} bytes)")
                else:
                    self.log(f"Failed to save {filename}", "WARNING")

                last_page_img = new_img
        
        if page_count >= self.config.MAX_PAGES_PER_SECTION:
            self.log(f"Reached max pages ({self.config.MAX_PAGES_PER_SECTION})", "WARNING")
        
        return last_page_img
    
    def try_next_section(self, last_section_img):
        """Attempt to move to next section."""
        self.log("")
        self.log("Attempting to move to next section (pressing ENTER)...")
        
        self.simulate_key_and_wait('enter')
        
        next_img = self.capture.capture()

        if getattr(self.config, 'DISABLE_PROCESSING', False):
            self.log("Processing disabled: skipping section-change comparison")
            return True

        # Guardrail: stop if top region changes too much
        if getattr(self.config, 'ENABLE_TOP_CHANGE_GUARD', True):
            top_change_ratio = self.calculate_top_region_change_ratio(last_section_img, next_img)
            threshold = float(getattr(self.config, 'TOP_CHANGE_STOP_THRESHOLD', 0.20))
            if top_change_ratio > threshold:
                self.log(
                    f"Top {int(getattr(self.config, 'TOP_REGION_RATIO', 0.33) * 100)}% changed "
                    f"by {top_change_ratio * 100:.1f}% (> {threshold * 100:.1f}%). Stopping capture.",
                    "WARNING",
                )
                self.should_stop = True
                return False

        is_same, method, score = self.comparator.compare(last_section_img, next_img)
        self.stats['comparisons'] += 1
        
        if is_same:
            self.log("No new section loaded (screen unchanged)")
            return False
        
        self.log("New section detected!")
        return True

    def calculate_top_region_change_ratio(self, img1, img2):
        """Return changed-pixel ratio in top region between two images."""
        if img1 is None or img2 is None or img1.shape != img2.shape:
            return 1.0

        top_ratio = float(getattr(self.config, 'TOP_REGION_RATIO', 0.33))
        top_ratio = min(max(top_ratio, 0.01), 1.0)

        height = img1.shape[0]
        top_height = max(1, int(height * top_ratio))

        region1 = img1[:top_height, :]
        region2 = img2[:top_height, :]

        gray1 = cv2.cvtColor(region1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(region2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)

        changed_pixels = np.count_nonzero(diff > 25)
        total_pixels = diff.size
        if total_pixels == 0:
            return 0.0

        return changed_pixels / total_pixels
    
    def stop(self):
        """Signal the automation to stop."""
        self.should_stop = True
        self.log("Stop requested by user...", "WARNING")
    
    def run(self):
        """Main automation loop."""
        self.is_running = True
        self.should_stop = False
        self.stats['start_time'] = datetime.now()
        
        try:
            if not self.initialize():
                self.log("Initialization cancelled", "WARNING")
                return
            
            while self.section_count < self.config.MAX_SECTIONS and not self.should_stop:
                last_section_img = self.process_section()
                
                if last_section_img is False:
                    self.log("Section processing failed, stopping", "ERROR")
                    break
                
                self.stats['sections'] = self.section_count
                
                if not self.try_next_section(last_section_img):
                    break
            
            if self.section_count >= self.config.MAX_SECTIONS:
                self.log(f"Reached max sections limit ({self.config.MAX_SECTIONS})", "WARNING")
            
            self.print_summary()
            
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            self.print_summary()
        finally:
            self.is_running = False
    
    def print_summary(self):
        """Print automation statistics."""
        if self.stats['start_time']:
            elapsed = datetime.now() - self.stats['start_time']
        else:
            elapsed = "N/A"
        
        self.log("")
        self.log("=" * 60)
        self.log("AUTOMATION COMPLETE")
        self.log("=" * 60)
        self.log(f"Sections processed: {self.stats['sections']}")
        self.log(f"Pages captured: {self.stats['pages']}")
        self.log(f"Image comparisons: {self.stats['comparisons']}")
        self.log(f"Total time: {elapsed}")
        self.log(f"Screenshots saved to: {self.config.SAVE_DIR}")
        self.log("=" * 60)


# ============================================================================
# GUI APPLICATION
# ============================================================================

class AutomationGUI:
    """GUI application for screen capture automation."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Capture Automation")
        self.root.geometry("900x700")
        
        # Load configuration
        Config.load_from_file()
        
        # Automation engine
        self.engine = None
        self.automation_thread = None
        
        # PyAutoGUI failsafe
        pyautogui.FAILSAFE = True
        
        # Build UI
        self.create_widgets()
        self.load_config_to_ui()
    
    def create_widgets(self):
        """Create all GUI widgets."""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # === Configuration Section ===
        config_notebook = ttk.Notebook(main_frame)
        config_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        config_frame = ttk.Frame(config_notebook, padding="10")
        features_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(config_frame, text="Capture Settings")
        config_notebook.add(features_frame, text="Feature Toggles")

        config_frame.columnconfigure(1, weight=1)
        features_frame.columnconfigure(0, weight=1)
        
        # Save Directory
        ttk.Label(config_frame, text="Save Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.save_dir_var = tk.StringVar(value=Config.SAVE_DIR)
        dir_frame = ttk.Frame(config_frame)
        dir_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        dir_frame.columnconfigure(0, weight=1)
        ttk.Entry(dir_frame, textvariable=self.save_dir_var).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory, width=10).grid(row=0, column=1)

        # Target Window Title
        ttk.Label(config_frame, text="Target Window:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_window_var = tk.StringVar(value=Config.TARGET_WINDOW_TITLE)
        target_frame = ttk.Frame(config_frame)
        target_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        target_frame.columnconfigure(0, weight=1)
        ttk.Entry(target_frame, textvariable=self.target_window_var).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(target_frame, text="Select...", command=self.use_active_window, width=10).grid(row=0, column=1)
        
        # Scroll Delay
        ttk.Label(config_frame, text="Scroll Delay (sec):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.scroll_delay_var = tk.DoubleVar(value=Config.SCROLL_DELAY)
        ttk.Spinbox(config_frame, from_=0.1, to=5.0, increment=0.1, 
                   textvariable=self.scroll_delay_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Initial Delay
        ttk.Label(config_frame, text="Initial Delay (sec):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.initial_delay_var = tk.DoubleVar(value=Config.INITIAL_DELAY)
        ttk.Spinbox(config_frame, from_=1, to=30, increment=1, 
                   textvariable=self.initial_delay_var, width=15).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # SSIM Tolerance
        ttk.Label(config_frame, text="SSIM Tolerance:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.ssim_tolerance_var = tk.DoubleVar(value=Config.SSIM_TOLERANCE)
        ttk.Spinbox(config_frame, from_=0.80, to=0.999, increment=0.01, 
                   textvariable=self.ssim_tolerance_var, width=15, format="%.3f").grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Max Pages Per Section
        ttk.Label(config_frame, text="Max Pages/Section:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.max_pages_var = tk.IntVar(value=Config.MAX_PAGES_PER_SECTION)
        ttk.Spinbox(config_frame, from_=10, to=500, increment=10, 
                   textvariable=self.max_pages_var, width=15).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Max Sections
        ttk.Label(config_frame, text="Max Sections:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.max_sections_var = tk.IntVar(value=Config.MAX_SECTIONS)
        ttk.Spinbox(config_frame, from_=1, to=200, increment=1, 
                   textvariable=self.max_sections_var, width=15).grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Max Consecutive Identical
        ttk.Label(config_frame, text="Max Consecutive Identical:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.max_consecutive_var = tk.IntVar(value=Config.MAX_CONSECUTIVE_IDENTICAL)
        ttk.Spinbox(config_frame, from_=1, to=10, increment=1, 
                   textvariable=self.max_consecutive_var, width=15).grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Config buttons
        config_btn_frame = ttk.Frame(config_frame)
        config_btn_frame.grid(row=8, column=0, columnspan=2, pady=10)
        ttk.Button(config_btn_frame, text="Save Config", 
                  command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="Load Config", 
                  command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="Reset to Defaults", 
                  command=self.reset_config).pack(side=tk.LEFT, padx=5)

        # === Feature Toggles Tab ===
        self.require_window_var = tk.BooleanVar(value=Config.REQUIRE_WINDOW_TITLE)
        self.adaptive_wait_enabled_var = tk.BooleanVar(value=Config.ENABLE_ADAPTIVE_WAIT)
        self.unchanged_stop_enabled_var = tk.BooleanVar(value=Config.ENABLE_UNCHANGED_SCREEN_STOP)
        self.top_guard_enabled_var = tk.BooleanVar(value=Config.ENABLE_TOP_CHANGE_GUARD)
        self.post_processing_enabled_var = tk.BooleanVar(value=Config.ENABLE_POST_PROCESSING)
        self.image_preprocessing_enabled_var = tk.BooleanVar(value=Config.ENABLE_IMAGE_PREPROCESSING)
        self.disable_processing_var = tk.BooleanVar(value=Config.DISABLE_PROCESSING)

        ttk.Checkbutton(
            features_frame,
            text="Require target window title before capture",
            variable=self.require_window_var,
        ).grid(row=0, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Enable adaptive wait after key press",
            variable=self.adaptive_wait_enabled_var,
        ).grid(row=1, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Stop section when screen remains unchanged",
            variable=self.unchanged_stop_enabled_var,
        ).grid(row=2, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Enable top-region change guard",
            variable=self.top_guard_enabled_var,
        ).grid(row=3, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Run OCR extraction after capture",
            variable=self.post_processing_enabled_var,
        ).grid(row=4, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Enable image preprocessing for OCR",
            variable=self.image_preprocessing_enabled_var,
        ).grid(row=5, column=0, sticky=tk.W, pady=4)

        ttk.Checkbutton(
            features_frame,
            text="Disable processing altogether (capture-only mode)",
            variable=self.disable_processing_var,
        ).grid(row=6, column=0, sticky=tk.W, pady=8)

        ttk.Label(
            features_frame,
            text="Capture-only mode disables adaptive waits, stop guards, and OCR post-processing.",
        ).grid(row=7, column=0, sticky=tk.W, pady=(2, 0))
        
        # === Control Section ===
        control_frame = ttk.LabelFrame(main_frame, text="Control", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start Capture", 
                                       command=self.start_automation, width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Capture", 
                                      command=self.stop_automation, width=20, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(control_frame, text="Clear Log", 
                                       command=self.clear_log, width=15)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, 
                                font=('Arial', 10, 'bold'))
        status_label.pack(side=tk.RIGHT, padx=10)
        
        # === Log Section ===
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                  wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initial message
        self.log_message("Screen Capture Automation GUI initialized")
        self.log_message("Configure settings above and click 'Start Capture' to begin")
        self.log_message(f"PyAutoGUI Failsafe: Move mouse to top-left corner to emergency stop")
    
    def browse_directory(self):
        """Open directory browser dialog."""
        directory = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if directory:
            self.save_dir_var.set(directory)

    def use_active_window(self):
        """Open a picker to explicitly choose the target window."""
        if gw is None:
            messagebox.showerror("Error", "pygetwindow is required to select a target window")
            return

        try:
            active = gw.getActiveWindow()
            active_title = active.title.strip() if active and active.title else ""
            titles = self.get_selectable_window_titles()
        except Exception as e:
            messagebox.showerror("Error", f"Could not read available windows: {e}")
            return

        if not titles:
            messagebox.showwarning("Warning", "No selectable application windows found")
            return

        title = self.show_window_picker(titles, active_title)
        if not title:
            return

        self.target_window_var.set(title)
        self.log_message(f"Target window set to: {title}")

    def get_selectable_window_titles(self):
        """Return unique non-empty window titles for explicit selection."""
        titles = []
        for title in gw.getAllTitles():
            cleaned = title.strip()
            if cleaned:
                titles.append(cleaned)

        unique_titles = []
        for title in titles:
            if title not in unique_titles:
                unique_titles.append(title)

        return unique_titles

    def show_window_picker(self, titles, active_title=""):
        """Show a modal picker and return selected title or None."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Target Window")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("620x420")

        ttk.Label(dialog, text="Choose the application window to capture:").pack(anchor=tk.W, padx=10, pady=(10, 6))

        listbox = tk.Listbox(dialog, exportselection=False)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        for title in titles:
            listbox.insert(tk.END, title)

        if active_title and active_title in titles:
            idx = titles.index(active_title)
            listbox.selection_set(idx)
            listbox.see(idx)
        elif titles:
            listbox.selection_set(0)

        selected = {'value': None}

        def confirm_selection():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a window title", parent=dialog)
                return
            selected['value'] = titles[selection[0]]
            dialog.destroy()

        def cancel_selection():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="Cancel", command=cancel_selection).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Select", command=confirm_selection).pack(side=tk.RIGHT, padx=(0, 6))

        listbox.bind('<Double-Button-1>', lambda _event: confirm_selection())
        dialog.protocol("WM_DELETE_WINDOW", cancel_selection)
        self.root.wait_window(dialog)

        return selected['value']
    
    def log_message(self, message):
        """Add message to log text widget."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def thread_safe_log_message(self, message):
        """Add a log message safely from any thread."""
        self.root.after(0, lambda: self.log_message(message))

    def thread_safe_set_status(self, message):
        """Update status safely from any thread."""
        self.root.after(0, lambda: self.status_var.set(message))
    
    def clear_log(self):
        """Clear the log text widget."""
        self.log_text.delete(1.0, tk.END)
    
    def update_config_from_ui(self):
        """Update Config class from UI values."""
        Config.SAVE_DIR = self.save_dir_var.get()
        Config.TARGET_WINDOW_TITLE = self.target_window_var.get().strip()
        Config.SCROLL_DELAY = self.scroll_delay_var.get()
        Config.INITIAL_DELAY = self.initial_delay_var.get()
        Config.SSIM_TOLERANCE = self.ssim_tolerance_var.get()
        Config.MAX_PAGES_PER_SECTION = self.max_pages_var.get()
        Config.MAX_SECTIONS = self.max_sections_var.get()
        Config.MAX_CONSECUTIVE_IDENTICAL = self.max_consecutive_var.get()
        Config.REQUIRE_WINDOW_TITLE = self.require_window_var.get()
        Config.ENABLE_ADAPTIVE_WAIT = self.adaptive_wait_enabled_var.get()
        Config.ENABLE_UNCHANGED_SCREEN_STOP = self.unchanged_stop_enabled_var.get()
        Config.ENABLE_TOP_CHANGE_GUARD = self.top_guard_enabled_var.get()
        Config.ENABLE_POST_PROCESSING = self.post_processing_enabled_var.get()
        Config.ENABLE_IMAGE_PREPROCESSING = self.image_preprocessing_enabled_var.get()
        Config.DISABLE_PROCESSING = self.disable_processing_var.get()
    
    def load_config_to_ui(self):
        """Load Config values to UI."""
        self.save_dir_var.set(Config.SAVE_DIR)
        self.target_window_var.set(Config.TARGET_WINDOW_TITLE)
        self.scroll_delay_var.set(Config.SCROLL_DELAY)
        self.initial_delay_var.set(Config.INITIAL_DELAY)
        self.ssim_tolerance_var.set(Config.SSIM_TOLERANCE)
        self.max_pages_var.set(Config.MAX_PAGES_PER_SECTION)
        self.max_sections_var.set(Config.MAX_SECTIONS)
        self.max_consecutive_var.set(Config.MAX_CONSECUTIVE_IDENTICAL)
        self.require_window_var.set(Config.REQUIRE_WINDOW_TITLE)
        self.adaptive_wait_enabled_var.set(Config.ENABLE_ADAPTIVE_WAIT)
        self.unchanged_stop_enabled_var.set(Config.ENABLE_UNCHANGED_SCREEN_STOP)
        self.top_guard_enabled_var.set(Config.ENABLE_TOP_CHANGE_GUARD)
        self.post_processing_enabled_var.set(Config.ENABLE_POST_PROCESSING)
        self.image_preprocessing_enabled_var.set(Config.ENABLE_IMAGE_PREPROCESSING)
        self.disable_processing_var.set(Config.DISABLE_PROCESSING)
    
    def save_config(self):
        """Save current configuration to file."""
        self.update_config_from_ui()
        Config.save_to_file()
        messagebox.showinfo("Success", f"Configuration saved to {Config.CONFIG_FILE}")
        self.log_message(f"Configuration saved to {Config.CONFIG_FILE}")
    
    def load_config(self):
        """Load configuration from file."""
        Config.load_from_file()
        self.load_config_to_ui()
        messagebox.showinfo("Success", f"Configuration loaded from {Config.CONFIG_FILE}")
        self.log_message(f"Configuration loaded from {Config.CONFIG_FILE}")
    
    def reset_config(self):
        """Reset configuration to defaults."""
        if messagebox.askyesno("Confirm Reset", "Reset all settings to defaults?"):
            Config.SAVE_DIR = os.path.join(os.getcwd(), "captured_screens")
            Config.TARGET_WINDOW_TITLE = ""
            Config.SCROLL_DELAY = 1.0
            Config.INITIAL_DELAY = 5.0
            Config.SSIM_TOLERANCE = 0.97
            Config.MAX_PAGES_PER_SECTION = 100
            Config.MAX_SECTIONS = 50
            Config.MAX_CONSECUTIVE_IDENTICAL = 3
            Config.TOP_REGION_RATIO = 0.33
            Config.TOP_CHANGE_STOP_THRESHOLD = 0.20
            Config.REQUIRE_WINDOW_TITLE = True
            Config.ENABLE_ADAPTIVE_WAIT = True
            Config.ENABLE_UNCHANGED_SCREEN_STOP = True
            Config.ENABLE_TOP_CHANGE_GUARD = True
            Config.ENABLE_POST_PROCESSING = True
            Config.ENABLE_IMAGE_PREPROCESSING = True
            Config.DISABLE_PROCESSING = False
            self.load_config_to_ui()
            self.log_message("Configuration reset to defaults")
    
    def start_automation(self):
        """Start the automation in a separate thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            messagebox.showwarning("Warning", "Automation is already running!")
            return
        
        # Update config from UI
        self.update_config_from_ui()
        
        # Validate save directory
        if not self.save_dir_var.get():
            messagebox.showerror("Error", "Please specify a save directory!")
            return

        if self.require_window_var.get() and not self.target_window_var.get().strip():
            messagebox.showerror("Error", "Please set a target window title (window-only capture is required)")
            return
        
        # Create engine with log callback
        self.engine = AutomationEngine(Config, log_callback=self.thread_safe_log_message)
        
        # Update UI state
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Running...")
        
        # Start automation in separate thread
        self.automation_thread = threading.Thread(target=self.run_automation, daemon=True)
        self.automation_thread.start()
        
        self.log_message("Automation started")
    
    def run_automation(self):
        """Run automation (called in separate thread)."""
        try:
            self.engine.run()
            if getattr(Config, 'DISABLE_PROCESSING', False):
                self.thread_safe_log_message("Processing disabled: skipping OCR extraction")
            elif not getattr(Config, 'ENABLE_POST_PROCESSING', True):
                self.thread_safe_log_message("Post-processing disabled: skipping OCR extraction")
            else:
                self.run_extraction_after_capture()
        finally:
            # Update UI when done (must use after to run in main thread)
            self.root.after(0, self.automation_finished)

    def run_extraction_after_capture(self):
        """Run extract.py batch OCR after screenshots are captured."""
        capture_dir = Config.SAVE_DIR
        if not capture_dir or not os.path.isdir(capture_dir):
            self.thread_safe_log_message("Skipping OCR extraction: capture directory is missing")
            return

        png_files = [name for name in os.listdir(capture_dir) if name.lower().endswith('.png')]
        if not png_files:
            self.thread_safe_log_message("Skipping OCR extraction: no PNG files found in capture directory")
            return

        extract_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extract.py')
        if not os.path.exists(extract_script):
            self.thread_safe_log_message("Skipping OCR extraction: extract.py not found")
            return

        output_csv = os.path.join(capture_dir, 'combined_output.csv')
        cmd = [sys.executable, extract_script, '--batch', capture_dir, output_csv]
        if not getattr(Config, 'ENABLE_IMAGE_PREPROCESSING', True):
            cmd.append('--no-preprocess')

        self.thread_safe_set_status("Running OCR extraction...")
        self.thread_safe_log_message("Starting OCR extraction on captured screenshots...")
        self.thread_safe_log_message(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as exc:
            self.thread_safe_log_message(f"OCR extraction failed to start: {exc}")
            return

        if result.returncode == 0:
            self.thread_safe_log_message(f"OCR extraction completed. Output: {output_csv}")
            if result.stdout.strip():
                self.thread_safe_log_message("Extractor output (last lines):")
                for line in result.stdout.strip().splitlines()[-8:]:
                    self.thread_safe_log_message(line)
        else:
            self.thread_safe_log_message(f"OCR extraction failed with exit code {result.returncode}")
            if result.stderr.strip():
                self.thread_safe_log_message("Extractor error output:")
                for line in result.stderr.strip().splitlines()[-8:]:
                    self.thread_safe_log_message(line)
    
    def automation_finished(self):
        """Called when automation completes."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Ready")
    
    def stop_automation(self):
        """Stop the running automation."""
        if self.engine and self.engine.is_running:
            self.engine.stop()
            self.log_message("Stop signal sent to automation engine")
            self.status_var.set("Stopping...")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = AutomationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
