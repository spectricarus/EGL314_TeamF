import os
import cv2
import time
import shutil
import zipfile
import threading
import json
import urllib.request
import urllib.error
import subprocess
import tkinter as tk
from tkinter import Label, Button
from datetime import datetime

import qrcode
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

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
    SECONDARY_FONT,
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

# rclone runs as a persistent background daemon (rcd) instead of a fresh
# CLI process per operation - this is what actually fixes the "seesaw"
# copy/link timing found during testing (e.g. 54s vs 4s for the same
# operation, run seconds apart): each fresh CLI process independently
# gambled on connection/OAuth-token setup, while the daemon negotiates
# once at startup and reuses that same warm connection for every
# operation afterward.
RCLONE_RC_PORT = 5572

CAMERA_DEVICE = "/dev/video0"

# Live preview feed resolution (continuous, needs to stay smooth)
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Event banner - drawn as a third layer ON TOP of the finished person+
# background composite, not baked into the background image itself, so
# it's never blocked by whoever's standing in the shot.
EVENT_BANNER_TEXT = "Project Phantom @ NYP S.536"
EVENT_DATE_FORMAT = "%d %B %Y"  # e.g. "19 August 2026" - always TODAY's date, not hardcoded
EVENT_BANNER_OPACITY = 0.6  # 0 = invisible, 1 = fully opaque black strip
EVENT_BANNER_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EVENT_DATE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # regular weight, not bold - keeps the date visually secondary to the title

# Custom-designed graphic overlay (OBS-style) - if this file exists, it's
# used INSTEAD of the plain banner above, with the date still drawn live
# on top at EVENT_DATE_POSITION. If it doesn't exist yet, falls back to
# the plain banner automatically - nothing breaks if no time to design.
EVENT_GRAPHIC_PATH = os.path.join(BASE_DIR, "assets", "event_overlay.png")
EVENT_DATE_POSITION = (OUTPUT_WIDTH // 2, OUTPUT_HEIGHT - 40)  # (x, y) - CENTER of the text, adjust once the real design exists
EVENT_DATE_FONT_SIZE = 28
EVENT_DATE_COLOR = (255, 255, 255)  # RGB

# LOCAL CLEANUP - no timers at all. saved_images/ and qrcodes/ get wiped
# completely (deleted and recreated empty) at both app STARTUP and
# SHUTDOWN via wipe_output_folders() - simpler than per-session timed
# deletion, and crash-proof by construction: even if the app never reaches
# a clean shutdown, the next startup wipes stale content before the new
# run begins. Google Drive is left alone entirely - cleaned up manually.

# DFRobot Gravity 8002 Digital Speaker - wired GND/VCC/Signal, Signal to
# this GPIO pin (BCM numbering, physical pin 12). Driven like an Arduino
# buzzer: toggling this pin at an audio frequency, not playing audio files.
SPEAKER_PIN = 18

# If the background camera reader thread claims to be running but hasn't
# produced a real frame in this many seconds, treat it as stuck (not
# just slow) and abandon it rather than trust the "running" flag, which
# can't tell the difference on its own - see start_camera().
STALE_FRAME_THRESHOLD = 3.0

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

# Matting never fully replaces the landscape model's original alpha -
# this caps how much weight the refinement can have (1.0 = full
# replacement, lower = blended with the original as a safety net). The
# general model is more permissive/soft than landscape, which is exactly
# why it's better at hair - but that same softness can occasionally
# over-include background under harsh/uneven lighting. A partial blend
# limits how much a bad call there can affect the result, without giving
# up the improvement when it gets it right.
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
        self.camera_released_at = None  # set by stop_camera(), used to guarantee a minimum gap before reopening
        self.camera_thread = None
        self.camera_thread_running = False
        self.camera_frame_lock = threading.Lock()
        self.latest_frame_raw = None  # most recent frame from the background reader thread
        self.last_frame_time = None  # when that frame actually arrived - used to detect a stuck reader thread
        self.live_screen_active = False  # True only while the live screen's widgets actually exist

        self.current_frame = None      # full-resolution camera frame
        self.captured_frame = None     # full-resolution still photo

        self.tk_preview_image = None
        self.tk_result_image = None

        self.backgrounds = self.load_backgrounds()

        self.session_folder = None
        self.output_files = []
        self.selected_outputs = set()
        self.gallery_index = 0

        # Wipe local outputs from any previous run before this one starts -
        # see the LOCAL CLEANUP comment near the top of the file.
        self.wipe_output_folders()

        # rclone daemon - started once here, reused for every download all
        # session, instead of a fresh CLI process (and fresh connection
        # negotiation) per copy/link call. See RCLONE_RC_PORT comment.
        self.rclone_daemon_process = None
        self.rclone_keepalive_running = False
        try:
            self.rclone_daemon_process = subprocess.Popen(
                [
                    "rclone", "rcd", "--rc-no-auth", f"--rc-addr=localhost:{RCLONE_RC_PORT}",
                    "--contimeout", "15s",
                    "--timeout", "15s",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            daemon_ready = False
            for _ in range(20):  # up to ~5 seconds, polling rather than a blind sleep
                try:
                    self.rclone_rc_call("core/version", {}, timeout=2)
                    daemon_ready = True
                    break
                except Exception:
                    time.sleep(0.25)
            if daemon_ready:
                print("rclone daemon ready on port", RCLONE_RC_PORT)
                # Periodic no-op call to keep the underlying connection to
                # Drive from going idle-stale (a real thing regardless of
                # wifi power-save specifically - TCP connections can be
                # dropped by the router/OS/Drive's own end after enough
                # idle time, independent of the radio's own sleep state).
                self.rclone_keepalive_running = True
                threading.Thread(target=self.rclone_keepalive_loop, daemon=True).start()
            else:
                print("rclone daemon did not become ready in time - downloads may fail")
        except Exception as e:
            print("Failed to start rclone daemon:", e)
            self.rclone_daemon_process = None

        # Speaker setup - once at startup (accepted small startup-time
        # cost), wrapped in try/except so a missing/failed speaker never
        # breaks the app, just plays no sound.
        self.speaker_available = False
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(SPEAKER_PIN, GPIO.OUT)
                self.speaker_available = True
                print("Speaker ready on GPIO", SPEAKER_PIN)
            except Exception as e:
                print("Speaker setup failed, continuing without sound:", e)
                self.speaker_available = False
        else:
            print("RPi.GPIO not installed - continuing without sound")

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
        self.live_screen_active = False
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
        pad_x=0,
    ):
        return Button(
            parent,
            text=text,
            command=command,
            font=font or BUTTON_FONT,
            width=width,
            height=height,
            pady=pad_y,
            padx=pad_x,
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
                font=LABEL_FONT,
                fg=MUTED_TEXT_COLOR,
                bg=BG_COLOR,
            )
            center_label.place(relx=0.5, rely=0.5, anchor="center")

        settings_btn = Button(
            bar,
            text="SETTINGS",
            command=self.open_settings_popup,
            font=("DejaVu Sans", 10, "bold"),
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
            font=SECONDARY_FONT,
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
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
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
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        end_btn.pack(pady=4)

        close_btn = self.make_button(
            content,
            text="CLOSE",
            command=popup.destroy,
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        close_btn.pack(pady=6)

    # ============================================================
    # CAMERA
    # ============================================================

    def start_camera(self, force_reopen=False):
        """Opens the camera and starts a background thread that
        continuously reads frames - reading happens OFF the main thread
        specifically because a slow/blocking camera read (the actual
        observed flakiness - can block for 10-40+ seconds INSIDE a single
        read call) would otherwise freeze the entire UI, including the
        loading spinner itself. update_preview() only ever polls whatever
        the background thread most recently read - it never blocks.

        If the camera is already open with its reader thread already
        running AND recently produced a real frame, does nothing and
        returns immediately - avoids an unnecessary close/reopen cycle
        (e.g. RETAKE going back to live preview, where the camera was
        never actually stopped).

        The "recently produced a frame" check matters on its own: a
        genuinely STUCK reader thread (a single cap.read() call that
        never returns - not just slow) still reports itself as "running"
        forever, since Python can't forcibly kill a thread blocked inside
        a C-level call. Trusting the flag alone would spin the loading
        indicator forever with no way to recover. Checking how long it's
        actually been since a real frame arrived is what catches this.
        """
        thread_claims_running = not force_reopen and self.cap is not None and self.camera_thread_running

        if thread_claims_running:
            frame_is_fresh = (
                self.last_frame_time is not None
                and (time.time() - self.last_frame_time) < STALE_FRAME_THRESHOLD
            )
            if frame_is_fresh:
                self.preview_running = True
                return True

            # Thread claims to be running but hasn't produced a frame
            # recently - likely stuck inside a hung read. Can't cleanly
            # kill it (no safe way to force-stop a blocked C-level call),
            # so abandon it and open a genuinely fresh camera instead of
            # waiting on a thread that may never come back.
            print("Camera reader thread appears stuck (no frame recently) - abandoning it and reopening fresh.")
            self.camera_thread_running = False
            self.camera_thread = None  # deliberately not joining - it may be blocked indefinitely
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            self.camera_released_at = time.time()

        if self.camera_released_at is not None:
            elapsed = time.time() - self.camera_released_at
            min_gap = 0.6
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)

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

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera opened at {actual_w}x{actual_h}")

        with self.camera_frame_lock:
            self.latest_frame_raw = None
            self.last_frame_time = time.time()

        self.camera_thread_running = True
        self.camera_thread = threading.Thread(target=self._camera_read_loop, daemon=True)
        self.camera_thread.start()

        self.preview_running = True

        return True

    def _camera_read_loop(self):
        """Runs on a background thread, NOT the main UI thread - keeps
        calling cap.read() in a loop regardless of how long any single
        call takes, storing only the latest successful frame. This is
        what actually keeps the UI (spinner, buttons, everything) fully
        responsive even during a genuinely slow/stuck camera read.
        """
        while self.camera_thread_running:
            cap = self.cap
            if cap is None:
                break
            try:
                ret, frame = cap.read()
            except Exception:
                ret, frame = False, None

            if ret and frame is not None:
                with self.camera_frame_lock:
                    self.latest_frame_raw = frame
                    self.last_frame_time = time.time()
            else:
                time.sleep(0.05)  # avoid a tight spin loop on rapid repeated failures

    def stop_camera(self):
        self.preview_running = False
        self.camera_thread_running = False

        if self.camera_thread is not None:
            self.camera_thread.join(timeout=2.0)
            self.camera_thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self.camera_released_at = time.time()

        with self.camera_frame_lock:
            self.latest_frame_raw = None

    def draw_spinner_frame(self):
        """Rotates the loading spinner by one step - reschedules itself
        via root.after() until stop_spinner() cancels it. Guards against
        the canvas having already been destroyed by a screen change."""
        if getattr(self, "spinner_canvas", None) is None:
            return
        try:
            self.spinner_angle = (self.spinner_angle + 20) % 360
            self.spinner_canvas.delete("spinner")
            self.spinner_canvas.create_arc(
                4, 4, 36, 36,
                start=self.spinner_angle,
                extent=270,
                style="arc",
                width=4,
                outline=CAPTURE_COLOR,
                tags="spinner",
            )
            self.spinner_after_id = self.root.after(80, self.draw_spinner_frame)
        except tk.TclError:
            pass  # canvas was destroyed by a screen change - stop quietly

    def stop_spinner(self):
        """Stops and removes the loading spinner - called once the camera
        confirms its first real frame (see update_preview)."""
        if getattr(self, "spinner_after_id", None) is not None:
            try:
                self.root.after_cancel(self.spinner_after_id)
            except Exception:
                pass
            self.spinner_after_id = None

        if getattr(self, "spinner_canvas", None) is not None:
            try:
                self.spinner_canvas.destroy()
            except Exception:
                pass
            self.spinner_canvas = None

    # ============================================================
    # AUDIO
    # ============================================================

    def play_tone(self, frequency, duration):
        """Plays a single tone at `frequency` Hz for `duration` seconds via
        the speaker's Signal pin. No-op if the speaker isn't available.

        This blocks the UI thread for `duration` - acceptable here since
        every call is well under 200ms total, but worth knowing if any
        future sound needs to be longer.
        """
        if not self.speaker_available:
            return
        try:
            pwm = GPIO.PWM(SPEAKER_PIN, frequency)
            pwm.start(50)
            time.sleep(duration)
            pwm.stop()
        except Exception as e:
            print("Speaker playback failed:", e)

    def play_countdown_beep(self):
        """One short beep - called once per number during the 3-2-1
        countdown (not the full sequence at once - each call is one tick).
        700Hz - a middle ground between 880 (too high/screeching on this
        speaker) and 500 (too low). Distinctness from the other two sounds
        now relies more on PATTERN (single repeated beep vs. two-tone blip
        vs. 3-note rising chime) than pitch separation alone, since this
        sits closer to success_chime's range than before.
        """
        self.play_tone(700, 0.12)

    def play_capture_sound(self):
        """Quick two-tone rising 'blip' for the actual capture moment -
        higher-pitched and snappier than the countdown beeps, so it reads
        as a clearly different event, not just another countdown tick."""
        self.play_tone(1200, 0.04)
        self.play_tone(1600, 0.06)

    def play_success_chime(self):
        """Rising 3-note major arpeggio (C5-E5-G5) - a standard 'good
        news' pattern, played once the download/QR screen is ready."""
        self.play_tone(523.25, 0.12)
        self.play_tone(659.25, 0.12)
        self.play_tone(783.99, 0.18)

    # ============================================================
    # SCREEN 1: LIVE PREVIEW + CAPTURE
    # ============================================================

    def show_live_screen(self):
        self.clear_screen()

        self.countdown_number = None
        self.current_frame = None

        # Status text shares the top bar row with settings - reclaims a
        # full row of vertical height for the preview on an 800x480 screen.
        _, self.status_label = self.build_top_bar(left_text="Starting camera...")

        # Real animated spinner (not just text) shown while the camera is
        # starting up - a rotating arc on a small canvas, removed the
        # moment update_preview() confirms the first real frame.
        self.spinner_canvas = tk.Canvas(
            self.root, width=40, height=40, bg=BG_COLOR, highlightthickness=0
        )
        self.spinner_canvas.pack(pady=(2, 0))
        self.spinner_angle = 0
        self.spinner_after_id = None
        self.draw_spinner_frame()

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

        self.live_screen_active = True

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
            self.update_preview()

    def update_preview(self):
        if not self.preview_running or self.cap is None or not self.live_screen_active:
            return

        with self.camera_frame_lock:
            frame = self.latest_frame_raw
            self.latest_frame_raw = None  # consume it, so we don't redraw the same frame twice

        if frame is not None:
            # First real frame since (re)starting the camera - THIS is
            # what actually confirms readiness, not isOpened() in
            # start_camera(), which can report true well before frames
            # genuinely start flowing (the real cause of the countdown
            # completing while the actual capture still lagged behind it).
            if str(self.capture_button["state"]) == "disabled":
                self.capture_button.config(state="normal")
                self.status_label.config(text="Ready")
                self.stop_spinner()

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
            if str(self.capture_button["state"]) == "disabled":
                self.status_label.config(text="Starting camera...")
            else:
                self.status_label.config(text="Camera frame not received")

        # 1080p webcam preview, ~24fps. Only affects preview smoothness -
        # the actual captured photo is a separate, fresh grab either way.
        self.root.after(42, self.update_preview)

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
            self.status_label.config(text=str(self.countdown_number))
            self.play_countdown_beep()
            self.root.after(1000, self.next_countdown_number)
        else:
            # "0" - the actual capture beat. No separate countdown beep
            # here - the capture sound itself (played inside
            # finish_capture) IS the 4th, evenly-spaced beat, not an
            # early/late capture relative to what's visible on screen.
            self.status_label.config(text="0")
            self.root.update_idletasks()  # force "0" to actually render before finish_capture changes the text again
            self.finish_capture()

    def next_countdown_number(self):
        if self.countdown_number is None:
            return

        self.countdown_number -= 1
        self.countdown_tick()

    def finish_capture(self):
        if self.current_frame is None:
            self.countdown_number = None
            self.capture_button.config(state="normal")
            self.status_label.config(text="Camera not ready")
            return

        self.play_capture_sound()
        self.countdown_number = None

        # Use the current live-preview frame DIRECTLY as the captured
        # photo - no separate resolution change, no extra camera read at
        # all. This used to attempt a 4K oversample, but changing
        # resolution turned out to be the actual, consistent trigger for
        # the camera flakiness fought all session - confirmed by it
        # happening on the simplest possible capture, first try, nothing
        # else touched. Capturing at the same resolution the live preview
        # is already reliably running at eliminates that operation
        # entirely. Loses the oversample bonus; reliability wins here.
        self.captured_frame = self.current_frame.copy()

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
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        retake_btn.grid(row=0, column=0, padx=10)

        proceed_btn = self.make_button(
            button_row,
            text="PROCEED",
            command=self.show_processing_screen,
            bg=CONFIRM_COLOR,
            fg="black",
            width=18,
            height=1,
            font=BUTTON_FONT,
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
            font=TITLE_FONT,
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

        # Spinner instead of a progress bar - a bar implies a real
        # percentage, which doesn't genuinely exist for mask creation
        # (duration isn't known ahead of time), and the per-background
        # step's real progress is already stated plainly in the text
        # label above ("Background X of Y..."), so a bar there was
        # redundant rather than adding real information.
        self.spinner_canvas = tk.Canvas(
            content, width=40, height=40, bg=BG_COLOR, highlightthickness=0
        )
        self.spinner_canvas.pack()
        self.spinner_angle = 0
        self.spinner_after_id = None
        self.draw_spinner_frame()

        self.root.update_idletasks()
        self.root.after(100, self.begin_processing)

    def begin_processing(self):
        if self.captured_frame is None:
            self.show_error_screen("No captured photo found.")
            return

        if not self.backgrounds:
            self.show_error_screen("No backgrounds found.")
            return

        # Camera only actually closes here, once the user has committed to
        # this photo - stays open through capture review/retake so retake
        # never needs the reopen cycle that's been causing instability.
        self.stop_camera()

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_folder = os.path.join(SAVE_FOLDER, f"session_{timestamp}")
            os.makedirs(self.session_folder, exist_ok=True)

            self.output_files = []
            self.selected_outputs = set()
            self.gallery_index = 0

            self.processing_progress_label.config(text="Analysing your photo - takes a moment...")
            self.root.update_idletasks()

            self._process_frame = cv2.resize(
                self.captured_frame,
                (OUTPUT_WIDTH, OUTPUT_HEIGHT),
                interpolation=cv2.INTER_AREA,
            )

            # Mask creation runs on a background thread - it's the one
            # genuinely heavy, duration-unpredictable step (1-7s+ per
            # timing logs), and running it directly here on the main
            # thread was what froze the whole app - spinner included -
            # for that entire window. Same underlying issue as the
            # camera-read and rclone freezes fixed earlier, just never
            # applied to this specific step until now.
            threading.Thread(target=self._create_mask_thread, daemon=True).start()

        except Exception as e:
            print("Processing error:", e)
            self.show_error_screen(f"Processing error:\n{e}")

    def _create_mask_thread(self):
        """Runs OFF the main thread - create_person_alpha_mask() (YOLO +
        MediaPipe inference) never touches Tkinter widgets directly
        (verified), so it's safe here. Hops back to the main thread via
        root.after(0, ...) once done, same pattern as snapshot/download
        threading - never touch widgets directly from a background thread.
        """
        mask_start = time.time()
        try:
            alpha = self.create_person_alpha_mask(self._process_frame)
            print(f"[timing] Mask creation (this photo): {time.time() - mask_start:.2f}s")
            self.root.after(0, lambda: self._on_mask_ready(alpha))
        except Exception as e:
            print("Mask creation error:", e)
            self.root.after(0, lambda msg=str(e): self.show_error_screen(f"Processing error:\n{msg}"))

    def _on_mask_ready(self, alpha):
        self._process_alpha = alpha
        self._process_bg_index = 0
        self.processing_title_label.config(text="Applying backgrounds...")
        self.processing_progress_label.config(text=f"Background 1 of {len(self.backgrounds)}...")
        self.root.after(10, self.process_next_background)

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
                final = self.add_event_banner(final)

                # JPEG, not PNG: the final composite is a photograph with
                # no transparency (compositing already happened), which is
                # exactly what JPEG's compression is built for - PNG's
                # lossless/palette approach is a better fit for graphics
                # with sharp edges and flat colors, not continuous-tone
                # photos. Quality 85 matches Instagram's own real-world
                # range (~70-85%) for exactly this kind of content.
                out_name = f"{self.safe_name(bg_path)}.jpg"
                out_path = os.path.join(self.session_folder, out_name)

                cv2.imwrite(out_path, final, [cv2.IMWRITE_JPEG_QUALITY, 85])
                self.output_files.append(out_path)

            self._process_bg_index += 1

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

        self.stop_spinner()
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
        for the body, then a focused general-model matting pass on just
        the hair/head portion of each crop for finer edge detail (see
        refine_hair_region / matte_region). Falls back to full-frame
        MediaPipe if YOLO isn't available or finds nobody.
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

    def add_event_banner(self, image_bgr):
        """Third layer on top of the already-composited person+background
        image, not baked into the background itself, so it's never
        blocked by whoever's standing in the shot.

        If a custom-designed graphic exists at EVENT_GRAPHIC_PATH (a
        1920x1080 PNG with real transparency, OBS-overlay style), that's
        used - alpha-composited on top of the photo, with just the date
        drawn live at EVENT_DATE_POSITION. Otherwise falls back to a
        plain programmatic banner automatically, so nothing breaks while
        the real graphic is still being designed.
        """
        if os.path.exists(EVENT_GRAPHIC_PATH):
            return self._apply_custom_event_graphic(image_bgr)
        return self._apply_plain_event_banner(image_bgr)

    def _apply_custom_event_graphic(self, image_bgr):
        """Alpha-composites a custom-designed PNG overlay on top of the
        photo, then draws just the live date on top of that - the static
        design comes from the graphic, only the date is generated here.
        """
        try:
            pil_photo = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
            overlay_graphic = Image.open(EVENT_GRAPHIC_PATH).convert("RGBA")

            if overlay_graphic.size != pil_photo.size:
                overlay_graphic = overlay_graphic.resize(pil_photo.size, Image.LANCZOS)

            # Respects the PNG's own transparency - only the parts the
            # designer actually drew show up, everything else lets the
            # photo underneath show through untouched.
            composited = Image.alpha_composite(pil_photo, overlay_graphic)

            draw = ImageDraw.Draw(composited)
            try:
                date_font = ImageFont.truetype(EVENT_BANNER_FONT_PATH, EVENT_DATE_FONT_SIZE)
            except Exception:
                date_font = ImageFont.load_default()

            date_text = datetime.now().strftime(EVENT_DATE_FORMAT)
            date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
            date_w = date_bbox[2] - date_bbox[0]
            date_h = date_bbox[3] - date_bbox[1]

            # EVENT_DATE_POSITION is the CENTER point of the text.
            x = EVENT_DATE_POSITION[0] - date_w // 2
            y = EVENT_DATE_POSITION[1] - date_h // 2
            draw.text((x, y), date_text, font=date_font, fill=EVENT_DATE_COLOR)

            return cv2.cvtColor(np.array(composited.convert("RGB")), cv2.COLOR_RGB2BGR)

        except Exception as e:
            print("Custom event graphic failed, falling back to plain banner:", e)
            return self._apply_plain_event_banner(image_bgr)

    def _apply_plain_event_banner(self, image_bgr):
        """Simple semi-transparent banner with the event text and date -
        used until a custom graphic exists at EVENT_GRAPHIC_PATH, or if
        loading that graphic ever fails for any reason.
        """
        height, width = image_bgr.shape[:2]
        banner_height = int(height * 0.11)

        overlay = image_bgr.copy()
        cv2.rectangle(overlay, (0, height - banner_height), (width, height), (0, 0, 0), -1)
        image_bgr = cv2.addWeighted(overlay, EVENT_BANNER_OPACITY, image_bgr, 1 - EVENT_BANNER_OPACITY, 0)

        pil_image = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        try:
            title_font = ImageFont.truetype(EVENT_BANNER_FONT_PATH, int(banner_height * 0.38))
            date_font = ImageFont.truetype(EVENT_DATE_FONT_PATH, int(banner_height * 0.20))
        except Exception as e:
            print("Event banner font not found, using PIL default:", e)
            title_font = ImageFont.load_default()
            date_font = title_font

        date_text = datetime.now().strftime(EVENT_DATE_FORMAT)

        title_bbox = draw.textbbox((0, 0), EVENT_BANNER_TEXT, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_w = date_bbox[2] - date_bbox[0]

        title_y = height - banner_height + int(banner_height * 0.12)
        date_y = height - banner_height + int(banner_height * 0.66)

        draw.text(((width - title_w) // 2, title_y), EVENT_BANNER_TEXT, font=title_font, fill=(255, 255, 255))
        draw.text(((width - date_w) // 2, date_y), date_text, font=date_font, fill=(210, 210, 210))

        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

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

        nav_font = BUTTON_FONT
        image_row = tk.Frame(self.root, bg=BG_COLOR)
        image_row.pack(pady=(4, 4))

        prev_btn = self.make_button(
            image_row,
            text="<",
            command=self.previous_output,
            bg=BUTTON_DARK,
            fg=BUTTON_TEXT,
            width=4,
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
            width=4,
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
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        self.select_btn.grid(row=0, column=0, padx=10)

        self.download_btn = self.make_button(
            primary_group,
            text="DOWNLOAD",
            command=self.start_download_flow,
            bg=CONFIRM_COLOR,
            fg="black",
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        self.download_btn.grid(row=0, column=1, padx=10)

        self.update_gallery_image()

    def retake_photo(self):
        """Discard this session's outputs entirely and go back to live
        preview to recapture from scratch — used when the user doesn't
        like the photo or how the background removal turned out.

        Only cleans up the local folder immediately - Google Drive is left
        alone entirely (cleaned up manually, see the LOCAL CLEANUP comment
        near the top of the file).
        """
        if self.session_folder and os.path.exists(self.session_folder):
            try:
                shutil.rmtree(self.session_folder)
            except Exception as e:
                print("Retake cleanup error:", e)

        self.session_folder = None
        self.output_files = []
        self.selected_outputs = set()
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

        content = tk.Frame(container, bg=BG_COLOR)
        content.pack(expand=True)

        label = Label(
            content,
            text="Preparing your download...",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        label.pack(pady=(0, 8))

        self.spinner_canvas = tk.Canvas(
            content, width=40, height=40, bg=BG_COLOR, highlightthickness=0
        )
        self.spinner_canvas.pack()
        self.spinner_angle = 0
        self.spinner_after_id = None
        self.draw_spinner_frame()

        # Created but NOT packed yet - only shown via
        # _show_fallback_notice() if the daemon actually fails and the
        # app falls back to a direct rclone call, which is genuinely
        # slower. No point showing this on a normal, fast download.
        self.fallback_notice_label = Label(
            content,
            text="Taking longer than usual...",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )

        self.root.update_idletasks()
        threading.Thread(target=self.process_download, daemon=True).start()

    def _show_fallback_notice(self):
        """Called (via root.after, so always on the main thread) only
        when rclone_copy_file/rclone_get_link actually fall back to a
        direct subprocess call - i.e. only on a genuinely slower path,
        never on a normal fast download."""
        if hasattr(self, "fallback_notice_label") and self.fallback_notice_label.winfo_exists():
            self.fallback_notice_label.pack(pady=(8, 0))

    def process_download(self):
        """Runs OFF the main thread. rclone's upload/link calls
        (subprocess.run) can take many seconds depending on connection
        quality, and were blocking the main thread directly - which is
        why the spinner used to animate partway then freeze solid until
        the upload finished, rather than spinning the whole time.
        """
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

            # Only zip when there's more than one photo - a single JPEG
            # uploads and downloads directly, no reason to make the user
            # unzip something for just one file.
            if len(selected_paths) == 1:
                upload_path = selected_paths[0]
                # NOT os.path.basename(upload_path) - that's just the
                # background template's name (e.g. "beach.jpg"), identical
                # across every session that uses the same template. Drive
                # allows multiple files with the same name to coexist, so
                # reusing it caused rclone link to sometimes resolve to an
                # OLDER same-named upload from a past session instead of
                # this one. Session-timestamped name guarantees uniqueness.
                upload_filename = f"{session_name}.jpg"
                print("[info] Single image selected - uploading JPEG directly, no zip")
            else:
                upload_filename = f"{session_name}.zip"
                upload_path = os.path.join(self.session_folder, upload_filename)

                zip_start = time.time()
                with zipfile.ZipFile(upload_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for path in selected_paths:
                        zf.write(path, arcname=os.path.basename(path))
                print(f"[timing] Zip creation: {time.time() - zip_start:.1f}s")

            remote_target = f"{RCLONE_REMOTE}:{RCLONE_REMOTE_FOLDER}"

            # Daemon-first, subprocess-fallback (see rclone_copy_file /
            # rclone_get_link) - fast when the daemon cooperates, still
            # reliable via the old proven subprocess approach if it doesn't.
            copy_start = time.time()
            self.rclone_copy_file(upload_path, remote_target, upload_filename)
            print(f"[timing] rclone copy (upload): {time.time() - copy_start:.1f}s")

            link_start = time.time()
            share_url = self.rclone_get_link(remote_target, upload_filename)
            print(f"[timing] rclone link (share URL): {time.time() - link_start:.1f}s")

            if not share_url:
                raise RuntimeError("rclone did not return a share link")

            qr_image = qrcode.make(share_url)
            qr_path = os.path.join(QR_SAVE_DIR, f"{session_name}.png")
            qr_image.save(qr_path)

            # Never touch Tkinter widgets directly from a background
            # thread - hop back to the main thread via root.after(0, ...).
            self.root.after(0, lambda: self._on_download_success(qr_path))

        except Exception as e:
            print("Download error:", e)
            error_text = str(e)
            self.root.after(0, lambda msg=error_text: self._on_download_error(f"Download error:\n{msg}"))

    def _on_download_success(self, qr_path):
        self.stop_spinner()
        self.show_qr_screen(qr_path)

    def _on_download_error(self, message):
        self.stop_spinner()
        self.show_error_screen(message)

    def show_qr_screen(self, qr_path):
        self.clear_screen()
        self.build_top_bar()

        self.play_success_chime()

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
            font=TITLE_FONT,
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

        done_btn = self.make_button(
            content,
            text="DONE",
            command=self.show_live_screen,
            bg=CAPTURE_COLOR,
            fg="black",
            width=18,
            height=1,
            font=BUTTON_FONT,
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
            width=18,
            height=1,
            font=BUTTON_FONT,
            pad_y=8,
        )
        retry_btn.pack(pady=12)

    def rclone_keepalive_loop(self):
        """Runs on a background thread for the app's whole lifetime.
        Periodically pings the daemon with a cheap no-op call, purely to
        keep the underlying connection to Drive from going idle-stale -
        this is separate from (and doesn't replace) the wifi power-save
        setting, since a TCP connection can go stale at the OS/router/
        Drive's own end regardless of the radio's own sleep state.
        """
        while self.rclone_keepalive_running:
            time.sleep(60)
            if not self.rclone_keepalive_running:
                break
            try:
                self.rclone_rc_call("core/version", {}, timeout=10)
            except Exception as e:
                print("rclone keepalive ping failed (not fatal, just a signal something may be stale):", e)

    def rclone_rc_call(self, command, params, timeout=30):
        """Makes a call to the persistent rclone daemon's remote-control
        API instead of spawning a fresh CLI process each time - see the
        RCLONE_RC_PORT comment near the top of the file for why.

        Raises RuntimeError with rclone's own error message (extracted
        from the JSON error body it returns) rather than a generic HTTP
        exception, so failures are still as readable as the old
        subprocess.CalledProcessError + e.stderr approach was.
        """
        url = f"http://localhost:{RCLONE_RC_PORT}/{command}"
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                error_message = error_body.get("error", str(e))
            except Exception:
                error_message = str(e)
            raise RuntimeError(f"rclone {command} failed: {error_message}")

    def rclone_copy_file(self, local_path, dst_fs, dst_remote):
        """Copies a file to Drive via the daemon (fast when it cooperates).
        Falls back to a direct one-off subprocess call the MOMENT the
        daemon fails, no retries - the subprocess fallback is the exact
        same approach that was proven working all session before the
        daemon was added, so reliability doesn't depend on the daemon
        succeeding eventually, just once, immediately.
        """
        try:
            self.rclone_rc_call("operations/copyfile", {
                "srcFs": os.path.dirname(local_path),
                "srcRemote": os.path.basename(local_path),
                "dstFs": dst_fs,
                "dstRemote": dst_remote,
            })
        except Exception as e:
            print("Daemon copy failed, falling back to direct rclone call immediately:", e)
            self.root.after(0, self._show_fallback_notice)
            subprocess.run(
                ["rclone", "copyto", local_path, f"{dst_fs}/{dst_remote}"],
                check=True,
                capture_output=True,
                text=True,
            )

    def rclone_get_link(self, fs, remote):
        """Same daemon-first, immediate-fallback pattern as
        rclone_copy_file - no retries."""
        try:
            result = self.rclone_rc_call("operations/publiclink", {"fs": fs, "remote": remote})
            url = result.get("url", "")
            if url:
                return url
            raise RuntimeError("empty link returned")
        except Exception as e:
            print("Daemon link failed, falling back to direct rclone call immediately:", e)
            self.root.after(0, self._show_fallback_notice)
            result = subprocess.run(
                ["rclone", "link", f"{fs}/{remote}"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()

    def wipe_output_folders(self):
        """Deletes and recreates saved_images/ and qrcodes/ completely
        empty. Called at both app startup and shutdown - no timers, no
        per-session tracking, nothing bound to specific values. Whatever
        exists when this runs gets removed, full stop.

        Google Drive is left alone entirely - cleaned up manually.
        """
        for folder in (SAVE_FOLDER, QR_SAVE_DIR):
            try:
                if os.path.isdir(folder):
                    shutil.rmtree(folder)
                os.makedirs(folder, exist_ok=True)
                print("Wiped:", folder)
            except Exception as e:
                print("Wipe error for", folder, ":", e)

    def close_app(self):
        self.stop_camera()

        self.rclone_keepalive_running = False

        if self.rclone_daemon_process is not None:
            try:
                self.rclone_daemon_process.terminate()
                self.rclone_daemon_process.wait(timeout=3)
            except Exception:
                try:
                    self.rclone_daemon_process.kill()
                except Exception:
                    pass

        self.wipe_output_folders()

        try:
            self.segmenter.close()
        except Exception:
            pass

        if self.speaker_available:
            try:
                GPIO.cleanup()
            except Exception:
                pass

        self.root.destroy()


def fix_system_clock():
    """The school network blocks NTP (UDP 123), so the Pi's clock can
    drift to a wrong date after being offline - which can cause TLS
    handshake failures for the rclone Drive uploads, since certificate
    validity checks depend on the system clock being roughly correct.
    This was very possibly a contributing factor to some of the upload
    flakiness fought earlier. HTTPS isn't blocked, so this grabs the
    correct time from a normal web response's Date header instead of NTP.

    Requires passwordless sudo for the default 'pi' user (the Raspberry
    Pi OS default, already true unless this was specifically changed).
    Best-effort - if it fails for any reason (no network yet, sudo not
    configured, etc.), prints a warning and the app continues anyway
    rather than blocking startup on this.
    """
    try:
        result = subprocess.run(
            ["bash", "-c",
             "sudo date -s \"$(curl -sI --max-time 5 https://google.com | grep -i '^date:' | cut -d' ' -f2-)\""],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            print("System clock corrected via HTTPS:", result.stdout.strip())
        else:
            print("Clock correction did not succeed (continuing anyway):", result.stderr.strip())
    except Exception as e:
        print("Clock correction failed (continuing anyway):", e)


if __name__ == "__main__":
    fix_system_clock()
    root = tk.Tk()
    app = PhotoboothApp(root)
    root.mainloop()