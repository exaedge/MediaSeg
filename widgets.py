import os
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from themes import THEME_DARK, THEMES


MIN_CHUNK_SIZE_MB = 10
MIN_RELIABLE_CHUNK_SIZE_MB = 30
MAX_SLIDER_CHUNK_SIZE_MB = 400
MAX_MANUAL_CHUNK_SIZE_MB = 999
SLIDER_TICK_LABEL_X_OFFSET = -6
OFFICIALLY_SUPPORTED_EXTENSIONS = (".mp4", ".webm", ".mov")
EXPERIMENTAL_SUPPORTED_EXTENSIONS = (".m4a", ".mp3", ".wav")
GUI_ACCEPTED_EXTENSIONS = OFFICIALLY_SUPPORTED_EXTENSIONS + EXPERIMENTAL_SUPPORTED_EXTENSIONS
EXAEDGE_ABOUT_URL = "https://exaedge.ai/?src=mediaseg"
EXAEDGE_FOOTER_URL = "https://exaedge.ai/?src=mediaseg"


def format_size(size_bytes):
    if size_bytes < 1000:
        return f"{size_bytes} B"
    if size_bytes < 1000 * 1000:
        return f"{size_bytes / 1000:.1f} KB"
    if size_bytes < 1000 * 1000 * 1000:
        return f"{size_bytes / (1000 * 1000):.1f} MB"
    return f"{size_bytes / (1000 * 1000 * 1000):.2f} GB"


def format_duration(seconds):
    try:
        secs = int(round(seconds))
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        remaining_secs = secs % 60
        return f"{hours:02d}:{minutes:02d}:{remaining_secs:02d}"
    except Exception:
        return "--:--:--"


def is_gui_supported_extension(file_path):
    return os.path.splitext(file_path)[1].lower() in GUI_ACCEPTED_EXTENSIONS


def supported_format_summary():
    return "Official: MP4, WEBM, MOV | Experimental: M4A, MP3, WAV"


def supported_file_dialog_filter():
    patterns = " ".join(f"*{ext}" for ext in GUI_ACCEPTED_EXTENSIONS)
    return f"Supported Media Files ({patterns});;All Files (*)"


def get_estimated_chunk_factor(target_mb):
    if target_mb >= 100:
        return 0.98
    if target_mb >= 50:
        return 0.965
    return 0.955


def format_filename_middle_elide(filename, label):
    if not filename or label is None:
        return filename

    width = label.contentsRect().width()
    if width <= 0:
        width = 400

    font = label.font()
    if font is None:
        return filename

    fm = QFontMetrics(font)
    if fm.horizontalAdvance(filename) <= width:
        return filename

    base, ext = os.path.splitext(filename)
    if len(base) > 180:
        base = f"{base[:90]}...{base[-90:]}"

    low = 0
    high = len(base)
    max_i = 0
    while low <= high:
        mid = (low + high) // 2
        if fm.horizontalAdvance(base[:mid]) <= width:
            max_i = mid
            low = mid + 1
        else:
            high = mid - 1

    low = 0
    high = len(base)
    min_i = len(base)
    while low <= high:
        mid = (low + high) // 2
        if fm.horizontalAdvance(base[mid:] + ext) <= width:
            min_i = mid
            high = mid - 1
        else:
            low = mid + 1

    best_split = -1
    if min_i <= max_i:
        allowed_min = max(1, min_i)
        allowed_max = min(len(base) - 1, max_i)
        if allowed_min <= allowed_max:
            mid_pt = len(base) // 2
            if allowed_min <= mid_pt <= allowed_max:
                best_split = mid_pt
            elif mid_pt < allowed_min:
                best_split = allowed_min
            else:
                best_split = allowed_max

    if best_split != -1:
        return f"{base[:best_split]}\n{base[best_split:]}{ext}"

    low = 0
    high = len(base)
    first_part_len = 0
    while low <= high:
        mid = (low + high) // 2
        if fm.horizontalAdvance(base[:mid] + "...") <= width:
            first_part_len = mid
            low = mid + 1
        else:
            high = mid - 1
    first_part = base[:first_part_len]

    low = 0
    high = len(base)
    second_part_len = 0
    while low <= high:
        mid = (low + high) // 2
        test_str = "..." + (base[-mid:] if mid > 0 else "") + ext
        if fm.horizontalAdvance(test_str) <= width:
            second_part_len = mid
            low = mid + 1
        else:
            high = mid - 1
    second_part = base[-second_part_len:] if second_part_len > 0 else ""

    if not first_part or not second_part:
        return fm.elidedText(filename, Qt.ElideMiddle, width)

    if len(first_part) + len(second_part) > len(base):
        split_idx = len(base) // 2
        first_part = base[:split_idx]
        second_part = base[split_idx:]

    return f"{first_part}...\n...{second_part}{ext}"


def get_asset_path(*parts):
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / Path(*parts)
    return Path(__file__).resolve().parent / "assets" / Path(*parts)


def get_bundle_path(*parts):
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / Path(*parts)
    return Path(__file__).resolve().parent / Path(*parts)


def get_asset_icon_path(icon_name):
    return get_asset_path("icons", icon_name)


def recolor_svg_bytes(svg_bytes, color="#F3F5F8"):
    if not color:
        return svg_bytes
    svg_bytes = svg_bytes.replace(b"currentColor", color.encode("utf-8"))
    svg_bytes = svg_bytes.replace(b'stroke="black"', f'stroke="{color}"'.encode("utf-8"))
    svg_bytes = svg_bytes.replace(b'stroke="#000000"', f'stroke="{color}"'.encode("utf-8"))
    svg_bytes = svg_bytes.replace(b'fill="black"', f'fill="{color}"'.encode("utf-8"))
    svg_bytes = svg_bytes.replace(b'fill="#000000"', f'fill="{color}"'.encode("utf-8"))
    return svg_bytes


def load_svg_widget(widget, icon_name, color="#F3F5F8"):
    icon_path = get_asset_icon_path(icon_name)
    widget.load(QByteArray(recolor_svg_bytes(icon_path.read_bytes(), color)))


def make_svg_icon(icon_name, color="#F3F5F8", size=24):
    icon_path = get_asset_icon_path(icon_name)
    svg_data = recolor_svg_bytes(icon_path.read_bytes(), color)
    renderer = QSvgRenderer(QByteArray(svg_data))
    screen = QApplication.primaryScreen()
    dpr = max(1.0, screen.devicePixelRatio()) if screen else 1.0

    pixel_size = max(1, int(round(size * dpr)))
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.transparent)
    if not renderer.isValid():
        return QIcon(pixmap)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, pixel_size, pixel_size))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return QIcon(pixmap)


def get_svg_scaled_size(svg_path, max_width, max_height):
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        return max_width, max_height

    view_box = renderer.viewBoxF()
    source_width = view_box.width() if view_box.width() > 0 else max_width
    source_height = view_box.height() if view_box.height() > 0 else max_height
    scale = min(max_width / source_width, max_height / source_height)
    target_width = max(1, int(round(source_width * scale)))
    target_height = max(1, int(round(source_height * scale)))
    return target_width, target_height


class DropArea(QFrame):
    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropArea")
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self._theme = THEMES[THEME_DARK]
        self.apply_theme(self._theme)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 16, 20, 16)

        self.icon_widget = QSvgWidget()
        self.icon_widget.setFixedSize(28, 28)
        load_svg_widget(self.icon_widget, "file-video-camera.svg", self._theme["text"])
        layout.addWidget(self.icon_widget, alignment=Qt.AlignCenter)

        self.text_label = QLabel("Drop file to segment")
        self.text_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._theme['text']};")
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)

        self.subtext_label = QLabel(supported_format_summary())
        self.subtext_label.setStyleSheet(f"font-size: 11px; color: {self._theme['muted_text']};")
        self.subtext_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtext_label)

    def apply_theme(self, theme, hovered=False):
        self._theme = theme
        border = theme["drop_border_hover"] if hovered else theme["drop_border"]
        background = theme["drop_hover"] if hovered else theme["drop_bg"]
        self.setStyleSheet(
            f"""
            #DropArea {{
                border: 2px dashed {border};
                border-radius: 16px;
                background-color: {background};
            }}
            """
        )
        if hasattr(self, "icon_widget"):
            load_svg_widget(self.icon_widget, "file-video-camera.svg", theme["text"])
            self.text_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme['text']};")
            self.subtext_label.setStyleSheet(f"font-size: 11px; color: {theme['muted_text']};")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path) and is_gui_supported_extension(local_path):
                    self.apply_theme(self._theme, hovered=True)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.apply_theme(self._theme)
        event.accept()

    def dropEvent(self, event):
        self.apply_theme(self._theme)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path) and is_gui_supported_extension(local_path):
                    self.fileDropped.emit(local_path)
                    event.acceptProposedAction()
                    return
        event.ignore()


class FileInfoCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileInfoCard")
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme = THEMES[THEME_DARK]
        self.apply_theme(self._theme)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.icon_badge = QWidget()
        self.icon_badge.setFixedSize(28, 28)
        icon_badge_layout = QVBoxLayout(self.icon_badge)
        icon_badge_layout.setContentsMargins(0, 0, 0, 0)
        icon_badge_layout.setAlignment(Qt.AlignCenter)
        self.icon_widget = QSvgWidget()
        self.icon_widget.setFixedSize(24, 24)
        load_svg_widget(self.icon_widget, "file-question-mark.svg", self._theme["text"])
        icon_badge_layout.addWidget(self.icon_widget, alignment=Qt.AlignCenter)
        layout.addWidget(self.icon_badge)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        self.name_label = QLabel("No file selected")
        self.name_label.setWordWrap(False)
        self.name_label.setFixedHeight(34)
        self.name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self._theme['text']}; line-height: 1.2;")
        text_layout.addWidget(self.name_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet(f"color: {self._theme['border']}; background-color: {self._theme['border']}; max-height: 1px; border: none;")
        text_layout.addWidget(divider)

        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)

        self.format_row = QHBoxLayout()
        self.format_lbl = QLabel("Format")
        self.format_lbl.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 11px;")
        self.format_val = QLabel("--")
        self.format_val.setStyleSheet(f"font-weight: normal; color: {self._theme['text']}; font-size: 11px;")
        self.format_row.addWidget(self.format_lbl)
        self.format_row.addStretch()
        self.format_row.addWidget(self.format_val)

        self.size_row = QHBoxLayout()
        self.size_lbl = QLabel("Original Size")
        self.size_lbl.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 11px;")
        self.size_val = QLabel("--")
        self.size_val.setStyleSheet(f"font-weight: normal; color: {self._theme['text']}; font-size: 11px;")
        self.size_row.addWidget(self.size_lbl)
        self.size_row.addStretch()
        self.size_row.addWidget(self.size_val)

        self.dur_row = QHBoxLayout()
        self.dur_lbl = QLabel("Duration")
        self.dur_lbl.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 11px;")
        self.dur_val = QLabel("--:--:--")
        self.dur_val.setStyleSheet(f"font-weight: normal; color: {self._theme['text']}; font-size: 11px;")
        self.dur_row.addWidget(self.dur_lbl)
        self.dur_row.addStretch()
        self.dur_row.addWidget(self.dur_val)

        self.chunks_row = QHBoxLayout()
        self.chunks_lbl = QLabel("Estimated Chunks")
        self.chunks_lbl.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 11px;")
        self.chunks_val = QLabel("--")
        self.chunks_val.setStyleSheet(f"font-weight: normal; color: {self._theme['link']}; font-size: 11px;")
        self.chunks_row.addWidget(self.chunks_lbl)
        self.chunks_row.addStretch()
        self.chunks_row.addWidget(self.chunks_val)

        details_layout.addLayout(self.format_row)
        details_layout.addLayout(self.size_row)
        details_layout.addLayout(self.dur_row)
        details_layout.addLayout(self.chunks_row)

        text_layout.addLayout(details_layout)
        layout.addLayout(text_layout, 1)
        self._full_filename = ""
        self._file_ext = ""
        self.empty_text = "No file selected"
        self.reset_card()

    def apply_theme(self, theme):
        self._theme = theme
        self.setStyleSheet(
            f"""
            #FileInfoCard {{
                border: 1px solid {theme['border']};
                border-radius: 16px;
                background-color: {theme['surface']};
            }}
            """
        )
        if hasattr(self, "name_label"):
            self.name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme['text']}; line-height: 1.2;")
            for label in (self.format_lbl, self.size_lbl, self.dur_lbl, self.chunks_lbl):
                label.setStyleSheet(f"color: {theme['muted_text']}; font-size: 11px;")
            self.format_val.setStyleSheet(f"font-weight: normal; color: {theme['text']}; font-size: 11px;")
            self.size_val.setStyleSheet(f"font-weight: normal; color: {theme['text']}; font-size: 11px;")
            self.dur_val.setStyleSheet(f"font-weight: normal; color: {theme['text']}; font-size: 11px;")
            self.chunks_val.setStyleSheet(f"font-weight: normal; color: {theme['link']}; font-size: 11px;")

    def set_ui_texts(self, texts):
        self.format_lbl.setText(texts["fileinfo_format"])
        self.size_lbl.setText(texts["fileinfo_size"])
        self.dur_lbl.setText(texts["fileinfo_duration"])
        self.chunks_lbl.setText(texts["fileinfo_chunks"])
        self.empty_text = texts["fileinfo_empty"]
        if not self._full_filename:
            self.name_label.setText(self.empty_text)

    def set_file_name(self, filename):
        self._full_filename = filename or ""
        self._file_ext = os.path.splitext(self._full_filename)[1].upper() if self._full_filename else ""
        load_svg_widget(self.icon_widget, "file-text.svg", "#F3F5F8")
        self.update_filename_display()

    def reset_card(self):
        self._full_filename = ""
        self._file_ext = ""
        load_svg_widget(self.icon_widget, "file-question-mark.svg", self._theme["text"])
        self.name_label.setText(self.empty_text)
        self.format_val.setText("--")
        self.size_val.setText("--")
        self.dur_val.setText("--:--:--")
        self.chunks_val.setText("--")

    def update_filename_display(self):
        if not self._full_filename:
            self.name_label.setText(self.empty_text)
            return
        self.name_label.setText(format_filename_middle_elide(self._full_filename, self.name_label))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_filename_display()


class ClickableSvgWidget(QSvgWidget):
    def __init__(self, url=None, parent=None):
        super().__init__(parent)
        self._url = url
        if url:
            self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._url:
            QDesktopServices.openUrl(QUrl(self._url))
            event.accept()
            return
        super().mousePressEvent(event)


class SliderTicksWidget(QWidget):
    def __init__(self, slider, tick_values, parent=None):
        super().__init__(parent)
        self.slider = slider
        self.tick_values = tick_values
        self.tick_labels = []
        self._theme = THEMES[THEME_DARK]
        self.setMinimumHeight(18)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for value, text in tick_values:
            label = QLabel(text, self)
            label.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 10px; font-weight: normal;")
            label.adjustSize()
            self.tick_labels.append((value, label))

        self.slider.valueChanged.connect(self.update_tick_positions)
        self.slider.rangeChanged.connect(self.update_tick_positions)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_tick_positions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_tick_positions()

    def update_tick_positions(self):
        if not self.slider:
            return

        option = QStyleOptionSlider()
        self.slider.initStyleOption(option)
        groove_rect = self.slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self.slider)
        handle_rect = self.slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self.slider)

        left = groove_rect.left() + (handle_rect.width() / 2.0)
        right = groove_rect.right() - (handle_rect.width() / 2.0)
        available = max(1.0, right - left)

        slider_min = self.slider.minimum()
        slider_max = self.slider.maximum()
        value_span = max(1, slider_max - slider_min)

        local_left = self.mapFromGlobal(self.slider.mapToGlobal(groove_rect.topLeft())).x()

        for value, label in self.tick_labels:
            ratio = (value - slider_min) / value_span
            center_x = local_left + left + (available * ratio)
            label.adjustSize()
            label_x = int(round(center_x - (label.width() / 2.0) + SLIDER_TICK_LABEL_X_OFFSET))
            label_x = max(0, min(label_x, max(0, self.width() - label.width())))
            label.move(label_x, 0)

    def apply_theme(self, theme):
        self._theme = theme
        for _, label in self.tick_labels:
            label.setStyleSheet(f"color: {theme['muted_text']}; font-size: 10px; font-weight: normal;")


class ProcessingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._theme = THEMES[THEME_DARK]
        self.setObjectName("ProcessingOverlay")

        self.container = QFrame(self)
        self.container.setMinimumWidth(320)
        self.container.setMaximumWidth(440)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(28, 24, 28, 24)
        container_layout.setSpacing(12)
        container_layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setPixmap(make_svg_icon("loader-circle.svg", color=self._theme["text"], size=28).pixmap(28, 28))

        self.title_label = QLabel("Processing...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"color: {self._theme['text']}; font-size: 16px; font-weight: bold;")

        self.subtitle_label = QLabel("Please wait while MediaSeg works.")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setFixedWidth(320)
        self.subtitle_label.setStyleSheet(f"color: {self._theme['muted_text']}; font-size: 12px;")

        container_layout.addWidget(self.icon_label)
        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.subtitle_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.container, alignment=Qt.AlignCenter)
        self.apply_theme(self._theme)

    def set_message(self, title, subtitle=None):
        self.title_label.setText(title)
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)
        self.title_label.adjustSize()
        self.title_label.setFixedHeight(self.title_label.sizeHint().height())
        self.subtitle_label.adjustSize()
        self.subtitle_label.setFixedHeight(self.subtitle_label.sizeHint().height())
        self.title_label.updateGeometry()
        self.subtitle_label.updateGeometry()
        self.container.adjustSize()
        self.updateGeometry()

    def apply_theme(self, theme):
        self._theme = theme
        self.setStyleSheet(
            f"""
            QWidget#ProcessingOverlay {{
                background-color: {theme['overlay_backdrop']};
            }}
            """
        )
        self.container.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme['overlay_card']};
                border: 1px solid {theme['border']};
                border-radius: 16px;
            }}
            """
        )
        self.icon_label.setPixmap(make_svg_icon("loader-circle.svg", color=theme["text"], size=28).pixmap(28, 28))
        self.title_label.setStyleSheet(f"color: {theme['text']}; font-size: 16px; font-weight: bold;")
        self.subtitle_label.setStyleSheet(f"color: {theme['muted_text']}; font-size: 12px;")
