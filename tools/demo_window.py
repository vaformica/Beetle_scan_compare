"""Open the real GUI with synthetic images for README screenshots."""

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from beetle_compare.app import CompareApp


class DemoCompareApp(CompareApp):
    """Disable file dialogs so automated screenshots cannot open a chooser."""

    def _choose(self, variable):
        del variable


def create_scan(path: Path, accent: str, offset: int) -> None:
    image = Image.new("RGB", (900, 1100), "#f1eee6")
    draw = ImageDraw.Draw(image)
    draw.ellipse((270 + offset, 130, 630 + offset, 890), fill="#201711", outline=accent, width=10)
    draw.ellipse((345 + offset, 40, 555 + offset, 260), fill="#2b1c12", outline=accent, width=8)
    draw.line((450 + offset, 260, 450 + offset, 870), fill=accent, width=5)
    for y in (360, 520, 680):
        draw.line((280 + offset, y, 130, y - 100), fill="#342219", width=14)
        draw.line((620 + offset, y, 770, y - 100), fill="#342219", width=14)
    draw.text((35, 1025), "Synthetic demonstration image — not research data", fill="#555555")
    image.save(path, quality=90)


def main() -> None:
    root = Path(tempfile.gettempdir()) / "beetle-compare-readme-demo"
    left = root / "Scanner_A"
    right = root / "Scanner_B"
    left.mkdir(parents=True, exist_ok=True)
    right.mkdir(parents=True, exist_ok=True)
    for index in range(1, 7):
        create_scan(left / f"Box12-Beetle-{index:03d}-D.jpg", "#9e7555", 0)
        create_scan(right / f"Box12_Beetle_{index:03d}-D.jpg", "#b86442", 7 if index % 2 else -5)

    app = DemoCompareApp()
    # Keep the window compact enough for a clean crop on common laptop displays.
    app.geometry("1180x850+40+60")
    app.left_folder.set(left)
    app.right_folder.set(right)
    app.after(500, app._load)
    app.after(1800, lambda: app.session and app.session.decide(0, "rejected"))
    app.after(1900, lambda: app.session and app.session.decide(2, "rejected"))
    app.after(2000, app._refresh_rejections)
    app.after(2100, lambda: setattr(app, "index", 2))
    app.after(2200, app._show)
    app.after(8000, lambda: app._activate_image("right"))
    app.after(8100, lambda: app._change_zoom(1.8))
    app.mainloop()


if __name__ == "__main__":
    main()
