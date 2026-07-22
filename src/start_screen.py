import tkinter as tk
import os

class StartScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")

        # Centering frame that expands with window size
        center = tk.Frame(self, bg="white")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ===== Logo =====
        logo_path = os.path.join("src", "assets", "logo.png")

        try:
            self.logo_img = tk.PhotoImage(file=logo_path)
            tk.Label(center, image=self.logo_img, bg="white").pack(pady=20)
        except Exception:
            tk.Label(center, text="(logo missing)", bg="white").pack(pady=20)

        # ===== Title =====
        tk.Label(
            center,
            text="EyeAble",
            font=("Arial", 32, "bold"),
            bg="white"
        ).pack(pady=10)

        # ===== Begin Button =====
        tk.Button(
            center,
            text="Begin",
            font=("Arial", 18),
            width=12,
            height=1,
            bg="#f0f0f0",
            command=lambda: controller.show_frame("SecondScreen")
        ).pack(pady=30)
