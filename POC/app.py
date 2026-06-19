import os
import cv2
import time
import tkinter as tk
from tkinter import Label, Button
from datetime import datetime

import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

from style import (
    BG_COLOR,
    PREVIEW_BG,
    TEXT_COLOR,
    MUTED_TEXT_COLOR,
    SELECTED_COLOR,
    NORMAL_BUTTON_COLOR,
    NORMAL_BUTTON_TEXT,
    ARROW_BUTTON_COLOR,
    ARROW_BUTTON_TEXT,
    ARROW_ACTIVE_COLOR,
    CAPTURE_COLOR,
    CONFIRM_COLOR,
    RETAKE_COLOR,
    EXIT_COLOR,
    DANGER_COLOR,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    THUMB_WIDTH,
    THUMB_HEIGHT,
    VISIBLE_THUMBNAILS,
    TITLE_FONT,
    LABEL_FONT,
    BUTTON_FONT,
    SMALL_BUTTON_FONT,
)


# ============================================================
# PATHS AND SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_DIR = os.path.join(BASE_DIR, "assets", "backgrounds")
SAVE_FOLDER = os.path.join(BASE_DIR, "saved_images")

os.makedirs(BACKGROUND_DIR, exist_ok=True)
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Use direct video device path to avoid camera-index confusion.
# Tested working with Logitech BRIO USB webcam.
CAMERA_DEVICE = "/dev/video0"

# Final saved PNG requirement: 1080p 16:9.
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Auto-delete final image after 15 minutes.
AUTO_DELETE_MS = 15 * 60 * 1000


class PhotoboothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photobooth")
        self.root.configure(bg=BG_COLOR)
        self.root.attributes("-fullscreen", True)

        self.cap = None
        self.preview_running = False

        self.current_frame = None
        self.captured_frame = None

        self.tk_preview_image = None
        self.tk_result_image = None
        self.thumbnail_images = []
        self.thumbnail_cache = {}

        self.backgrounds = self.load_backgrounds()
        self.selected_bg_index = 0
        self.bg_page_start = 0

        self.saved_file_path = None
        self.delete_timer_id = None

        # MediaPipe Selfie Segmentation
        self.mp_selfie = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie.SelfieSegmentation(model_selection=1)

        # Escape key exits app if keyboard is connected
        self.root.bind("<Escape>", lambda event: self.close_app())

        self.show_live_screen()

    # ============================================================
    # BACKGROUND HELPERS
    # ============================================================

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

    def format_bg_name(self, path):
        return os.path.splitext(os.path.basename(path))[0].upper()

    def selected_background_name(self):
        if not self.backgrounds:
            return "None"
        return os.path.basename(self.backgrounds[self.selected_bg_index])

    # ============================================================
    # UI HELPERS
    # ============================================================

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def make_placeholder(self):
        placeholder = Image.new("RGB", (PREVIEW_WIDTH, PREVIEW_HEIGHT), (28, 30, 36))
        self.tk_preview_image = ImageTk.PhotoImage(placeholder)
        self.preview_label.config(image=self.tk_preview_image)

    def make_button(
        self,
        parent,
        text,
        command,
        width=10,
        height=2,
        bg=NORMAL_BUTTON_COLOR,
        fg=NORMAL_BUTTON_TEXT,
    ):
        return Button(
            parent,
            text=text,
            font=BUTTON_FONT,
            width=width,
            height=height,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )

    # ============================================================
    # CAMERA
    # ============================================================

    def start_camera(self):
        self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

        # USB webcam tested at 640x480.
        # UI preview is resized to fit the 7-inch screen.
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        if not self.cap.isOpened():
            self.status_label.config(text=f"Camera error: {CAMERA_DEVICE} not opened")
            return False

        time.sleep(0.5)
        self.preview_running = True
        return True

    def stop_camera(self):
        self.preview_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def delayed_start_camera(self):
        if self.start_camera():
            self.capture_button.config(state="normal")
            self.status_label.config(
                text=f"Selected background: {self.selected_background_name()}"
            )
            self.update_preview()


    # ============================================================
    # LIVE SCREEN
    # ============================================================

    def show_live_screen(self):
        self.stop_camera()
        self.clear_screen()

        title = Label(
            self.root,
            text="PHOTOBOOTH",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        title.pack(pady=3)

        subtitle = Label(
            self.root,
            text="Choose a background, then press capture",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )
        subtitle.pack(pady=1)

        self.preview_label = Label(self.root, bg=PREVIEW_BG)
        self.preview_label.pack(pady=2)
        self.make_placeholder()

        self.status_label = Label(
            self.root,
            text=f"Selected background: {self.selected_background_name()}",
            font=LABEL_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        self.status_label.pack(pady=1)

        # Background thumbnail selector
        self.thumbnail_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.thumbnail_frame.pack(pady=2)

        self.left_button = Button(
            self.thumbnail_frame,
            text="<",
            font=("Arial", 16, "bold"),
            width=3,
            height=2,
            command=self.previous_background_page,
            bg=ARROW_BUTTON_COLOR,
            fg=ARROW_BUTTON_TEXT,
            activebackground=ARROW_ACTIVE_COLOR,
            activeforeground=ARROW_BUTTON_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.left_button.grid(row=0, column=0, padx=4)

        self.thumbnail_buttons = []
        self.thumbnail_images = []

        for i in range(VISIBLE_THUMBNAILS):
            btn = Button(
                self.thumbnail_frame,
                text=f"BG {i + 1}",
                font=SMALL_BUTTON_FONT,
                compound="top",
                command=lambda index=i: self.select_visible_background(index),
                bg=NORMAL_BUTTON_COLOR,
                fg=NORMAL_BUTTON_TEXT,
                activebackground="#333333",
                activeforeground="white",
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=3,
                pady=2,
            )
            btn.grid(row=0, column=i + 1, padx=4)
            self.thumbnail_buttons.append(btn)

        self.right_button = Button(
            self.thumbnail_frame,
            text=">",
            font=("Arial", 16, "bold"),
            width=3,
            height=2,
            command=self.next_background_page,
            bg=ARROW_BUTTON_COLOR,
            fg=ARROW_BUTTON_TEXT,
            activebackground=ARROW_ACTIVE_COLOR,
            activeforeground=ARROW_BUTTON_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.right_button.grid(row=0, column=VISIBLE_THUMBNAILS + 1, padx=4)

        self.update_thumbnail_buttons()

        # Main controls
        self.control_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.control_frame.pack(pady=3)

        self.capture_button = self.make_button(
            self.control_frame,
            text="CAPTURE",
            command=self.capture_photo,
            width=12,
            height=2,
            bg=CAPTURE_COLOR,
            fg="black",
        )
        self.capture_button.config(state="disabled")
        self.capture_button.grid(row=0, column=0, padx=8)

        self.exit_button = self.make_button(
            self.control_frame,
            text="EXIT",
            command=self.close_app,
            width=8,
            height=2,
            bg=EXIT_COLOR,
            fg="white",
        )
        self.exit_button.grid(row=0, column=1, padx=8)

        self.status_label.config(text="Starting camera...")
        self.root.after(400, self.delayed_start_camera)

    def get_thumbnail_image(self, bg_path):
        # Cache thumbnail images so background selection does not freeze the UI.
        if bg_path in self.thumbnail_cache:
            return self.thumbnail_cache[bg_path]

        thumb = Image.open(bg_path).convert("RGB")
        thumb = thumb.resize((THUMB_WIDTH, THUMB_HEIGHT))
        tk_thumb = ImageTk.PhotoImage(thumb)

        self.thumbnail_cache[bg_path] = tk_thumb
        return tk_thumb

    def update_thumbnail_buttons(self):
        self.thumbnail_images = []

        for i, btn in enumerate(self.thumbnail_buttons):
            bg_index = self.bg_page_start + i

            if bg_index < len(self.backgrounds):
                bg_path = self.backgrounds[bg_index]
                name = self.format_bg_name(bg_path)

                try:
                    tk_thumb = self.get_thumbnail_image(bg_path)
                    self.thumbnail_images.append(tk_thumb)

                    btn.config(text=name, image=tk_thumb, state="normal")

                except Exception as e:
                    print("Thumbnail error:", e)
                    btn.config(text=name, image="", state="normal")

                if bg_index == self.selected_bg_index:
                    btn.config(
                        bg=SELECTED_COLOR,
                        fg="black",
                        relief="solid",
                        bd=3,
                    )
                else:
                    btn.config(
                        bg=NORMAL_BUTTON_COLOR,
                        fg=NORMAL_BUTTON_TEXT,
                        relief="flat",
                        bd=0,
                    )

            else:
                btn.config(
                    text="-",
                    image="",
                    state="disabled",
                    bg=BG_COLOR,
                    fg=MUTED_TEXT_COLOR,
                    relief="flat",
                    bd=0,
                )

    def select_visible_background(self, visible_index):
        bg_index = self.bg_page_start + visible_index

        if bg_index < len(self.backgrounds):
            self.selected_bg_index = bg_index
            self.status_label.config(
                text=f"Selected background: {self.selected_background_name()}"
            )
            self.update_thumbnail_buttons()

    def previous_background_page(self):
        self.bg_page_start = max(0, self.bg_page_start - VISIBLE_THUMBNAILS)
        self.update_thumbnail_buttons()

    def next_background_page(self):
        if self.bg_page_start + VISIBLE_THUMBNAILS < len(self.backgrounds):
            self.bg_page_start += VISIBLE_THUMBNAILS
        self.update_thumbnail_buttons()

    def update_preview(self):
        if not self.preview_running or self.cap is None:
            return

        ret, frame = self.cap.read()

        if ret:
            # Mirror preview for better photobooth experience
            frame = cv2.flip(frame, 1)
            self.current_frame = frame.copy()

            # Live preview is normal camera view.
            display_frame = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
            display_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

            image = Image.fromarray(display_rgb)
            self.tk_preview_image = ImageTk.PhotoImage(image=image)
            self.preview_label.config(image=self.tk_preview_image)
        else:
            self.status_label.config(text="Camera frame not received")

        # About 20 FPS target. Teacher said slight lag is acceptable if reliable.
        self.root.after(90, self.update_preview)

    # ============================================================
    # CAPTURE / CONFIRM FLOW
    # ============================================================

    def capture_photo(self):
        if self.current_frame is None:
            self.status_label.config(text="No camera frame available")
            return

        self.captured_frame = self.current_frame.copy()
        self.stop_camera()
        self.show_confirm_screen()

    def show_confirm_screen(self):
        self.clear_screen()

        title = Label(
            self.root,
            text="PHOTO CAPTURED",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        title.pack(pady=3)

        display_frame = cv2.resize(self.captured_frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
        display_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(display_rgb)
        self.tk_result_image = ImageTk.PhotoImage(image=image)

        image_label = Label(self.root, image=self.tk_result_image, bg=BG_COLOR)
        image_label.pack(pady=3)

        info = Label(
            self.root,
            text=f"Selected background: {self.selected_background_name()}",
            font=LABEL_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        info.pack(pady=1)

        prompt = Label(
            self.root,
            text="Retake if needed, or confirm to process final image",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )
        prompt.pack(pady=1)

        button_frame = tk.Frame(self.root, bg=BG_COLOR)
        button_frame.pack(pady=3)

        retake_btn = self.make_button(
            button_frame,
            text="RETAKE",
            command=self.retake_photo,
            width=10,
            height=2,
            bg=RETAKE_COLOR,
            fg="black",
        )
        retake_btn.grid(row=0, column=0, padx=8)

        confirm_btn = self.make_button(
            button_frame,
            text="CONFIRM",
            command=self.process_and_save,
            width=10,
            height=2,
            bg=CONFIRM_COLOR,
            fg="black",
        )
        confirm_btn.grid(row=0, column=1, padx=8)

    def retake_photo(self):
        self.stop_camera()
        self.clear_screen()

        label = Label(
            self.root,
            text="Restarting camera...",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        label.pack(expand=True)

        self.root.after(600, self.show_live_screen)


    # ============================================================
    # MEDIAPIPE PROCESSING
    # ============================================================

    def process_and_save(self):
        self.clear_screen()

        label = Label(
            self.root,
            text="PROCESSING...",
            font=("Arial", 24, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        label.pack(expand=True)

        self.root.update()

        if self.captured_frame is None:
            label.config(text="No captured frame found")
            return

        if not self.backgrounds:
            label.config(text="No backgrounds found")
            return

        try:
            final = self.remove_background_and_composite(
                self.captured_frame,
                self.backgrounds[self.selected_bg_index],
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photobooth_{timestamp}.png"
            self.saved_file_path = os.path.join(SAVE_FOLDER, filename)

            final_1080p = cv2.resize(final, (OUTPUT_WIDTH, OUTPUT_HEIGHT))
            cv2.imwrite(self.saved_file_path, final_1080p)

            print("Saved:", self.saved_file_path)

            self.show_final_screen(final_1080p)

            # Start 15-minute auto-delete timer after final image is generated
            if self.delete_timer_id is not None:
                self.root.after_cancel(self.delete_timer_id)

            self.delete_timer_id = self.root.after(
                AUTO_DELETE_MS, self.auto_delete_saved_file
            )

        except Exception as e:
            print("Processing error:", e)
            label.config(text=f"Processing error: {e}")

    def remove_background_and_composite(self, frame, background_path):
        # Resize captured frame to final output resolution
        frame = cv2.resize(frame, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

        background = cv2.imread(background_path)
        if background is None:
            raise ValueError(f"Could not load background: {background_path}")

        background = cv2.resize(background, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

        # MediaPipe needs RGB, OpenCV uses BGR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Raw MediaPipe confidence mask
        result = self.segmenter.process(rgb_frame)
        mask = result.segmentation_mask

        if mask is None:
            raise RuntimeError("MediaPipe did not return a mask")

        # Lightly smooth MediaPipe confidence mask first.
        # Threshold 0.45 is more generous than 0.5, helping include more of the person.
        smooth_mask = cv2.GaussianBlur(mask, (5, 5), 0)
        person_mask = smooth_mask > 0.45

        # Convert to soft alpha mask for smoother edges
        mask_float = person_mask.astype(np.float32)
        mask_float = cv2.GaussianBlur(mask_float, (9, 9), 0)
        mask_3ch = np.dstack([mask_float, mask_float, mask_float])

        # Composite person onto selected background
        final = (frame * mask_3ch + background * (1 - mask_3ch)).astype(np.uint8)

        return final

    # ============================================================
    # FINAL SCREEN / AUTO DELETE
    # ============================================================

    def show_final_screen(self, final_frame):
        self.clear_screen()

        title = Label(
            self.root,
            text="FINAL IMAGE",
            font=TITLE_FONT,
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        title.pack(pady=3)

        display_frame = cv2.resize(final_frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
        display_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(display_rgb)
        self.tk_result_image = ImageTk.PhotoImage(image=image)

        image_label = Label(self.root, image=self.tk_result_image, bg=BG_COLOR)
        image_label.pack(pady=3)

        status = Label(
            self.root,
            text="Saved locally. Auto-delete in 15 minutes.",
            font=LABEL_FONT,
            fg=MUTED_TEXT_COLOR,
            bg=BG_COLOR,
        )
        status.pack(pady=2)

        button_frame = tk.Frame(self.root, bg=BG_COLOR)
        button_frame.pack(pady=3)

        again_btn = self.make_button(
            button_frame,
            text="TAKE ANOTHER",
            command=self.show_live_screen,
            width=13,
            height=2,
            bg=CAPTURE_COLOR,
            fg="black",
        )
        again_btn.grid(row=0, column=0, padx=8)

        exit_btn = self.make_button(
            button_frame,
            text="EXIT",
            command=self.close_app,
            width=8,
            height=2,
            bg=EXIT_COLOR,
            fg="white",
        )
        exit_btn.grid(row=0, column=1, padx=8)

    def auto_delete_saved_file(self):
        if self.saved_file_path and os.path.exists(self.saved_file_path):
            try:
                os.remove(self.saved_file_path)
                print("Auto-deleted:", self.saved_file_path)
                self.saved_file_path = None
            except Exception as e:
                print("Auto-delete error:", e)

    # ============================================================
    # EXIT
    # ============================================================

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
