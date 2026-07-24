import tkinter as tk
import os
from PIL import Image, ImageTk

class SecondScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")

        # ===== Header =====
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", pady=10)

        top_row = tk.Frame(header, bg="white")
        top_row.pack(fill="x", padx=10)

        # --- Logo ---
        logo_path = os.path.join("src", "assets", "logo.png")
        img = Image.open(logo_path)
        img = img.resize((60, 60), Image.LANCZOS)
        self.logo_img = ImageTk.PhotoImage(img)

        tk.Label(top_row, image=self.logo_img, bg="white").pack(side="left", padx=(0, 10))

        # --- Vertical line 1 ---
        tk.Label(top_row, text="|", font=("Arial", 22), fg="#cccccc", bg="white").pack(side="left", padx=10)

        # --- EyeAble Control System text ---
        tk.Label(
            top_row,
            text="EyeAble Control System",
            font=("Arial", 20, "bold"),
            fg="#0078D7",
            bg="white"
        ).pack(side="left", padx=10)

        # --- Vertical line 2 ---
        tk.Label(top_row, text="|", font=("Arial", 22), fg="#cccccc", bg="white").pack(side="left", padx=10)

        # --- Welcome text ---
        tk.Label(
            top_row,
            text="Welcome\nUse your eyes to control the computer",
            font=("Arial", 12),
            justify="left",
            bg="white"
        ).pack(side="left", padx=10)

        # --- Spacer pushes tracking to the right ---
        tk.Label(top_row, bg="white").pack(side="left", expand=True)

        # --- Tracking + Settings ---
        status_frame = tk.Frame(top_row, bg="white")
        status_frame.pack(side="right", padx=10)

        tk.Label(
            status_frame,
            text="Tracking: OFF",
            font=("Arial", 8, "bold"),
            fg="red",
            bg="white"
        ).pack(side="left", padx=5)

        tk.Button(
            status_frame,
            text="Settings ⚙",
            font=("Arial", 8),
            bg="#e0e0e0",
            command=lambda: print("Settings clicked")
        ).pack(side="left", padx=5)

        # --- Horizontal line under header ---
        line = tk.Canvas(header, width=1024, height=2, bg="white", highlightthickness=0)
        line.pack(fill="x", pady=5)
        line.create_line(0, 0, 1024, 0, fill="#cccccc", width=2)

        # ===== Load button icons =====
        icon_path = os.path.join("src", "assets")

        def load_icon(filename, size=(40, 40)):
            full_path = os.path.join(icon_path, filename)
            img = Image.open(full_path)
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)

        self.icon_tracking = load_icon("tracking.png")
        self.icon_calibration = load_icon("calibration.png")
        self.icon_tutorial = load_icon("tutorial.png")
        self.icon_exit = load_icon("exit.png")

        # ===== Main Section =====
        main = tk.Frame(self, bg="white")
        main.pack(expand=True)

        tk.Label(
            main,
            text="Home",
            font=("Arial", 20, "bold"),
            bg="white"
        ).grid(row=0, column=0, columnspan=2, pady=10)

        tk.Label(
            main,
            text="Select an option by looking at it and blinking.",
            font=("Arial", 12),
            bg="white"
        ).grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # Helper to create icon buttons
        def make_icon_button(parent, icon, text, command):
            return tk.Button(
                parent,
                image=icon,
                text=text,
                compound="left",
                font=("Arial", 14),
                width=180,
                height=50,
                bg="#ffffff",
                anchor="w",
                padx=10,
                command=command
            )

        # Buttons with icons
        make_icon_button(main, self.icon_tracking, "Start Tracking",
                         lambda: (controller.show_frame("TrackingScreen"),controller.start())).grid(row=2, column=0, padx=30, pady=15)

        make_icon_button(main, self.icon_calibration, "Calibration",
                         lambda: controller.open_calibration()).grid(row=2, column=1, padx=30, pady=15)

        make_icon_button(main, self.icon_tutorial, "Tutorial",
                         lambda: print("Tutorial clicked")).grid(row=3, column=0, padx=30, pady=15)

        make_icon_button(main, self.icon_exit, "Exit",
                         lambda: controller.exit_app()).grid(row=3, column=1, padx=30, pady=15)

        # ===== Footer =====
        footer = tk.Frame(self, bg="white")
        footer.pack(fill="x", pady=5)

        tk.Label(
            footer,
            text="EyeAble v1.0",
            font=("Arial", 9),
            bg="white"
        ).pack(side="left", padx=10)

        tk.Label(
            footer,
            text="Making technology accessible for everyone.",
            font=("Arial", 9),
            bg="white"
        ).pack(side="left", padx=10)

        tk.Button(
            footer,
            text="Help",
            font=("Arial", 9),
            bg="#e0e0e0",
            command=lambda: print("Help clicked")
        ).pack(side="right", padx=10)
