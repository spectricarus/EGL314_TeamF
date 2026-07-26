# EGL314 Photobooth Project

This repository contains the Proof of Concept and MVP documentation and
source files for the EGL314 Media Solutioning Project 1 photobooth project.

The project is a self-contained digital photobooth system that combines
software, hardware, and enclosure design. The system uses a Raspberry Pi,
touchscreen display, USB webcam, OpenCV, and MediaPipe to capture a user
photo, remove the original background, replace it with a selected
background, and save the final output image.

## How the software and hardware fit together

These are documented separately (different team members are responsible for
each), but they form one physical system:

- The **Raspberry Pi** runs the software in this repository directly —
  `finalV6.py` is the app that appears on the touchscreen.
- The **touchscreen display** is what the software's Tkinter GUI renders to.
- The **USB webcam**, mounted in the enclosure, is what the software reads
  from (`CAMERA_DEVICE` in `finalV6.py` points to it).
- The **enclosure** physically houses and positions the Pi, screen, and
  camera, and its cable routing/mounting design determines how those
  components are physically wired to each other.

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
│   ├── images/
│   └── Enclosure/
│       ├── README.md
│       ├── CAD/
│       ├── STL/
│       └── Images/
│
└── MVP/
    ├── README.md
    ├── Hardware/
    └── Software/
        ├── README.md
        ├── finalV6.py
        ├── style.py
        ├── requirements.txt
        ├── docs/
        │   ├── CODE_STRUCTURE.md
        │   ├── environment-setup.md
        │   ├── dependencies.md
        │   ├── file-connections.md
        │   ├── pipeline-explained.md
        │   ├── ui-flow.md
        │   └── background-templates.md
        └── assets/
            ├── pipeline-diagram.svg
            ├── screenshots/
            └── background-templates/
```

## Sections

### [`POC`](./POC)

The `POC` folder contains the software Proof of Concept for the photobooth
application — Python source code, required dependencies, and background
assets.

### [`Enclosure`](./POC/Enclosure)

Nested inside `POC`, this folder contains the physical enclosure design:
CAD files, STL files, images, and documentation for the Raspberry Pi,
touchscreen display, USB webcam, cable routing, and mounting system.

### [`MVP`](./MVP)

The `MVP` folder contains the working MVP version of the photobooth
application — the stage after Proof of Concept, split into two parts:

- [**Software**](./MVP/Software/README.md) — full documentation covering the
  code, dependencies, environment setup, a diagram of the background-removal
  pipeline and the reasoning behind it, and UI flow
- [**Hardware**](./MVP/Hardware) — enclosure and physical build for the MVP
  stage
  