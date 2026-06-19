# EGL314 Photobooth Project

This repository contains the Proof of Concept documentation and source files for the EGL314 Media Solutioning Project 1 photobooth project.

The project is a self-contained digital photobooth system that combines software, hardware, and enclosure design. The system uses a Raspberry Pi, touchscreen display, USB webcam, OpenCV, and MediaPipe to capture a user photo, remove the original background, replace it with a selected background, and save the final output image.

## Repository Structure

```text
EGL314_TeamF/
├── README.md
├── POC/
│   ├── README.md
│   ├── CODE_STRUCTURE.md
│   ├── app.py
│   ├── style.py
│   ├── requirements.txt
│   ├── assets/
│   │   └── backgrounds/
│   └── images/
│
└── Enclosure/
    ├── README.md
    └── POC/
        ├── CAD/
        ├── STL/
        └── Images/
```

## Sections

### [`POC`](./POC)

The `POC` folder contains the software Proof of Concept for the photobooth application. It includes the Python source code, required dependencies, background assets, hardware reference images, and documentation explaining the system flow and implementation.

### [`Enclosure`](./Enclosure)

The `Enclosure` folder contains the physical enclosure Proof of Concept created by the team. It includes enclosure documentation, CAD files, STL files, images, and design files for the Raspberry Pi, touchscreen display, USB webcam, cable routing, and mounting system.

## Current Status

The current completed stage is the **Proof of Concept**.

The software POC demonstrates that the main photobooth pipeline can run on a Raspberry Pi using a USB webcam, touchscreen display, OpenCV, and MediaPipe background segmentation.

The enclosure POC demonstrates the physical housing design for the Raspberry Pi, touchscreen display, USB webcam, cable routing, and tripod mounting system.

## Future Development

The next stage will be the MVP version of the photobooth system. The MVP will focus on improving the user experience, increasing image quality, generating multiple background outputs, allowing users to select final images, and adding a download or QR code access function.
