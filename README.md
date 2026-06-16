# EGL314 Photobooth Project

This repository contains the documentation and source code for the EGL314 System Design & Project Management photobooth project.

The project is divided into two main development stages:

* **POC / Proof of Concept**: Initial working prototype demonstrating hardware integration, camera capture, background removal, background replacement, and local image saving.
* **MVP / Minimum Viable Product**: Improved version with refined user experience, better output selection, download function, and final product-level features.

## Repository Structure

```text
POC/
├── app.py
├── style.py
├── requirements.txt
├── assets/backgrounds/
├── saved_images/
└── docs/

MVP/
└── README.md
```

## Current Status

The current completed stage is the **POC version**. The POC demonstrates that the core photobooth system can run on a Raspberry Pi using a USB webcam, touchscreen display, OpenCV, and MediaPipe background segmentation.

The MVP version will be developed after the POC.
