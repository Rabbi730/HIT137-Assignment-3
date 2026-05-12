import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk


class Alteration:
    """Base class for all image alterations."""

    name = "Alteration"

    def apply(self, image, region):
        raise NotImplementedError("Subclasses must implement apply().")


class ColourShiftAlteration(Alteration):
    name = "Colour Shift"

    def apply(self, image, region):
        x, y, width, height = region["x"], region["y"], region["w"], region["h"]
        roi = image[y : y + height, x : x + width]
        working_roi = roi.astype(np.int16)
        shift = np.array(
            [
                random.choice([-42, -32, 32, 42]),
                random.choice([-34, -24, 24, 34]),
                random.choice([-42, -32, 32, 42]),
            ],
            dtype=np.int16,
        )
        shifted_roi = np.clip(working_roi + shift, 0, 255).astype(np.uint8)
        image[y : y + height, x : x + width] = cv2.addWeighted(
            shifted_roi, 0.55, roi, 0.45, 0
        )


class BlurAlteration(Alteration):
    name = "Blur"

    def apply(self, image, region):
        x, y, width, height = region["x"], region["y"], region["w"], region["h"]
        roi = image[y : y + height, x : x + width]
        smallest_side = max(3, min(width, height))
        kernel_size = min(31, smallest_side if smallest_side % 2 == 1 else smallest_side - 1)
        kernel_size = max(3, kernel_size)
        if kernel_size % 2 == 0:
            kernel_size -= 1

        blurred = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
        image[y : y + height, x : x + width] = blurred


class ShapeAlteration(Alteration):
    name = "Shape"

    def apply(self, image, region):
        x, y, width, height = region["x"], region["y"], region["w"], region["h"]
        roi = image[y : y + height, x : x + width]
        soft_colour = self._soft_region_colour(roi)
        overlay = image.copy()

        center = (x + width // 2, y + height // 2)
        radius = max(6, min(width, height) // 3)

        if random.choice([True, False]):
            cv2.circle(
                overlay,
                center,
                radius,
                soft_colour,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )
        else:
            left = x + max(2, width // 5)
            top = y + max(2, height // 5)
            right = x + width - max(2, width // 5)
            bottom = y + height - max(2, height // 5)
            cv2.rectangle(
                overlay,
                (left, top),
                (right, bottom),
                soft_colour,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )

        cv2.addWeighted(overlay, 0.35, image, 0.65, 0, dst=image)

    def _soft_region_colour(self, roi):
        mean_colour = np.mean(roi, axis=(0, 1))
        soft_channels = []

        for channel in mean_colour:
            direction = 1 if channel < 150 else -1
            offset = random.randint(18, 36) * direction
            soft_channels.append(int(np.clip(channel + offset, 0, 255)))

        return tuple(soft_channels)


class ImageProcessor:
    """Loads images, creates differences, and prepares images for Tkinter."""

    def __init__(self):
        self.alteration_classes = [
            ColourShiftAlteration,
            BlurAlteration,
            ShapeAlteration,
        ]

    def load_image(self, file_path):
        image = cv2.imread(file_path)
        if image is None:
            raise ValueError("Could not load the selected image.")

        height, width = image.shape[:2]
        if width < 120 or height < 120:
            raise ValueError("Please choose an image at least 120 x 120 pixels.")

        return image

    def resize_for_display(self, image, max_width, max_height):
        height, width = image.shape[:2]
        max_width = max(200, int(max_width))
        max_height = max(200, int(max_height))
        # Keep the aspect ratio so clicks can be scaled back to the original image.
        scale = min(max_width / width, max_height / height, 1.0)
        new_width = max(1, int(width * scale))
        new_height = max(1, int(height * scale))

        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        resized = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
        return resized, scale

    def generate_random_region(self, image):
        height, width = image.shape[:2]
        shortest_side = min(width, height)
        min_size = max(24, shortest_side // 16)
        max_size = max(min_size + 1, shortest_side // 8)

        # Random regions keep every round different while staying proportional to the image.
        region_width = random.randint(min_size, max_size)
        region_height = random.randint(min_size, max_size)
        x = random.randint(0, width - region_width)
        y = random.randint(0, height - region_height)

        return {"x": x, "y": y, "w": region_width, "h": region_height}

    def is_region_suitable(self, image, region):
        x, y, width, height = region["x"], region["y"], region["w"], region["h"]
        roi = image[y : y + height, x : x + width]
        mean_brightness = float(np.mean(roi))
        texture_value = float(np.std(roi))

        return mean_brightness <= 240 and texture_value >= 8

    def regions_overlap(self, region_a, region_b, padding=12):
        # Padding leaves clear space between differences so one click cannot find two.
        ax1 = region_a["x"] - padding
        ay1 = region_a["y"] - padding
        ax2 = region_a["x"] + region_a["w"] + padding
        ay2 = region_a["y"] + region_a["h"] + padding

        bx1 = region_b["x"]
        by1 = region_b["y"]
        bx2 = region_b["x"] + region_b["w"]
        by2 = region_b["y"] + region_b["h"]

        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def create_differences(self, original_image, number_of_differences=5):
        modified_image = original_image.copy()
        regions = []
        alterations = self._build_alteration_sequence(number_of_differences)
        attempts = 0
        max_attempts = 5000

        while len(regions) < number_of_differences and attempts < max_attempts:
            attempts += 1
            region = self.generate_random_region(original_image)

            if not self.is_region_suitable(original_image, region):
                continue

            if any(self.regions_overlap(region, existing) for existing in regions):
                continue

            alteration = alterations[len(regions)]
            alteration.apply(modified_image, region)
            region["alteration"] = alteration.name
            regions.append(region)

        if len(regions) != number_of_differences:
            raise ValueError(
                "Could not place five non-overlapping differences. Try a larger image."
            )

        return modified_image, regions

    def convert_cv_to_tk(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        return ImageTk.PhotoImage(pil_image)

    def _build_alteration_sequence(self, number_of_differences):
        sequence = [alteration_class() for alteration_class in self.alteration_classes]
        while len(sequence) < number_of_differences:
            sequence.append(random.choice(self.alteration_classes)())
        random.shuffle(sequence)
        return sequence[:number_of_differences]


class GameManager:
    """Tracks found differences, mistakes, and round lock state."""

    def __init__(self, max_mistakes=3):
        self.max_mistakes = max_mistakes
        self.total_differences = 5
        self.reset_game()

    def reset_game(self, total_differences=5):
        self.total_differences = total_differences
        self.found_indices = set()
        self.mistakes = 0
        self.locked = False

    def remaining_count(self):
        return self.total_differences - len(self.found_indices)

    def is_click_inside_region(self, click_x, click_y, region, tolerance=18):
        # A small tolerance makes the game playable without requiring pixel-perfect clicks.
        left = region["x"] - tolerance
        top = region["y"] - tolerance
        right = region["x"] + region["w"] + tolerance
        bottom = region["y"] + region["h"] + tolerance
        return left <= click_x <= right and top <= click_y <= bottom

    def check_click(self, click_x, click_y, regions):
        if self.locked:
            return None

        for index, region in enumerate(regions):
            if index in self.found_indices:
                continue
            if self.is_click_inside_region(click_x, click_y, region):
                self.found_indices.add(index)
                return index

        self.mistakes += 1
        if self.mistakes >= self.max_mistakes:
            self.locked = True
        return None

    def all_found(self):
        return len(self.found_indices) == self.total_differences

    def reveal_all(self):
        self.found_indices.update(range(self.total_differences))
        self.locked = True


class SpotDifferenceApp:
    """Main desktop application for the Spot the Difference game."""

    def __init__(self, root):
        self.root = root
        self.root.title("Spot the Difference Game")
        self.root.geometry("1100x720")
        self.root.minsize(800, 560)

        self.image_processor = ImageProcessor()
        self.game_manager = GameManager()

        self.original_image = None
        self.modified_image = None
        self.regions = []
        self.revealed_indices = set()
        self.original_photo = None
        self.modified_photo = None
        self.display_scale = 1.0
        self.resize_job = None

        self.remaining_var = tk.StringVar(value="Remaining: 5")
        self.mistakes_var = tk.StringVar(value="Mistakes: 0 / 3")
        self.status_var = tk.StringVar(value="Load an image to start the game.")

        self._build_gui()
        self.root.bind("<Configure>", self._schedule_resize)

    def _build_gui(self):
        toolbar = tk.Frame(self.root, padx=12, pady=10)
        toolbar.pack(fill=tk.X)

        self.load_button = tk.Button(
            toolbar, text="Load Image", command=self.load_image, width=14
        )
        self.load_button.pack(side=tk.LEFT, padx=(0, 8))

        self.reveal_button = tk.Button(
            toolbar,
            text="Reveal Differences",
            command=self.reveal_differences,
            width=18,
            state=tk.DISABLED,
        )
        self.reveal_button.pack(side=tk.LEFT, padx=(0, 18))

        tk.Label(toolbar, textvariable=self.remaining_var, font=("Arial", 11, "bold")).pack(
            side=tk.LEFT, padx=(0, 16)
        )
        tk.Label(toolbar, textvariable=self.mistakes_var, font=("Arial", 11, "bold")).pack(
            side=tk.LEFT
        )

        image_area = tk.Frame(self.root, padx=12, pady=8)
        image_area.pack(fill=tk.BOTH, expand=True)
        image_area.columnconfigure(0, weight=1)
        image_area.columnconfigure(1, weight=1)
        image_area.rowconfigure(1, weight=1)

        tk.Label(image_area, text="Original Image", font=("Arial", 12, "bold")).grid(
            row=0, column=0, pady=(0, 6)
        )
        tk.Label(image_area, text="Modified Image", font=("Arial", 12, "bold")).grid(
            row=0, column=1, pady=(0, 6)
        )

        self.original_panel = tk.Frame(image_area, bd=1, relief=tk.SOLID, bg="#f4f4f4")
        self.original_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))

        self.modified_panel = tk.Frame(image_area, bd=1, relief=tk.SOLID, bg="#f4f4f4")
        self.modified_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        self.original_label = tk.Label(
            self.original_panel,
            text="Load an image",
            bg="#f4f4f4",
            borderwidth=0,
            highlightthickness=0,
        )
        self.original_label.pack(expand=True)

        self.modified_label = tk.Label(
            self.modified_panel,
            text="Click this image to guess",
            bg="#f4f4f4",
            cursor="crosshair",
            borderwidth=0,
            highlightthickness=0,
        )
        self.modified_label.pack(expand=True)
        self.modified_label.bind("<Button-1>", self.handle_modified_click)

        status_bar = tk.Frame(self.root, padx=12, pady=10)
        status_bar.pack(fill=tk.X)
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            anchor="w",
            font=("Arial", 10),
        ).pack(fill=tk.X)

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            original_image = self.image_processor.load_image(file_path)
            modified_image, regions = self.image_processor.create_differences(
                original_image, 5
            )
        except Exception as error:
            messagebox.showerror("Image Error", str(error))
            return

        self.original_image = original_image
        self.modified_image = modified_image
        self.regions = regions
        self.revealed_indices = set()
        self.game_manager.reset_game(total_differences=len(regions))
        self.reveal_button.configure(state=tk.NORMAL)

        file_name = os.path.basename(file_path)
        self.status_var.set(f"{file_name} loaded. Find all 5 differences.")
        self._update_counters()
        self.update_display_images()

    def handle_modified_click(self, event):
        if self.modified_image is None:
            return

        if self.game_manager.locked:
            self.status_var.set("This round is locked. Load a new image to play again.")
            return

        if self.display_scale <= 0:
            return

        # Convert the displayed click position back to original image coordinates.
        click_x = int(event.x / self.display_scale)
        click_y = int(event.y / self.display_scale)
        height, width = self.modified_image.shape[:2]

        if click_x < 0 or click_y < 0 or click_x >= width or click_y >= height:
            return

        found_index = self.game_manager.check_click(click_x, click_y, self.regions)

        if found_index is not None:
            remaining = self.game_manager.remaining_count()
            self.status_var.set(f"Correct. {remaining} differences remaining.")
            if self.game_manager.all_found():
                self.game_manager.locked = True
                self.status_var.set("Success. You found all 5 differences.")
                messagebox.showinfo("Round Complete", "You found all 5 differences!")
        else:
            if self.game_manager.locked:
                self.status_var.set("Game locked after 3 mistakes. Load a new image or reveal.")
                messagebox.showwarning(
                    "Game Locked", "You made 3 mistakes. This round is now locked."
                )
            else:
                self.status_var.set("Wrong spot. Try another area on the modified image.")

        self._update_counters()
        self.update_display_images()

    def reveal_differences(self):
        if self.modified_image is None:
            return

        # Store only the answers that were still hidden so they can be marked in blue.
        self.revealed_indices = set(range(len(self.regions))) - self.game_manager.found_indices
        self.game_manager.reveal_all()
        self.status_var.set("Differences revealed. Load a new image to restart.")
        self._update_counters()
        self.update_display_images()
        messagebox.showinfo(
            "Differences Revealed",
            "All remaining differences are marked in blue. Load a new image to play again.",
        )

    def update_display_images(self):
        if self.original_image is None or self.modified_image is None:
            return

        marked_original, marked_modified = self._images_with_markers()
        max_width, max_height = self._available_image_size()

        original_display, scale = self.image_processor.resize_for_display(
            marked_original, max_width, max_height
        )
        modified_display, _ = self.image_processor.resize_for_display(
            marked_modified, max_width, max_height
        )

        self.display_scale = scale
        self.original_photo = self.image_processor.convert_cv_to_tk(original_display)
        self.modified_photo = self.image_processor.convert_cv_to_tk(modified_display)

        self.original_label.configure(image=self.original_photo, text="")
        self.modified_label.configure(image=self.modified_photo, text="")

    def _images_with_markers(self):
        marked_original = self.original_image.copy()
        marked_modified = self.modified_image.copy()

        for index in sorted(self.game_manager.found_indices):
            if index >= len(self.regions):
                continue
            colour = (255, 0, 0) if index in self.revealed_indices else (0, 0, 255)
            self._draw_region_circle(marked_original, self.regions[index], colour)
            self._draw_region_circle(marked_modified, self.regions[index], colour)

        return marked_original, marked_modified

    def _draw_region_circle(self, image, region, colour):
        center_x = region["x"] + region["w"] // 2
        center_y = region["y"] + region["h"] // 2
        radius = max(12, max(region["w"], region["h"]) // 2 + 5)
        cv2.circle(image, (center_x, center_y), radius, colour, thickness=2)

    def _available_image_size(self):
        window_width = max(self.root.winfo_width(), 800)
        window_height = max(self.root.winfo_height(), 560)
        max_width = (window_width - 72) // 2
        max_height = window_height - 160
        return max_width, max_height

    def _update_counters(self):
        self.remaining_var.set(f"Remaining: {self.game_manager.remaining_count()}")
        self.mistakes_var.set(
            f"Mistakes: {self.game_manager.mistakes} / {self.game_manager.max_mistakes}"
        )

    def _schedule_resize(self, event):
        if event.widget != self.root or self.original_image is None:
            return

        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(120, self._finish_resize)

    def _finish_resize(self):
        self.resize_job = None
        self.update_display_images()


if __name__ == "__main__":
    root = tk.Tk()
    app = SpotDifferenceApp(root)
    root.mainloop()
