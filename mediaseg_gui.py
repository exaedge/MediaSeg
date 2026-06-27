import sys
import os
import subprocess
import math
import time
from pathlib import Path
from mediaseg_version import get_public_version, get_build_version
from dialogs import (
    DependencyWarningDialog,
    InfoDialog,
    SessionLogDialog,
    build_dialog_body_label,
    build_dialog_panel,
    build_dialog_title_label,
    calculate_fill_height,
    center_window_to_parent,
)
from menu_helpers import (
    build_utility_menu,
    create_help_menu,
    create_language_actions,
    create_theme_actions,
    create_utility_actions,
    update_action_texts,
)
from themes import THEME_SYSTEM, THEME_DARK, THEME_LIGHT, THEME_NEON, THEME_KEYS, THEMES, resolve_theme_key, theme_display_tokens, dialog_stylesheet
from ui_strings import LANG_SYSTEM, LANG_EN, LANG_JA, LANG_VI, build_strings, system_language_code
from workers import DurationWorker, Worker
from widgets import (
    EXAEDGE_ABOUT_URL,
    EXAEDGE_FOOTER_URL,
    ClickableSvgWidget,
    DropArea,
    FileInfoCard,
    MAX_MANUAL_CHUNK_SIZE_MB,
    MAX_SLIDER_CHUNK_SIZE_MB,
    MIN_CHUNK_SIZE_MB,
    MIN_RELIABLE_CHUNK_SIZE_MB,
    ProcessingOverlay,
    SliderTicksWidget,
    format_duration,
    format_size,
    get_asset_icon_path,
    get_asset_path,
    get_bundle_path,
    get_estimated_chunk_factor,
    get_svg_scaled_size,
    is_gui_supported_extension,
    load_svg_widget,
    make_svg_icon,
    recolor_svg_bytes,
    supported_file_dialog_filter,
)
from PySide6.QtCore import QEvent, Slot, Qt, QSize, QTimer, QRectF, QByteArray, QUrl, QSettings
from PySide6.QtGui import QDesktopServices, QIntValidator, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
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
    QDialog,
)

SUPPORT_FEEDBACK_URL = "https://github.com/exaedge/MediaSeg/issues"
GITHUB_REPO_URL = "https://github.com/exaedge/MediaSeg"
STRINGS = build_strings(MIN_RELIABLE_CHUNK_SIZE_MB)

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
        window_lightness = QApplication.palette().window().color().lightness()
        return resolve_theme_key(selected_theme, window_lightness)

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

    def apply_config_panel_styles(self):
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

    def apply_main_action_styles(self):
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
        self.utility_actions = create_utility_actions(
            self,
            {
                "how_to_use": self.show_how_to_use_dialog,
                "setup_ffmpeg": self.show_setup_help_dialog,
                "common_issues": self.show_common_issues_dialog,
                "licenses": self.show_third_party_licenses_dialog,
                "about": self.show_about_dialog,
                "support_feedback": lambda: QDesktopServices.openUrl(QUrl(SUPPORT_FEEDBACK_URL)),
            },
        )
        self.theme_action_group, self.theme_actions = create_theme_actions(self, self.set_theme_preference)
        self.language_action_group, self.language_actions = create_language_actions(self, self.set_language_preference)
        self.help_menu = create_help_menu(self.menuBar(), self.utility_actions)
        self.update_action_texts()

    def create_help_menu(self):
        self.help_menu = create_help_menu(self.menuBar(), self.utility_actions)

    def build_utility_menu(self):
        self.utility_menu, self.theme_menu, self.language_menu = build_utility_menu(
            self,
            self.utility_button,
            self.theme_actions,
            self.language_actions,
            self.utility_actions,
        )
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
        update_action_texts(
            self.t,
            self.selected_theme,
            self.selected_language,
            self.help_menu,
            self.theme_menu,
            self.language_menu,
            self.utility_actions,
            self.theme_actions,
            self.language_actions,
        )

    def apply_theme(self):
        self.current_theme_key = self.resolve_theme_key(self.selected_theme)
        self.theme = THEMES[self.current_theme_key]
        self.setup_styles()
        for themed_widget in (
            getattr(self, "drop_area", None),
            getattr(self, "file_info_card", None),
            getattr(self, "size_slider_ticks", None),
            getattr(self, "processing_overlay", None),
        ):
            if themed_widget is not None and hasattr(themed_widget, "apply_theme"):
                themed_widget.apply_theme(self.theme)
        self.apply_config_panel_styles()
        self.apply_main_action_styles()
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
                "body": (
                    f'<a href="{EXAEDGE_ABOUT_URL}" style="color:#8FB3FF; text-decoration:none;">ExaEdge</a> '
                    '- Delivering practical AI solutions for businesses and digital creators.<br><br>'
                    f'<a href="{GITHUB_REPO_URL}" style="color:#8FB3FF; text-decoration:none;">GitHub Repository</a> '
                    '- Source code, releases, and issue tracking.'
                ),
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

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(6, 6, 6, 6)
        dialog.setStyleSheet(dialog_stylesheet(self.theme))
        _, panel_layout = build_dialog_panel(root_layout, (10, 10, 10, 10), 0)

        title_label = build_dialog_title_label("Third-Party Licenses", self.theme)
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        body_label = build_dialog_body_label(
            "Bundled third-party license and attribution notes for this release.",
            self.theme,
        )
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

        center_window_to_parent(dialog, self)

        dialog.layout().activate()
        panel_layout.activate()
        header_height = title_label.sizeHint().height() + body_label.sizeHint().height()
        button_height = close_button.sizeHint().height()
        explicit_spacing_height = 16 + 16 + 16
        license_height = calculate_fill_height(
            dialog.height(),
            root_layout,
            panel_layout,
            [header_height, button_height],
            explicit_spacing_height,
        )
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
        current_icon = self.loader_icon_cache[self.rotation_frame_index]
        self.start_button.setIcon(current_icon)
        if hasattr(self, "processing_overlay") and self.processing_overlay is not None and self.processing_overlay.isVisible():
            self.processing_overlay.set_spinner_icon(current_icon)

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
                    current_icon = self.loader_icon_cache[self.rotation_frame_index]
                    self.start_button.setIcon(current_icon)
                    if hasattr(self, "processing_overlay") and self.processing_overlay is not None:
                        self.processing_overlay.set_spinner_icon(current_icon)
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
        self.main_layout.addWidget(self.config_title)

        self.config_panel = QFrame()
        self.config_panel.setMinimumHeight(340)
        self.config_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        config_layout = QVBoxLayout(self.config_panel)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(14)

        # A. Target Chunk Size Line
        target_size_header = QHBoxLayout()
        self.target_size_lbl = QLabel("Target Chunk Size")
        
        self.size_edit = QLineEdit()
        self.size_edit.setObjectName("sizeEdit")
        self.size_edit.setValidator(QIntValidator(MIN_CHUNK_SIZE_MB, MAX_MANUAL_CHUNK_SIZE_MB, self))
        self.size_edit.setText("200")
        self.size_edit.setAlignment(Qt.AlignCenter)
        self.size_edit.setFixedWidth(80)
        self.size_edit.installEventFilter(self)
        self.size_edit.textChanged.connect(self.on_lineedit_changed)

        self.mb_label = QLabel("MB")

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
        config_layout.addWidget(self.out_folder_lbl)

        self.out_folder_help = QLabel("Use Browse to choose a custom output folder.")
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

        self.apply_config_panel_styles()
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
        self.open_folder_button.setIconSize(QSize(18, 18))

        self.session_log_button = QPushButton(self.session_log_button_label())
        self.session_log_button.setObjectName("sessionLogButton")
        self.session_log_button.clicked.connect(self.show_session_log_dialog)
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
        self.apply_main_action_styles()

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
