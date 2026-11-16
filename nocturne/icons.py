"""Vector icons (same paths as the HTML design) rendered for QML, menus and the taskbar."""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

# Each icon: (stroke width or None for fill-only icons, [elements]).
# Elements: ("p", d, filled) | ("c", cx, cy, r, filled) | ("r", x, y, w, h, rx, filled)
ICONS: dict[str, tuple[float | None, list[tuple]]] = {
    "moon": (2, [("p", "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z", False)]),
    "moon-wave": (
        1.2,
        [
            ("p", "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z", False),
            ("p", "M8 13v2M11 11v6M14 12.5v3", False),
        ],
    ),
    "music": (2, [("p", "M9 18V5l12-2v13", False), ("c", 6, 18, 3, False), ("c", 18, 16, 3, False)]),
    "playlists": (2, [("p", "M3 6h12M3 12h12M3 18h7", False), ("p", "M17 13v8l5-4z", True)]),
    "download": (2, [("p", "M12 3v12", False), ("p", "m7 10 5 5 5-5", False), ("p", "M5 21h14", False)]),
    "heart": (
        2,
        [
            (
                "p",
                "M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 "
                "2 8.5c0 2.3 1.5 4 3 5.5l7 7z",
                False,
            )
        ],
    ),
    "heart-filled": (
        2,
        [
            (
                "p",
                "M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 "
                "2 8.5c0 2.3 1.5 4 3 5.5l7 7z",
                True,
            )
        ],
    ),
    "plus": (2.6, [("p", "M12 5v14M5 12h14", False)]),
    "settings": (
        2,
        [
            ("p", "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12", False),
            ("c", 16, 6, 2, False),
            ("c", 10, 12, 2, False),
            ("c", 18, 18, 2, False),
        ],
    ),
    "link": (
        2,
        [
            ("p", "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1", False),
            ("p", "M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1", False),
        ],
    ),
    "search": (2, [("c", 11, 11, 7, False), ("p", "m20 20-3.5-3.5", False)]),
    "shuffle": (
        2,
        [
            ("p", "M16 3h5v5", False),
            ("p", "M4 20 21 3", False),
            ("p", "M21 16v5h-5", False),
            ("p", "m15 15 6 6", False),
            ("p", "M4 4l5 5", False),
        ],
    ),
    "play": (None, [("p", "M7 4v16l13-8z", True)]),
    "pause": (None, [("r", 6, 4, 4, 16, 1, True), ("r", 14, 4, 4, 16, 1, True)]),
    "more": (None, [("c", 5, 12, 1.6, True), ("c", 12, 12, 1.6, True), ("c", 19, 12, 1.6, True)]),
    "grip": (2, [("p", "M5 9h14M5 15h14", False)]),
    "previous": (2, [("p", "M19 20 9 12l10-8z", True), ("p", "M5 19V5", False)]),
    "next": (2, [("p", "m5 4 10 8-10 8z", True), ("p", "M19 5v14", False)]),
    "repeat": (
        2,
        [
            ("p", "m17 2 4 4-4 4", False),
            ("p", "M3 11v-1a4 4 0 0 1 4-4h14", False),
            ("p", "m7 22-4-4 4-4", False),
            ("p", "M21 13v1a4 4 0 0 1-4 4H3", False),
        ],
    ),
    "queue": (2, [("p", "M3 6h13M3 12h13M3 18h9", False), ("p", "M17 15v6l4-3z", True)]),
    "volume": (2, [("p", "M11 5 6 9H2v6h4l5 4z", False), ("p", "M15.5 8.5a5 5 0 0 1 0 7", False)]),
    "volume-x": (2, [("p", "M11 5 6 9H2v6h4l5 4z", False), ("p", "M22 9l-6 6M16 9l6 6", False)]),
    "miniplayer": (2, [("r", 3, 5, 18, 14, 2, False), ("r", 12, 12, 7, 5, 1, True)]),
    "expand": (
        2.2,
        [("p", "M15 3h6v6", False), ("p", "M9 21H3v-6", False), ("p", "M21 3l-7 7", False), ("p", "M3 21l7-7", False)],
    ),
    "close": (2.2, [("p", "M18 6 6 18M6 6l12 12", False)]),
    "check": (2.4, [("p", "M20 6 9 17l-5-5", False)]),
    "trash": (2, [("p", "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6", False), ("p", "M10 11v6M14 11v6", False)]),
    "folder": (2, [("p", "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", False)]),
    "x-circle": (2, [("c", 12, 12, 9, False), ("p", "M15 9l-6 6M9 9l6 6", False)]),
    "retry": (2, [("p", "M3 12a9 9 0 1 0 3-6.7L3 8", False), ("p", "M3 3v5h5", False)]),
    "refresh": (2, [("p", "M21 12a9 9 0 1 1-3-6.7L21 8", False), ("p", "M21 3v5h-5", False)]),
    "clock": (2, [("c", 12, 12, 9, False), ("p", "M12 7v5l3 2", False)]),
    "globe": (
        2,
        [
            ("c", 12, 12, 9, False),
            ("p", "M3 12h18", False),
            ("p", "M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z", False),
        ],
    ),
    "chevron-down": (2, [("p", "m6 9 6 6 6-6", False)]),
    "chevron-right": (2, [("p", "m9 6 6 6-6 6", False)]),
    "pin": (2, [("p", "M12 17v5", False), ("p", "M9 3h6l-1 7 4 3H6l4-3z", False)]),
    "layers": (2, [("p", "m12 3 9 5-9 5-9-5z", False), ("p", "m3 13 9 5 9-5", False)]),
    "eye-off": (
        2,
        [
            ("p", "M3 3l18 18", False),
            ("p", "M10.6 6.1A10 10 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-2.8 3.4", False),
            ("p", "M6.4 6.4C3.9 8 2.5 12 2.5 12s3.5 6 9.5 6a9.7 9.7 0 0 0 4.6-1.2", False),
        ],
    ),
    "edit": (2, [("p", "M4 20h4L19 9l-4-4L4 16z", False), ("p", "m13 7 4 4", False)]),
    "widgets": (
        2,
        [
            ("r", 3, 3, 8, 8, 2, False),
            ("r", 13, 3, 8, 8, 2, False),
            ("r", 3, 13, 8, 8, 2, False),
            ("r", 13, 13, 8, 8, 2, False),
        ],
    ),
    "resize": (2, [("r", 3, 7, 18, 10, 5, False), ("p", "M7 12h6", False)]),
    "power": (2, [("p", "M12 3v9", False), ("p", "M6.4 6.4a8 8 0 1 0 11.2 0", False)]),
    "window": (2, [("r", 3, 4, 18, 16, 2, False), ("p", "M3 9h18", False)]),
    "info": (2, [("c", 12, 12, 9, False), ("p", "M12 11v5M12 8h.01", False)]),
}


def svg(name: str, color: str = "#F1F1F7") -> str:
    stroke_width, elements = ICONS.get(name, ICONS["music"])
    if not color.startswith("#"):
        color = "#" + color
    stroke = f'stroke="{color}" stroke-width="{stroke_width}"' if stroke_width else 'stroke="none"'
    parts = []
    for el in elements:
        fill = f'fill="{color}"' if el[-1] else 'fill="none"'
        if el[0] == "p":
            parts.append(f'<path d="{el[1]}" {fill}/>')
        elif el[0] == "c":
            parts.append(f'<circle cx="{el[1]}" cy="{el[2]}" r="{el[3]}" {fill}/>')
        elif el[0] == "r":
            parts.append(f'<rect x="{el[1]}" y="{el[2]}" width="{el[3]}" height="{el[4]}" rx="{el[5]}" {fill}/>')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'{stroke} stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</svg>'
    )


def render(name: str, color: str, size: int) -> QImage:
    size = max(1, int(size))
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode()))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def qicon(name: str, color: str = "#F1F1F7") -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        icon.addPixmap(QPixmap.fromImage(render(name, color, size)))
    return icon


def png_bytes(name: str, color: str, size: int) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    render(name, color, size).save(buf, "PNG")
    buf.close()
    return bytes(data.data())


def app_icon_image(size: int) -> QImage:
    """The Nocturne logo: gradient rounded square with a white moon."""
    from PySide6.QtGui import QLinearGradient, QPainterPath

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#1E40AF"))
    grad.setColorAt(1, QColor("#3B0764"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    p.fillPath(path, grad)
    inset = size * 0.24
    QSvgRenderer(QByteArray(svg("moon", "#F1F1F7").encode())).render(
        p, QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    )
    p.end()
    return image


def app_qicon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(app_icon_image(size)))
    return icon


class IconProvider(QQuickImageProvider):
    """``image://icon/<name>/<RRGGBB>`` — crisp at any size/DPI."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, image_id: str, size: QSize, requested: QSize) -> QImage:  # noqa: N802
        name, _, color = image_id.partition("/")
        color = color.split("?")[0] or "F1F1F7"
        px = max(requested.width(), requested.height(), 24)
        image = render(name, "#" + color.lstrip("#"), px)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image
