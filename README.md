# Spot the Difference Game

**Assignment:** HIT137 Assignment 3

A Python desktop game for HIT137 Assignment 3. The program loads an image, creates a modified copy with exactly five hidden non-overlapping differences, and lets the player find the differences by clicking on the modified image.

## Features

- Load JPG, JPEG, PNG, and BMP images from disk.
- Display the original image on the left and the modified image on the right.
- Generate exactly five random hidden differences for every loaded image.
- Use non-overlapping difference regions.
- Include three alteration types: colour shift, blur, and shape/object-like changes.
- Track remaining differences and mistakes.
- Lock the round after three wrong guesses.
- Mark correct guesses with red circles.
- Reveal all remaining differences with blue circles.

## Technologies Used

- Python 3
- Tkinter
- OpenCV
- Pillow
- NumPy

## Installation

Install Python 3, then install the required packages:

```bash
pip install -r requirements.txt
```

## How to Run

Run the application from the project folder:

```bash
python main.py
```

## How to Play

1. Click `Load Image` and choose a JPG, JPEG, PNG, or BMP image.
2. Compare the original image on the left with the modified image on the right.
3. Click the modified image where you think a difference exists.
4. Correct clicks are marked with red circles on both images.
5. Wrong clicks increase the mistake counter.
6. After three mistakes, the round is locked.
7. Click `Reveal Differences` to show remaining differences in blue.
8. Load a new image to start a new round.

## OOP Design

The project separates responsibilities into several classes:

- `SpotDifferenceApp` manages the Tkinter interface, buttons, image display, and click handling.
- `ImageProcessor` loads images, creates modified images, generates non-overlapping regions, and converts OpenCV images for Tkinter.
- `GameManager` tracks found differences, remaining differences, mistakes, and round locking.
- `Alteration` is a base class for image changes.
- `ColourShiftAlteration`, `BlurAlteration`, and `ShapeAlteration` inherit from `Alteration` and implement their own `apply(image, region)` method. This demonstrates inheritance and polymorphism.

## Screenshots

- `screenshots/game_loaded.png`
- `screenshots/correct_click.png`
- `screenshots/reveal_differences.png`

## GitHub Repository

https://github.com/Rabbi730/HIT137-Assignment-3
## Student / Group Members

MD Mustafizur Rahman Himel
ID: S401025
T M Fazla Rabbi
ID: S388938
Miraj Hossain
ID: S399379
