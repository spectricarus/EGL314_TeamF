import os
import cv2
import time
import shutil
import zipfile
import subprocess
import tkinter as tk
from tkinter import Label, Button, ttk
from datetime import datetime

import qrcode
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    from pymatting import estimate_alpha_cf
    PYMATTING_AVAILABLE = True
except ImportError:
    PYMATTING_AVAILABLE = False

from style import (
    BG_COLOR,
    PANEL_COLOR,
    TEXT_COLOR,
    MUTED_TEXT_COLOR,
    SELECTED_COLOR,
    BUTTON_DARK,
    BUTTON_TEXT,
    CAPTURE_COLOR,
    CONFIRM_COLOR,
    RETAKE_COLOR,
    PREVIEW_BG,
    TITLE_FONT,
    LABEL_FONT,
    BUTTON_FONT,
    BIG_BUTTON_FONT,
)


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_DIR = os.path.join(BASE_DIR, "assets", "backgrounds")
SAVE_FOLDER = os.path.join(BASE_DIR, "saved_images")
QR_SAVE_DIR = os.path.join(BASE_DIR, "qrcodes")

os.makedirs(BACKGROUND_DIR, exist_ok=True)
os.makedirs(SAVE_FOLDER, exist_ok=True)
os.makedirs(QR_SAVE_DIR, exist_ok=True)

# rclone remote must already be configured (rclone config) — change these two
# to match what you set up when you tested with test.txt.
RCLONE_REMOTE = "gdrive"
RCLONE_REMOTE_FOLDER = "Photobooth"

CAMERA_DEVICE = "/dev/video0"

# Live preview feed resolution (continuous, needs to stay smooth)
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080

# Requested resolution for the actual still photo only - higher than the
# live feed on purpose. Capturing at 4K and downscaling to the final
# OUTPUT size gives more processing headroom and a cleaner downscaled
# result than capturing natively at OUTPUT resolution. Falls back safely
# if the camera doesn't actually support this (common webcam/V4L2
# behavior: it just clamps to its nearest supported resolution).
SNAPSHOT_WIDTH = 3840
SNAPSHOT_HEIGHT = 2160

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Auto-delete whole output session after 15 minutes
AUTO_DELETE_MS = 15 * 60 * 1000

# Reserved height for the top settings bar, subtracted from preview budgets
# below so nothing overlaps it.
TOP_BAR_HEIGHT = 34

# YOLO detection box expansion - how much padding (as a fraction of box
# width/height) to add before cropping and feeding to MediaPipe, so hair
# sticking up past the box or feet right at the edge don't get clipped.
BOX_MARGIN_FRACTION = 0.18

# MediaPipe mask tuning (same as V3's original soft-alpha approach, now
# applied per-person-crop instead of the full frame).
ALPHA_LOW = 0.28
ALPHA_HIGH = 0.75

# Focused hair-region matting refinement (on top of each person's already
# fast MediaPipe crop mask). The refined region is found adaptively from
# where MediaPipe's own mask is uncertain (see get_uncertain_region_bbox),
# not a fixed fraction - this is what makes it work regardless of hair
# length/style rather than assuming a fixed proportion of the crop.

# Hair region gets downscaled to at most this many pixels on the long side
# before pymatting's closed-form solve, then upscaled back - keeps the
# per-person cost small regardless of photo resolution.
MATTING_MAX_DIM = 200

# Matting never fully replaces MediaPipe's original alpha - this caps how
# much weight the matting solve can have (1.0 = full replacement, lower =
# blended with the original as a safety net). Closed-form matting's local-
# color-affinity assumption is more fragile under harsh/uneven lighting
# (strong highlights, hard shadows), and can over-smooth fine hair detail
# in exactly those conditions. A partial blend limits how flat a bad solve
# can make things look, without giving up the improvement in good lighting.
MATTING_BLEND_STRENGTH = 0.7


class PhotoboothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photobooth")
        self.root.configure(bg=BG_COLOR)
        self.root.attributes("-fullscreen", True)

        # Force 1:1 pixel scaling. Some Raspberry Pi OS + touchscreen setups
        # leave Tk's internal scaling factor mismatched with the real display,
        # which shows up as touches only registering near a button's exact
        # center instead of anywhere on it. If buttons are still imprecise
        # after this, the mismatch is likely at the touchscreen driver level
        # (see the note below).
        self.root.tk.call("tk", "scaling", 1.0)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.cap = None
        self.preview_running = False
        self.countdown_number = None

        self.current_frame = None      # full-resolution camera frame
        self.captured_frame = None     # full-resolution still photo

        self.tk_preview_image = None
        self.tk_result_image = None

        self.backgrounds = self.load_backgrounds()

        self.session_folder = None
        self.output_files = []
        self.selected_outputs = set()
        self.gallery_index = 0
        self.delete_timer_id = None
        self.drive_zip_path = None     # remote rclone path, set after a successful upload

        # MediaPipe kept loaded as a safety-net fallback - if YOLO fails to
        # install, load, or errors on a specific photo, the app degrades to
        # this known-working hard cutout instead of failing outright. This
        # matters because the YOLO pipeline below hasn't been tested on
        # real hardware yet.
        self.mp_selfie = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie.SelfieSegmentation(model_selection=1)

        # Primary detection: plain YOLO11n (boxes only, not the -seg
        # variant - we only need bounding boxes here, MediaPipe does the
        # actual per-person masking on each crop). Trained on general
        # multi-person photos (COCO), not selfie/video-call framing - the
        # bet here is that generalizes better to distant, multi-person,
        # non-centered group shots for LOCATING people. Exported to ONNX
        # once at startup for CPU inference speed.
        self.yolo_model = None
        if YOLO_AVAILABLE:
            try:
                base_model = YOLO("yolo11n.pt")
                onnx_path = base_model.export(format="onnx")
                self.yolo_model = YOLO(onnx_path)
                print("YOLO11n loaded (ONNX)")
            except Exception as e:
                print("YOLO failed to load, falling back to MediaPipe:", e)
                self.yolo_model = None
        else:
            print(
                "ultralytics not installed - falling back to MediaPipe. "
                "Run: pip install ultralytics --break-system-packages"
            )

        if not PYMATTING_AVAILABLE:
            print(
                "pymatting not installed - hair regions will use MediaPipe's "
                "own mask unrefined. Run: pip install pymatting --break-system-packages"
            )

        # Second MediaPipe segmenter, model_selection=0 (general/selfie),
        # used ONLY for hair-region refinement. Your own A/B test on a real
        # YOLO crop showed general is noticeably better around hair, but
        # lets more background through elsewhere on the body - so it's
        # confined to small hair/hand crops here, same as the rembg
        # variant was, rather than replacing the body's landscape model.
        self.mp_selfie_general = mp.solutions.selfie_segmentation
        self.segmenter_general = self.mp_selfie_general.SelfieSegmentation(model_selection=0)

        self.root.bind("<Escape>", lambda event: self.close_app())

        self.show_live_screen()

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def fit_16_9(self, max_w, max_h):
        """Return the largest 16:9 size that fits within max_w x max_h."""
        target_ratio = 16 / 9

        w = int(max_w)
        h = int(w / target_ratio)

        if h > max_h:
            h = int(max_h)
            w = int(h * target_ratio)

        return max(1, w), max(1, h)

    def frame_to_tk(self, frame_bgr, max_w, max_h, selected=False):
        """Convert BGR frame to resized Tk image."""
        display_w, display_h = self.fit_16_9(max_w, max_h)

        if selected:
            # Small pop-out effect for selected gallery image
            display_w = min(int(display_w * 1.03), int(max_w))
            display_h = min(int(display_h * 1.03), int(max_h))

        display_frame = cv2.resize(
            frame_bgr,
            (display_w, display_h),
            interpolation=cv2.INTER_AREA,
        )
        display_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(display_rgb)
        return ImageTk.PhotoImage(image=image)

    def load_backgrounds(self):
        valid_ext = (".jpg", ".jpeg", ".png")

        files = [
            os.path.join(BACKGROUND_DIR, f)
            for f in os.listdir(BACKGROUND_DIR)
            if f.lower().endswith(valid_ext)
        ]

        files.sort()

        if not files:
            print("No backgrounds found in:", BACKGROUND_DIR)

        return files

    def safe_name(self, path):
        name = os.path.splitext(os.path.basename(path))[0].lower()
        cleaned = "".join(c if c.isalnum() else "_" for c in name)
        cleaned = cleaned.strip("_")
        return cleaned or "background"

    def make_button(
        self,
        parent,
        text,
        command,
        bg,
        fg="black",
        width=12,
        height=2,
        font=None,
        pad_y=4,
    ):
        return Button(
            parent,
            text=text,
            command=command,
            font=font or BUTTON_FONT,
            width=width,
            height=height,
            pady=pad_y,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )

    def build_top_bar(self, left_text=""):
        """Consistent top bar used on every screen: optional centered
        status/position text and the settings button on the right, always
        at the same height/position - this is what makes button
        positioning consistent across the whole app rather than each
        screen improvising its own layout.

        Returns (bar_frame, center_label) - center_label is None if
        left_text was empty; callers can .config(text=...) it later.
        """
        bar = tk.Frame(self.root, bg=BG_COLOR, height=TOP_BAR_HEIGHT)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        center_label = None
        if left_text:
            center_label = Label(
                bar,
                text=left_text,
                font=("Arial", 12),
                fg=MUTED_TEXT_COLOR,
                bg=BG_COLOR,
            )
            center_label.place(relx=0.5, rely=0.5, anchor="center")

        settings_btn = Button(
            bar,
            text="SETTINGS",
            command=self.open_settings_popup,
            font=("Arial", 10, "bold"),
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=4,
        )
        settings_btn.pack(side="right", padx=8, pady=4)

        return bar, center_label


    def show_alert_popup(self, message):
        """Prominent popup for messages the user needs to actually notice
        (e.g. 'select at least one image') - bigger and more attention-
        grabbing than a small status-label flash."""
        popup = tk.Toplevel(self.root)
        popup.configure(bg=PANEL_COLOR)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        popup_w, popup_h = 480, 260
        x = (self.screen_w - popup_w) // 2
        y = (self.screen_h - popup_h) // 2
        popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

        message_label = Label(
            popup,
            text=message,
            font=("Arial", 20, "bold"),
            fg=TEXT_COLOR,
            bg=PANEL_COLOR,
            wraplength=popup_w - 60,
            justify="center",
        )
        message_label.pack(expand=True, pady=(20, 10))

        ok_btn = self.make_button(
            popup,
            text="OK",
            command=popup.destroy,
            bg=CAPTURE_COLOR,
            fg="black",
            width=14,
            height=1,
            font=BUTTON_FONT,
            pad_y=10,
        )
        ok_btn.pack(pady=(0, 20))

    def open_settings_popup(self):
        popup = tk.Toplevel(self.root)
        popup.configure(bg=PANEL_COLOR)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        popup_w, popup_h = 340, 240
        x = (self.screen_w - popup_w) // 2
        y = (self.screen_h - popup_h) // 2
        popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

        # Grouped so it centers as one block, rather than sitting at the
        # top of the popup.
        content = tk.Frame(popup, bg=PANEL_COLOR)
        content.pack(expand=True)

        title = Label(
            content,
            text="Settings",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=PANEL_COLOR,
        )
        title.pack(pady=(0, 12))

        end_btn = self.make_button(
            content,
            text="END PROGRAM",
            command=self.close_app,
            bg="#D9534F",
            fg="white",
            width=20,
            height=1,
            font=BUTTON_FONT,
            pad_y=6,
        )
        end_btn.pack(pady=4)

        close_btn = self.make_button(
            content,
            text="CLOSE",
            command=popup.destroy,
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            width=20,
            height=1,
            font=BUTTON_FONT,
            pad_y=6,
        )
        close_btn.pack(pady=6)

    # ============================================================
    # CAMERA
    # ============================================================

    def start_camera(self):
        self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

        # Low buffer helps reduce delay
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        if not self.cap.isOpened():
            self.status_label.config(text=f"Camera error: {CAMERA_DEVICE} not opened")
            return False

        time.sleep(0.4)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera opened at {actual_w}x{actual_h}")

        self.preview_running = True

        return True


    def flash_status(self, message, color, duration_ms=1200):
        """Briefly show a message on the live screen's status label, then
        restore whatever it said before. No-op if the live screen isn't up."""
        if not hasattr(self, "status_label") or not self.status_label.winfo_exists():
            return

        previous_text = self.status_label.cget("text")

        self.status_label.config(text=message, fg=color)
        self.root.after(
            duration_ms,
            lambda: self._restore_status_label(previous_text),
        )

    def _restore_status_label(self, previous_text):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.config(text=previous_text, fg=MUTED_TEXT_COLOR)

    def stop_camera(self):
        self.preview_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    # ============================================================
    # SCREEN 1: LIVE PREVIEW + CAPTURE
    # ============================================================

    def show_live_screen(self):
        self.stop_camera()
        self.clear_screen()

        self.countdown_number = None
        self.current_frame = None

        # Status text shares the top bar row with settings - reclaims a
        # full row of vertical height for the preview on an 800x480 screen.
        _, self.status_label = self.build_top_bar(left_text="Starting camera...")

        # Capture button pinned to the very bottom (packed first with
        # side="bottom" so it claims its space regardless of what's
        # packed above it), slightly bigger touch target than before.
        self.capture_button = self.make_button(
            self.root,
            text="CAPTURE",
            command=self.start_countdown,
            bg=CAPTURE_COLOR,
            fg="black",
            width=20,
            height=2,
            font=BIG_BUTTON_FONT,
            pad_y=13,
        )
        self.capture_button.config(state="disabled")
        self.capture_button.pack(side="bottom", pady=(0, 6))

        # Preview fills whatever's left between the top bar and the
        # capture button - on an 800x480 screen this is real, measurable
        # extra space compared to a separate status row.
        max_preview_w = self.screen_w - 16
        max_preview_h = self.screen_h - TOP_BAR_HEIGHT - 90

        self.preview_label = Label(
            self.root,
            bg=PREVIEW_BG,
            bd=0,
            highlightthickness=0,
        )
        self.preview_label.pack(pady=(4, 4))

        placeholder = np.zeros((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), dtype=np.uint8)
        placeholder[:] = (28, 30, 36)
        self.tk_preview_image = self.frame_to_tk(
            placeholder,
            max_preview_w,
            max_preview_h,
        )
        self.preview_label.config(image=self.tk_preview_image)

        if self.start_camera():
            self.capture_button.config(state="normal")
            self.status_label.config(text="Ready")
            self.update_preview()

    def update_preview(self):
        if not self.preview_running or self.cap is None:
            return

        ret, frame = self.cap.read()

        if ret:
            # Mirror the camera like a normal photobooth
            frame = cv2.flip(frame, 1)
            self.current_frame = frame.copy()

            max_preview_w = self.screen_w - 16
            max_preview_h = self.screen_h - TOP_BAR_HEIGHT - 90

            display_frame = frame.copy()

            if self.countdown_number is not None:
                display_frame = self.draw_countdown(
                    display_frame,
                    self.countdown_number,
                )

            self.tk_preview_image = self.frame_to_tk(
                display_frame,
                max_preview_w,
                max_preview_h,
            )
            self.preview_label.config(image=self.tk_preview_image)

        else:
            self.status_label.config(text="Camera frame not received")

        # 1080p webcam preview. Slower refresh = more reliable on Raspberry Pi.
        self.root.after(80, self.update_preview)

    def draw_countdown(self, frame, number):
        overlay = frame.copy()
        text = str(number)

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(frame.shape[1] / 420, 3)
        thickness = max(int(frame.shape[1] / 180), 8)

        text_size, _ = cv2.getTextSize(text, font, scale, thickness)
        text_w, text_h = text_size

        x = (frame.shape[1] - text_w) // 2
        y = (frame.shape[0] + text_h) // 2

        # Dark translucent circle behind number
        center = (frame.shape[1] // 2, frame.shape[0] // 2)
        radius = int(min(frame.shape[:2]) * 0.18)

        cv2.circle(overlay, center, radius, (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

        # Shadow
        cv2.putText(
            frame,
            text,
            (x + 6, y + 6),
            font,
            scale,
            (0, 0, 0),
            thickness + 3,
            cv2.LINE_AA,
        )

        # Main number
        cv2.putText(
            frame,
            text,
            (x, y),
            font,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

        return frame

    def start_countdown(self):
        if self.current_frame is None:
            self.status_label.config(text="Camera not ready yet")
            return

        self.capture_button.config(state="disabled")
        self.status_label.config(text="Get ready...")
        self.countdown_number = 3
        self.countdown_tick()

    def countdown_tick(self):
        if self.countdown_number is None:
            return

        if self.countdown_number > 0:
            self.status_label.config(text=f"Capturing in {self.countdown_number}...")
            self.root.after(1000, self.next_countdown_number)
        else:
            self.finish_capture()

    def next_countdown_number(self):
        if self.countdown_number is None:
            return

        self.countdown_number -= 1

        if self.countdown_number == 0:
            self.status_label.config(text="Capturing...")
            self.root.after(250, self.finish_capture)
        else:
            self.countdown_tick()

    def grab_high_res_snapshot(self):
        """Briefly switch the camera to a higher resolution for the actual
        still photo, then restore the live-preview resolution regardless of
        outcome. Capturing at a higher resolution than the final output and
        downscaling gives a cleaner result and more processing headroom
        than capturing natively at the output resolution.

        Safe by design: if the camera doesn't actually support 3840x2160 it
        will silently clamp to its nearest supported resolution (normal
        webcam/V4L2 behavior) - we just log whatever it actually gave us.
        If the grab fails outright, falls back to the current live preview
        frame so a capture never hard-fails.
        """
        fallback = self.current_frame.copy()

        if self.cap is None:
            return fallback

        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, SNAPSHOT_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SNAPSHOT_HEIGHT)

            for _ in range(3):
                self.cap.read()

            ret, frame = self.cap.read()

            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

            if ret and frame is not None:
                print(
                    f"Snapshot captured at {actual_w}x{actual_h} "
                    f"(requested {SNAPSHOT_WIDTH}x{SNAPSHOT_HEIGHT})"
                )
                return cv2.flip(frame, 1)

        except Exception as e:
            print("High-res snapshot failed, using live preview frame instead:", e)

        return fallback

    def finish_capture(self):
        if self.current_frame is None:
            self.countdown_number = None
            self.capture_button.config(state="normal")
            self.status_label.config(text="Camera not ready")
            return

        self.captured_frame = self.grab_high_res_snapshot()
        self.countdown_number = None

        self.stop_camera()
        self.show_capture_review_screen()

    # ============================================================
    # SCREEN 2: CAPTURED STILL + RETAKE / PROCEED
    # ============================================================

    def show_capture_review_screen(self):
        self.clear_screen()
        self.build_top_bar()

        max_preview_w = self.screen_w - 16
        max_preview_h = self.screen_h - TOP_BAR_HEIGHT - 60

        self.tk_result_image = self.frame_to_tk(
            self.captured_frame,
            max_preview_w,
            max_preview_h,
        )

        # RETAKE left, PROCEED right, centered together as a pair - same
        # size as each other, and smaller than CAPTURE, which is
        # deliberately the biggest button in the app.
        button_row = tk.Frame(self.root, bg=BG_COLOR)
        button_row.pack(side="bottom", pady=(0, 6))

        retake_btn = self.make_button(
            button_row,
            text="RETAKE",
            command=self.show_live_screen,
            bg=RETAKE_COLOR,
            fg="black",
            width=13,
            height=1,
            font=BIG_BUTTON_FONT,
            pad_y=8,
        )
        retake_btn.grid(row=0, column=0, padx=10)

        proceed_btn = self.make_button(
            button_row,
            text="PROCEED",
            command=self.show_processing_screen,
            bg=CONFIRM_COLOR,
            fg="black",
            width=13,
            height=1,
            font=BIG_BUTTON_FONT,
            pad_y=8,
        )
        proceed_btn.grid(row=0, column=1, padx=10)

        image_label = Label(
            self.root,
            image=self.tk_result_image,
            bg=PREVIEW_BG,
            bd=0,
            highlightthickness=0,
        )
        image_label.pack(pady=(4, 4))

    # ============================================================
    # SCREEN 3: PROCESSING
    # ============================================================

    def show_processing_screen(self):
        self.clear_screen()

        container = tk.Frame(self.root, bg=BG_COLOR)
        container.pack(expand=True, fill="both")

        # Grouped in their own frame so the pair centers as one block, the
        # same way the download screen's single label centers with
        # pack(expand=True).
        content = tk.Frame(container, bg=BG_COLOR)
        content.pack(expand=True)

        self.processing_title_label = Label(
            content,
            text="Processing your photo...",
            font=("Arial", 22, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        self.processing_title_label.pack(pady=(0, 10))

        self.processing_progress_label = Label(
            content,
            text="Getting started...",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )
        self.processing_progress_label.pack(pady=(0, 12))

        # Real ttk styling so the bar actually looks intentional rather
        # than a default gray strip.
        style = ttk.Style()
        style.theme_use(style.theme_use())  # keep current theme, just configure it
        style.configure(
            "Photobooth.Horizontal.TProgressbar",
            troughcolor=PANEL_COLOR,
            background=CAPTURE_COLOR,
            bordercolor=PANEL_COLOR,
            lightcolor=CAPTURE_COLOR,
            darkcolor=CAPTURE_COLOR,
        )

        self.processing_progress_bar = ttk.Progressbar(
            content,
            orient="horizontal",
            length=360,
            mode="indeterminate",
            style="Photobooth.Horizontal.TProgressbar",
        )
        self.processing_progress_bar.pack()
        # Indeterminate/pulsing during "analyzing your photo" - that step's
        # duration isn't known ahead of time, so a real percentage would be
        # a lie. Switched to determinate once the per-background loop
        # starts, where real progress fractions actually exist.
        self.processing_progress_bar.start(12)

        self.root.update_idletasks()
        self.root.after(100, self.begin_processing)

    def begin_processing(self):
        if self.captured_frame is None:
            self.show_error_screen("No captured photo found.")
            return

        if not self.backgrounds:
            self.show_error_screen("No backgrounds found.")
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_folder = os.path.join(SAVE_FOLDER, f"session_{timestamp}")
            os.makedirs(self.session_folder, exist_ok=True)

            self.output_files = []
            self.selected_outputs = set()
            self.gallery_index = 0
            self.drive_zip_path = None

            # This step (MediaPipe + reference bg subtraction) is the one
            # genuinely heavy, unavoidably synchronous chunk — say so clearly.
            self.processing_progress_label.config(text="Analyzing your photo (this takes a moment)...")
            self.root.update_idletasks()

            self._process_frame = cv2.resize(
                self.captured_frame,
                (OUTPUT_WIDTH, OUTPUT_HEIGHT),
                interpolation=cv2.INTER_AREA,
            )

            # Important: MediaPipe (and the bg-subtraction diff) run once only
            mask_start = time.time()
            self._process_alpha = self.create_person_alpha_mask(self._process_frame)
            print(f"[timing] Mask creation (this photo): {time.time() - mask_start:.2f}s")

            self._process_bg_index = 0
            self.processing_title_label.config(text="Applying backgrounds...")

            self.processing_progress_bar.stop()
            self.processing_progress_bar.config(mode="determinate", maximum=len(self.backgrounds), value=0)

            self.root.after(10, self.process_next_background)

        except Exception as e:
            print("Processing error:", e)
            self.show_error_screen(f"Processing error:\n{e}")

    def process_next_background(self):
        try:
            total = len(self.backgrounds)
            idx = self._process_bg_index

            if idx >= total:
                self.finish_processing()
                return

            bg_path = self.backgrounds[idx]

            # Update the label BEFORE the heavy work for this background, so
            # the count visibly advances instead of jumping at the end.
            self.processing_progress_label.config(
                text=f"Background {idx + 1} of {total}..."
            )
            self.root.update_idletasks()

            background = cv2.imread(bg_path)

            if background is None:
                print("Skipping unreadable background:", bg_path)
            else:
                background = cv2.resize(
                    background,
                    (OUTPUT_WIDTH, OUTPUT_HEIGHT),
                    interpolation=cv2.INTER_AREA,
                )

                final = self.composite_with_alpha(self._process_frame, background, self._process_alpha)

                out_name = f"{self.safe_name(bg_path)}.png"
                out_path = os.path.join(self.session_folder, out_name)

                cv2.imwrite(out_path, final)
                self.output_files.append(out_path)

            self._process_bg_index += 1
            self.processing_progress_bar.config(value=self._process_bg_index)

            # Schedule the next one instead of looping straight through —
            # this hands control back to Tkinter's event loop each time, so
            # the UI actually repaints and stays responsive between steps.
            self.root.after(10, self.process_next_background)

        except Exception as e:
            print("Processing error:", e)
            self.show_error_screen(f"Processing error:\n{e}")

    def finish_processing(self):
        if not self.output_files:
            self.show_error_screen("No outputs were generated.")
            return

        # Auto-delete the entire session folder after 15 minutes
        if self.delete_timer_id is not None:
            try:
                self.root.after_cancel(self.delete_timer_id)
            except Exception:
                pass

        self.delete_timer_id = self.root.after(
            AUTO_DELETE_MS,
            self.auto_delete_session,
        )

        self.show_gallery_screen()

    def get_yolo_person_boxes(self, frame_bgr):
        """Returns a list of (x_min, y_min, x_max, y_max) boxes, one per
        detected person, expanded with margin and clamped to frame bounds.
        Empty list if YOLO isn't loaded or found nobody - callers should
        treat that as "fall back to full-frame MediaPipe".

        Uses plain YOLO11n (detection only, not the -seg variant) since we
        only need boxes here, not per-pixel masks - lighter and simpler.
        """
        if self.yolo_model is None:
            return []

        h, w = frame_bgr.shape[:2]

        try:
            results = self.yolo_model(frame_bgr, classes=[0], verbose=False)
            result = results[0]
        except Exception as e:
            print("YOLO inference failed on this photo:", e)
            return []

        if result.boxes is None or len(result.boxes) == 0:
            return []

        boxes = []
        for box in result.boxes.xyxy.cpu().numpy():
            x_min, y_min, x_max, y_max = box
            box_w = x_max - x_min
            box_h = y_max - y_min

            # Expand the box - YOLO's detection box often crops tight to
            # the visible body, which would clip hair sticking up past it
            # or feet right at the bottom edge if used as-is.
            margin_x = box_w * BOX_MARGIN_FRACTION
            margin_y = box_h * BOX_MARGIN_FRACTION

            x_min = max(0, int(x_min - margin_x))
            y_min = max(0, int(y_min - margin_y))
            x_max = min(w, int(x_max + margin_x))
            y_max = min(h, int(y_max + margin_y))

            if x_max > x_min and y_max > y_min:
                boxes.append((x_min, y_min, x_max, y_max))

        return boxes

    def get_mediapipe_crop_alpha(self, crop_bgr):
        """MediaPipe on a single-person crop instead of the full frame.

        This is the actual fix for MediaPipe's group-photo weakness: it
        isn't that the algorithm can't handle people, it's that "selfie"
        segmentation is trained overwhelmingly on close-up, roughly-
        centered, single-subject framing. A wide 10-person shot is far
        outside that training distribution. Cropping each person out
        first recreates the close-up framing MediaPipe actually knows.

        Soft alpha (not a hard cutout) - MediaPipe's own probabilistic
        mask already gives usable edge softness natively.
        """
        rgb_crop = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        result = self.segmenter.process(rgb_crop)
        mask = result.segmentation_mask

        if mask is None:
            return np.zeros(crop_bgr.shape[:2], dtype=np.float32)

        smooth_mask = cv2.GaussianBlur(mask, (5, 5), 0)
        alpha = np.clip((smooth_mask - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW), 0, 1)
        return alpha.astype(np.float32)

    def get_uncertain_regions(self, crop_alpha, max_regions=4):
        """Bounding boxes of MediaPipe's separate 'uncertain' clusters (not
        confidently foreground or background), each with a small margin.

        This used to return a SINGLE box spanning all uncertain pixels,
        which was diluted when hair (near the head) and hand/finger
        translucency (elsewhere on the body) were both present - one box
        had to stretch across both plus everything confidently-fine in
        between. Connected-components finds each disjoint uncertain area
        separately, so hair and hands each get their own tightly-cropped
        refinement instead of one oversized, unfocused one.

        Returns a list of (y_min, y_max, x_min, x_max) tuples, largest
        first, capped at max_regions to bound total matting cost. Empty
        list if there's nothing meaningfully uncertain to refine.
        """
        h, w = crop_alpha.shape
        uncertain = ((crop_alpha > 0.05) & (crop_alpha < 0.95)).astype(np.uint8)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(uncertain, connectivity=8)

        if num_labels <= 1:
            return []

        # Sort components by area, largest first, skip background label 0
        component_ids = sorted(
            range(1, num_labels),
            key=lambda i: stats[i, cv2.CC_STAT_AREA],
            reverse=True,
        )

        regions = []
        for label_id in component_ids[:max_regions]:
            if stats[label_id, cv2.CC_STAT_AREA] < 20:
                continue

            x = stats[label_id, cv2.CC_STAT_LEFT]
            y = stats[label_id, cv2.CC_STAT_TOP]
            comp_w = stats[label_id, cv2.CC_STAT_WIDTH]
            comp_h = stats[label_id, cv2.CC_STAT_HEIGHT]

            margin_y = int(comp_h * 0.15) + 4
            margin_x = int(comp_w * 0.15) + 4

            y_min = max(0, y - margin_y)
            y_max = min(h, y + comp_h + margin_y)
            x_min = max(0, x - margin_x)
            x_max = min(w, x + comp_w + margin_x)

            if y_max > y_min and x_max > x_min:
                regions.append((y_min, y_max, x_min, x_max))

        return regions

    def matte_region(self, region_bgr, region_alpha):
        """Matte one small region using MediaPipe's general/selfie model
        (model_selection=0) - your own A/B test showed this is noticeably
        better around hair than the landscape model used for the body,
        confined here to a small region so its "lets more background
        through" tendency stays contained rather than affecting the whole
        body. Returns None (caller keeps the landscape model's unrefined
        alpha) if it fails on this region.
        """
        try:
            return self._matte_with_general_model(region_bgr)
        except Exception as e:
            print("General-model matting failed on one region, skipping it:", e)
            return None

    def _matte_with_general_model(self, region_bgr):
        rgb_region = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2RGB)
        result = self.segmenter_general.process(rgb_region)
        mask = result.segmentation_mask

        if mask is None:
            raise RuntimeError("General model did not return a segmentation mask")

        smooth_mask = cv2.GaussianBlur(mask, (5, 5), 0)
        alpha = np.clip((smooth_mask - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW), 0, 1)
        return alpha.astype(np.float32)

    def _matte_with_pymatting(self, region_bgr, region_alpha):
        orig_h, orig_w = region_alpha.shape
        scale = min(1.0, MATTING_MAX_DIM / max(orig_h, orig_w))
        small_w = max(1, int(orig_w * scale))
        small_h = max(1, int(orig_h * scale))

        small_bgr = cv2.resize(region_bgr, (small_w, small_h))
        small_alpha = cv2.resize(region_alpha, (small_w, small_h))

        trimap = np.full((small_h, small_w), 0.5, dtype=np.float64)
        trimap[small_alpha > 0.9] = 1.0
        trimap[small_alpha < 0.1] = 0.0

        image_float = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0
        refined_small = estimate_alpha_cf(image_float, trimap)
        refined = cv2.resize(refined_small.astype(np.float32), (orig_w, orig_h))
        return np.clip(refined, 0, 1)

    def refine_hair_region(self, crop_bgr, crop_alpha):
        """Focused matting refinement on each of MediaPipe's separately
        uncertain regions within one person's crop (hair, hand/finger
        translucency, any other soft edge) - NOT a fixed fraction, and NOT
        a single box spanning everything, so this adapts to wherever the
        ambiguity actually is without diluting the refinement across
        unrelated confident pixels in between. Confident pixels elsewhere
        in the crop are left completely untouched, so there's nothing
        there to fade.

        Uses MediaPipe's general/selfie model as the matting engine. Skips
        refinement (keeps the landscape model's unrefined alpha) for a
        region if the general model isn't
        available or fails on it - never worse than before, just not
        improved for this photo.

        IMPORTANT: all regions are computed first, then blended in ONE
        pass at the end. A raised hand near head height can make the hand
        region and hair region's bounding boxes overlap - blending each
        region into the result sequentially meant an overlapping pixel got
        blended twice, compounding the intended cap each time and fading
        exactly at the intersection. Tracking the strongest single
        contribution per pixel (not stacking multiple regions' blends)
        fixes that.
        """
        regions = self.get_uncertain_regions(crop_alpha)
        if not regions:
            return crop_alpha

        # Accumulate each region's contribution without touching the
        # result yet - combined_weight tracks the STRONGEST weight seen so
        # far at each pixel, combined_refined tracks whichever region's
        # value goes with that strongest weight. This ensures an
        # overlapping pixel is only ever blended by ONE region, not
        # multiple stacked blends.
        combined_refined = crop_alpha.copy()
        combined_weight = np.zeros_like(crop_alpha)

        for (y_min, y_max, x_min, x_max) in regions:
            region_bgr = crop_bgr[y_min:y_max, x_min:x_max]
            region_alpha = crop_alpha[y_min:y_max, x_min:x_max]

            refined = self.matte_region(region_bgr, region_alpha)
            if refined is None:
                continue

            # Feather all four edges of the patch, since each region can
            # sit anywhere in the crop - protects against a visible
            # rectangle wherever it meets the untouched surrounding mask.
            patch_h, patch_w = refined.shape
            feather = max(3, int(0.08 * min(patch_h, patch_w)))

            blend_weight = np.ones((patch_h, patch_w), dtype=np.float32)
            for i in range(feather):
                weight = i / feather
                blend_weight[i, :] *= weight
                blend_weight[patch_h - 1 - i, :] *= weight
                blend_weight[:, i] *= weight
                blend_weight[:, patch_w - 1 - i] *= weight

            # Cap the matting solve's maximum influence - it can never
            # fully replace MediaPipe's own alpha, only nudge it.
            blend_weight = blend_weight * MATTING_BLEND_STRENGTH

            existing_weight = combined_weight[y_min:y_max, x_min:x_max]
            existing_refined = combined_refined[y_min:y_max, x_min:x_max]

            take_new = blend_weight > existing_weight
            existing_refined[take_new] = refined[take_new]
            existing_weight[take_new] = blend_weight[take_new]

            combined_refined[y_min:y_max, x_min:x_max] = existing_refined
            combined_weight[y_min:y_max, x_min:x_max] = existing_weight

        # Single final blend using whichever region "won" at each pixel -
        # never blended more than once anywhere.
        result = combined_refined * combined_weight + crop_alpha * (1 - combined_weight)
        return result

    def create_mediapipe_fallback_mask(self, frame_bgr):
        """Safety net if YOLO isn't loaded or finds nobody: MediaPipe on
        the full frame directly. Still gets the same hair-matting
        refinement and speck cleanup as the per-person path - this is what
        was actually running throughout testing while YOLO was silently
        failing, so it needs full quality treatment too, not a stripped-
        down version."""
        alpha = self.get_mediapipe_crop_alpha(frame_bgr)
        alpha = self.refine_hair_region(frame_bgr, alpha)
        alpha = self.remove_small_specks(alpha)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        return alpha.astype(np.float32)

    def create_person_alpha_mask(self, frame_bgr):
        """YOLO11n for per-person detection boxes only (no segmentation
        masks), MediaPipe run separately on each person's cropped region
        for the body, then a focused pymatting pass on just the hair/head
        portion of each crop for finer edge detail. Falls back to
        full-frame MediaPipe if YOLO isn't available or finds nobody - this
        pipeline hasn't been tested on real hardware yet, so it should
        degrade gracefully rather than fail outright.
        """
        h, w = frame_bgr.shape[:2]
        boxes = self.get_yolo_person_boxes(frame_bgr)

        if not boxes:
            return self.create_mediapipe_fallback_mask(frame_bgr)

        alpha = np.zeros((h, w), dtype=np.float32)

        for (x_min, y_min, x_max, y_max) in boxes:
            crop_bgr = frame_bgr[y_min:y_max, x_min:x_max]
            crop_alpha = self.get_mediapipe_crop_alpha(crop_bgr)
            crop_alpha = self.refine_hair_region(crop_bgr, crop_alpha)

            # Merge with max rather than overwrite - if two people's boxes
            # overlap (standing close together), this keeps both people's
            # detected pixels rather than one crop erasing the other's.
            alpha[y_min:y_max, x_min:x_max] = np.maximum(
                alpha[y_min:y_max, x_min:x_max], crop_alpha
            )

        # Connected-component cleanup: remove small, disconnected specks of
        # misclassified pixels (a common source of odd noise, especially
        # near hands/limbs) that aren't attached to a real person region.
        alpha = self.remove_small_specks(alpha)

        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        return alpha.astype(np.float32)

    def remove_small_specks(self, alpha, min_area_fraction=0.0015):
        """Zero out small disconnected foreground blobs - genuine people
        produce one large, solid connected region; misclassification noise
        tends to show up as small, isolated specks. Threshold is relative
        to total frame area so it scales with resolution automatically."""
        binary = (alpha > 0.5).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

        if num_labels <= 1:  # only the background label - nothing to clean
            return alpha

        total_area = alpha.shape[0] * alpha.shape[1]
        min_area = total_area * min_area_fraction

        cleaned = alpha.copy()
        for label_id in range(1, num_labels):  # skip label 0 (background)
            if stats[label_id, cv2.CC_STAT_AREA] < min_area:
                cleaned[labels == label_id] = 0.0

        return cleaned

    def composite_with_alpha(self, frame, background, alpha):
        alpha_3ch = np.dstack([alpha, alpha, alpha])
        final = frame.astype(np.float32) * alpha_3ch + background.astype(np.float32) * (1 - alpha_3ch)
        return np.clip(final, 0, 255).astype(np.uint8)

    # ============================================================
    # SCREEN 4: OUTPUT GALLERY
    # ============================================================

    def show_gallery_screen(self):
        self.clear_screen()

        if not self.output_files:
            self.show_error_screen("No gallery images found.")
            return

        # Timestamp for diagnosing whether browsing/selection time before
        # pressing DOWNLOAD correlates with upload speed (suspected: Wi-Fi
        # power-saving causing the adapter to need to wake/re-negotiate
        # after a period of no network traffic).
        self.gallery_entered_at = time.time()

        _, self.gallery_position_label = self.build_top_bar(left_text="Gallery")

        # Everything below packs top-down in visual order (no side="bottom"
        # mixing) - any imprecision in the height budget collects as slack
        # at the very bottom of the screen instead of as a gap in the
        # middle, between the image and the status text below it.

        max_preview_w = self.screen_w - 200
        max_preview_h = self.screen_h - TOP_BAR_HEIGHT - 70

        nav_font = ("Arial", 22, "bold")
        image_row = tk.Frame(self.root, bg=BG_COLOR)
        image_row.pack(pady=(4, 4))

        prev_btn = self.make_button(
            image_row,
            text="<",
            command=self.previous_output,
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            width=3,
            height=3,
            font=nav_font,
            pad_y=6,
        )
        prev_btn.pack(side="left", padx=(0, 10))

        self.gallery_image_label = Label(
            image_row,
            bg=PREVIEW_BG,
            bd=0,
            highlightthickness=0,
        )
        self.gallery_image_label.pack(side="left")
        # Tap the image itself to select/unselect, in addition to the
        # SELECT button - the button stays for a clear, discoverable
        # target, this is just a shortcut for the obvious gesture.
        self.gallery_image_label.bind("<Button-1>", lambda e: self.toggle_select_current())

        next_btn = self.make_button(
            image_row,
            text=">",
            command=self.next_output,
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            width=3,
            height=3,
            font=nav_font,
            pad_y=6,
        )
        next_btn.pack(side="left", padx=(10, 0))

        # One row, pinned to the bottom edge and spanning the full width -
        # RETAKE sits at the far left, SELECT/DOWNLOAD grouped to the
        # right, with a flexible spacer column between them. Everything
        # here is genuinely aligned (same frame) so there's no risk of
        # RETAKE and the others drifting apart like the old place()-based
        # corner button did.
        button_row = tk.Frame(self.root, bg=BG_COLOR)
        button_row.pack(side="bottom", fill="x", pady=(0, 8))
        button_row.grid_columnconfigure(1, weight=1)

        retake_btn = self.make_button(
            button_row,
            text="RETAKE",
            command=self.retake_photo,
            bg=RETAKE_COLOR,
            fg="black",
            width=8,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        retake_btn.grid(row=0, column=0, padx=(16, 0), sticky="w")

        primary_group = tk.Frame(button_row, bg=BG_COLOR)
        primary_group.grid(row=0, column=2, padx=(0, 16), sticky="e")

        self.select_btn = self.make_button(
            primary_group,
            text="SELECT",
            command=self.toggle_select_current,
            bg=SELECTED_COLOR,
            fg="black",
            width=12,
            height=1,
            font=BIG_BUTTON_FONT,
            pad_y=8,
        )
        self.select_btn.grid(row=0, column=0, padx=10)

        self.download_btn = self.make_button(
            primary_group,
            text="DOWNLOAD",
            command=self.start_download_flow,
            bg=CONFIRM_COLOR,
            fg="black",
            width=12,
            height=1,
            font=BIG_BUTTON_FONT,
            pad_y=8,
        )
        self.download_btn.grid(row=0, column=1, padx=10)

        self.update_gallery_image()

    def retake_photo(self):
        """Discard this session's outputs entirely and go back to live
        preview to recapture from scratch — used when the user doesn't
        like the photo or how the background removal turned out."""
        if self.delete_timer_id is not None:
            try:
                self.root.after_cancel(self.delete_timer_id)
            except Exception:
                pass
            self.delete_timer_id = None

        if self.session_folder and os.path.exists(self.session_folder):
            try:
                shutil.rmtree(self.session_folder)
            except Exception as e:
                print("Retake cleanup error:", e)

        if self.drive_zip_path:
            try:
                subprocess.run(
                    ["rclone", "deletefile", self.drive_zip_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except Exception as e:
                print("Retake Drive cleanup error:", e)

        self.session_folder = None
        self.output_files = []
        self.selected_outputs = set()
        self.drive_zip_path = None
        self.captured_frame = None

        self.show_live_screen()

    def start_download_flow(self):
        if not self.selected_outputs:
            self.show_alert_popup("Select at least one image first")
            return

        self.show_download_screen()

    def update_gallery_image(self):
        current_path = self.output_files[self.gallery_index]
        image = cv2.imread(current_path)

        if image is None:
            self.show_error_screen("Could not load gallery image.")
            return

        is_selected = current_path in self.selected_outputs

        max_preview_w = self.screen_w - 200
        max_preview_h = self.screen_h - TOP_BAR_HEIGHT - 70

        self.tk_result_image = self.frame_to_tk(
            image,
            max_preview_w,
            max_preview_h,
            selected=False,  # size-changing pop-out was shifting prev/next arrows; border highlight alone already conveys selection
        )

        # Border/highlight thickness stays CONSTANT regardless of selection
        # - only the color toggles (invisible vs SELECTED_COLOR). Changing
        # bd/highlightthickness between states was itself shifting the
        # prev/next arrows next to the image, on top of the old pop-out
        # scale effect above.
        border_color = SELECTED_COLOR if is_selected else BG_COLOR
        self.gallery_image_label.config(
            image=self.tk_result_image,
            bd=5,
            relief="solid",
            highlightthickness=3,
            highlightbackground=border_color,
        )

        if is_selected:
            self.select_btn.config(text="UNSELECT", bg=RETAKE_COLOR)
        else:
            self.select_btn.config(text="SELECT", bg=SELECTED_COLOR)

        # Selection state is already visually obvious (border highlight +
        # button label toggling to UNSELECT) - no need for redundant
        # instructional or confirmation text taking up screen space.
        position_text = f"Photo {self.gallery_index + 1} of {len(self.output_files)}"
        if is_selected:
            position_text += " - Selected"
        self.gallery_position_label.config(text=position_text)

    def previous_output(self):
        self.gallery_index = (self.gallery_index - 1) % len(self.output_files)
        self.update_gallery_image()

    def next_output(self):
        self.gallery_index = (self.gallery_index + 1) % len(self.output_files)
        self.update_gallery_image()

    def toggle_select_current(self):
        current_path = self.output_files[self.gallery_index]

        if current_path in self.selected_outputs:
            self.selected_outputs.remove(current_path)
        else:
            self.selected_outputs.add(current_path)

        self.update_gallery_image()

    # ============================================================
    # SCREEN 5: DOWNLOAD (ZIP -> RCLONE -> QR)
    # ============================================================

    def show_download_screen(self):
        self.clear_screen()

        container = tk.Frame(self.root, bg=BG_COLOR)
        container.pack(expand=True, fill="both")

        label = Label(
            container,
            text="Preparing your download...",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        label.pack(expand=True)

        self.root.update_idletasks()
        self.root.after(100, self.process_download)

    def process_download(self):
        try:
            # Keep gallery order rather than set order, nicer in the zip.
            selected_paths = [
                path for path in self.output_files if path in self.selected_outputs
            ]

            if not selected_paths:
                raise RuntimeError("No images selected")

            browsing_seconds = time.time() - getattr(self, "gallery_entered_at", time.time())
            print(f"[timing] Time spent in gallery before DOWNLOAD: {browsing_seconds:.1f}s")

            session_name = os.path.basename(self.session_folder)
            zip_path = os.path.join(self.session_folder, f"{session_name}.zip")

            zip_start = time.time()
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in selected_paths:
                    zf.write(path, arcname=os.path.basename(path))
            print(f"[timing] Zip creation: {time.time() - zip_start:.1f}s")

            remote_target = f"{RCLONE_REMOTE}:{RCLONE_REMOTE_FOLDER}"

            copy_start = time.time()
            subprocess.run(
                ["rclone", "copy", zip_path, remote_target],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"[timing] rclone copy (upload): {time.time() - copy_start:.1f}s")

            remote_zip_path = f"{RCLONE_REMOTE}:{RCLONE_REMOTE_FOLDER}/{session_name}.zip"

            link_start = time.time()
            link_result = subprocess.run(
                ["rclone", "link", remote_zip_path],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"[timing] rclone link (share URL): {time.time() - link_start:.1f}s")

            share_url = link_result.stdout.strip()

            if not share_url:
                raise RuntimeError("rclone did not return a share link")

            # Remember this so the 15-minute auto-delete can clean up Drive too.
            self.drive_zip_path = remote_zip_path

            qr_image = qrcode.make(share_url)
            qr_path = os.path.join(QR_SAVE_DIR, f"{session_name}.png")
            qr_image.save(qr_path)

            self.show_qr_screen(qr_path)

        except subprocess.CalledProcessError as e:
            print("rclone error:", e.stderr)
            self.show_error_screen(f"Upload error:\n{e.stderr.strip()}")
        except Exception as e:
            print("Download error:", e)
            self.show_error_screen(f"Download error:\n{e}")

    def show_qr_screen(self, qr_path):
        self.clear_screen()
        self.build_top_bar()

        container = tk.Frame(self.root, bg=BG_COLOR)
        container.pack(expand=True, fill="both")

        # Grouped in their own frame so everything centers as one block -
        # the previous version packed these directly into container, which
        # only centers the container itself, not its children individually.
        content = tk.Frame(container, bg=BG_COLOR)
        content.pack(expand=True)

        title = Label(
            content,
            text="Scan to download your photos",
            font=("Arial", 22, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        title.pack(pady=(0, 6))

        qr_source = Image.open(qr_path)
        # Sized to fit within the available height alongside the top bar,
        # title, note, and button - genuinely bigger than the old 260px,
        # not just a larger number that would overflow the 480px screen.
        qr_size = min(self.screen_w - 40, self.screen_h - TOP_BAR_HEIGHT - 130)
        qr_source = qr_source.resize((qr_size, qr_size), Image.NEAREST)
        self.tk_qr_image = ImageTk.PhotoImage(qr_source)

        qr_label = Label(content, image=self.tk_qr_image, bg=BG_COLOR)
        qr_label.pack(pady=4)

        note = Label(
            content,
            text="Link stays active for 15 minutes",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )
        note.pack(pady=(2, 6))

        done_btn = self.make_button(
            content,
            text="DONE",
            command=self.show_live_screen,
            bg=CAPTURE_COLOR,
            fg="black",
            width=16,
            height=1,
            font=BIG_BUTTON_FONT,
            pad_y=8,
        )
        done_btn.pack(pady=4)

    # ============================================================
    # ERROR / AUTO DELETE / EXIT
    # ============================================================

    def show_error_screen(self, message):
        self.clear_screen()

        label = Label(
            self.root,
            text=message,
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
            wraplength=self.screen_w - 40,
            justify="center",
        )
        label.pack(expand=True)

        retry_btn = self.make_button(
            self.root,
            text="NEW PHOTO",
            command=self.show_live_screen,
            bg=CAPTURE_COLOR,
            fg="black",
            width=14,
            height=2,
            font=BIG_BUTTON_FONT,
        )
        retry_btn.pack(pady=12)

    def auto_delete_session(self):
        if self.session_folder and os.path.exists(self.session_folder):
            try:
                shutil.rmtree(self.session_folder)
                print("Auto-deleted local session:", self.session_folder)
            except Exception as e:
                print("Local auto-delete error:", e)

        if self.drive_zip_path:
            try:
                subprocess.run(
                    ["rclone", "deletefile", self.drive_zip_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print("Auto-deleted Drive file:", self.drive_zip_path)
            except subprocess.CalledProcessError as e:
                print("Drive auto-delete error:", e.stderr)
            except Exception as e:
                print("Drive auto-delete error:", e)

        self.session_folder = None
        self.output_files = []
        self.selected_outputs = set()
        self.drive_zip_path = None

    def close_app(self):
        self.stop_camera()

        try:
            if self.delete_timer_id is not None:
                self.root.after_cancel(self.delete_timer_id)
        except Exception:
            pass

        try:
            self.segmenter.close()
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoboothApp(root)
    root.mainloop()