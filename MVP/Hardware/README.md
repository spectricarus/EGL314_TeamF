# Hardware - Designing and 3D-printing the enclosure
[↑ Back to MVP overview](../README.md) (Software section is documented separately by teammate — linked from there)

This is the hardware half of the MVP: thought processes behind design decisions and STL files for 3D-printing

## What's in this folder

| File | What it is |
|---|---|
| [`CAD/back and front wall.dwg`](./CAD/back_and_front_wall.dwg) | AutoCAD drawing for the back and the front wall |
| [`CAD/base_(updated).dwg`](./CAD/base_(updated).dwg) | AutoCAD drawing for the base of the enclosure |
| [`CAD/side_walls.dwg`](./CAD/side_walls.dwg) | AutoCAD drawing for the side walls of the enclosure |
| [`CAD/top_cover.dwg`](./CAD/top_cover.dwg) | AutoCAD drawing for the top cover of the enclosure |
| [`STL/back-wall.stl`](./STL/back-wall.stl) | STL file for back wall of the enclosure |
| [`STL/base.stl`](./STL/base.stl) | STL file for base of the enclosure |
| [`STL/front-wall.stl`](./STL/front-wall.stl) | STL file for front wall of the enclosure |
| [`STL/side-wall-with-hole.stl`](./STL/side-wall-with-hole.stl) | STL file for the side wall of the enclosure with the power cable access hole |
| [`STL/side-wall.stl`](./STL/side-wall.stl) | STL file for side wall of the enclosure |
| [`STL/top.stl`](./STL/top.stl) | STL file for top cover of the enclosure |

## Designing the enclosure
When designing the enclosure, there were a few things to consider:
* Standoffs to mount the Raspberry Pi
* Mounting for a 7 inch Raspberry Pi touchscreen
* Mounting for USB camera
* Cable routing (eg. for power supply)
* Enclosure is able to be mounted on a tripod

## Images
To accommodate for these requirements, the design would include a front wall with "jailbars" to mount the touchscreen, standoffs on the base to mount the Raspberry Pi and a simple hole in the top cover where the USB camera will simply hang. The entire enclosure looks as such:
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 26 (1)" src="https://github.com/user-attachments/assets/e6b46c7f-5f1b-4a62-9228-e5b16361bb3c" />

With Raspberry Pi mounting and screen mounting shown:
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 23 (1)" src="https://github.com/user-attachments/assets/fb8d2eb2-a77f-4307-9f40-07eff895779f" />

Enclosure mounted on tripod:
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 27 (3)" src="https://github.com/user-attachments/assets/8f0b8ec3-9a43-4d53-8ee2-0fef201681c3" />

## Individual parts
The following images will show what each individual part of the enclosure would look like, including a brief description of special features, if any.

### Top cover
The top cover has a clearance hole for the USB camera to sit in and for the cable to pass through, as well as four bosses at each corner to make alignment of the top cover to the box easy.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 16 (1)" src="https://github.com/user-attachments/assets/e78a3b57-8b17-496a-8b4a-4faca72d5a70" />

### Front wall
The front wall has an opening the size of a 7-inch Raspberry Pi touchscreen and two "jailbars" that securely mount the screen itself.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 15 (2)" src="https://github.com/user-attachments/assets/d6188b96-5b11-45c7-b2a2-19f2c61e3c7b" />

### Back wall
The back wall has no special features.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 16 (4)" src="https://github.com/user-attachments/assets/81eaf2a5-1137-43cc-bbd6-d6289e76860c" />

### Left wall
The left wall has no special features.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 02 (2)" src="https://github.com/user-attachments/assets/4d9bf9fc-e6cd-460c-9ba5-02631778f4ce" />

### Right wall
The right wall has an opening to allow the power supply cable to reach the Raspberry Pi inside the enclosure.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 02" src="https://github.com/user-attachments/assets/8ee0b060-4fe6-41fc-a4ec-e52633e4e490" />

### Base
The base has four standoffs that mount the Raspberry Pi, as well as a quarter inch screw hole at the bottom that mounts the tripod plate.
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 17 (3)" src="https://github.com/user-attachments/assets/51e34e4c-4d8a-4fa9-a768-1f1be1eeaed2" /><img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 19 (4)" src="https://github.com/user-attachments/assets/64c08bad-5189-4d14-a95a-330f2bae7bcd" />

## Possible improvements
* Mesh on the back wall to increase upload and download speed.
* Proper mount for USB camera instead of a hole.

