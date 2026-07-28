"""Native Tk GUI for rapid side-by-side beetle scan review."""

from __future__ import annotations

import tempfile
import tkinter as tk
from collections import OrderedDict
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from .matching import MatchResult, match_records, scan_folder
from .session import ReviewSession


class ThumbnailCache:
    """Decode upcoming images off the GUI thread and retain recent thumbnails."""

    def __init__(self, maximum_items: int = 40) -> None:
        self.maximum_items = maximum_items
        self.images: OrderedDict[tuple[Path, int, int], Image.Image] = OrderedDict()
        self.futures: dict[tuple[Path, int, int], Future[Image.Image]] = {}
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="image-prefetch")

    @staticmethod
    def _dimensions(width: int, height: int) -> tuple[int, int]:
        # Buckets avoid re-decoding after tiny window-size changes.
        return max(320, width // 64 * 64), max(320, height // 64 * 64)

    def _key(self, path: Path, width: int, height: int) -> tuple[Path, int, int]:
        bucket_width, bucket_height = self._dimensions(width, height)
        return path, bucket_width, bucket_height

    @staticmethod
    def _decode(key: tuple[Path, int, int]) -> Image.Image:
        path, width, height = key
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            return image.copy()

    def prefetch(self, path: Path, width: int, height: int) -> None:
        key = self._key(path, width, height)
        with self.lock:
            if key in self.images or key in self.futures:
                return
            future = self.executor.submit(self._decode, key)
            self.futures[key] = future
            future.add_done_callback(lambda completed, item_key=key: self._store(item_key, completed))

    def _store(self, key: tuple[Path, int, int], future: Future[Image.Image]) -> None:
        try:
            image = future.result()
        except (CancelledError, OSError, ValueError):
            with self.lock:
                if self.futures.get(key) is future:
                    self.futures.pop(key, None)
            return
        with self.lock:
            if self.futures.get(key) is not future:
                return
            self.futures.pop(key, None)
            self.images[key] = image
            self.images.move_to_end(key)
            while len(self.images) > self.maximum_items:
                self.images.popitem(last=False)

    def get(self, path: Path, width: int, height: int) -> Image.Image:
        key = self._key(path, width, height)
        with self.lock:
            cached = self.images.get(key)
            future = self.futures.get(key)
            if cached is not None:
                self.images.move_to_end(key)
                return cached
        # The first visible pair may still need to wait; prefetched pairs do not.
        image = future.result() if future is not None else self._decode(key)
        with self.lock:
            self.futures.pop(key, None)
            self.images[key] = image
            self.images.move_to_end(key)
            while len(self.images) > self.maximum_items:
                self.images.popitem(last=False)
        return image

    def clear(self) -> None:
        with self.lock:
            pending = list(self.futures.values())
            self.futures.clear()
            self.images.clear()
        for future in pending:
            future.cancel()

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)


class CompareApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Beetle Scan Compare")
        self.geometry("1300x850")
        self.minsize(900, 650)
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()
        self.view = tk.StringVar(value="D")
        self.threshold = tk.DoubleVar(value=82)
        self.recursive = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choose two folders and a view.")
        self.result: MatchResult | None = None
        self.session: ReviewSession | None = None
        self.index = 0
        self.rapid = False
        self.left_photo: ImageTk.PhotoImage | None = None
        self.right_photo: ImageTk.PhotoImage | None = None
        self.zoom = {"left": 1.0, "right": 1.0}
        self.active_image = "left"
        self.thumbnail_cache = ThumbnailCache()
        self._build()
        self.bind("<KeyPress-a>", lambda _: self._decide("approved"))
        self.bind("<KeyPress-A>", lambda _: self._decide("approved"))
        self.bind("<KeyPress-r>", lambda _: self._decide("rejected"))
        self.bind("<KeyPress-R>", lambda _: self._decide("rejected"))
        self.bind("<Left>", lambda _: self._move(-1))
        self.bind("<Right>", lambda _: self._move(1))
        self.bind("<Configure>", self._resize)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        controls = ttk.Frame(self, padding=12)
        controls.pack(fill="x")
        self._folder_row(controls, 0, "Folder 1", self.left_folder)
        self._folder_row(controls, 1, "Folder 2", self.right_folder)
        view_frame = ttk.Frame(controls)
        view_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(view_frame, text="Image view:").pack(side="left")
        for value, label in (("D", "Dorsal (-D)"), ("V", "Ventral (-V)"), ("R", "Right (-R)")):
            ttk.Radiobutton(view_frame, text=label, value=value, variable=self.view).pack(side="left", padx=8)
        ttk.Checkbutton(view_frame, text="Include subfolders", variable=self.recursive).pack(side="left", padx=14)
        ttk.Label(view_frame, text="Minimum match %:").pack(side="left")
        ttk.Spinbox(view_frame, from_=50, to=100, increment=1, width=5, textvariable=self.threshold).pack(side="left")
        ttk.Button(view_frame, text="Match Images", command=self._load).pack(side="left", padx=12)
        controls.columnconfigure(1, weight=1)

        names = ttk.Frame(self, padding=(12, 4))
        names.pack(fill="x")
        self.left_name = ttk.Label(names, text="Folder 1 image", anchor="center", font=("TkDefaultFont", 13, "bold"))
        self.right_name = ttk.Label(names, text="Folder 2 image", anchor="center", font=("TkDefaultFont", 13, "bold"))
        self.left_name.grid(row=0, column=0, sticky="ew", padx=4)
        self.right_name.grid(row=0, column=1, sticky="ew", padx=4)
        names.columnconfigure((0, 1), weight=1)

        images = ttk.Frame(self, padding=(12, 0))
        images.pack(fill="both", expand=True)
        self.left_image = tk.Canvas(images, background="#181818", highlightthickness=2)
        self.right_image = tk.Canvas(images, background="#181818", highlightthickness=2)
        self.left_image.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.right_image.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        for side, canvas in (("left", self.left_image), ("right", self.right_image)):
            canvas.bind("<ButtonPress-1>", lambda event, selected=side: self._pan_start(event, selected))
            canvas.bind("<B1-Motion>", lambda event, selected=side: self._pan_move(event, selected))
            canvas.bind("<MouseWheel>", lambda event, selected=side: self._wheel_zoom(event, selected))
            canvas.bind("<Enter>", lambda _event, selected=side: self._activate_image(selected))
        images.columnconfigure((0, 1), weight=1)
        images.rowconfigure(0, weight=1)
        self.image_frame = images
        self._activate_image("left")

        footer = ttk.Frame(self, padding=12)
        footer.pack(fill="x")
        ttk.Button(footer, text="◀ Previous", command=lambda: self._move(-1)).pack(side="left")
        ttk.Button(footer, text="Approve (A)", command=lambda: self._decide("approved")).pack(side="left", padx=8)
        ttk.Button(footer, text="Reject (R)", command=lambda: self._decide("rejected")).pack(side="left")
        self.rapid_button = ttk.Button(footer, text="Start Rapid Review", command=self._start_rapid)
        self.rapid_button.pack(side="left", padx=18)
        ttk.Button(footer, text="Next ▶", command=lambda: self._move(1)).pack(side="left")
        ttk.Button(footer, text="Zoom −", command=lambda: self._change_zoom(0.8)).pack(side="left", padx=(18, 4))
        ttk.Button(footer, text="100%", command=self._reset_zoom).pack(side="left", padx=4)
        ttk.Button(footer, text="Zoom +", command=lambda: self._change_zoom(1.25)).pack(side="left", padx=4)
        ttk.Button(footer, text="Export CSV Lists", command=self._export).pack(side="right")
        ttk.Label(footer, textvariable=self.status).pack(side="right", padx=16)

    def _folder_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8)
        ttk.Button(parent, text="Choose…", command=lambda: self._choose(variable)).grid(row=row, column=2)

    def _choose(self, variable: tk.StringVar) -> None:
        selected = filedialog.askdirectory()
        if selected:
            variable.set(selected)

    def _load(self) -> None:
        left = Path(self.left_folder.get())
        right = Path(self.right_folder.get())
        if not left.is_dir() or not right.is_dir():
            messagebox.showerror("Folders required", "Please choose two valid image folders.")
            return
        left_records = scan_folder(left, self.view.get(), self.recursive.get())
        right_records = scan_folder(right, self.view.get(), self.recursive.get())
        self.result = match_records(left_records, right_records, self.threshold.get())
        self.thumbnail_cache.clear()
        temp_dir = Path(tempfile.gettempdir()) / "beetle-scan-compare"
        self.session = ReviewSession(self.result, temp_dir)
        self.index = 0
        self.rapid = False
        self.zoom = {"left": 1.0, "right": 1.0}
        self._show()
        self.status.set(
            f"{len(self.result.matches)} pairs · "
            f"{len(self.result.left_unmatched)} left unmatched · "
            f"{len(self.result.right_unmatched)} right unmatched"
        )

    def _show(self) -> None:
        if not self.result or not self.result.matches:
            self.left_name.config(text="No matched images")
            self.right_name.config(text="No matched images")
            self.left_image.delete("all")
            self.right_image.delete("all")
            return
        match = self.result.matches[self.index]
        decision = self.session.decisions.get(self.index) if self.session else None
        marker = f" — {decision.status.upper()}" if decision else ""
        self.left_name.config(text=match.left.path.name + marker)
        self.right_name.config(text=match.right.path.name + f" — match {match.score:.1f}%")
        self._render_images()
        self._prefetch_upcoming()
        self.status.set(f"Pair {self.index + 1} of {len(self.result.matches)}")

    def _render_images(self) -> None:
        if not self.result or not self.result.matches:
            return
        match = self.result.matches[self.index]
        self.left_photo = self._render_canvas(self.left_image, match.left.path, "left")
        self.right_photo = self._render_canvas(self.right_image, match.right.path, "right")

    def _render_canvas(self, canvas: tk.Canvas, path: Path, side: str) -> ImageTk.PhotoImage:
        viewport_width = max(320, canvas.winfo_width() - 8)
        viewport_height = max(320, canvas.winfo_height() - 8)
        scale = self.zoom[side]
        photo = self._photo(path, int(viewport_width * scale), int(viewport_height * scale))
        content_width = max(canvas.winfo_width(), photo.width())
        content_height = max(canvas.winfo_height(), photo.height())
        old_x = canvas.xview()
        old_y = canvas.yview()
        canvas.delete("all")
        canvas.create_image(content_width / 2, content_height / 2, image=photo, anchor="center")
        canvas.configure(scrollregion=(0, 0, content_width, content_height))
        if scale > 1 and old_x != (0.0, 1.0):
            canvas.xview_moveto(old_x[0])
            canvas.yview_moveto(old_y[0])
        else:
            center_x = max(0.0, (content_width - canvas.winfo_width()) / (2 * content_width))
            center_y = max(0.0, (content_height - canvas.winfo_height()) / (2 * content_height))
            canvas.xview_moveto(center_x)
            canvas.yview_moveto(center_y)
        return photo

    def _photo(self, path: Path, width: int, height: int) -> ImageTk.PhotoImage:
        return ImageTk.PhotoImage(self.thumbnail_cache.get(path, width, height))

    def _prefetch_upcoming(self) -> None:
        if not self.result or not self.result.matches:
            return
        width = max(320, self.image_frame.winfo_width() // 2 - 20)
        height = max(320, self.image_frame.winfo_height() - 20)
        # Keep several pairs ready even during very fast keyboard review.
        upcoming = range(self.index + 1, min(self.index + 9, len(self.result.matches)))
        for index in upcoming:
            match = self.result.matches[index]
            self.thumbnail_cache.prefetch(match.left.path, width, height)
            self.thumbnail_cache.prefetch(match.right.path, width, height)

    def _activate_image(self, side: str) -> None:
        self.active_image = side
        self.left_image.configure(highlightbackground="#56a8ff" if side == "left" else "#555555")
        self.right_image.configure(highlightbackground="#56a8ff" if side == "right" else "#555555")

    def _pan_start(self, event: tk.Event, side: str) -> None:
        self._activate_image(side)
        canvas = self.left_image if side == "left" else self.right_image
        canvas.scan_mark(event.x, event.y)

    def _pan_move(self, event: tk.Event, side: str) -> None:
        canvas = self.left_image if side == "left" else self.right_image
        canvas.scan_dragto(event.x, event.y, gain=1)

    def _wheel_zoom(self, event: tk.Event, side: str) -> str:
        self._activate_image(side)
        self._change_zoom(1.25 if event.delta > 0 else 0.8)
        return "break"

    def _change_zoom(self, factor: float) -> None:
        side = self.active_image
        self.zoom[side] = min(4.0, max(1.0, self.zoom[side] * factor))
        self._render_images()
        self.status.set(f"{side.title()} image zoom: {self.zoom[side] * 100:.0f}% · drag to pan")

    def _reset_zoom(self) -> None:
        self.zoom[self.active_image] = 1.0
        self._render_images()
        self.status.set(f"{self.active_image.title()} image zoom reset to fit")

    def _resize(self, _event: tk.Event) -> None:
        if getattr(self, "_resize_job", None):
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, self._render_images)

    def _move(self, amount: int) -> None:
        if not self.result or not self.result.matches:
            return
        self.index = min(max(self.index + amount, 0), len(self.result.matches) - 1)
        self._show()

    def _start_rapid(self) -> None:
        if not self.result or not self.result.matches:
            messagebox.showinfo("No matches", "Match images before starting rapid review.")
            return
        self.rapid = True
        self.focus_force()
        self.status.set("Rapid Review: press A to approve or R to reject; arrows move.")

    def _decide(self, status: str) -> None:
        if not self.session or not self.result or not self.result.matches:
            return
        if not self.rapid and not messagebox.askyesno("Start review?", "Start Rapid Review now?"):
            return
        self.rapid = True
        self.session.decide(self.index, status)
        if self.index < len(self.result.matches) - 1:
            self.index += 1
        self._show()

    def _export(self) -> None:
        if not self.session:
            messagebox.showinfo("Nothing to export", "Match images first.")
            return
        destination = filedialog.askdirectory(title="Choose a folder for the CSV lists")
        if destination:
            decisions, unmatched = self.session.export(Path(destination))
            messagebox.showinfo("Export complete", f"Saved:\n{decisions.name}\n{unmatched.name}")

    def _close(self) -> None:
        self.thumbnail_cache.close()
        self.destroy()


def main() -> None:
    app = CompareApp()
    app.mainloop()
