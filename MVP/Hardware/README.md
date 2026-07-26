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

To accommodate for these requirements, the design would include a front wall with "jailbars" to mount the touchscreen, standoffs on the base to mount the Raspberry Pi and a simple hole in the top cover where the USB camera will simply hang. The entire enclosure looks as such:
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 26 (1)" src="https://github.com/user-attachments/assets/e6b46c7f-5f1b-4a62-9228-e5b16361bb3c" />

With Raspberry Pi mounting and screen mounting shown:
<img width="1148" height="2040" alt="WhatsApp Image 2026-07-25 at 21 46 23 (1)" src="https://github.com/user-attachments/assets/fb8d2eb2-a77f-4307-9f40-07eff895779f" />
