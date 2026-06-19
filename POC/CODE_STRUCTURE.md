# POC Code Structure Documentation

## Overview

The POC photobooth application is built using two main Python files:

| File       | Purpose                                                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.py`   | Main application logic, user interface flow, camera preview, image capture, MediaPipe processing, background replacement, image saving, and auto-delete |
| `style.py` | UI colours, font settings, preview size, thumbnail size, and button styling                                                                             |

The code is separated this way so that the main application logic remains in `app.py`, while visual styling and layout values can be adjusted in `style.py` without changing the core program logic.

---

## Folder Structure

```text
POC/
├── README.md
├── CODE_STRUCTURE.md
├── app.py
├── style.py
├── requirements.txt
├── assets/
│   └── backgrounds/
└── images/
```

### Folder Purposes

| Folder / File         | Purpose                                                      |
| --------------------- | ------------------------------------------------------------ |
| `app.py`              | Runs the photobooth application                              |
| `style.py`            | Stores interface colours, fonts, and sizing values           |
| `requirements.txt`    | Lists the required Python libraries                          |
| `assets/backgrounds/` | Stores the background image templates used by the photobooth |
| `images/`             | Stores hardware setup and connection reference images        |

Generated output images are created locally during runtime and are not committed to the repository.

---

## Main Application File: `app.py`

`app.py` contains the main photobooth program. It uses Tkinter for the touchscreen interface, OpenCV for USB webcam capture, MediaPipe for background segmentation, NumPy for image compositing, and Pillow for converting images into a Tkinter-compatible display format.

The main class is:

```python
class PhotoboothApp:
```

This class controls the full application, including:

* starting and stopping the camera
* displaying the live preview
* showing background thumbnails
* capturing a photo
* allowing retake or confirm
* processing the image
* saving the final output
* deleting saved images after 15 minutes

---

## Key Settings

At the top of `app.py`, the program defines important file paths and settings.

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_DIR = os.path.join(BASE_DIR, "assets", "backgrounds")
SAVE_FOLDER = os.path.join(BASE_DIR, "saved_images")
```

These settings make sure the app can locate its background images and save generated outputs in the correct folders.

The camera is set using:

```python
CAMERA_DEVICE = "/dev/video0"
```

This is used instead of a generic camera index because the Raspberry Pi may detect multiple video devices. Using `/dev/video0` makes the webcam path more specific and reliable.

The final output resolution is set to:

```python
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
```

This ensures the generated image is saved as a 1920 × 1080 PNG.

The auto-delete timer is set to:

```python
AUTO_DELETE_MS = 15 * 60 * 1000
```

This deletes the final saved image after 15 minutes.

---

## Main User Flow

The POC application follows this user flow:

```text
Live Preview
→ Select Background
→ Capture Photo
→ Retake or Confirm
→ Process Image
→ Display Final Image
→ Auto-delete after 15 minutes
```

This flow proves the core photobooth concept by allowing the user to capture a photo, apply a selected background, and save the final image.

---

## Main Functions in `app.py`

### `load_backgrounds()`

This function loads all background images from:

```text
assets/backgrounds/
```

It supports:

```text
.jpg
.jpeg
.png
```

The images are sorted so that the backgrounds appear in a consistent order every time the app runs.

---

### `start_camera()`

This function starts the USB webcam using OpenCV.

```python
self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
```

The camera preview is set to 640 × 480 for smoother and more reliable performance on the Raspberry Pi during the POC stage.

```python
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

Although the preview is smaller, the final output image is resized and saved at 1920 × 1080.

---

### `stop_camera()`

This function stops the preview loop and releases the camera.

It is used when moving from the live preview screen to the captured image screen, and also when exiting the application.

---

### `delayed_start_camera()`

This function starts the camera after a short delay.

It was added to improve reliability when returning from the retake screen. Without the delay, the camera could sometimes lag or freeze when being reopened too quickly.

---

### `show_live_screen()`

This function displays the main live preview screen.

The screen includes:

* title
* instruction text
* live camera preview
* selected background label
* background thumbnail selector
* capture button
* exit button

The user selects a background first, then presses the capture button.

---

### `get_thumbnail_image()`

This function creates and caches thumbnail images for the background selector.

The thumbnail cache prevents the app from repeatedly loading and resizing image files from storage whenever the user selects a background.

This improves responsiveness on the Raspberry Pi and reduces UI freezing.

---

### `update_thumbnail_buttons()`

This function updates the visible background thumbnail buttons.

Only a few thumbnails are shown at a time to fit the 7-inch touchscreen layout. The selected background is highlighted using a yellow border and different button styling.

---

### `select_visible_background()`

This function changes the selected background when the user taps one of the visible background thumbnails.

It updates:

* selected background index
* selected background label
* thumbnail highlight state

---

### `previous_background_page()` and `next_background_page()`

These functions allow the user to move through the available background options using the left and right arrow buttons.

---

### `update_preview()`

This function continuously reads frames from the webcam and updates the live preview.

The frame is flipped horizontally using:

```python
frame = cv2.flip(frame, 1)
```

This makes the camera preview feel more natural, similar to a phone front camera or real photobooth mirror preview.

The frame is resized to fit the touchscreen preview area before being displayed in Tkinter.

---

### `capture_photo()`

This function stores the current camera frame as the captured image.

After capturing, the camera is stopped and the app moves to the confirmation screen.

---

### `show_confirm_screen()`

This function displays the captured still image and gives the user two choices:

```text
RETAKE
CONFIRM
```

* `RETAKE` returns the user to the live preview.
* `CONFIRM` starts the image processing step.

---

### `retake_photo()`

This function shows a short “Restarting camera...” message before returning to the live preview screen.

This improves stability because the Raspberry Pi needs a short delay before reopening the webcam.

---

### `process_and_save()`

This function handles the full image processing and saving flow.

It:

1. Shows a processing screen.
2. Checks that a photo has been captured.
3. Checks that background images exist.
4. Runs background removal and compositing.
5. Saves the final image.
6. Shows the final output screen.
7. Starts the 15-minute auto-delete timer.

The final file is saved into:

```text
saved_images/
```

---

### `remove_background_and_composite()`

This is the main image processing function.

It performs the following steps:

1. Resize the captured frame to 1920 × 1080.
2. Load and resize the selected background to 1920 × 1080.
3. Convert the image from BGR to RGB for MediaPipe.
4. Run MediaPipe Selfie Segmentation.
5. Generate a segmentation mask.
6. Smooth the mask using Gaussian blur.
7. Apply a threshold of `0.45`.
8. Composite the person onto the selected background.

The threshold value of `0.45` was used because it is slightly more generous than `0.50`, helping to include more of the person, hair, and shoulders.

The mask is blurred again to create smoother edges before compositing.

---

### `show_final_screen()`

This function displays the final generated image.

The screen includes:

* final image preview
* auto-delete message
* take another button
* exit button

---

### `auto_delete_saved_file()`

This function deletes the saved output image after 15 minutes.

This prevents old generated photobooth images from remaining permanently on the Raspberry Pi.

---

### `close_app()`

This function safely exits the application.

It:

* stops the camera
* cancels the auto-delete timer if needed
* closes the MediaPipe segmenter
* destroys the Tkinter window

---

## Style File: `style.py`

`style.py` stores the visual settings for the POC interface.

It includes:

* main background colour
* preview background colour
* text colours
* button colours
* selected thumbnail colour
* preview size
* thumbnail size
* font settings

This makes the UI easier to adjust without editing the main application logic.

For example, the preview size is controlled using:

```python
PREVIEW_WIDTH = 440
PREVIEW_HEIGHT = 248
```

The final saved output is still 1920 × 1080, even though the preview is smaller for touchscreen performance.

---

## POC Limitations

The POC successfully demonstrates the core technical pipeline, but several limitations were identified:

1. The UI works but can use the touchscreen screen space more effectively.
2. The user must select a background before taking the photo.
3. Only one final image is generated per capture.
4. Background removal quality depends heavily on lighting.
5. MediaPipe segmentation can struggle with hair, shoulders, and multiple people.
6. The live preview is kept at a lower resolution for reliability.
7. Download or QR code access is not implemented yet.

---

## Planned Improvements

Future improvements include:

1. Larger live preview using more of the 7-inch screen.
2. Countdown before capture.
3. Higher-resolution image capture.
4. Capturing first before choosing backgrounds.
5. Processing all background options after capture.
6. Running MediaPipe once and reusing the mask for all background outputs.
7. Gallery view for generated outputs.
8. Selecting one or multiple final images.
9. Download or QR code access.
10. Improved lighting and mask tuning for better background removal.
