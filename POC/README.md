# EGL314 Photobooth POC Documentation

## 1. Project Context and Rationale

This project is a self-contained digital photobooth system designed for EGL314 Media Solutioning Project 1. The goal of the project is to build an interactive booth where users can take a photo, remove the original background, replace it with a selected digital background, and save the final output.

The project is relevant because modern photobooths are commonly used in events, studios, and social spaces. A good photobooth system should be simple to use, visually clear, and able to produce an output that users would actually want to keep. For the Proof of Concept stage, the focus is on proving that the main technical pipeline works before improving the full user experience for the MVP stage.

## 2. POC Objectives

The POC aims to demonstrate the following core functions:

1. Hardware integration between Raspberry Pi, touchscreen display, and USB webcam.
2. Live camera preview using OpenCV.
3. Photo capture and retake flow.
4. Background removal using MediaPipe segmentation.
5. Background replacement using digital image templates.
6. Final image output saved as a 1920 × 1080 PNG.
7. Auto-delete function to remove saved photos after 15 minutes.

## 3. Research and Hypothesis

The POC uses OpenCV for camera capture and image processing because it provides direct webcam access and frame manipulation in Python. MediaPipe Selfie Segmentation is used because it can separate a human subject from the background using a machine-learning segmentation mask.

The main hypothesis is:

> If the Raspberry Pi can reliably capture a webcam image, generate a person segmentation mask, and composite the person onto a new background, then the core photobooth concept is technically feasible for further MVP development.

During testing, lighting and image resolution were identified as important factors affecting background removal quality. Better lighting and higher camera resolution are expected to improve the segmentation result and final image quality.

## 4. System Overview

The POC system uses the following hardware:

* Raspberry Pi 4
* Raspberry Pi touchscreen display
* USB webcam
* Background image templates
* Local storage for saved output images

The software stack includes:

* Python
* OpenCV
* MediaPipe
* NumPy
* Pillow
* Tkinter

## 5. Core Processing Pipeline

The POC follows this image-processing pipeline:

```text
USB Webcam
→ OpenCV camera capture
→ Live preview on touchscreen
→ User captures photo
→ MediaPipe generates segmentation mask
→ Mask is refined and smoothed
→ Person is composited onto selected background
→ Final 1920 × 1080 PNG is saved locally
→ Image is automatically deleted after 15 minutes
```

## 6. User Flow

The POC user flow is:

```text
Live Preview
→ Select Background
→ Capture Photo
→ Retake or Confirm
→ Process Background Removal
→ Save Final Image
→ Auto-delete after 15 minutes
```

For the MVP version, the planned improved flow is:

```text
Live Preview
→ Capture Photo
→ Retake or Proceed
→ Process All Backgrounds
→ Display Gallery of Outputs
→ User Selects Final Image(s)
→ Download / QR Code Access
```

## 7. POC Implementation

The main application is built using `app.py`, with UI settings separated into `style.py`.

### Main Files

| File                  | Purpose                                    |
| --------------------- | ------------------------------------------ |
| `app.py`              | Main photobooth application                |
| `style.py`            | UI colours, fonts, and layout settings     |
| `requirements.txt`    | Python package dependencies                |
| `assets/backgrounds/` | Stores background image templates          |
| `saved_images/`       | Stores generated output images temporarily |
| `docs/`               | Stores documentation images and diagrams   |

## 8. Testing and Observations

The POC successfully demonstrated the main technical functions:

* USB webcam was detected and used for live preview.
* Photo capture worked through the touchscreen UI.
* MediaPipe was able to detect and segment the human subject.
* The selected background was applied to the captured image.
* The final output image was saved locally.
* Auto-delete logic was included to remove the image after 15 minutes.

However, several areas were identified for improvement:

* The original UI did not use the touchscreen screen space efficiently.
* Background removal quality depends heavily on lighting and camera quality.
* MediaPipe segmentation can struggle with hair, body edges, and multiple people.
* The user experience should be improved so the user captures first and chooses from generated outputs later.

## 9. Improvements Planned for MVP

The MVP version will focus on:

1. Improved touchscreen layout with larger live preview.
2. Countdown before photo capture.
3. Capturing at minimum 1920 × 1080 resolution.
4. Running MediaPipe once and reusing the mask across all backgrounds.
5. Gallery view for all generated outputs.
6. Selecting one or multiple final images.
7. Download or QR code access for users.
8. Better background removal quality through improved lighting, mask tuning.

## 10. Conclusion

The POC proves that the main photobooth concept is technically feasible. The Raspberry Pi can capture an image from a USB webcam, process the image using MediaPipe, replace the background, and save the final output locally. The next stage will focus on improving the user experience, output quality, and download process for the MVP version.

