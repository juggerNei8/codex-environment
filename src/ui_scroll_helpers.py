from __future__ import annotations

import tkinter as tk


class ScrollablePage(tk.Frame):
    def __init__(self, master, *, bg: str = "#000000", **kwargs):
        super().__init__(master, bg=bg, **kwargs)

        self.canvas = tk.Canvas(
            self,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        self.bg_label = tk.Label(self.canvas, bg=bg, bd=0, highlightthickness=0)
        self.bg_window = self.canvas.create_window((0, 0), window=self.bg_label, anchor="nw")

        self.content = tk.Frame(self.canvas, bg=bg)
        self.content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content.bind("<Configure>", self._on_content_configure)

        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.content)
        self._bind_mousewheel(self.bg_label)

    def _on_canvas_configure(self, event):
        width = max(1, event.width)
        height = max(1, event.height)
        self.canvas.itemconfigure(self.bg_window, width=width, height=height)
        self.canvas.itemconfigure(self.content_window, width=width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_content_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        delta = 0
        if getattr(event, "delta", 0):
            delta = int(-1 * (event.delta / 120))
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")

    def set_background_image(self, image=None, text: str = ""):
        if image is not None:
            self.bg_label.configure(image=image, text="")
            self.bg_label.image = image
        else:
            self.bg_label.configure(image="", text=text)
            self.bg_label.image = None

    def scroll_to_top(self):
        self.canvas.yview_moveto(0.0)
