from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from tracking_dashboard_bridge import TrackingDashboardBridge


class TrackingDashboardPanel(tk.LabelFrame):
    """
    What this is:
      A drop-in Tkinter panel that shows SimVision tracking artifact status.

    Where to use it:
      Inside your simulator dashboard/live match page.

    Why it matters:
      It turns the raw tracking files into a readable status panel for the UI.
    """

    def __init__(self, parent, project_root: str | Path, match_id: str = "video_demo", **kwargs):
        super().__init__(
            parent,
            text="Tracking Analysis",
            bg=kwargs.pop("bg", "#161327"),
            fg=kwargs.pop("fg", "white"),
            padx=10,
            pady=10,
            **kwargs,
        )
        self.project_root = Path(project_root)
        self.match_id = match_id
        self.bridge = TrackingDashboardBridge(self.project_root, self.match_id)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=self["bg"])
        top.pack(fill="x")

        self.match_label = tk.Label(
            top,
            text=f"Match ID: {self.match_id}",
            bg=self["bg"],
            fg="white",
            anchor="w",
            font=("Arial", 10, "bold"),
        )
        self.match_label.pack(side="left", fill="x", expand=True)

        btn_cfg = {"bg": "#7c3aed", "fg": "white", "relief": "flat", "activebackground": "#6d28d9"}
        tk.Button(top, text="Refresh", command=self.refresh, **btn_cfg).pack(side="right", padx=(6, 0))

        self.status_label = tk.Label(
            self,
            text="Tracking dashboard waiting...",
            bg=self["bg"],
            fg="#fbbf24",
            anchor="w",
            justify="left",
        )
        self.status_label.pack(fill="x", pady=(8, 8))

        self.text = tk.Text(
            self,
            height=18,
            bg="#09111f",
            fg="white",
            relief="flat",
            wrap="word",
        )
        self.text.pack(fill="both", expand=True)

        bottom = tk.Frame(self, bg=self["bg"])
        bottom.pack(fill="x", pady=(8, 0))

        tk.Button(bottom, text="Show Paths", command=self.show_paths, **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bottom, text="Change Match ID", command=self.prompt_match_id, **btn_cfg).pack(side="left", padx=6)

    def set_match_id(self, match_id: str) -> None:
        self.match_id = match_id.strip()
        self.bridge = TrackingDashboardBridge(self.project_root, self.match_id)
        self.match_label.config(text=f"Match ID: {self.match_id}")
        self.refresh()

    def refresh(self) -> None:
        headline = self.bridge.get_headline_metrics()
        lines = self.bridge.as_dashboard_lines()

        self.status_label.config(
            text=(
                f"Readiness {headline['readiness_score']}/100 | "
                f"Tracking={headline['tracking_ready']} | "
                f"PitchMap={headline['pitch_map_ready']} | "
                f"Calibration={headline['calibration_ready']}"
            )
        )

        self.text.delete("1.0", "end")
        for line in lines:
            self.text.insert("end", line + "\n")

    def show_paths(self) -> None:
        message = (
            f"Project Root:\n{self.project_root}\n\n"
            f"Tracking Output:\n{self.bridge.tracking_output_path}\n\n"
            f"Pitch Map:\n{self.bridge.pitch_map_path}\n\n"
            f"Calibration:\n{self.bridge.calibration_points_path}\n\n"
            f"Calibration Preview:\n{self.bridge.calibration_preview_path}\n\n"
            f"Frames Dir:\n{self.bridge.frames_dir}"
        )
        messagebox.showinfo("Tracking Paths", message)

    def prompt_match_id(self) -> None:
        win = tk.Toplevel(self)
        win.title("Change Match ID")
        win.geometry("360x120")
        win.configure(bg="#111827")

        tk.Label(
            win,
            text="Enter match id",
            bg="#111827",
            fg="white",
        ).pack(anchor="w", padx=10, pady=(10, 4))

        entry = tk.Entry(win, bg="#09111f", fg="white", insertbackground="white")
        entry.pack(fill="x", padx=10, pady=(0, 10))
        entry.insert(0, self.match_id)

        def apply_change():
            value = entry.get().strip()
            if value:
                self.set_match_id(value)
                win.destroy()

        btn_cfg = {"bg": "#7c3aed", "fg": "white", "relief": "flat", "activebackground": "#6d28d9"}
        tk.Button(win, text="Apply", command=apply_change, **btn_cfg).pack(padx=10, pady=(0, 10), anchor="e")
