"""
Entry point - run this file to launch the app.

This is a prototype for a class milestone, not a finished product.
Check the README for what's done, what's not, and what's planned.
"""

import tkinter as tk

from src.gui import EyeAbleGUI


def main():
    root = tk.Tk()
    root.geometry("1024x600")
    app = EyeAbleGUI(root)

    # Makes sure the webcam actually gets released if you close the
    # window with the OS "X" button instead of clicking Exit.
    root.protocol("WM_DELETE_WINDOW", app.exit_app)

    root.mainloop()


if __name__ == "__main__":
    main()
