# EGL314 Photobooth POC Documentation

## 1. Project Context and Rationale

This project is a self-contained digital photobooth system designed for EGL314 Media Solutioning Project 1. The goal of the project is to build an interactive booth where users can take a photo, remove the original background, replace it with a selected digital background, and save the final output.

The project is relevant because modern photobooths are commonly used in events, studios, and social spaces. A good photobooth system should be simple to use, visually clear, and able to produce an output that users would actually want to keep. For the Proof of Concept stage, the focus is on proving that the main technical pipeline works before improving the full user experience for the next stage.

## 2. POC Objectives

The POC aims to demonstrate the following core functions:

1. Hardware integration between Raspberry Pi, touchscreen display, and USB webcam.
2. Live camera preview using OpenCV.
3. Background selection through a touchscreen-friendly interface.
4. Photo capture and retake flow.
5. Background removal using MediaPipe segmentation.
6. Background replacement using digital image templates.
7. Final image output saved as a 1920 × 1080 PNG.
8. Auto-delete function to remove saved photos after 15 minutes.

## 3. Research and Hypothesis

The POC uses OpenCV for camera capture and image processing because it provides direct webcam access and frame manipulation in Python. MediaPipe Selfie Segmentation is used because it can separate a human subject from the background using a machine-learning segmentation mask.

The main hypothesis is:

> If the Raspberry Pi can reliably capture a webcam image, generate a person segmentation mask, and composite the person onto a new background, then the core photobooth concept is technically feasible for further development.

During testing, lighting and image resolution were identified as important factors affecting background removal quality. Better lighting and higher camera resolution are expected to improve the segmentation result and final image quality.

## 4. System Overview

The POC system uses the following hardware:

* Raspberry Pi 4 Model B
* Raspberry Pi 7" touchscreen display
* Display ribbon cable for touchscreen connection
* USB webcam
* 32GB microSD card
* Jumper wires and power supply

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
→ User selects a background
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

This flow proves the main photobooth concept. The user can preview themselves, select a background, capture a photo, retake if needed, and confirm the final output.

## 7. POC Implementation

The main application is built using `app.py`, with UI settings separated into `style.py`.

### Main Files

| File / Folder         | Purpose                                                             |
| --------------------- | ------------------------------------------------------------------- |
| `app.py`              | Main photobooth application                                         |
| `style.py`            | UI colours, fonts, preview size, thumbnail size, and button styling |
| `requirements.txt`    | Python package dependencies                                         |
| `assets/backgrounds/` | Stores background image templates                                   |
| `images/`             | Stores hardware setup and connection reference images               |
| `CODE_STRUCTURE.md`   | Explains the source code structure and main functions               |

For a more detailed explanation of the source code structure, main functions, and processing logic, refer to:

[POC Code Structure Documentation](./CODE_STRUCTURE.md)

## 8. Testing and Observations

The POC successfully demonstrated the main technical functions:

* USB webcam was detected and used for live preview.
* Photo capture worked through the touchscreen UI.
* MediaPipe was able to detect and segment the human subject.
* The selected background was applied to the captured image.
* The final output image was saved locally.
* Auto-delete logic was included to remove the image after 15 minutes.

Several technical and UX observations were identified during POC presentation:

* The UI works, but it can use the touchscreen screen space more effectively.
* Background removal quality depends heavily on lighting and camera quality.
* MediaPipe segmentation can struggle with hair, body edges, and multiple people.
* The current POC generates one output based on the selected background.
* The future version should allow the user to capture first, then choose from multiple generated background outputs.

## 9. Improvements Planned for Next Stage

The next stage will focus on improving the photobooth into a more polished MVP.

Planned improvements include:

1. Improved touchscreen layout with a larger live preview.
2. Countdown before photo capture.
3. Capturing at minimum 1920 × 1080 resolution.
4. Running MediaPipe once and reusing the mask across all backgrounds.
5. Processing all background options after the user confirms the captured photo.
6. Gallery view for all generated outputs.
7. Selecting one or multiple final images.
8. Download or QR code access for users.
9. Better background removal quality through improved lighting and mask tuning.

## 10. Conclusion

The POC proves that the main photobooth concept is technically feasible. The Raspberry Pi can capture an image from a USB webcam, process the image using MediaPipe, replace the background, and save the final output locally.

The next stage will focus on improving the user experience, output quality, background removal accuracy, and user download process.
