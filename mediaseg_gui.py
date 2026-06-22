import sys
import os
import subprocess
import math
import time
from pathlib import Path
from mediaseg_version import get_public_version, get_build_version
from PySide6.QtCore import QThread, Signal, Slot, Qt, QSize, QTimer, QRectF, QByteArray, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIntValidator, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QPushButton,
    QPlainTextEdit,
    QFileDialog,
    QFrame,
    QSizePolicy,
    QToolButton,
    QDialog
)

def format_size(size_bytes):
    if size_bytes < 1000:
        return f"{size_bytes} B"
    elif size_bytes < 1000 * 1000:
        return f"{size_bytes / 1000:.1f} KB"
    elif size_bytes < 1000 * 1000 * 1000:
        return f"{size_bytes / (1000 * 1000):.1f} MB"
    else:
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

def format_filename_middle_elide(filename, label):
    if not filename or label is None:
        return filename

    width = label.contentsRect().width()
    if width <= 0:
        width = 400  # Sensible default before first layout render

    font = label.font()
    if font is None:
        return filename

    fm = QFontMetrics(font)
    
    # If the entire filename fits on 1 line:
    if fm.horizontalAdvance(filename) <= width:
        return filename

    base, ext = os.path.splitext(filename)
    
    # If base name is extremely long, truncate the middle to create a working_base
    if len(base) > 180:
        base = f"{base[:90]}...{base[-90:]}"

    # Try to fit on 2 lines without any ellipsis
    # Use binary search to find the valid range of split points [min_i, max_i]
    # base[:i] must fit in width -> find max_i
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

    # base[i:] + ext must fit in width -> find min_i
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

    # If it doesn't fit on 2 lines without ellipsis, perform 2-line middle-elision
    # Use binary search to find first_part and second_part to avoid linear loops
    low = 0
    high = len(base)
    first_part_len = 0
    while low <= high:
        mid = (low + high) // 2
        test_str = base[:mid] + "..."
        if fm.horizontalAdvance(test_str) <= width:
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

    # Ensure they don't overlap in a weird way
    if len(first_part) + len(second_part) > len(base):
        split_idx = len(base) // 2
        first_part = base[:split_idx]
        second_part = base[split_idx:]

    return f"{first_part}...\n...{second_part}{ext}"

def get_asset_path(*parts):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "assets" / Path(*parts)
    return Path(__file__).resolve().parent / "assets" / Path(*parts)

def get_bundle_path(*parts):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / Path(*parts)
    return Path(__file__).resolve().parent / Path(*parts)

def get_asset_icon_path(icon_name):
    return get_asset_path("icons", icon_name)

EXAEDGE_ABOUT_URL = "https://exaedge.ai/?src=mediaseg"
EXAEDGE_FOOTER_URL = "https://exaedge.ai/?src=mediaseg"

def recolor_svg_bytes(svg_bytes, color="#F3F5F8"):
    if not color:
        return svg_bytes
    svg_bytes = svg_bytes.replace(b'currentColor', color.encode("utf-8"))
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
    dpr = 1.0
    if screen:
        dpr = max(1.0, screen.devicePixelRatio())

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
        
        self.setStyleSheet("""
            #DropArea {
                border: 2px dashed #5B8CFF;
                border-radius: 16px;
                background-color: #171B22;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 16, 20, 16)
        
        self.icon_widget = QSvgWidget()
        self.icon_widget.setFixedSize(28, 28)
        load_svg_widget(self.icon_widget, "file-video-camera.svg", "#F3F5F8")
        layout.addWidget(self.icon_widget, alignment=Qt.AlignCenter)
        
        self.text_label = QLabel("Drop file to segment")
        self.text_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #F3F5F8;")
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)
        
        self.subtext_label = QLabel("Supports MP4, WEBM")
        self.subtext_label.setStyleSheet("font-size: 11px; color: #A6B0BF;")
        self.subtext_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtext_label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    ext = os.path.splitext(local_path)[1].lower()
                    if ext in [".mp4", ".webm"]:
                        self.setStyleSheet("""
                            #DropArea {
                                border: 2px dashed #7DA2FF;
                                border-radius: 16px;
                                background-color: #16233A;
                            }
                        """)
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            #DropArea {
                border: 2px dashed #5B8CFF;
                border-radius: 16px;
                background-color: #171B22;
            }
        """)
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("""
            #DropArea {
                border: 2px dashed #5B8CFF;
                border-radius: 16px;
                background-color: #171B22;
            }
        """)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    ext = os.path.splitext(local_path)[1].lower()
                    if ext in [".mp4", ".webm"]:
                        self.fileDropped.emit(local_path)
                        event.acceptProposedAction()
                        return
        event.ignore()

class FileInfoCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileInfoCard")
        # Keep the card height stable so long filenames do not shift the layout.
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            #FileInfoCard {
                border: 1px solid #2B313B;
                border-radius: 16px;
                background-color: #171B22;
            }
        """)
        
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
        load_svg_widget(self.icon_widget, "file-question-mark.svg", "#F3F5F8")
        icon_badge_layout.addWidget(self.icon_widget, alignment=Qt.AlignCenter)
        layout.addWidget(self.icon_badge)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        
        self.name_label = QLabel("No file selected")
        self.name_label.setWordWrap(False)
        self.name_label.setFixedHeight(34)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #F3F5F8; line-height: 1.2;")
        text_layout.addWidget(self.name_label)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("color: #2B313B; background-color: #2B313B; max-height: 1px; border: none;")
        text_layout.addWidget(divider)
        
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        self.format_row = QHBoxLayout()
        format_lbl = QLabel("Format")
        format_lbl.setStyleSheet("color: #A6B0BF; font-size: 11px;")
        self.format_val = QLabel("--")
        self.format_val.setStyleSheet("font-weight: bold; color: #F3F5F8; font-size: 11px;")
        self.format_row.addWidget(format_lbl)
        self.format_row.addStretch()
        self.format_row.addWidget(self.format_val)

        self.size_row = QHBoxLayout()
        size_lbl = QLabel("Original Size")
        size_lbl.setStyleSheet("color: #A6B0BF; font-size: 11px;")
        self.size_val = QLabel("--")
        self.size_val.setStyleSheet("font-weight: bold; color: #F3F5F8; font-size: 11px;")
        self.size_row.addWidget(size_lbl)
        self.size_row.addStretch()
        self.size_row.addWidget(self.size_val)
        
        self.dur_row = QHBoxLayout()
        dur_lbl = QLabel("Duration")
        dur_lbl.setStyleSheet("color: #A6B0BF; font-size: 11px;")
        self.dur_val = QLabel("--:--:--")
        self.dur_val.setStyleSheet("font-weight: bold; color: #F3F5F8; font-size: 11px;")
        self.dur_row.addWidget(dur_lbl)
        self.dur_row.addStretch()
        self.dur_row.addWidget(self.dur_val)
        
        self.chunks_row = QHBoxLayout()
        chunks_lbl = QLabel("Estimated Chunks")
        chunks_lbl.setStyleSheet("color: #A6B0BF; font-size: 11px;")
        self.chunks_val = QLabel("--")
        self.chunks_val.setStyleSheet("font-weight: bold; color: #7DA2FF; font-size: 11px;")
        self.chunks_row.addWidget(chunks_lbl)
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
        self.reset_card()

    def set_file_name(self, filename):
        self._full_filename = filename or ""
        self._file_ext = os.path.splitext(self._full_filename)[1].upper() if self._full_filename else ""
        load_svg_widget(self.icon_widget, "file-text.svg", "#F3F5F8")
        self.update_filename_display()

    def reset_card(self):
        self._full_filename = ""
        self._file_ext = ""
        load_svg_widget(self.icon_widget, "file-question-mark.svg", "#F3F5F8")
        self.name_label.setText("No file selected")
        self.format_val.setText("--")
        self.size_val.setText("--")
        self.dur_val.setText("--:--:--")
        self.chunks_val.setText("--")

    def update_filename_display(self):
        if not self._full_filename:
            self.name_label.setText("No file selected")
            return
        self.name_label.setText(format_filename_middle_elide(self._full_filename, self.name_label))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_filename_display()

class AccordionHeader(QWidget):
    toggled = Signal(bool)

    def __init__(self, title, expanded=True, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._expanded = expanded
        self._title = title

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.arrow_widget = QSvgWidget()
        self.arrow_widget.setFixedSize(14, 14)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #F3F5F8; font-size: 15px; font-weight: bold; letter-spacing: 0.4px;")

        layout.addWidget(self.arrow_widget)
        layout.addWidget(self.title_label)
        layout.addStretch()
        self.setExpanded(expanded)

    def mousePressEvent(self, event):
        self.setExpanded(not self._expanded)
        self.toggled.emit(self._expanded)
        super().mousePressEvent(event)

    def setExpanded(self, expanded):
        self._expanded = expanded
        icon_name = "chevron-down.svg" if expanded else "chevron-right.svg"
        load_svg_widget(self.arrow_widget, icon_name, "#F3F5F8")


class AccordionSection(QWidget):
    toggled = Signal(bool)

    def __init__(self, title, expanded=True, parent=None):
        super().__init__(parent)
        self.header = AccordionHeader(title, expanded=expanded)
        self.header.toggled.connect(self._on_toggled)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 10, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_widget.setVisible(expanded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.header)
        layout.addWidget(self.content_widget)

    def _on_toggled(self, checked):
        self.content_widget.setVisible(checked)
        self.toggled.emit(checked)


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


class DependencyWarningDialog(QDialog):
    def __init__(self, missing_dependencies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setModal(True)
        self.setFixedWidth(460)

        self.setStyleSheet("""
            QDialog {
                background-color: #171B22;
            }
            QLabel {
                color: #E8EAF0;
            }
            QFrame#dialogPanel {
                border: 1px solid #2B313B;
                border-radius: 16px;
                background-color: #171B22;
            }
            QPushButton#dialogPrimaryButton {
                background-color: #1F64FF;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                padding: 8px 18px;
                min-height: 38px;
                max-height: 38px;
            }
            QLineEdit#commandPreview {
                border: 1px solid #2B313B;
                border-radius: 10px;
                padding: 8px 12px;
                background-color: #141821;
                color: #F3F5F8;
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                min-height: 24px;
            }
        """)

        missing_text = ", ".join(missing_dependencies)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(14)

        title_label = QLabel("ffmpeg / ffprobe is required")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F3F5F8;")

        summary_label = QLabel(
            f"MediaSeg could not find: {missing_text}."
        )
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("font-size: 13px; color: #F3F5F8;")

        body_label = QLabel(
            "This app uses the system ffmpeg toolchain for media conversion, duration checks, and splitting. "
            "Install ffmpeg first, then restart MediaSeg."
        )
        body_label.setWordWrap(True)
        body_label.setStyleSheet("font-size: 13px; color: #A6B0BF; line-height: 1.4;")

        command_label = QLabel("Install on macOS with Homebrew")
        command_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #F3F5F8;")

        command_preview = QLineEdit("brew install ffmpeg")
        command_preview.setObjectName("commandPreview")
        command_preview.setReadOnly(True)

        button_row = QHBoxLayout()
        button_row.addStretch()

        close_button = QPushButton("Close")
        close_button.setObjectName("dialogPrimaryButton")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_row.addWidget(close_button)

        panel_layout.addWidget(title_label)
        panel_layout.addWidget(summary_label)
        panel_layout.addWidget(body_label)
        panel_layout.addSpacing(4)
        panel_layout.addWidget(command_label)
        panel_layout.addWidget(command_preview)
        panel_layout.addSpacing(8)
        panel_layout.addLayout(button_row)

        root_layout.addWidget(panel)

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        parent_center = parent.frameGeometry().center()
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        self.move(dialog_rect.topLeft())


class InfoDialog(QDialog):
    def __init__(self, window_title, headline, sections, parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setModal(True)
        self.setFixedWidth(560)

        self.setStyleSheet("""
            QDialog {
                background-color: #171B22;
            }
            QLabel {
                color: #E8EAF0;
            }
            QLabel[role="linkBody"] {
                color: #A6B0BF;
            }
            QFrame#dialogPanel {
                border: 1px solid #2B313B;
                border-radius: 16px;
                background-color: #171B22;
            }
            QPushButton#dialogPrimaryButton {
                background-color: #1F64FF;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                padding: 8px 18px;
                min-height: 38px;
                max-height: 38px;
            }
            QLineEdit#commandPreview {
                border: 1px solid #2B313B;
                border-radius: 10px;
                padding: 8px 12px;
                background-color: #141821;
                color: #F3F5F8;
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                min-height: 24px;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        title_label = QLabel(headline)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F3F5F8;")
        title_label.setWordWrap(True)
        panel_layout.addWidget(title_label)

        for section in sections:
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(4)

            section_title = QLabel(section["title"])
            section_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #F3F5F8;")
            section_layout.addWidget(section_title)

            body_label = QLabel(section["body"])
            body_label.setWordWrap(True)
            body_label.setOpenExternalLinks(True)
            body_label.setTextFormat(Qt.RichText)
            body_label.setStyleSheet("font-size: 13px; color: #A6B0BF; line-height: 1.4;")
            section_layout.addWidget(body_label)

            command = section.get("command")
            if command:
                command_preview = QLineEdit(command)
                command_preview.setObjectName("commandPreview")
                command_preview.setReadOnly(True)
                section_layout.addWidget(command_preview)

            panel_layout.addLayout(section_layout)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_button = QPushButton("Close")
        close_button.setObjectName("dialogPrimaryButton")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_row.addWidget(close_button)
        panel_layout.addSpacing(16)
        panel_layout.addLayout(button_row)

        root_layout.addWidget(panel)

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        parent_center = parent.frameGeometry().center()
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        self.move(dialog_rect.topLeft())

class ProcessingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#ProcessingOverlay {
                background-color: rgba(10, 12, 16, 150);
            }
        """)
        self.setObjectName("ProcessingOverlay")

        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(23, 27, 34, 240);
                border: 1px solid #2B313B;
                border-radius: 16px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(28, 24, 28, 24)
        container_layout.setSpacing(12)
        container_layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setPixmap(make_svg_icon("loader-circle.svg", color="#F3F5F8", size=28).pixmap(28, 28))

        self.title_label = QLabel("Processing...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #F3F5F8; font-size: 16px; font-weight: bold;")

        self.subtitle_label = QLabel("Please wait while MediaSeg works.")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #A6B0BF; font-size: 12px;")

        container_layout.addWidget(self.icon_label)
        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.subtitle_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(container, alignment=Qt.AlignCenter)

    def set_message(self, title, subtitle=None):
        self.title_label.setText(title)
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)

class DurationWorker(QThread):
    duration_signal = Signal(str, float)
    error_signal = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            from mediaseg_core import get_duration
            duration = get_duration(Path(self.file_path))
            self.duration_signal.emit(self.file_path, duration)
        except Exception:
            self.error_signal.emit(self.file_path)

class Worker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, input_file, max_size_mb, output_dir=None):
        super().__init__()
        self.input_file = input_file
        self.max_size_mb = max_size_mb
        self.output_dir = output_dir

    def run(self):
        try:
            from mediaseg_core import split_media

            input_file_path = Path(self.input_file).resolve()

            outdir_path = split_media(
                input_file=str(input_file_path),
                max_size_mb=self.max_size_mb,
                logger=self.log_signal.emit,
                output_dir=self.output_dir
            )
            self.finished_signal.emit(str(outdir_path))
        except Exception as e:
            self.error_signal.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediaSeg")
        self.setWindowIcon(make_svg_icon("scissors.svg"))
        
        # Enforce minimum size: height is 760, width allows 600 as requested
        self.setMinimumSize(600, 760)
        self.resize(1000, 920)
        self.worker = None
        self.duration_worker = None
        self.current_duration_file_path = None
        self.last_output_dir = None
        self.custom_output_dir = None
        self.current_file_size_bytes = 0
        self.processing_active = False
        self.start_cooldown_active = False
        self.start_button_state = "idle"
        self.start_button_texts = {
            "idle": "\u00A0\u00A0Start Splitting",
            "preparing": "\u00A0\u00A0Preparing...",
            "converting": "\u00A0\u00A0Converting...",
            "splitting": "\u00A0\u00A0Splitting...",
            "cleaning": "\u00A0\u00A0Cleaning...",
            "completed": "\u00A0\u00A0Completed",
            "error": "\u00A0\u00A0Error",
        }
        self.start_button_icon_paths = {
            "idle": "scissors.svg",
            "preparing": "loader-circle.svg",
            "converting": "loader-circle.svg",
            "splitting": "loader-circle.svg",
            "cleaning": "loader-circle.svg",
            "completed": "circle-check-big.svg",
            "error": "circle-alert.svg",
        }

        self.rotation_timer = QTimer(self)
        self.rotation_timer.setInterval(50)  # ~20 FPS for smooth rotation
        self.rotation_timer.timeout.connect(self.update_rotation)
        self.start_cooldown_timer = QTimer(self)
        self.start_cooldown_timer.setSingleShot(True)
        self.start_cooldown_timer.timeout.connect(self.on_start_cooldown_timeout)
        self.rotation_frame_index = 0
        self.loader_icon_cache = []
        self.loader_icon_cache_path = None
        self.log_section = None
        self.start_cooldown_deadline = 0.0
        self.missing_dependencies = []
        self._last_logged_missing_dependencies = None
        self.dependency_warning_shown = False

        self.setup_styles()
        self.init_ui()
        QTimer.singleShot(0, self.check_runtime_dependencies_on_startup)

    def create_help_menu(self):
        help_menu = self.menuBar().addMenu("Help")

        how_to_use_action = QAction("How to Use", self)
        how_to_use_action.setMenuRole(QAction.MenuRole.NoRole)
        how_to_use_action.triggered.connect(self.show_how_to_use_dialog)
        help_menu.addAction(how_to_use_action)

        setup_action = QAction("Setup ffmpeg", self)
        setup_action.setMenuRole(QAction.MenuRole.NoRole)
        setup_action.triggered.connect(self.show_setup_help_dialog)
        help_menu.addAction(setup_action)

        common_issues_action = QAction("Common Issues", self)
        common_issues_action.setMenuRole(QAction.MenuRole.NoRole)
        common_issues_action.triggered.connect(self.show_common_issues_dialog)
        help_menu.addAction(common_issues_action)

        third_party_action = QAction("Third-Party Licenses", self)
        third_party_action.setMenuRole(QAction.MenuRole.NoRole)
        third_party_action.triggered.connect(self.show_third_party_licenses_dialog)
        help_menu.addAction(third_party_action)

        about_action = QAction("About MediaSeg", self)
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.lock_height_to_content)

    def setup_styles(self):
        self.setStyleSheet("""
            QWidget {
                color: #E8EAF0;
            }
            QMainWindow {
                background-color: #121417;
            }
            QLabel {
                color: #E8EAF0;
            }
            QLineEdit {
                border: 1px solid #2B313B;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #171B22;
                font-size: 13px;
                color: #E8EAF0;
                min-height: 40px;
                max-height: 40px;
            }
            QLineEdit:focus {
                border: 1px solid #5B8CFF;
            }
            QLineEdit#sizeEdit {
                border: 1px solid #2B313B;
                border-radius: 8px;
                padding: 6px 10px;
                background-color: #171B22;
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
                min-height: 40px;
                max-height: 40px;
            }
            QLineEdit#sizeEdit:focus {
                border: 1px solid #5B8CFF;
            }
            QSlider:horizontal {
                padding-left: 10px;
                padding-right: 10px;
                min-height: 24px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #2B313B;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #F5F7FA;
                border: 1px solid #67718A;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8CFF;
                border-radius: 2px;
            }
            QPlainTextEdit {
                border: 1px solid #2B313B;
                border-radius: 12px;
                background-color: #141821;
                color: #D7DCE6;
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                font-size: 11px;
                padding: 8px;
                min-height: 80px;
                max-height: 140px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px 14px;
                min-height: 40px;
                max-height: 40px;
            }
            QPushButton#browseFileButton {
                background-color: #232833;
                color: #E8EAF0;
                min-width: 110px;
                max-width: 110px;
                padding: 10px 16px;
            }
            QPushButton#browseFileButton:disabled {
                background-color: #1B202A;
                color: #6E7686;
            }
            QPushButton#tertiaryButton {
                background-color: #232833;
                color: #E8EAF0;
                min-width: 110px;
                max-width: 110px;
                padding: 10px 16px;
            }
            QPushButton#tertiaryButton:disabled {
                background-color: #1B202A;
                color: #6E7686;
            }
            QPushButton#tertiaryButtonReset {
                background-color: #2B1F22;
                border: 1px solid #FF9A9A;
                color: #FF9A9A;
                min-width: 110px;
                max-width: 110px;
                font-weight: normal;
            }
            QPushButton#tertiaryButtonReset:hover {
                border: 1px solid #FFB0B0;
                background-color: #342125;
            }
            QPushButton#tertiaryButtonReset:disabled {
                background-color: #1B202A;
                border: 1px solid #8A4D4D;
                color: #8A4D4D;
            }
            QPushButton#startButton {
                background-color: #1F64FF;
                color: #FFFFFF;
                font-size: 15px;
                padding: 10px 16px;
            }
            QPushButton#startButton:disabled {
                background-color: #24407F;
                color: #B9C9EE;
            }
            QPushButton#openFolderButton {
                background-color: #18263A;
                color: #8FB3FF;
                font-size: 14px;
                padding: 10px 16px;
            }
            QPushButton#openFolderButton:disabled {
                background-color: #1B202A;
                color: #6E7686;
            }
            QPushButton#helpLinkButton {
                background-color: transparent;
                color: #8FB3FF;
                font-size: 12px;
                font-weight: 600;
                padding: 2px 6px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton#helpLinkButton:disabled {
                color: #53627B;
            }
        """)

    def _start_button_icon_path(self, state):
        icon_name = self.start_button_icon_paths.get(state, self.start_button_icon_paths["idle"])
        return get_asset_icon_path(icon_name)

    def detect_missing_dependencies(self):
        from mediaseg_core import find_executable

        missing = []
        if not find_executable("ffmpeg"):
            missing.append("ffmpeg")
        if not find_executable("ffprobe"):
            missing.append("ffprobe")
        return missing

    def dependency_help_text(self, missing_dependencies):
        tools = ", ".join(missing_dependencies)
        return (
            f"Missing runtime dependency: {tools}.\n\n"
            "Release builds include bundled ffmpeg and ffprobe.\n"
            "If you are running MediaSeg from source, install ffmpeg first, then restart the app.\n\n"
            "Example for source runs on macOS with Homebrew:\n"
            "brew install ffmpeg"
        )

    def append_info(self, message):
        self.log_area.appendPlainText(message)
        self.log_area.ensureCursorVisible()

    def append_warning(self, message):
        self.append_info(f"Warning: {message}")

    def append_error(self, message):
        self.append_info(f"Error: {message}")

    def append_success(self, message):
        self.append_info(f"Success: {message}")

    def show_dependency_warning_dialog(self):
        if not self.missing_dependencies:
            return

        dialog = DependencyWarningDialog(self.missing_dependencies, self)
        dialog.exec()

    def show_about_dialog(self):
        public_version = get_public_version()
        build_version = get_build_version()
        sections = [
            {
                "title": "Version (Build)",
                "body": f'{public_version} <span style="color:#7E8CA4;">({build_version})</span>',
            },
            {
                "title": "Overview",
                "body": "MediaSeg is a local macOS utility for splitting large media files into smaller upload-friendly chunks.",
            },
            {
                "title": "Supported Formats",
                "body": "Current primary support is MP4 and WEBM. WEBM files are converted before splitting.",
            },
            {
                "title": "Runtime Requirement",
                "body": "Release builds bundle FFmpeg and FFprobe. Source runs use local ffmpeg and ffprobe. Bundled FFmpeg is distributed under the LGPL v2.1.",
            },
            {
                "title": "FFmpeg Source",
                "body": "Matching FFmpeg source and build-configuration files are distributed alongside MediaSeg release artifacts.",
            },
            {
                "title": "Developer",
                "body": f'<a href="{EXAEDGE_ABOUT_URL}" style="color:#8FB3FF; text-decoration:none;">ExaEdge</a> - Delivering practical AI solutions for businesses and digital creators.',
            },
        ]
        InfoDialog("About MediaSeg", "About MediaSeg", sections, self).exec()

    def show_how_to_use_dialog(self):
        sections = [
            {
                "title": "1. Select a video file",
                "body": "Drag and drop an MP4 or WEBM file, or click Browse to choose a file manually.",
            },
            {
                "title": "2. Choose target chunk size",
                "body": "Use the default 200 MB target or enter any value between 10 MB and 400 MB.",
            },
            {
                "title": "3. Start splitting",
                "body": "Click Start Splitting. MediaSeg creates a timestamped output folder and saves chunked files there.",
            },
            {
                "title": "WEBM note",
                "body": "WEBM files are converted to MP4 before splitting, so that workflow may take longer than MP4 input.",
            },
        ]
        InfoDialog("How to Use", "How to Use MediaSeg", sections, self).exec()

    def show_setup_help_dialog(self):
        sections = [
            {
                "title": "What is ffmpeg?",
                "body": "ffmpeg is an external video-processing tool. MediaSeg uses it to read, convert, and split media files.",
            },
            {
                "title": "Release builds",
                "body": "MediaSeg release builds bundle ffmpeg and ffprobe. If those tools are missing in a release build, the app bundle is incomplete or damaged.",
            },
            {
                "title": "Source runs with Homebrew",
                "body": "If you are running MediaSeg from source, install ffmpeg with Homebrew.",
                "command": "brew install ffmpeg",
            },
            {
                "title": "If Homebrew is not installed",
                "body": "Install Homebrew first, then run the ffmpeg command above. After installation, restart MediaSeg.",
            },
            {
                "title": "How to verify installation",
                "body": "Open Terminal and check whether ffmpeg and ffprobe are available for source runs.",
                "command": "which ffmpeg && which ffprobe",
            },
        ]
        InfoDialog("Setup ffmpeg", "Setup ffmpeg for MediaSeg", sections, self).exec()

    def show_common_issues_dialog(self):
        sections = [
            {
                "title": "If Start Splitting is disabled",
                "body": "MediaSeg may not be able to find bundled or local ffmpeg / ffprobe. In a release build, rebuild or re-copy the app bundle. In a source run, open Setup ffmpeg from the Help menu and complete the installation steps.",
            },
            {
                "title": "If WEBM processing takes a long time",
                "body": "WEBM files are converted to MP4 before splitting. Large recordings may take several minutes before chunking begins.",
            },
            {
                "title": "If output folder cannot be opened",
                "body": "Run at least one successful split first, or verify that the previously generated output folder still exists.",
            },
        ]
        InfoDialog("Common Issues", "Common Issues", sections, self).exec()

    def show_third_party_licenses_dialog(self):
        license_path = get_bundle_path("THIRD_PARTY_LICENSES.md")
        try:
            license_text = license_path.read_text(encoding="utf-8")
        except OSError:
            license_text = "Third-party license information is not available in this build."

        dialog = QDialog(self)
        dialog.setWindowTitle("Third-Party Licenses")
        dialog.setModal(True)
        dialog.setMinimumSize(720, 640)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #171B22;
            }
            QLabel {
                color: #E8EAF0;
            }
            QFrame#dialogPanel {
                border: 1px solid #2B313B;
                border-radius: 16px;
                background-color: #171B22;
            }
            QPushButton#dialogPrimaryButton {
                background-color: #1F64FF;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                padding: 8px 18px;
                min-height: 38px;
                max-height: 38px;
            }
            QPlainTextEdit#licenseText {
                border: 1px solid #2B313B;
                border-radius: 10px;
                background-color: #141821;
                color: #D7DCE6;
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        title_label = QLabel("Third-Party Licenses")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F3F5F8;")

        body_label = QLabel("Bundled third-party license and attribution notes for this release.")
        body_label.setWordWrap(True)
        body_label.setStyleSheet("font-size: 13px; color: #A6B0BF; line-height: 1.4;")

        license_view = QPlainTextEdit()
        license_view.setObjectName("licenseText")
        license_view.setReadOnly(True)
        license_view.setPlainText(license_text)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_button = QPushButton("Close")
        close_button.setObjectName("dialogPrimaryButton")
        close_button.clicked.connect(dialog.accept)
        close_button.setDefault(True)
        button_row.addWidget(close_button)

        panel_layout.addWidget(title_label)
        panel_layout.addWidget(body_label)
        panel_layout.addWidget(license_view, 1)
        panel_layout.addSpacing(8)
        panel_layout.addLayout(button_row)

        root_layout.addWidget(panel)
        dialog.exec()

    def check_runtime_dependencies(self, show_dialog=False):
        self.missing_dependencies = self.detect_missing_dependencies()
        self.refresh_control_states()

        if self.missing_dependencies:
            current_missing = tuple(self.missing_dependencies)
            if self.log_area is not None and current_missing != self._last_logged_missing_dependencies:
                self.append_warning(
                    f"Missing dependency: {', '.join(self.missing_dependencies)} not available. "
                    "For source runs, install ffmpeg and restart MediaSeg."
                )
                self.append_info("")
                self._last_logged_missing_dependencies = current_missing
            if show_dialog:
                self.show_dependency_warning_dialog()
            return False

        self._last_logged_missing_dependencies = None
        return True

    @Slot()
    def check_runtime_dependencies_on_startup(self):
        if self.check_runtime_dependencies(show_dialog=not self.dependency_warning_shown):
            return
        self.dependency_warning_shown = True

    def build_loader_icon_cache(self, icon_path):
        if self.loader_icon_cache_path == str(icon_path) and self.loader_icon_cache:
            return

        self.loader_icon_cache = []
        self.loader_icon_cache_path = str(icon_path)

        svg_data = recolor_svg_bytes(icon_path.read_bytes(), "#F3F5F8")
        renderer = QSvgRenderer(QByteArray(svg_data))
        if not renderer.isValid():
            return

        icon_size = self.start_button.iconSize().width()
        center = icon_size / 2
        for angle in range(0, 360, 30):
            pixmap = QPixmap(icon_size, icon_size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.translate(center, center)
            painter.rotate(angle)
            painter.translate(-center, -center)
            renderer.render(painter, QRectF(0, 0, icon_size, icon_size))
            painter.end()
            self.loader_icon_cache.append(QIcon(pixmap))

    def update_rotation(self):
        if not self.loader_icon_cache:
            return
        self.rotation_frame_index = (self.rotation_frame_index + 1) % len(self.loader_icon_cache)
        self.start_button.setIcon(self.loader_icon_cache[self.rotation_frame_index])

    def set_start_button_state(self, state):
        self.start_button_state = state
        self.start_button.setText(self.start_button_texts.get(state, self.start_button_texts["idle"]))

        icon_path = self._start_button_icon_path(state)

        rotating_states = ["preparing", "converting", "splitting", "cleaning"]
        if state in rotating_states:
            if icon_path.exists():
                self.build_loader_icon_cache(icon_path)
                self.rotation_frame_index = 0
                if self.loader_icon_cache:
                    self.start_button.setIcon(self.loader_icon_cache[self.rotation_frame_index])
                if not self.rotation_timer.isActive():
                    self.rotation_timer.start()
            else:
                self.rotation_timer.stop()
                self.start_button.setIcon(QIcon())
        else:
            self.rotation_timer.stop()
            self.rotation_frame_index = 0
            if icon_path.exists():
                self.start_button.setIcon(make_svg_icon(icon_name=icon_path.name, color="#F3F5F8", size=18))
            else:
                self.start_button.setIcon(QIcon())

    def init_ui(self):
        content_widget = QWidget()
        self.setCentralWidget(content_widget)
        self.create_help_menu()

        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignTop)

        # 1. Drop Area
        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.on_file_selected)
        main_layout.addWidget(self.drop_area)

        # 2. File Selection path / Browse
        file_selection_widget = QWidget()
        file_selection_layout = QHBoxLayout(file_selection_widget)
        file_selection_layout.setContentsMargins(0, 0, 0, 0)
        file_selection_layout.setSpacing(8)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Or select path manually...")
        self.file_path_edit.editingFinished.connect(self.on_file_path_edited)
        
        self.browse_button = QPushButton("\u00A0\u00A0Browse")
        self.browse_button.setObjectName("browseFileButton")
        self.browse_button.clicked.connect(self.browse_file)
        self.browse_button.setIcon(make_svg_icon("folder-input.svg"))
        self.browse_button.setIconSize(QSize(18, 18))
        
        file_selection_layout.addWidget(self.file_path_edit)
        file_selection_layout.addWidget(self.browse_button)
        main_layout.addWidget(file_selection_widget)

        # 3. File Info Card
        self.file_info_card = FileInfoCard()
        main_layout.addWidget(self.file_info_card)

        # 4. Configuration Panel
        config_title = QLabel("CONFIGURATION")
        config_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F5F8; letter-spacing: 0.4px;")
        main_layout.addWidget(config_title)

        config_panel = QFrame()
        config_panel.setMinimumHeight(340)
        config_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        config_panel.setStyleSheet("""
            QFrame {
                border: 1px solid #2B313B;
                border-radius: 16px;
                background-color: #171B22;
            }
            QLabel {
                border: none;
            }
        """)
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(14)

        # A. Target Chunk Size Line
        target_size_header = QHBoxLayout()
        target_size_lbl = QLabel("Target Chunk Size")
        target_size_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #F3F5F8;")
        
        self.size_edit = QLineEdit()
        self.size_edit.setObjectName("sizeEdit")
        self.size_edit.setValidator(QIntValidator(10, 400, self))
        self.size_edit.setText("200")
        self.size_edit.setAlignment(Qt.AlignCenter)
        self.size_edit.setFixedWidth(80)
        self.size_edit.textChanged.connect(self.on_lineedit_changed)
        
        mb_label = QLabel("MB")
        mb_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #A6B0BF;")
        
        target_size_header.addWidget(target_size_lbl)
        target_size_header.addStretch()
        target_size_header.addWidget(self.size_edit)
        target_size_header.addWidget(mb_label)
        config_layout.addLayout(target_size_header)

        # B. Chunk Size Slider (Range: 10 - 400)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(10, 400)
        self.size_slider.setValue(200)
        self.size_slider.setSingleStep(10)
        self.size_slider.setPageStep(50)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self.on_slider_value_changed)
        self.size_slider.sliderReleased.connect(self.on_slider_released)
        config_layout.addWidget(self.size_slider)

        # C. Slider Labels positioned to roughly follow the actual value spacing.
        ticks_layout = QHBoxLayout()
        ticks_layout.setContentsMargins(10, 0, 10, 0)
        ticks_layout.setSpacing(0)
        lbl1 = QLabel("10MB")
        lbl2 = QLabel("100MB")
        lbl3 = QLabel("200MB")
        lbl4 = QLabel("300MB")
        lbl5 = QLabel("400MB")
        for lbl in [lbl1, lbl2, lbl3, lbl4, lbl5]:
            lbl.setStyleSheet("color: #A6B0BF; font-size: 10px; font-weight: 500;")
            lbl.setAlignment(Qt.AlignCenter)

        ticks_layout.addWidget(lbl1)
        ticks_layout.addStretch(90)
        ticks_layout.addWidget(lbl2)
        ticks_layout.addStretch(100)
        ticks_layout.addWidget(lbl3)
        ticks_layout.addStretch(100)
        ticks_layout.addWidget(lbl4)
        ticks_layout.addStretch(100)
        ticks_layout.addWidget(lbl5)
        config_layout.addLayout(ticks_layout)

        divider_config = QFrame()
        divider_config.setFrameShape(QFrame.HLine)
        divider_config.setStyleSheet("color: #2B313B; background-color: #2B313B; max-height: 1px; border: none;")
        config_layout.addWidget(divider_config)

        # E. Output Folder layout (New 2-row structure)
        config_layout.addSpacing(10)
        out_folder_lbl = QLabel("Output Folder")
        out_folder_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #F3F5F8;")
        config_layout.addWidget(out_folder_lbl)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("Same folder as source (Default)")
        config_layout.addWidget(self.output_path_edit)

        out_buttons_layout = QHBoxLayout()
        out_buttons_layout.setContentsMargins(0, 4, 0, 4)
        out_buttons_layout.setSpacing(8)
        self.out_browse_button = QPushButton("\u00A0\u00A0Browse")
        self.out_browse_button.setObjectName("tertiaryButton")
        self.out_browse_button.clicked.connect(self.browse_output_folder)
        self.out_browse_button.setIcon(make_svg_icon("folder-output.svg"))
        self.out_browse_button.setIconSize(QSize(18, 18))

        self.out_reset_button = QPushButton("Reset")
        self.out_reset_button.setObjectName("tertiaryButtonReset")
        self.out_reset_button.clicked.connect(self.reset_output_folder)
        self.out_reset_button.setEnabled(False)
        self.out_reset_button.setStyleSheet("color: #FF9A9A;")
        
        out_buttons_layout.addWidget(self.out_browse_button)
        out_buttons_layout.addWidget(self.out_reset_button)
        out_buttons_layout.addStretch()
        config_layout.addLayout(out_buttons_layout)

        main_layout.addWidget(config_panel)
        config_panel.adjustSize()
        config_panel.setFixedHeight(config_panel.sizeHint().height())

        # 5. Session Log Area
        self.log_section = AccordionSection("SESSION LOG", expanded=False)
        self.log_section.toggled.connect(lambda _: QTimer.singleShot(0, self.lock_height_to_content))
        main_layout.addWidget(self.log_section)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Activity logs will display here...")
        self.log_area.setFixedHeight(140)
        self.log_section.content_layout.addWidget(self.log_area)

        # 6. Action Buttons Bottom Layout
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)
        
        self.start_button = QPushButton("Start Splitting")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_splitting)
        self.start_button.setIconSize(QSize(18, 18))
        self.set_start_button_state("idle")
        
        self.open_folder_button = QPushButton("\u00A0\u00A0Open Output Folder")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.open_folder_button.setIcon(make_svg_icon("folder.svg", color="#F3F5F8", size=18))
        self.open_folder_button.setIconSize(QSize(18, 18))

        footer_links_layout = QHBoxLayout()
        footer_links_layout.setContentsMargins(0, 2, 0, 0)
        footer_links_layout.setSpacing(4)

        self.brand_logo_widget = ClickableSvgWidget(EXAEDGE_FOOTER_URL)
        brand_logo_path = get_asset_path("brand", "exaedge_logo_white.svg")
        if brand_logo_path.exists():
            logo_width, logo_height = get_svg_scaled_size(brand_logo_path, 112, 22)
            self.brand_logo_widget.setFixedSize(logo_width, logo_height)
            self.brand_logo_widget.load(str(brand_logo_path))
        else:
            self.brand_logo_widget.setFixedSize(112, 22)
        footer_links_layout.addWidget(self.brand_logo_widget, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        footer_links_layout.addStretch()

        self.how_to_use_link = QPushButton("How to Use")
        self.how_to_use_link.setObjectName("helpLinkButton")
        self.how_to_use_link.clicked.connect(self.show_how_to_use_dialog)

        self.setup_ffmpeg_link = QPushButton("Setup ffmpeg")
        self.setup_ffmpeg_link.setObjectName("helpLinkButton")
        self.setup_ffmpeg_link.clicked.connect(self.show_setup_help_dialog)

        self.common_issues_link = QPushButton("Common Issues")
        self.common_issues_link.setObjectName("helpLinkButton")
        self.common_issues_link.clicked.connect(self.show_common_issues_dialog)

        self.about_link = QPushButton("About MediaSeg")
        self.about_link.setObjectName("helpLinkButton")
        self.about_link.clicked.connect(self.show_about_dialog)

        footer_links_layout.addWidget(self.how_to_use_link)
        footer_links_layout.addWidget(self.setup_ffmpeg_link)
        footer_links_layout.addWidget(self.common_issues_link)
        footer_links_layout.addWidget(self.about_link)
        
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.open_folder_button)
        action_layout.addLayout(footer_links_layout)
        main_layout.addLayout(action_layout)
        content_widget.adjustSize()
        self.adjustSize()

        target_size = self.sizeHint()
        self.resize(target_size)
        self.setMinimumSize(max(600, target_size.width()), target_size.height())

    def lock_height_to_content(self):
        content_widget = self.centralWidget()
        if not content_widget:
            return

        content_widget.adjustSize()
        self.adjustSize()

        target_height = self.sizeHint().height()
        current_width = self.width()
        self.setMinimumHeight(target_height)
        self.setMaximumHeight(target_height)
        self.resize(current_width, target_height)

    @Slot()
    def browse_file(self):
        default_dir = os.path.expanduser("~/Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            default_dir,
            "Video Files (*.mp4 *.webm);;All Files (*)"
        )
        if file_path:
            self.on_file_selected(file_path)

    @Slot()
    def browse_output_folder(self):
        default_dir = os.path.expanduser("~/Downloads")
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            default_dir
        )
        if dir_path:
            self.custom_output_dir = dir_path
            self.output_path_edit.setText(dir_path)
            self.out_reset_button.setEnabled(True)

    @Slot()
    def reset_output_folder(self):
        self.custom_output_dir = None
        self.output_path_edit.clear()
        self.out_reset_button.setEnabled(False)

    def on_file_selected(self, file_path):
        self.file_path_edit.setText(file_path)
        self.update_file_info(file_path)

    def on_file_path_edited(self):
        path = self.file_path_edit.text().strip()
        self.update_file_info(path)

    def update_file_info(self, file_path):
        if not file_path or not os.path.exists(file_path):
            self.current_duration_file_path = None
            self.current_file_size_bytes = 0
            self.file_info_card.reset_card()
            return

        if not self.processing_active:
            self.set_start_button_state("idle")

        file_path_obj = Path(file_path)
        file_name = file_path_obj.name
        file_size = file_path_obj.stat().st_size
        self.current_file_size_bytes = file_size

        self.file_info_card.set_file_name(file_name)
        self.file_info_card.format_val.setText(file_path_obj.suffix[1:].upper() if file_path_obj.suffix else "UNKNOWN")
        self.file_info_card.size_val.setText(format_size(file_size))
        self.file_info_card.dur_val.setText("Loading...")
        
        self.update_estimated_chunks()
        self.file_info_card.show()
        self.start_duration_loading(str(file_path_obj))

    def start_duration_loading(self, file_path):
        self.current_duration_file_path = file_path

        if self.duration_worker and self.duration_worker.isRunning():
            self.duration_worker.requestInterruption()

        self.duration_worker = DurationWorker(file_path)
        self.duration_worker.duration_signal.connect(self.on_duration_loaded)
        self.duration_worker.error_signal.connect(self.on_duration_error)
        self.duration_worker.finished.connect(self.cleanup_duration_worker)
        self.duration_worker.start()

    @Slot(str, float)
    def on_duration_loaded(self, file_path, duration):
        if file_path != self.current_duration_file_path:
            return
        self.file_info_card.dur_val.setText(format_duration(duration))

    @Slot(str)
    def on_duration_error(self, file_path):
        if file_path != self.current_duration_file_path:
            return
        self.file_info_card.dur_val.setText("--:--:--")

    @Slot()
    def cleanup_duration_worker(self):
        if self.duration_worker:
            self.duration_worker.deleteLater()
            self.duration_worker = None

    def update_estimated_chunks(self):
        if not self.current_file_size_bytes:
            self.file_info_card.chunks_val.setText("--")
            return
        
        try:
            target_mb = int(self.size_edit.text())
        except ValueError:
            target_mb = 200
            
        if target_mb <= 0:
            target_mb = 1
            
        MB_BASE = 1000 * 1000  # constant from core
        size_mb = self.current_file_size_bytes / MB_BASE
        
        chunks = int(math.ceil(size_mb / target_mb))
        if chunks <= 0:
            chunks = 1
        self.file_info_card.chunks_val.setText(f"~{chunks} Parts")

    @Slot(int)
    def on_slider_value_changed(self, value):
        snapped = (value // 10) * 10
        if snapped < 10:
            snapped = 10
        
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(snapped)
        self.size_slider.blockSignals(False)
        
        self.size_edit.blockSignals(True)
        self.size_edit.setText(str(snapped))
        self.size_edit.blockSignals(False)

        # Refresh immediately so wheel changes and drag changes stay in sync.
        self.update_estimated_chunks()

    @Slot()
    def on_slider_released(self):
        self.update_estimated_chunks()

    @Slot(str)
    def on_lineedit_changed(self, text):
        if not text:
            return
        try:
            value = int(text)
            if 10 <= value <= 400:
                slider_val = min(value, 400)
                self.size_slider.blockSignals(True)
                self.size_slider.setValue(slider_val)
                self.size_slider.blockSignals(False)
                
                self.update_estimated_chunks()
        except ValueError:
            pass

    @Slot()
    def start_splitting(self):
        if not self.check_runtime_dependencies(show_dialog=True):
            return

        input_file = self.file_path_edit.text().strip()
        if not input_file:
            self.append_error("No input file selected. Choose a video file and try again.")
            return

        try:
            max_size_mb = int(self.size_edit.text())
        except ValueError:
            max_size_mb = 200

        if max_size_mb <= 0:
            self.append_error("Invalid chunk size. Enter a value between 10 MB and 400 MB.")
            return

        self.processing_active = True
        self.start_cooldown_active = True
        self.start_cooldown_deadline = time.monotonic() + 3.0
        self.start_cooldown_timer.start(3000)
        self.refresh_control_states()
        self.set_start_button_state("preparing")
        self.log_area.clear()
        self.append_info(f"Starting process for file: {input_file}")

        self.worker = Worker(input_file, max_size_mb, self.custom_output_dir)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def refresh_control_states(self):
        enabled = not self.processing_active
        cooldown_active = self.start_cooldown_active and time.monotonic() < self.start_cooldown_deadline
        dependencies_ready = not self.missing_dependencies
        self.start_button.setEnabled(enabled and not cooldown_active and dependencies_ready)
        self.browse_button.setEnabled(enabled)
        self.file_path_edit.setEnabled(enabled)
        self.size_edit.setEnabled(enabled)
        self.size_slider.setEnabled(enabled)
        self.out_browse_button.setEnabled(enabled)
        self.out_reset_button.setEnabled(enabled and self.custom_output_dir is not None)
        self.open_folder_button.setEnabled(enabled and bool(self.last_output_dir and os.path.exists(self.last_output_dir)))

    @Slot()
    def on_start_cooldown_timeout(self):
        self.start_cooldown_active = False
        if not self.processing_active and self.start_button_state == "completed":
            self.set_start_button_state("idle")
        self.refresh_control_states()

    @Slot()
    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            subprocess.run(["open", self.last_output_dir])
        else:
            self.append_error("Output folder is not available. Run a split first or choose a valid folder.")

    @Slot(str)
    def append_log(self, message):
        self.append_info(message)

        if "Output folder created:" in message:
            self.set_start_button_state("preparing")
        elif "Converting..." in message:
            self.set_start_button_state("converting")
        elif "Splitting..." in message or "Input Size" in message:
            self.set_start_button_state("splitting")
        elif "Cleaning temporary files..." in message:
            self.set_start_button_state("cleaning")
        elif "Done." in message:
            self.set_start_button_state("completed")

    @Slot(str)
    def on_success(self, output_dir):
        self.append_info("")
        self.append_success("Media splitting completed successfully.")
        self.last_output_dir = output_dir
        self.processing_active = False
        self.refresh_control_states()
        self.set_start_button_state("completed")
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    @Slot(str)
    def on_error(self, error_message):
        self.append_info("")
        self.append_error(error_message)
        self.processing_active = False
        self.refresh_control_states()
        self.set_start_button_state("error")
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    ext = os.path.splitext(local_path)[1].lower()
                    if ext in [".mp4", ".webm"]:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    ext = os.path.splitext(local_path)[1].lower()
                    if ext in [".mp4", ".webm"]:
                        self.on_file_selected(local_path)
                        event.acceptProposedAction()
                        return
        event.ignore()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MediaSeg")
    app.setApplicationDisplayName("MediaSeg")
    app.setOrganizationName("ExaEdge")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
