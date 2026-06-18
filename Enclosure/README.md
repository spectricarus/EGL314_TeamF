# EGL314 Photobooth Enclosure POC Documentation

## 1. Project Context and Rationale

This enclosure was designed for the EGL314 Photobooth Project. The purpose of the enclosure is to house and protect the Raspberry Pi 4, touchscreen display, USB webcam, power cabling, and supporting hardware while maintaining portability and convenient assembly.

The enclosure is intended to be mounted onto a tripod, allowing the photobooth system to be deployed in various locations. The design must also allow access to power, USB connections, and future maintenance.

For the Proof of Concept (POC) stage, the focus is on demonstrating that the enclosure can physically accommodate all required components and that the major structural features can be successfully manufactured using 3D printing.

## 2. POC Objectives

The enclosure POC aims to demonstrate the following:

* Successful mounting of a Raspberry Pi 4 using standoffs
* Successful mounting of a touchscreen display
* Functional tripod mounting system
* Functional screw-based assembly system
* Space for cable routing
* 3D printable

## 3. Design Requirements

The enclosure must accommodate:

* Raspberry Pi 4
* Raspberry Pi touchscreen display
* USB webcam
* Power supply cable
* USB camera cable

The current enclosure design includes:

* M2.5 mounting points for the Raspberry Pi
* M3 mounting points for the touchscreen
* M3 assembly screws between enclosure panels
* Tripod mounting thread
* Removable top cover

## 4. Current Enclosure Dimensions

### Base

* Length: 220 mm
* Width: 130 mm
* Height: 40 mm

### Front Panel

* Length: 240 mm
* Height: 190 mm
* Thickness: 10 mm

### Back Panel

* Length: 240 mm
* Height: 190 mm
* Thickness: 10 mm

### Side Panels

* Length: 130 mm
* Height: 190 mm
* Thickness: 10 mm

### Top Cover

* Length: 220 mm
* Width: 150 mm
* Thickness: 10 mm

### Overall Enclosure

* 240 mm × 150 mm × 200 mm

## 5. Design Overview

The enclosure consists of six primary printed components:

1. Base
2. Front Panel
3. Back Panel
4. Left Side Panel
5. Right Side Panel
6. Top Cover

The top cover is removable to allow access to internal components.

## 6. Raspberry Pi Mounting System

The Raspberry Pi is mounted using four standoffs positioned according to the official Raspberry Pi 4 mounting pattern.

### Features

* Four M2.5 threaded mounting holes
* Elevated standoff design
* Clearance for underside components
* Space for power and USB cable routing

## 7. Screen Mounting System

The touchscreen is mounted using internal support bars positioned behind the front panel.

### Features

* Four M3 threaded mounting points
* Structural support bars

## 8. Tripod Mounting System

A threaded mounting hole is located at the centre of the base.

### Features

* Compatible with the project tripod mounting screw
* Placed in the center of the base for stability
  
The tripod mounting system allows the enclosure to be mounted without additional brackets.

## 9. Assembly System

The enclosure uses M3 screws for assembly.

### Assembly Sequence

1. Front panel attached to side panels
2. Back panel attached to side panels
3. Wall assembly attached to base
4. Internal components installed
5. Top cover attached

This approach simplifies maintenance and future upgrades.

## 10. Cable Routing

Cable routing space has been reserved for:

* Raspberry Pi power cable
* USB webcam cable
* Display connections

The routing design aims to minimise cable obstruction and improve internal organisation.

## 11. Manufacturing Status

### Completed

* Base printed
* Front panel printed

### Designed in CAD

* Back panel
* Side panels
* Top cover

### Generated Files

* DWG files
* STL files

## 12. Future Improvements

There were some problems with the design, such as there still being insufficient space for cables (e.g. not enough space for the USB camera's cable from the Raspberry Pi to the top of the enclosure). To solve this, I will be making the base longer so that there is sufficient space for the cable to run comfortably and seamlessly through the enclosure.
More improvements I plan to implement include:
* Reduced print time by making the walls thinner
* Improved camera mounting solution
* Final aesthetic refinements

## 13. Conclusion

The enclosure POC demonstrates that the major structural requirements of the photobooth system can be achieved through a modular 3D-printed design. The printed base and front panel validate the manufacturing approach, while the remaining CAD models establish the foundation for the MVP enclosure.
