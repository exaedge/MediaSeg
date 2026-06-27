from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from themes import dialog_stylesheet


def center_window_to_parent(window, parent):
    if parent is None:
        return
    parent_center = parent.frameGeometry().center()
    window_rect = window.frameGeometry()
    window_rect.moveCenter(parent_center)
    window.move(window_rect.topLeft())


def build_dialog_panel(root_layout, margins, spacing):
    panel = QFrame()
    panel.setObjectName("dialogPanel")
    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(*margins)
    panel_layout.setSpacing(spacing)
    root_layout.addWidget(panel)
    return panel, panel_layout


def build_dialog_title_label(text, theme):
    label = QLabel(text)
    label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme['text']};")
    return label


def build_dialog_body_label(text, theme):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"font-size: 13px; color: {theme['muted_text']}; line-height: 1.4;")
    return label


def calculate_fill_height(window_height, root_layout, panel_layout, fixed_heights, explicit_spacing_height, min_height=520):
    root_margins = root_layout.contentsMargins()
    panel_margins = panel_layout.contentsMargins()
    non_fill_height = (
        root_margins.top()
        + root_margins.bottom()
        + panel_margins.top()
        + panel_margins.bottom()
        + sum(fixed_heights)
        + explicit_spacing_height
    )
    return max(min_height, window_height - non_fill_height)


class DependencyWarningDialog(QDialog):
    def __init__(self, missing_dependencies, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setModal(True)
        self.setFixedWidth(460)

        missing_text = ", ".join(missing_dependencies)

        self.setStyleSheet(dialog_stylesheet(theme))
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        _, panel_layout = build_dialog_panel(root_layout, (20, 20, 20, 20), 14)

        title_label = build_dialog_title_label("ffmpeg / ffprobe is required", theme)

        summary_label = QLabel(f"MediaSeg could not find: {missing_text}.")
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(f"font-size: 13px; color: {theme['text']};")

        body_label = build_dialog_body_label(
            "This app uses the system ffmpeg toolchain for media conversion, duration checks, and splitting. "
            "Install ffmpeg first, then restart MediaSeg.",
            theme,
        )

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

    def showEvent(self, event):
        super().showEvent(event)
        center_window_to_parent(self, self.parentWidget())


class InfoDialog(QDialog):
    def __init__(self, window_title, headline, sections, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setModal(True)
        self.setFixedWidth(560)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        self.setStyleSheet(dialog_stylesheet(theme))
        _, panel_layout = build_dialog_panel(root_layout, (20, 20, 20, 20), 12)

        title_label = build_dialog_title_label(headline, theme)
        title_label.setWordWrap(True)
        panel_layout.addWidget(title_label)

        for section in sections:
            section_layout = QVBoxLayout()
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(4)

            section_title = QLabel(section["title"])
            section_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme['text']};")
            section_layout.addWidget(section_title)

            body_label = build_dialog_body_label(section["body"], theme)
            body_label.setOpenExternalLinks(True)
            body_label.setTextFormat(Qt.RichText)
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

    def showEvent(self, event):
        super().showEvent(event)
        center_window_to_parent(self, self.parentWidget())


class SessionLogDialog(QDialog):
    def __init__(self, title, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle(title)
        self.setModal(False)
        self.setFixedSize(560, 760)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        self.setStyleSheet(dialog_stylesheet(theme))
        _, panel_layout = build_dialog_panel(root_layout, (12, 12, 12, 12), 0)
        panel_layout.setAlignment(Qt.AlignTop)

        self.title_label = build_dialog_title_label(title, theme)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logText")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Activity logs will display here...")
        self.log_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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
        center_window_to_parent(self, self.parentWidget())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recalculate_log_view_height()

    def recalculate_log_view_height(self):
        if not hasattr(self, "_root_layout"):
            return
        self.layout().activate()
        self._panel_layout.activate()
        title_height = self.title_label.sizeHint().height()
        button_height = self._close_button.sizeHint().height()
        explicit_spacing_height = 16 + 12
        log_height = calculate_fill_height(
            self.height(),
            self._root_layout,
            self._panel_layout,
            [title_height, button_height],
            explicit_spacing_height,
        )
        self.log_view.setFixedHeight(log_height)
