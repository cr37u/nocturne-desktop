"""Generate icons and packaging images from the vector logo.

    python tools/make_assets.py

Outputs (all reproducible, no binary sources needed):
  nocturne/assets/icons/nocturne.ico, nocturne-{16..512}.png
  packaging/linux/icons/hicolor/<size>/apps/io.github.nocturne.png
  packaging/msix/Assets/*.png               (logos, widget gradient, widget icon/screenshot)
  widget-bridge/Assets/widget-gradient.png  (Adaptive Card background)
  build/version_info.txt                    (PyInstaller version resource)
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath  # noqa: E402

from nocturne import __version__, icons  # noqa: E402


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    return bytes(data.data())


def write_ico(path: Path, sizes: list[int]) -> None:
    images = [png_bytes(icons.app_icon_image(s)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for size, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(images))


def gradient_image(w: int, h: int, stops: list[tuple[float, str]], radius: float = 0, angle_deg: float = 135) -> QImage:
    import math

    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    rad = math.radians(angle_deg)
    dx, dy = math.sin(rad), -math.cos(rad)
    length = abs(w * dx) + abs(h * dy)
    cx, cy = w / 2, h / 2
    grad = QLinearGradient(cx - dx * length / 2, cy - dy * length / 2, cx + dx * length / 2, cy + dy * length / 2)
    for pos, color in stops:
        grad.setColorAt(pos, QColor(color))
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.fillPath(path, grad)
    p.end()
    return img


def logo_on_canvas(w: int, h: int, logo: int, bg: str | None = None) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(bg) if bg else Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawImage((w - logo) // 2, (h - logo) // 2, icons.app_icon_image(logo))
    p.end()
    return img


def version_info(path: Path) -> None:
    parts = [int(x) for x in __version__.split(".")[:3]] + [0]
    ver = tuple(parts[:4])
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver}, prodvers={ver}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Nocturne'),
      StringStruct('FileDescription', 'Nocturne'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'Nocturne'),
      StringStruct('LegalCopyright', 'Nocturne contributors'),
      StringStruct('OriginalFilename', 'Nocturne.exe'),
      StringStruct('ProductName', 'Nocturne'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def main() -> None:
    QGuiApplication.instance() or QGuiApplication(sys.argv)

    icon_dir = ROOT / "nocturne" / "assets" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    write_ico(icon_dir / "nocturne.ico", [16, 20, 24, 32, 40, 48, 64, 128, 256])
    for s in (16, 32, 48, 64, 128, 256, 512):
        icons.app_icon_image(s).save(str(icon_dir / f"nocturne-{s}.png"))

    hicolor = ROOT / "packaging" / "linux" / "icons" / "hicolor"
    for s in (32, 48, 64, 128, 256, 512):
        d = hicolor / f"{s}x{s}" / "apps"
        d.mkdir(parents=True, exist_ok=True)
        icons.app_icon_image(s).save(str(d / "io.github.nocturne.png"))

    msix = ROOT / "packaging" / "msix" / "Assets"
    msix.mkdir(parents=True, exist_ok=True)
    for old in msix.glob("*.png"):
        old.unlink()
    # App list / taskbar icon. "altform-unplated" variants (indexed in resources.pri by build_msix.ps1)
    # stop Windows from drawing the icon on a coloured/grey plate.
    logo_on_canvas(44, 44, 44).save(str(msix / "Square44x44Logo.png"))
    for scale in (100, 125, 150, 200, 400):
        size = 44 * scale // 100
        logo_on_canvas(size, size, size).save(str(msix / f"Square44x44Logo.scale-{scale}.png"))
    for t in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
        for form in ("altform-unplated", "altform-lightunplated"):
            logo_on_canvas(t, t, t).save(str(msix / f"Square44x44Logo.targetsize-{t}_{form}.png"))
        logo_on_canvas(t, t, t).save(str(msix / f"Square44x44Logo.targetsize-{t}.png"))
    for scale in (100, 200):
        f = scale / 100
        logo_on_canvas(int(150 * f), int(150 * f), int(96 * f)).save(str(msix / f"Square150x150Logo.scale-{scale}.png"))
        logo_on_canvas(int(310 * f), int(150 * f), int(96 * f)).save(str(msix / f"Wide310x150Logo.scale-{scale}.png"))
        logo_on_canvas(int(50 * f), int(50 * f), int(50 * f)).save(str(msix / f"StoreLogo.scale-{scale}.png"))
    logo_on_canvas(150, 150, 96).save(str(msix / "Square150x150Logo.png"))
    logo_on_canvas(310, 150, 96).save(str(msix / "Wide310x150Logo.png"))
    logo_on_canvas(50, 50, 50).save(str(msix / "StoreLogo.png"))
    logo_on_canvas(620, 300, 160, "#0A0A14").save(str(msix / "SplashScreen.png"))

    # Widgets board assets
    card = gradient_image(600, 300, [(0, "#1E40AF"), (1, "#3B0764")], radius=0, angle_deg=135)
    card.save(str(msix / "widget-gradient.png"))
    bridge_assets = ROOT / "widget-bridge" / "Assets"
    bridge_assets.mkdir(parents=True, exist_ok=True)
    card.save(str(bridge_assets / "widget-gradient.png"))
    icons.app_icon_image(96).save(str(msix / "WidgetIcon.png"))
    icons.app_icon_image(96).save(str(bridge_assets / "WidgetIcon.png"))
    shot = gradient_image(300, 304, [(0, "#20202C"), (1, "#20202C")], radius=16)
    p = QPainter(shot)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawImage(16, 52, gradient_image(268, 120, [(0, "#1E40AF"), (1, "#3B0764")], radius=14))
    p.drawImage(32, 76, icons.app_icon_image(72))
    p.drawImage(16, 14, icons.app_icon_image(22))
    p.end()
    shot.save(str(msix / "WidgetScreenshot.png"))
    shot.save(str(bridge_assets / "WidgetScreenshot.png"))

    # Action icons for the Adaptive Cards (white glyphs, embedded as data URIs by the bridge)
    for name in ("previous", "play", "pause", "next", "plus"):
        icons.render(name, "#F1F1F7", 48).save(str(bridge_assets / f"icon-{name}.png"))
    # Round buttons (rendered at 2x): white primary play/pause with purple glyph, translucent prev/next.
    def round_button(name: str, size: int, fill: str, glyph: str, glyph_ratio: float) -> QImage:
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(fill))
        p.drawEllipse(0, 0, size, size)
        if fill.upper() == "#F1F1F7":  # keep the white button visible on the light Widgets theme
            from PySide6.QtGui import QPen

            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#667C3AED"), size * 0.035))
            inset = size * 0.035 / 2
            p.drawEllipse(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))
        g = int(size * glyph_ratio)
        p.drawImage((size - g) // 2 + (int(size * 0.03) if name == "play" else 0), (size - g) // 2,
                    icons.render(name, glyph, g))
        p.end()
        return img

    round_button("play", 96, "#F1F1F7", "#3B0764", 0.40).save(str(bridge_assets / "btn-play.png"))
    round_button("pause", 96, "#F1F1F7", "#3B0764", 0.40).save(str(bridge_assets / "btn-pause.png"))
    round_button("previous", 80, "#2E2A4A", "#F1F1F7", 0.42).save(str(bridge_assets / "btn-previous.png"))
    round_button("next", 80, "#2E2A4A", "#F1F1F7", 0.42).save(str(bridge_assets / "btn-next.png"))
    # Artwork placeholder: rounded gradient square with the moon (shown when a track has no cover).
    ph = gradient_image(144, 144, [(0, "#2B4FD0"), (1, "#5B21B6")], radius=20)
    p = QPainter(ph)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawImage(40, 40, icons.render("moon", "#F1F1F7", 64))
    p.end()
    ph.save(str(bridge_assets / "art-placeholder.png"))
    gradient_image(320, 160, [(0, "#1E40AF"), (1, "#3B0764")], radius=0).save(str(bridge_assets / "widget-gradient.png"))

    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    version_info(build / "version_info.txt")
    print("Assets generated.")


if __name__ == "__main__":
    main()
