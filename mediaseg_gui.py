import sys
import os
import subprocess
import math
import time
from pathlib import Path
from mediaseg_version import get_public_version, get_build_version
from PySide6.QtCore import QEvent, QThread, Signal, Slot, Qt, QSize, QTimer, QRectF, QByteArray, QUrl, QSettings, QLocale
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIntValidator, QFontMetrics, QIcon, QPainter, QPixmap, QPalette
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
    QStyle,
    QStyleOptionSlider,
    QToolButton,
    QDialog,
    QMenu,
    QProxyStyle,
)

class InstantSubmenuStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_Menu_SubMenuPopupDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)


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


MIN_CHUNK_SIZE_MB = 10
MIN_RELIABLE_CHUNK_SIZE_MB = 30
MAX_SLIDER_CHUNK_SIZE_MB = 400
MAX_MANUAL_CHUNK_SIZE_MB = 999
SLIDER_TICK_LABEL_X_OFFSET = -6
OFFICIALLY_SUPPORTED_EXTENSIONS = (".mp4", ".webm", ".mov")
EXPERIMENTAL_SUPPORTED_EXTENSIONS = (".m4a", ".mp3", ".wav")
GUI_ACCEPTED_EXTENSIONS = OFFICIALLY_SUPPORTED_EXTENSIONS + EXPERIMENTAL_SUPPORTED_EXTENSIONS
SUPPORT_FEEDBACK_URL = "https://github.com/exaedge/MediaSeg/issues"
THEME_SYSTEM = "system"
THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_NEON = "neon_tokyo"
LANG_SYSTEM = "system"
LANG_EN = "en"
LANG_JA = "ja"
LANG_VI = "vi"

THEMES = {
    THEME_DARK: {
        "window_bg": "#131313",
        "text": "#E5E2E1",
        "muted_text": "#C2C6D8",
        "subtle_text": "#8C90A1",
        "surface": "#171B22",
        "surface_alt": "#141821",
        "surface_soft": "#232833",
        "surface_modal": "#201F1F",
        "surface_hover": "#2A2A2A",
        "border": "#2B313B",
        "border_soft": "#424656",
        "primary": "#0066FF",
        "primary_hover": "#2A7BFF",
        "primary_disabled": "#24407F",
        "primary_disabled_text": "#B9C9EE",
        "link": "#8FB3FF",
        "success": "#34D399",
        "warning": "#FF9A9A",
        "warning_bg": "#2B1F22",
        "warning_bg_hover": "#342125",
        "warning_border_disabled": "#8A4D4D",
        "warning_text_disabled": "#8A4D4D",
        "button_secondary_bg": "#232833",
        "button_secondary_disabled": "#1B202A",
        "button_secondary_text": "#E8EAF0",
        "button_secondary_text_disabled": "#6E7686",
        "open_button_bg": "#18263A",
        "open_button_text": "#8FB3FF",
        "open_button_disabled_bg": "#202734",
        "open_button_disabled_border": "#36465E",
        "open_button_disabled_text": "#91A5C6",
        "drop_bg": "#171B22",
        "drop_hover": "#16233A",
        "drop_border": "#5B8CFF",
        "drop_border_hover": "#7DA2FF",
        "overlay_backdrop": "rgba(10, 12, 16, 150)",
        "overlay_card": "rgba(23, 27, 34, 240)",
        "menu_trigger_fg": "#E8EAF0",
        "menu_trigger_hover_bg": "rgba(232, 234, 240, 0.10)",
        "menu_trigger_pressed_bg": "rgba(232, 234, 240, 0.16)",
        "menu_trigger_disabled_fg": "#6E7686",
        "footer_text": "#8C90A1",
        "footer_logo_fg": "#F4F6FF",
    },
    THEME_LIGHT: {
        "window_bg": "#F4F7FB",
        "text": "#1B2430",
        "muted_text": "#4F637A",
        "subtle_text": "#66778E",
        "surface": "#FFFFFF",
        "surface_alt": "#F7F9FC",
        "surface_soft": "#E9EEF6",
        "surface_modal": "#FFFFFF",
        "surface_hover": "#EDF3FF",
        "border": "#CFD8E6",
        "border_soft": "#DDE5F0",
        "primary": "#005EEB",
        "primary_hover": "#1F6DFF",
        "primary_disabled": "#9EB8E8",
        "primary_disabled_text": "#EFF5FF",
        "link": "#005EEB",
        "success": "#0B8F60",
        "warning": "#D9485F",
        "warning_bg": "#FFF1F3",
        "warning_bg_hover": "#FFE6EA",
        "warning_border_disabled": "#E7B4BE",
        "warning_text_disabled": "#C68C97",
        "button_secondary_bg": "#E9EEF6",
        "button_secondary_disabled": "#F0F3F8",
        "button_secondary_text": "#1B2430",
        "button_secondary_text_disabled": "#98A4B7",
        "open_button_bg": "#EAF2FF",
        "open_button_text": "#005EEB",
        "open_button_disabled_bg": "#E3EAF5",
        "open_button_disabled_border": "#C8D5E8",
        "open_button_disabled_text": "#6F83A3",
        "drop_bg": "#FFFFFF",
        "drop_hover": "#EFF5FF",
        "drop_border": "#4C7EFF",
        "drop_border_hover": "#2F63F7",
        "overlay_backdrop": "rgba(241, 245, 251, 185)",
        "overlay_card": "rgba(255, 255, 255, 245)",
        "menu_trigger_fg": "#42536A",
        "menu_trigger_hover_bg": "rgba(27, 36, 48, 0.08)",
        "menu_trigger_pressed_bg": "rgba(27, 36, 48, 0.14)",
        "menu_trigger_disabled_fg": "#A8B3C4",
        "footer_text": "#66778E",
        "footer_logo_fg": "#1B2430",
    },
    THEME_NEON: {
        "window_bg": "#0A0A12",
        "text": "#F4F6FF",
        "muted_text": "#B6BDD6",
        "subtle_text": "#8891AF",
        "surface": "#111320",
        "surface_alt": "#0E1020",
        "surface_soft": "#171B2A",
        "surface_modal": "#131725",
        "surface_hover": "#161C30",
        "border": "#4E3156",
        "border_soft": "#263349",
        "primary": "#FF2D78",
        "primary_hover": "#FF4D8E",
        "primary_disabled": "#73415B",
        "primary_disabled_text": "#F8D2E0",
        "link": "#00FFCC",
        "success": "#00FFCC",
        "warning": "#FFE04A",
        "warning_bg": "#2E2430",
        "warning_bg_hover": "#3B2B3A",
        "warning_border_disabled": "#8D7D42",
        "warning_text_disabled": "#B8AA72",
        "button_secondary_bg": "#151826",
        "button_secondary_disabled": "#12141F",
        "button_secondary_text": "#F4F6FF",
        "button_secondary_text_disabled": "#77819D",
        "open_button_bg": "#131C27",
        "open_button_text": "#00FFCC",
        "open_button_disabled_bg": "#161A24",
        "open_button_disabled_border": "#273141",
        "open_button_disabled_text": "#7B95B1",
        "drop_bg": "#111320",
        "drop_hover": "#13192A",
        "drop_border": "#FF2D78",
        "drop_border_hover": "#00FFCC",
        "overlay_backdrop": "rgba(10, 10, 18, 175)",
        "overlay_card": "rgba(17, 19, 32, 245)",
        "menu_trigger_fg": "#F4F6FF",
        "menu_trigger_hover_bg": "rgba(255, 45, 120, 0.12)",
        "menu_trigger_pressed_bg": "rgba(255, 45, 120, 0.20)",
        "menu_trigger_disabled_fg": "#77819D",
        "footer_text": "#8891AF",
        "footer_logo_fg": "#F4F6FF",
    },
}

STRINGS = {
    LANG_EN: {
        "menu_button": "Options",
        "menu_theme": "Theme",
        "menu_language": "Language",
        "menu_support_feedback": "Support & Feedback",
        "menu_how_to_use": "How to Use",
        "menu_setup_ffmpeg": "Setup ffmpeg",
        "menu_common_issues": "Common Issues",
        "menu_licenses": "Third-Party Licenses",
        "menu_about": "About MediaSeg",
        "theme_system": "System",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_neon": "Neon Tokyo",
        "lang_system": "System",
        "lang_english": "English",
        "lang_japanese": "Japanese",
        "lang_vietnamese": "Vietnamese",
        "drop_title": "Drop file to segment",
        "drop_subtitle": "Official: MP4, WEBM, MOV | Experimental: M4A, MP3, WAV",
        "path_placeholder": "Or select path manually...",
        "browse": "Browse",
        "config_title": "CONFIGURATION",
        "chunk_size": "Target Chunk Size",
        "output_folder": "Output Folder",
        "output_folder_help": "Use Browse to choose a custom output folder.",
        "output_folder_placeholder": "Same folder as source (Default). Use Browse to change.",
        "reset": "Reset",
        "session_log": "SESSION LOG",
        "start_idle": "\u00A0\u00A0Start Splitting",
        "start_preparing": "\u00A0\u00A0Preparing...",
        "start_converting": "\u00A0\u00A0Converting...",
        "start_splitting": "\u00A0\u00A0Splitting...",
        "start_cleaning": "\u00A0\u00A0Cleaning...",
        "start_completed": "\u00A0\u00A0Completed",
        "start_error": "\u00A0\u00A0Error",
        "open_output": "\u00A0\u00A0Open Output Folder",
        "fileinfo_empty": "No file selected",
        "fileinfo_format": "Format",
        "fileinfo_size": "Original Size",
        "fileinfo_duration": "Duration",
        "fileinfo_chunks": "Estimated Chunks",
        "size_warning_below_reliable": f"Below {MIN_RELIABLE_CHUNK_SIZE_MB} MB, some media files may fail.",
        "overlay_preparing_title": "Preparing",
        "overlay_preparing_body": "MediaSeg is preparing the current file. Controls are temporarily locked.",
        "overlay_converting_title": "Converting",
        "overlay_converting_body": "MediaSeg is converting this file before splitting. Controls are temporarily locked.",
        "overlay_splitting_title": "Splitting",
        "overlay_splitting_body": "MediaSeg is splitting the current file. Controls are temporarily locked.",
        "overlay_cleaning_title": "Cleaning",
        "overlay_cleaning_body": "MediaSeg is cleaning temporary files. Controls are temporarily locked.",
    },
    LANG_JA: {
        "menu_button": "オプション",
        "menu_theme": "テーマ",
        "menu_language": "言語",
        "menu_support_feedback": "サポートとフィードバック",
        "menu_how_to_use": "使い方",
        "menu_setup_ffmpeg": "ffmpeg設定",
        "menu_common_issues": "よくある問題",
        "menu_licenses": "サードパーティライセンス",
        "menu_about": "MediaSegについて",
        "theme_system": "システム",
        "theme_dark": "ダーク",
        "theme_light": "ライト",
        "theme_neon": "Neon Tokyo",
        "lang_system": "システム",
        "lang_english": "英語",
        "lang_japanese": "日本語",
        "lang_vietnamese": "ベトナム語",
        "drop_title": "ファイルをドロップして分割",
        "drop_subtitle": "正式: MP4, WEBM, MOV | 試験対応: M4A, MP3, WAV",
        "path_placeholder": "またはパスを手入力...",
        "browse": "参照",
        "config_title": "設定",
        "chunk_size": "目標チャンクサイズ",
        "output_folder": "出力フォルダ",
        "output_folder_help": "カスタム出力先は参照から選択してください。",
        "output_folder_placeholder": "既定ではソースと同じ場所に出力します。変更は参照から行います。",
        "reset": "リセット",
        "session_log": "セッションログ",
        "start_idle": "\u00A0\u00A0分割開始",
        "start_preparing": "\u00A0\u00A0準備中...",
        "start_converting": "\u00A0\u00A0変換中...",
        "start_splitting": "\u00A0\u00A0分割中...",
        "start_cleaning": "\u00A0\u00A0整理中...",
        "start_completed": "\u00A0\u00A0完了",
        "start_error": "\u00A0\u00A0エラー",
        "open_output": "\u00A0\u00A0出力フォルダを開く",
        "fileinfo_empty": "ファイル未選択",
        "fileinfo_format": "形式",
        "fileinfo_size": "元サイズ",
        "fileinfo_duration": "長さ",
        "fileinfo_chunks": "想定チャンク数",
        "size_warning_below_reliable": f"{MIN_RELIABLE_CHUNK_SIZE_MB} MB未満では、一部メディアで失敗する場合があります。",
        "overlay_preparing_title": "準備中",
        "overlay_preparing_body": "MediaSeg が現在のファイルを準備中です。操作は一時的にロックされています。",
        "overlay_converting_title": "変換中",
        "overlay_converting_body": "MediaSeg が分割前の変換を実行しています。操作は一時的にロックされています。",
        "overlay_splitting_title": "分割中",
        "overlay_splitting_body": "MediaSeg が現在のファイルを分割中です。操作は一時的にロックされています。",
        "overlay_cleaning_title": "整理中",
        "overlay_cleaning_body": "MediaSeg が一時ファイルを整理中です。操作は一時的にロックされています。",
    },
    LANG_VI: {
        "menu_button": "Tùy chọn",
        "menu_theme": "Giao diện",
        "menu_language": "Ngôn ngữ",
        "menu_support_feedback": "Hỗ trợ & Phản hồi",
        "menu_how_to_use": "Hướng dẫn sử dụng",
        "menu_setup_ffmpeg": "Thiết lập ffmpeg",
        "menu_common_issues": "Sự cố thường gặp",
        "menu_licenses": "Giấy phép bên thứ ba",
        "menu_about": "Giới thiệu MediaSeg",
        "theme_system": "Hệ thống",
        "theme_dark": "Tối",
        "theme_light": "Sáng",
        "theme_neon": "Neon Tokyo",
        "lang_system": "Hệ thống",
        "lang_english": "Tiếng Anh",
        "lang_japanese": "Tiếng Nhật",
        "lang_vietnamese": "Tiếng Việt",
        "drop_title": "Thả tệp vào đây để chia nhỏ",
        "drop_subtitle": "Chính thức: MP4, WEBM, MOV | Thử nghiệm: M4A, MP3, WAV",
        "path_placeholder": "Hoặc chọn đường dẫn...",
        "browse": "Duyệt...",
        "config_title": "CẤU HÌNH",
        "chunk_size": "Kích thước mỗi phần",
        "output_folder": "Thư mục đầu ra",
        "output_folder_help": "Nhấn \"Duyệt...\" để chọn thư mục đầu ra.",
        "output_folder_placeholder": "Mặc định sẽ lưu cùng thư mục với tệp gốc. Nhấn \"Duyệt...\" để thay đổi.",
        "reset": "Đặt lại",
        "session_log": "NHẬT KÝ PHIÊN",
        "start_idle": "\u00A0\u00A0Bắt đầu chia tệp",
        "start_preparing": "\u00A0\u00A0Đang chuẩn bị...",
        "start_converting": "\u00A0\u00A0Đang chuyển đổi...",
        "start_splitting": "\u00A0\u00A0Đang chia...",
        "start_cleaning": "\u00A0\u00A0Đang dọn...",
        "start_completed": "\u00A0\u00A0Hoàn tất",
        "start_error": "\u00A0\u00A0Lỗi",
        "open_output": "\u00A0\u00A0Mở thư mục đầu ra",
        "fileinfo_empty": "Chưa chọn tệp",
        "fileinfo_format": "Định dạng",
        "fileinfo_size": "Kích thước gốc",
        "fileinfo_duration": "Thời lượng",
        "fileinfo_chunks": "Số phần dự kiến",
        "size_warning_below_reliable": f"Dưới {MIN_RELIABLE_CHUNK_SIZE_MB} MB, một số tệp có thể thất bại.",
        "overlay_preparing_title": "Đang chuẩn bị",
        "overlay_preparing_body": "MediaSeg đang chuẩn bị tệp hiện tại. Các điều khiển tạm thời bị khóa.",
        "overlay_converting_title": "Đang chuyển đổi",
        "overlay_converting_body": "MediaSeg đang chuyển đổi tệp trước khi chia. Các điều khiển tạm thời bị khóa.",
        "overlay_splitting_title": "Đang chia",
        "overlay_splitting_body": "MediaSeg đang chia tệp hiện tại. Các điều khiển tạm thời bị khóa.",
        "overlay_cleaning_title": "Đang dọn",
        "overlay_cleaning_body": "MediaSeg đang dọn các tệp tạm. Các điều khiển tạm thời bị khóa.",
    },
}


def system_language_code():
    locale_name = QLocale.system().name().lower()
    if locale_name.startswith("ja"):
        return LANG_JA
    if locale_name.startswith("vi"):
        return LANG_VI
    return LANG_EN


def theme_display_tokens(theme_key):
    return THEMES[THEME_NEON if theme_key == THEME_NEON else theme_key]


def dialog_stylesheet(theme):
    return f"""
        QDialog {{
            background-color: {theme['surface']};
        }}
        QLabel {{
            color: {theme['text']};
        }}
        QFrame#dialogPanel {{
            border: 1px solid {theme['border']};
            border-radius: 16px;
            background-color: {theme['surface']};
        }}
        QPushButton#dialogPrimaryButton {{
            background-color: {theme['primary']};
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            font-weight: normal;
            padding: 8px 18px;
            min-height: 38px;
            max-height: 38px;
        }}
        QLineEdit#commandPreview {{
            border: 1px solid {theme['border']};
            border-radius: 10px;
            padding: 8px 12px;
            background-color: {theme['surface_alt']};
            color: {theme['text']};
            font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
            min-height: 24px;
        }}
        QPlainTextEdit#licenseText {{
            border: 1px solid {theme['border']};
            border-radius: 10px;
            background-color: {theme['surface_alt']};
            color: {theme['text']};
            font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
            font-size: 11px;
            padding: 10px;
        }}
        QPlainTextEdit#logText {{
            border: 1px solid {theme['border']};
            border-radius: 10px;
            background-color: {theme['surface_alt']};
            color: {theme['text']};
            font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
            font-size: 11px;
            padding: 10px;
        }}
    """


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
        self.setStyleSheet(f"""
            #DropArea {{
                border: 2px dashed {border};
                border-radius: 16px;
                background-color: {background};
            }}
        """)
        if hasattr(self, "icon_widget"):
            load_svg_widget(self.icon_widget, "file-video-camera.svg", theme["text"])
            self.text_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme['text']};")
            self.subtext_label.setStyleSheet(f"font-size: 11px; color: {theme['muted_text']};")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    if is_gui_supported_extension(local_path):
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
                if os.path.isfile(local_path):
                    if is_gui_supported_extension(local_path):
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
        self.setStyleSheet(f"""
            #FileInfoCard {{
                border: 1px solid {theme['border']};
                border-radius: 16px;
                background-color: {theme['surface']};
            }}
        """)
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
        self._theme = THEMES[THEME_DARK]
        self.title_label.setStyleSheet(f"color: {self._theme['text']}; font-size: 15px; font-weight: bold; letter-spacing: 0.4px;")

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
        load_svg_widget(self.arrow_widget, icon_name, self._theme["text"])

    def setTitle(self, title):
        self._title = title
        self.title_label.setText(title)

    def apply_theme(self, theme):
        self._theme = theme
        self.title_label.setStyleSheet(f"color: {theme['text']}; font-size: 15px; font-weight: bold; letter-spacing: 0.4px;")
        self.setExpanded(self._expanded)


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

    def set_title(self, title):
        self.header.setTitle(title)

    def apply_theme(self, theme):
        self.header.apply_theme(theme)


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
        groove_rect = self.slider.style().subControlRect(
            QStyle.CC_Slider,
            option,
            QStyle.SC_SliderGroove,
            self.slider,
        )
        handle_rect = self.slider.style().subControlRect(
            QStyle.CC_Slider,
            option,
            QStyle.SC_SliderHandle,
            self.slider,
        )

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


class DependencyWarningDialog(QDialog):
    def __init__(self, missing_dependencies, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setModal(True)
        self.setFixedWidth(460)

        self.setStyleSheet(dialog_stylesheet(theme))

        missing_text = ", ".join(missing_dependencies)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(14)

        title_label = QLabel("ffmpeg / ffprobe is required")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme['text']};")

        summary_label = QLabel(
            f"MediaSeg could not find: {missing_text}."
        )
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(f"font-size: 13px; color: {theme['text']};")

        body_label = QLabel(
            "This app uses the system ffmpeg toolchain for media conversion, duration checks, and splitting. "
            "Install ffmpeg first, then restart MediaSeg."
        )
        body_label.setWordWrap(True)
        body_label.setStyleSheet(f"font-size: 13px; color: {theme['muted_text']}; line-height: 1.4;")

        command_label = QLabel("Install on macOS with Homebrew")
        command_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme['text']};")

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
    def __init__(self, window_title, headline, sections, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setModal(True)
        self.setFixedWidth(560)

        self.setStyleSheet(dialog_stylesheet(theme))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        title_label = QLabel(headline)
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme['text']};")
        title_label.setWordWrap(True)
        panel_layout.addWidget(title_label)

        for section in sections:
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(4)

            section_title = QLabel(section["title"])
            section_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme['text']};")
            section_layout.addWidget(section_title)

            body_label = QLabel(section["body"])
            body_label.setWordWrap(True)
            body_label.setOpenExternalLinks(True)
            body_label.setTextFormat(Qt.RichText)
            body_label.setStyleSheet(f"font-size: 13px; color: {theme['muted_text']}; line-height: 1.4;")
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


class SessionLogDialog(QDialog):
    def __init__(self, title, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle(title)
        self.setModal(False)
        self.setFixedSize(560, 760)
        self.setStyleSheet(dialog_stylesheet(theme))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setAlignment(Qt.AlignTop)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme['text']};")

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logText")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Activity logs will display here...")
        self.log_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.log_view.setStyleSheet(f"""
            QPlainTextEdit {{
                border: 1px solid {theme['border']};
                border-radius: 10px;
                background-color: {theme['surface_alt']};
                color: {theme['text']};
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                font-size: 11px;
                padding: 10px;
                min-height: 0px;
                max-height: 16777215px;
            }}
        """)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_button = QPushButton("Close")
        close_button.setObjectName("dialogPrimaryButton")
        close_button.clicked.connect(self.close)
        button_row.addWidget(close_button)

        panel_layout.addWidget(self.title_label)
        panel_layout.addSpacing(16)
        panel_layout.addWidget(self.log_view)
        panel_layout.addSpacing(12)
        panel_layout.addLayout(button_row)
        root_layout.addWidget(panel, 1)
        self._root_layout = root_layout
        self._panel_layout = panel_layout
        self._close_button = close_button
        self.recalculate_log_view_height()

    def set_theme(self, theme):
        self._theme = theme
        self.setStyleSheet(dialog_stylesheet(theme))
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme['text']};")
        self.recalculate_log_view_height()

    def set_title(self, title):
        self.setWindowTitle(title)
        self.title_label.setText(title)

    def set_log_text(self, text):
        self.log_view.setPlainText(text)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def append_log_line(self, message):
        self.log_view.appendPlainText(message)
        self.log_view.ensureCursorVisible()

    def showEvent(self, event):
        super().showEvent(event)
        self.recalculate_log_view_height()
        parent = self.parentWidget()
        if parent is None:
            return
        parent_center = parent.frameGeometry().center()
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        self.move(dialog_rect.topLeft())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recalculate_log_view_height()

    def recalculate_log_view_height(self):
        if not hasattr(self, "_root_layout"):
            return
        self.layout().activate()
        self._panel_layout.activate()
        root_margins = self._root_layout.contentsMargins()
        panel_margins = self._panel_layout.contentsMargins()
        title_height = self.title_label.sizeHint().height()
        button_height = self._close_button.sizeHint().height()
        explicit_spacing_height = 16 + 12
        non_log_height = (
            root_margins.top()
            + root_margins.bottom()
            + panel_margins.top()
            + panel_margins.bottom()
            + title_height
            + button_height
            + explicit_spacing_height
        )
        log_height = max(520, self.height() - non_log_height)
        self.log_view.setFixedHeight(log_height)

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
        self.setStyleSheet(f"""
            QWidget#ProcessingOverlay {{
                background-color: {theme['overlay_backdrop']};
            }}
        """)
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['overlay_card']};
                border: 1px solid {theme['border']};
                border-radius: 16px;
            }}
        """)
        self.icon_label.setPixmap(make_svg_icon("loader-circle.svg", color=theme["text"], size=28).pixmap(28, 28))
        self.title_label.setStyleSheet(f"color: {theme['text']}; font-size: 16px; font-weight: bold;")
        self.subtitle_label.setStyleSheet(f"color: {theme['muted_text']}; font-size: 12px;")

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
        self.settings = QSettings("ExaEdge", "MediaSeg")
        self.selected_theme = self.settings.value("ui/theme", THEME_SYSTEM, type=str)
        self.selected_language = self.settings.value("ui/language", LANG_SYSTEM, type=str)
        self.current_theme_key = self.resolve_theme_key(self.selected_theme)
        self.current_language_key = self.resolve_language_key(self.selected_language)
        self.theme = THEMES[self.current_theme_key]

        self.setWindowTitle("MediaSeg")
        self.setWindowIcon(make_svg_icon("scissors.svg"))
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
        self.start_button_texts = {}
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
        self.log_area = None
        self.session_log_button = None
        self.session_log_dialog = None
        self.log_messages = []
        self.start_cooldown_deadline = 0.0
        self.missing_dependencies = []
        self._last_logged_missing_dependencies = None
        self.dependency_warning_shown = False
        self.main_layout = None
        self.utility_button = None
        self.utility_menu = None
        self.help_menu = None
        self.theme_menu = None
        self.language_menu = None
        self.footer_logo_widget = None
        self.footer_logo_container = None
        self.footer_version_label = None
        self.theme_actions = {}
        self.language_actions = {}
        self.utility_actions = {}

        self.build_start_button_texts()
        self.create_actions()
        self.setup_styles()
        self.init_ui()
        self.apply_language()
        self.apply_theme()
        QTimer.singleShot(0, self.check_runtime_dependencies_on_startup)

    def resolve_theme_key(self, selected_theme):
        if selected_theme != THEME_SYSTEM:
            return selected_theme if selected_theme in THEMES else THEME_DARK
        window_color = QApplication.palette().color(QPalette.Window)
        return THEME_DARK if window_color.lightness() < 128 else THEME_LIGHT

    def resolve_language_key(self, selected_language):
        if selected_language == LANG_SYSTEM:
            return system_language_code()
        return selected_language if selected_language in STRINGS else LANG_EN

    def t(self, key):
        return STRINGS[self.current_language_key].get(key, STRINGS[LANG_EN].get(key, key))

    def footer_logo_path(self):
        logo_name = "exaedge_logo_black.svg" if self.current_theme_key == THEME_LIGHT else "exaedge_logo_white.svg"
        return get_asset_path("brand", logo_name)

    def refresh_footer_logo(self):
        if not hasattr(self, "footer_logo_widget") or self.footer_logo_widget is None:
            return
        logo_path = self.footer_logo_path()
        if not logo_path.exists():
            return
        logo_width, logo_height = get_svg_scaled_size(logo_path, 112, 20)
        self.footer_logo_widget.setFixedSize(logo_width, logo_height)
        self.footer_logo_widget.load(str(logo_path))

    def build_start_button_texts(self):
        self.start_button_texts = {
            "idle": self.t("start_idle"),
            "preparing": self.t("start_preparing"),
            "converting": self.t("start_converting"),
            "splitting": self.t("start_splitting"),
            "cleaning": self.t("start_cleaning"),
            "completed": self.t("start_completed"),
            "error": self.t("start_error"),
        }

    def create_actions(self):
        self.utility_actions["how_to_use"] = QAction(self)
        self.utility_actions["how_to_use"].triggered.connect(self.show_how_to_use_dialog)
        self.utility_actions["setup_ffmpeg"] = QAction(self)
        self.utility_actions["setup_ffmpeg"].triggered.connect(self.show_setup_help_dialog)
        self.utility_actions["common_issues"] = QAction(self)
        self.utility_actions["common_issues"].triggered.connect(self.show_common_issues_dialog)
        self.utility_actions["licenses"] = QAction(self)
        self.utility_actions["licenses"].triggered.connect(self.show_third_party_licenses_dialog)
        self.utility_actions["about"] = QAction(self)
        self.utility_actions["about"].setMenuRole(QAction.MenuRole.AboutRole)
        self.utility_actions["about"].triggered.connect(self.show_about_dialog)
        self.utility_actions["support_feedback"] = QAction(self)
        self.utility_actions["support_feedback"].triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(SUPPORT_FEEDBACK_URL))
        )

        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        for theme_key in (THEME_SYSTEM, THEME_DARK, THEME_LIGHT, THEME_NEON):
            action = QAction(self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, key=theme_key: self.set_theme_preference(key))
            self.theme_action_group.addAction(action)
            self.theme_actions[theme_key] = action

        self.language_action_group = QActionGroup(self)
        self.language_action_group.setExclusive(True)
        for language_key in (LANG_SYSTEM, LANG_EN, LANG_JA, LANG_VI):
            action = QAction(self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, key=language_key: self.set_language_preference(key))
            self.language_action_group.addAction(action)
            self.language_actions[language_key] = action

        self.create_help_menu()
        self.update_action_texts()

    def create_help_menu(self):
        self.help_menu = self.menuBar().addMenu("Help")
        self.help_menu.clear()
        for key in ("how_to_use", "setup_ffmpeg", "common_issues", "licenses", "support_feedback", "about"):
            self.help_menu.addAction(self.utility_actions[key])

    def build_utility_menu(self):
        self.utility_menu = QMenu(self)
        self.utility_menu.setStyle(InstantSubmenuStyle(self.utility_menu.style()))
        self.utility_menu.setMinimumWidth(250)
        self.theme_menu = QMenu(self.utility_menu)
        self.theme_menu.setStyle(InstantSubmenuStyle(self.theme_menu.style()))
        self.theme_menu.setMinimumWidth(180)
        for theme_key in (THEME_SYSTEM, THEME_DARK, THEME_LIGHT, THEME_NEON):
            self.theme_menu.addAction(self.theme_actions[theme_key])
        self.utility_menu.addMenu(self.theme_menu)

        self.language_menu = QMenu(self.utility_menu)
        self.language_menu.setStyle(InstantSubmenuStyle(self.language_menu.style()))
        self.language_menu.setMinimumWidth(180)
        for language_key in (LANG_SYSTEM, LANG_EN, LANG_JA, LANG_VI):
            self.language_menu.addAction(self.language_actions[language_key])
        self.utility_menu.addMenu(self.language_menu)
        self.utility_menu.addSeparator()
        for key in ("support_feedback", "how_to_use", "setup_ffmpeg", "common_issues", "licenses", "about"):
            self.utility_menu.addAction(self.utility_actions[key])

        self.utility_button.setMenu(self.utility_menu)
        self.update_action_texts()

    def showEvent(self, event):
        super().showEvent(event)
        self.current_theme_key = self.resolve_theme_key(self.selected_theme)
        self.current_language_key = self.resolve_language_key(self.selected_language)
        self.apply_theme()
        self.apply_language()
        QTimer.singleShot(0, self.lock_height_to_content)

    def setup_styles(self):
        theme = self.theme
        self.setStyleSheet(f"""
            QWidget {{
                color: {theme['text']};
            }}
            QMainWindow {{
                background-color: {theme['window_bg']};
            }}
            QLabel {{
                color: {theme['text']};
            }}
            QLineEdit {{
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 8px 12px;
                background-color: {theme['surface']};
                font-size: 13px;
                color: {theme['text']};
                min-height: 40px;
                max-height: 40px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme['primary']};
            }}
            QLineEdit#sizeEdit {{
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 6px 10px;
                background-color: {theme['surface']};
                font-size: 14px;
                font-weight: normal;
                color: {theme['text']};
                min-height: 40px;
                max-height: 40px;
            }}
            QLineEdit#sizeEdit:focus {{
                border: 1px solid {theme['primary']};
            }}
            QSlider:horizontal {{
                padding-left: 10px;
                padding-right: 10px;
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {theme['border']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['text']};
                border: 1px solid {theme['subtle_text']};
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: {theme['primary']};
                border-radius: 2px;
            }}
            QPlainTextEdit {{
                border: 1px solid {theme['border']};
                border-radius: 12px;
                background-color: {theme['surface_alt']};
                color: {theme['text']};
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
                font-size: 11px;
                padding: 8px;
                min-height: 80px;
                max-height: 140px;
            }}
            QPushButton {{
                border: none;
                border-radius: 8px;
                font-weight: normal;
                padding: 10px 14px;
                min-height: 40px;
                max-height: 40px;
            }}
            QPushButton#browseFileButton {{
                background-color: {theme['button_secondary_bg']};
                color: {theme['button_secondary_text']};
                min-width: 110px;
                max-width: 110px;
                padding: 10px 16px;
            }}
            QPushButton#browseFileButton:disabled {{
                background-color: {theme['button_secondary_disabled']};
                color: {theme['button_secondary_text_disabled']};
            }}
            QPushButton#tertiaryButton {{
                background-color: {theme['button_secondary_bg']};
                color: {theme['button_secondary_text']};
                min-width: 110px;
                max-width: 110px;
                padding: 10px 16px;
            }}
            QPushButton#tertiaryButton:disabled {{
                background-color: {theme['button_secondary_disabled']};
                color: {theme['button_secondary_text_disabled']};
            }}
            QPushButton#tertiaryButtonReset {{
                background-color: {theme['warning_bg']};
                border: 1px solid {theme['warning']};
                color: {theme['warning']};
                min-width: 110px;
                max-width: 110px;
                font-weight: normal;
            }}
            QPushButton#tertiaryButtonReset:hover {{
                border: 1px solid {theme['warning']};
                background-color: {theme['warning_bg_hover']};
            }}
            QPushButton#tertiaryButtonReset:disabled {{
                background-color: {theme['button_secondary_disabled']};
                border: 1px solid {theme['warning_border_disabled']};
                color: {theme['warning_text_disabled']};
            }}
            QPushButton#startButton {{
                background-color: {theme['primary']};
                color: #FFFFFF;
                font-size: 15px;
                padding: 10px 16px;
            }}
            QPushButton#startButton:disabled {{
                background-color: {theme['primary_disabled']};
                color: {theme['primary_disabled_text']};
            }}
            QPushButton#openFolderButton {{
                background-color: {theme['open_button_bg']};
                color: {theme['open_button_text']};
                border: 1px solid transparent;
                font-size: 14px;
                padding: 10px 16px;
            }}
            QPushButton#sessionLogButton {{
                background-color: {theme['button_secondary_bg']};
                color: {theme['button_secondary_text']};
                border: 1px solid transparent;
                font-size: 13px;
                font-weight: normal;
                padding: 10px 16px;
            }}
            QPushButton#openFolderButton:disabled {{
                background-color: {theme['open_button_disabled_bg']};
                border: 1px solid {theme['open_button_disabled_border']};
                color: {theme['open_button_disabled_text']};
            }}
            QToolButton#utilityMenuButton {{
                background-color: transparent;
                color: {theme['menu_trigger_fg']};
                border: none;
                border-radius: 18px;
                padding: 0px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }}
            QToolButton#utilityMenuButton:hover,
            QToolButton#utilityMenuButton:focus {{
                background-color: {theme['menu_trigger_hover_bg']};
            }}
            QToolButton#utilityMenuButton:pressed {{
                background-color: {theme['menu_trigger_pressed_bg']};
            }}
            QToolButton#utilityMenuButton::menu-indicator {{
                image: none;
                width: 0px;
            }}
            QToolButton#utilityMenuButton:disabled {{
                background-color: transparent;
                color: {theme['menu_trigger_disabled_fg']};
            }}
            QMenu {{
                background-color: {theme['surface']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {theme['surface_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {theme['border']};
                margin: 4px 8px;
            }}
        """)

    def update_action_texts(self):
        if self.help_menu is not None:
            self.help_menu.setTitle("Help")
        if self.theme_menu is not None:
            self.theme_menu.setTitle(self.t("menu_theme"))
        if self.language_menu is not None:
            self.language_menu.setTitle(self.t("menu_language"))

        self.utility_actions["support_feedback"].setText(self.t("menu_support_feedback"))
        self.utility_actions["how_to_use"].setText(self.t("menu_how_to_use"))
        self.utility_actions["setup_ffmpeg"].setText(self.t("menu_setup_ffmpeg"))
        self.utility_actions["common_issues"].setText(self.t("menu_common_issues"))
        self.utility_actions["licenses"].setText(self.t("menu_licenses"))
        self.utility_actions["about"].setText(self.t("menu_about"))

        theme_labels = {
            THEME_SYSTEM: self.t("theme_system"),
            THEME_DARK: self.t("theme_dark"),
            THEME_LIGHT: self.t("theme_light"),
            THEME_NEON: self.t("theme_neon"),
        }
        for key, action in self.theme_actions.items():
            action.setText(theme_labels[key])
            action.setChecked(self.selected_theme == key)

        language_labels = {
            LANG_SYSTEM: self.t("lang_system"),
            LANG_EN: self.t("lang_english"),
            LANG_JA: self.t("lang_japanese"),
            LANG_VI: self.t("lang_vietnamese"),
        }
        for key, action in self.language_actions.items():
            action.setText(language_labels[key])
            action.setChecked(self.selected_language == key)

    def apply_theme(self):
        self.current_theme_key = self.resolve_theme_key(self.selected_theme)
        self.theme = THEMES[self.current_theme_key]
        self.setup_styles()
        for themed_widget in (
            getattr(self, "drop_area", None),
            getattr(self, "file_info_card", None),
            getattr(self, "size_slider_ticks", None),
            getattr(self, "log_section", None),
            getattr(self, "processing_overlay", None),
        ):
            if themed_widget is not None and hasattr(themed_widget, "apply_theme"):
                themed_widget.apply_theme(self.theme)

        if hasattr(self, "config_title"):
            self.config_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.theme['text']}; letter-spacing: 0.4px;")
        if hasattr(self, "config_panel"):
            self.config_panel.setStyleSheet(f"""
                QFrame {{
                    border: 1px solid {self.theme['border']};
                    border-radius: 16px;
                    background-color: {self.theme['surface']};
                }}
                QLabel {{
                    border: none;
                }}
            """)
        if hasattr(self, "target_size_lbl"):
            self.target_size_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self.theme['text']};")
        if hasattr(self, "mb_label"):
            self.mb_label.setStyleSheet(f"font-weight: normal; font-size: 14px; color: {self.theme['muted_text']};")
        if hasattr(self, "size_warning_icon"):
            self.size_warning_icon.setPixmap(make_svg_icon("circle-alert.svg", color=self.theme["warning"], size=14).pixmap(14, 14))
        if hasattr(self, "size_warning_text"):
            self.size_warning_text.setStyleSheet(f"font-size: 10px; color: {self.theme['warning']};")
        if hasattr(self, "out_folder_lbl"):
            self.out_folder_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self.theme['text']};")
        if hasattr(self, "out_folder_help"):
            self.out_folder_help.setStyleSheet(f"font-size: 11px; color: {self.theme['muted_text']};")
        if hasattr(self, "utility_button"):
            utility_icon_color = self.theme["menu_trigger_fg"] if self.utility_button.isEnabled() else self.theme["menu_trigger_disabled_fg"]
            self.utility_button.setIcon(make_svg_icon("settings.svg", color=utility_icon_color, size=18))
        if hasattr(self, "browse_button"):
            self.browse_button.setIcon(make_svg_icon("folder-input.svg", color=self.theme["button_secondary_text"], size=18))
        if hasattr(self, "out_browse_button"):
            self.out_browse_button.setIcon(make_svg_icon("folder-output.svg", color=self.theme["button_secondary_text"], size=18))
        if hasattr(self, "open_folder_button"):
            open_folder_icon_color = self.theme["open_button_text"] if self.open_folder_button.isEnabled() else self.theme["open_button_disabled_text"]
            self.open_folder_button.setIcon(make_svg_icon("folder.svg", color=open_folder_icon_color, size=18))
        if hasattr(self, "session_log_button") and self.session_log_button is not None:
            self.session_log_button.setIcon(make_svg_icon("file-text.svg", color=self.theme["button_secondary_text"], size=18))
        if hasattr(self, "footer_version_label") and self.footer_version_label is not None:
            self.footer_version_label.setStyleSheet(f"font-size: 12px; font-weight: normal; color: {self.theme['footer_text']};")
        if hasattr(self, "footer_logo_widget") and self.footer_logo_widget is not None:
            self.refresh_footer_logo()
        if self.session_log_dialog is not None:
            self.session_log_dialog.set_theme(self.theme)
        self.set_start_button_state(self.start_button_state)
        self.update_action_texts()

    def apply_language(self):
        self.current_language_key = self.resolve_language_key(self.selected_language)
        self.build_start_button_texts()
        self.update_action_texts()
        self.setWindowTitle("MediaSeg")
        if hasattr(self, "drop_area"):
            self.drop_area.text_label.setText(self.t("drop_title"))
            self.drop_area.subtext_label.setText(self.t("drop_subtitle"))
        if hasattr(self, "file_path_edit"):
            self.file_path_edit.setPlaceholderText(self.t("path_placeholder"))
        if hasattr(self, "browse_button"):
            self.browse_button.setText(f"\u00A0\u00A0{self.t('browse')}")
        if hasattr(self, "config_title"):
            self.config_title.setText(self.t("config_title"))
        if hasattr(self, "target_size_lbl"):
            self.target_size_lbl.setText(self.t("chunk_size"))
        if hasattr(self, "out_folder_lbl"):
            self.out_folder_lbl.setText(self.t("output_folder"))
        if hasattr(self, "out_folder_help"):
            self.out_folder_help.setText(self.t("output_folder_help"))
        if hasattr(self, "output_path_edit"):
            self.output_path_edit.setPlaceholderText(self.t("output_folder_placeholder"))
        if hasattr(self, "out_browse_button"):
            self.out_browse_button.setText(f"\u00A0\u00A0{self.t('browse')}")
        if hasattr(self, "out_reset_button"):
            self.out_reset_button.setText(self.t("reset"))
        if hasattr(self, "open_folder_button"):
            self.open_folder_button.setText(self.t("open_output"))
        if hasattr(self, "session_log_button") and self.session_log_button is not None:
            self.session_log_button.setText(self.session_log_button_label())
        if self.session_log_dialog is not None:
            self.session_log_dialog.set_title(self.session_log_window_title())
        if hasattr(self, "file_info_card"):
            self.file_info_card.set_ui_texts(STRINGS[self.current_language_key])
        self.update_processing_overlay()
        self.set_start_button_state(self.start_button_state)

    def set_theme_preference(self, theme_key):
        self.selected_theme = theme_key
        self.settings.setValue("ui/theme", theme_key)
        self.apply_theme()

    def set_language_preference(self, language_key):
        self.selected_language = language_key
        self.settings.setValue("ui/language", language_key)
        self.apply_language()

    def _start_button_icon_path(self, state):
        icon_name = self.start_button_icon_paths.get(state, self.start_button_icon_paths["idle"])
        return get_asset_icon_path(icon_name)

    def _start_button_icon_color(self, state):
        if state in {"preparing", "converting", "splitting", "cleaning"}:
            return self.theme["primary_disabled_text"] if not self.start_button.isEnabled() else "#FFFFFF"
        if state in {"completed", "error"}:
            return "#FFFFFF"
        return "#FFFFFF"

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
        self.log_messages.append(message)
        if self.session_log_dialog is not None:
            self.session_log_dialog.append_log_line(message)

    def append_warning(self, message):
        self.append_info(f"Warning: {message}")

    def append_error(self, message):
        self.append_info(f"Error: {message}")

    def append_success(self, message):
        self.append_info(f"Success: {message}")

    def current_log_text(self):
        return "\n".join(self.log_messages)

    def session_log_button_label(self):
        return "LOG"

    def session_log_window_title(self):
        return "Log"

    def show_session_log_dialog(self):
        if self.session_log_dialog is None:
            self.session_log_dialog = SessionLogDialog(self.session_log_window_title(), self.theme, self)
        self.session_log_dialog.set_title(self.session_log_window_title())
        self.session_log_dialog.set_theme(self.theme)
        self.session_log_dialog.set_log_text(self.current_log_text())
        self.session_log_dialog.show()
        self.session_log_dialog.raise_()
        self.session_log_dialog.activateWindow()

    def show_dependency_warning_dialog(self):
        if not self.missing_dependencies:
            return

        dialog = DependencyWarningDialog(self.missing_dependencies, self.theme, self)
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
                "body": "Official GUI support is MP4, WEBM, and MOV. Experimental GUI support is M4A, MP3, and WAV. WEBM files are converted before splitting.",
            },
            {
                "title": "Runtime Requirement",
                "body": "This software uses libraries from the FFmpeg project under the LGPL v2.1. Release builds bundle FFmpeg and FFprobe. Source runs use local ffmpeg and ffprobe.",
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
        InfoDialog("About MediaSeg", "About MediaSeg", sections, self.theme, self).exec()

    def show_how_to_use_dialog(self):
        sections = [
            {
                "title": "1. Select a video file",
                "body": "Drag and drop a supported file, or click Browse to choose one manually. Official GUI support is MP4, WEBM, and MOV. Experimental GUI support is M4A, MP3, and WAV.",
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
        InfoDialog("How to Use", "How to Use MediaSeg", sections, self.theme, self).exec()

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
        InfoDialog("Setup ffmpeg", "Setup ffmpeg for MediaSeg", sections, self.theme, self).exec()

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
        InfoDialog("Common Issues", "Common Issues", sections, self.theme, self).exec()

    def show_third_party_licenses_dialog(self):
        license_path = get_bundle_path("THIRD_PARTY_LICENSES.md")
        try:
            license_text = license_path.read_text(encoding="utf-8")
        except OSError:
            license_text = "Third-party license information is not available in this build."

        dialog = QDialog(self)
        dialog.setWindowTitle("Third-Party Licenses")
        dialog.setModal(True)
        dialog.setFixedSize(560, 860)

        dialog.setStyleSheet(dialog_stylesheet(self.theme))

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(6, 6, 6, 6)

        panel = QFrame()
        panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(0)

        title_label = QLabel("Third-Party Licenses")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.theme['text']};")
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        body_label = QLabel("Bundled third-party license and attribution notes for this release.")
        body_label.setWordWrap(True)
        body_label.setStyleSheet(f"font-size: 13px; color: {self.theme['muted_text']}; line-height: 1.4;")
        body_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        license_view = QPlainTextEdit()
        license_view.setObjectName("licenseText")
        license_view.setReadOnly(True)
        license_view.setPlainText(license_text)
        license_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_button = QPushButton("Close")
        close_button.setObjectName("dialogPrimaryButton")
        close_button.clicked.connect(dialog.accept)
        close_button.setDefault(True)
        button_row.addWidget(close_button)

        panel_layout.addWidget(title_label)
        panel_layout.addSpacing(16)
        panel_layout.addWidget(body_label)
        panel_layout.addSpacing(16)
        panel_layout.addWidget(license_view)
        panel_layout.addSpacing(16)
        panel_layout.addLayout(button_row)

        root_layout.addWidget(panel)

        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())

        dialog.layout().activate()
        panel_layout.activate()
        root_margins = root_layout.contentsMargins()
        panel_margins = panel_layout.contentsMargins()
        header_height = title_label.sizeHint().height() + body_label.sizeHint().height()
        button_height = close_button.sizeHint().height()
        explicit_spacing_height = 16 + 16 + 16
        non_license_height = (
            root_margins.top()
            + root_margins.bottom()
            + panel_margins.top()
            + panel_margins.bottom()
            + header_height
            + button_height
            + explicit_spacing_height
        )
        license_height = max(520, dialog.height() - non_license_height)
        license_view.setFixedHeight(license_height)

        dialog.exec()

    def check_runtime_dependencies(self, show_dialog=False):
        self.missing_dependencies = self.detect_missing_dependencies()
        self.refresh_control_states()

        if self.missing_dependencies:
            current_missing = tuple(self.missing_dependencies)
            if current_missing != self._last_logged_missing_dependencies:
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
        icon_color = self._start_button_icon_color(self.start_button_state)
        cache_key = f"{icon_path}:{icon_color}"
        if self.loader_icon_cache_path == cache_key and self.loader_icon_cache:
            return

        self.loader_icon_cache = []
        self.loader_icon_cache_path = cache_key

        svg_data = recolor_svg_bytes(icon_path.read_bytes(), icon_color)
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
                self.start_button.setIcon(make_svg_icon(icon_name=icon_path.name, color=self._start_button_icon_color(state), size=18))
            else:
                self.start_button.setIcon(QIcon())
        self.update_processing_overlay()

    def init_ui(self):
        content_widget = QWidget()
        self.setCentralWidget(content_widget)

        self.main_layout = QVBoxLayout(content_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)
        self.main_layout.setAlignment(Qt.AlignTop)

        # 1. Drop Area
        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.on_file_selected)
        self.main_layout.addWidget(self.drop_area)

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
        self.main_layout.addWidget(file_selection_widget)

        # 3. File Info Card
        self.file_info_card = FileInfoCard()
        self.main_layout.addWidget(self.file_info_card)

        # 4. Configuration Panel
        self.config_title = QLabel("CONFIGURATION")
        self.config_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.theme['text']}; letter-spacing: 0.4px;")
        self.main_layout.addWidget(self.config_title)

        self.config_panel = QFrame()
        self.config_panel.setMinimumHeight(340)
        self.config_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.config_panel.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {self.theme['border']};
                border-radius: 16px;
                background-color: {self.theme['surface']};
            }}
            QLabel {{
                border: none;
            }}
        """)
        config_layout = QVBoxLayout(self.config_panel)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(14)

        # A. Target Chunk Size Line
        target_size_header = QHBoxLayout()
        self.target_size_lbl = QLabel("Target Chunk Size")
        self.target_size_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self.theme['text']};")
        
        self.size_edit = QLineEdit()
        self.size_edit.setObjectName("sizeEdit")
        self.size_edit.setValidator(QIntValidator(MIN_CHUNK_SIZE_MB, MAX_MANUAL_CHUNK_SIZE_MB, self))
        self.size_edit.setText("200")
        self.size_edit.setAlignment(Qt.AlignCenter)
        self.size_edit.setFixedWidth(80)
        self.size_edit.installEventFilter(self)
        self.size_edit.textChanged.connect(self.on_lineedit_changed)

        self.mb_label = QLabel("MB")
        self.mb_label.setStyleSheet(f"font-weight: normal; font-size: 14px; color: {self.theme['muted_text']};")

        size_input_row = QHBoxLayout()
        size_input_row.setContentsMargins(0, 0, 0, 0)
        size_input_row.setSpacing(6)
        size_input_row.addStretch()
        size_input_row.addWidget(self.size_edit)
        size_input_row.addWidget(self.mb_label)

        self.size_warning_icon = QLabel()
        self.size_warning_icon.setPixmap(make_svg_icon("circle-alert.svg", color=self.theme["warning"], size=14).pixmap(14, 14))
        self.size_warning_text = QLabel("")
        self.size_warning_text.setWordWrap(False)
        self.size_warning_text.setStyleSheet(f"font-size: 10px; color: {self.theme['warning']};")

        self.size_warning_row = QHBoxLayout()
        self.size_warning_row.setContentsMargins(0, 0, 0, 0)
        self.size_warning_row.setSpacing(6)
        self.size_warning_row.addStretch()
        self.size_warning_row.addWidget(self.size_warning_icon, alignment=Qt.AlignTop)
        self.size_warning_row.addWidget(self.size_warning_text, 0, alignment=Qt.AlignRight | Qt.AlignTop)
        self.update_size_warning(show_on_small_value=False)

        target_size_header.addWidget(self.target_size_lbl)
        target_size_header.addStretch()
        target_size_header.addLayout(size_input_row)
        config_layout.addLayout(target_size_header)
        config_layout.addLayout(self.size_warning_row)

        # B. Chunk Size Slider (Range: 30 - 400)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(MIN_RELIABLE_CHUNK_SIZE_MB, MAX_SLIDER_CHUNK_SIZE_MB)
        self.size_slider.setValue(200)
        self.size_slider.setSingleStep(10)
        self.size_slider.setPageStep(50)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self.on_slider_value_changed)
        self.size_slider.sliderReleased.connect(self.on_slider_released)
        config_layout.addWidget(self.size_slider)

        # C. Slider tick labels follow the slider's actual rendered track positions.
        self.size_slider_ticks = SliderTicksWidget(
            self.size_slider,
            [
                (30, "30MB"),
                (100, "100MB"),
                (200, "200MB"),
                (300, "300MB"),
                (400, "400MB"),
            ],
        )
        config_layout.addWidget(self.size_slider_ticks)

        divider_config = QFrame()
        divider_config.setFrameShape(QFrame.HLine)
        divider_config.setStyleSheet(f"color: {self.theme['border']}; background-color: {self.theme['border']}; max-height: 1px; border: none;")
        config_layout.addWidget(divider_config)

        # E. Output Folder layout (New 2-row structure)
        config_layout.addSpacing(10)
        self.out_folder_lbl = QLabel("Output Folder")
        self.out_folder_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self.theme['text']};")
        config_layout.addWidget(self.out_folder_lbl)

        self.out_folder_help = QLabel("Use Browse to choose a custom output folder.")
        self.out_folder_help.setStyleSheet(f"font-size: 11px; color: {self.theme['muted_text']};")
        config_layout.addWidget(self.out_folder_help)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setFocusPolicy(Qt.NoFocus)
        self.output_path_edit.setCursorPosition(0)
        self.output_path_edit.setPlaceholderText("Same folder as source (Default). Use Browse to change.")
        config_layout.addWidget(self.output_path_edit)

        out_buttons_layout = QHBoxLayout()
        out_buttons_layout.setContentsMargins(0, 4, 0, 4)
        out_buttons_layout.setSpacing(8)
        out_buttons_layout.addStretch()
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
        config_layout.addLayout(out_buttons_layout)

        self.main_layout.addWidget(self.config_panel)
        self.config_panel.adjustSize()
        self.config_panel.setFixedHeight(self.config_panel.sizeHint().height())

        # 5. Action Buttons Bottom Layout
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

        self.session_log_button = QPushButton(self.session_log_button_label())
        self.session_log_button.setObjectName("sessionLogButton")
        self.session_log_button.clicked.connect(self.show_session_log_dialog)
        self.session_log_button.setIcon(make_svg_icon("file-text.svg", color=self.theme["button_secondary_text"], size=18))
        self.session_log_button.setIconSize(QSize(18, 18))

        secondary_action_row = QHBoxLayout()
        secondary_action_row.setContentsMargins(0, 0, 0, 0)
        secondary_action_row.setSpacing(8)
        secondary_action_row.addWidget(self.session_log_button, 3)
        secondary_action_row.addWidget(self.open_folder_button, 5)

        action_layout.addWidget(self.start_button)
        action_layout.addLayout(secondary_action_row)
        action_layout.addSpacing(4)

        self.footer_logo_container = QWidget()
        self.footer_logo_container.setFixedHeight(24)
        footer_logo_layout = QHBoxLayout(self.footer_logo_container)
        footer_logo_layout.setContentsMargins(0, 0, 0, 0)
        footer_logo_layout.setSpacing(0)
        self.footer_logo_widget = ClickableSvgWidget(EXAEDGE_FOOTER_URL)
        self.footer_logo_widget.setFixedSize(112, 20)
        footer_logo_layout.addWidget(self.footer_logo_widget, alignment=Qt.AlignLeft | Qt.AlignVCenter)

        self.footer_version_label = QLabel(f"MediaSeg {get_public_version()} ({get_build_version()})")
        self.footer_version_label.setAlignment(Qt.AlignCenter)

        self.utility_button = QToolButton()
        self.utility_button.setObjectName("utilityMenuButton")
        self.utility_button.setPopupMode(QToolButton.InstantPopup)
        self.utility_button.setIconSize(QSize(18, 18))
        self.utility_button.setFixedSize(36, 36)
        self.utility_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.build_utility_menu()
        self.refresh_footer_logo()

        footer_side_width = 136
        footer_left_cell = QWidget()
        footer_left_cell.setFixedWidth(footer_side_width)
        footer_left_layout = QHBoxLayout(footer_left_cell)
        footer_left_layout.setContentsMargins(4, 0, 0, 0)
        footer_left_layout.addWidget(self.footer_logo_container, alignment=Qt.AlignLeft | Qt.AlignVCenter)

        footer_center_cell = QWidget()
        footer_center_layout = QHBoxLayout(footer_center_cell)
        footer_center_layout.setContentsMargins(0, 0, 0, 0)
        footer_center_layout.addWidget(self.footer_version_label, alignment=Qt.AlignCenter)

        footer_right_cell = QWidget()
        footer_right_cell.setFixedWidth(footer_side_width)
        footer_right_layout = QHBoxLayout(footer_right_cell)
        footer_right_layout.setContentsMargins(0, 0, 0, 0)
        footer_right_layout.addWidget(self.utility_button, alignment=Qt.AlignRight | Qt.AlignVCenter)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addWidget(footer_left_cell)
        footer_layout.addWidget(footer_center_cell, 1)
        footer_layout.addWidget(footer_right_cell)

        action_layout.addLayout(footer_layout)
        self.main_layout.addLayout(action_layout)
        content_widget.adjustSize()
        self.adjustSize()

        self.processing_overlay = ProcessingOverlay(content_widget)
        self.processing_overlay.raise_()

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
        self.update_overlay_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_overlay_geometry()

    def update_overlay_geometry(self):
        if hasattr(self, "processing_overlay") and self.processing_overlay is not None:
            self.processing_overlay.setGeometry(self.centralWidget().rect())
            self.processing_overlay.raise_()

    def update_processing_overlay(self):
        if not hasattr(self, "processing_overlay") or self.processing_overlay is None:
            return
        active_states = {"preparing", "converting", "splitting", "cleaning"}
        if self.processing_active and self.start_button_state in active_states:
            title = self.t(f"overlay_{self.start_button_state}_title")
            body = self.t(f"overlay_{self.start_button_state}_body")
            self.processing_overlay.set_message(title, body)
            self.processing_overlay.setVisible(True)
            self.processing_overlay.raise_()
        else:
            self.processing_overlay.setVisible(False)

    @Slot()
    def browse_file(self):
        default_dir = os.path.expanduser("~/Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media File",
            default_dir,
            supported_file_dialog_filter()
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

    def eventFilter(self, watched, event):
        if watched is self.size_edit and event.type() == QEvent.FocusOut:
            self.normalize_size_input()
            self.update_size_warning(show_on_small_value=True)
        return super().eventFilter(watched, event)

    def normalize_size_input(self):
        text = self.size_edit.text().strip()
        if not text:
            normalized = "200"
        else:
            try:
                value = int(text)
            except ValueError:
                value = 200
            value = max(MIN_CHUNK_SIZE_MB, min(value, MAX_MANUAL_CHUNK_SIZE_MB))
            normalized = str(value)

        if self.size_edit.text() != normalized:
            self.size_edit.blockSignals(True)
            self.size_edit.setText(normalized)
            self.size_edit.blockSignals(False)
            self.on_lineedit_changed(normalized)

    def update_size_warning(self, show_on_small_value=False):
        warning_text = ""

        try:
            target_mb = int(self.size_edit.text())
        except ValueError:
            target_mb = None

        if (
            show_on_small_value
            and target_mb is not None
            and MIN_CHUNK_SIZE_MB <= target_mb < MIN_RELIABLE_CHUNK_SIZE_MB
        ):
            warning_text = self.t("size_warning_below_reliable")

        self.size_warning_icon.setVisible(bool(warning_text))
        self.size_warning_text.setText(warning_text)

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

        effective_target_mb = target_mb * get_estimated_chunk_factor(target_mb)
        if effective_target_mb <= 0:
            effective_target_mb = target_mb

        chunks = int(math.ceil(size_mb / effective_target_mb))
        if chunks <= 0:
            chunks = 1
        self.file_info_card.chunks_val.setText(f"~{chunks} Parts")

    @Slot(int)
    def on_slider_value_changed(self, value):
        snapped = (value // 10) * 10
        if snapped < MIN_RELIABLE_CHUNK_SIZE_MB:
            snapped = MIN_RELIABLE_CHUNK_SIZE_MB
        
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(snapped)
        self.size_slider.blockSignals(False)
        
        self.size_edit.blockSignals(True)
        self.size_edit.setText(str(snapped))
        self.size_edit.blockSignals(False)

        # Refresh immediately so wheel changes and drag changes stay in sync.
        self.update_size_warning(show_on_small_value=False)
        self.update_estimated_chunks()

    @Slot()
    def on_slider_released(self):
        self.update_estimated_chunks()

    @Slot(str)
    def on_lineedit_changed(self, text):
        if not text:
            self.update_size_warning(show_on_small_value=False)
            return
        try:
            value = int(text)
            if MIN_CHUNK_SIZE_MB <= value <= MAX_MANUAL_CHUNK_SIZE_MB:
                slider_val = min(max(value, MIN_RELIABLE_CHUNK_SIZE_MB), MAX_SLIDER_CHUNK_SIZE_MB)
                self.size_slider.blockSignals(True)
                self.size_slider.setValue(slider_val)
                self.size_slider.blockSignals(False)
                
                self.update_size_warning(show_on_small_value=not self.size_edit.hasFocus())
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
            self.append_error(
                f"Invalid chunk size. Enter a value between {MIN_CHUNK_SIZE_MB} MB and {MAX_MANUAL_CHUNK_SIZE_MB} MB."
            )
            return

        self.processing_active = True
        self.start_cooldown_active = True
        self.start_cooldown_deadline = time.monotonic() + 3.0
        self.start_cooldown_timer.start(3000)
        self.refresh_control_states()
        self.set_start_button_state("preparing")
        self.log_messages = []
        if self.session_log_dialog is not None:
            self.session_log_dialog.set_log_text("")
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
        open_folder_icon_color = self.theme["open_button_text"] if self.open_folder_button.isEnabled() else self.theme["open_button_disabled_text"]
        self.open_folder_button.setIcon(make_svg_icon("folder.svg", color=open_folder_icon_color, size=18))
        if self.utility_button is not None:
            self.utility_button.setEnabled(enabled)
            utility_icon_color = self.theme["menu_trigger_fg"] if enabled else self.theme["menu_trigger_disabled_fg"]
            self.utility_button.setIcon(make_svg_icon("settings.svg", color=utility_icon_color, size=18))
        self.update_processing_overlay()

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
                    if is_gui_supported_extension(local_path):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isfile(local_path):
                    if is_gui_supported_extension(local_path):
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
class InstantSubmenuStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_Menu_SubMenuPopupDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)
