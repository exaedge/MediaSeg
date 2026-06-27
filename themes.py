THEME_SYSTEM = "system"
THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_NEON = "neon_tokyo"

THEME_KEYS = (
    THEME_SYSTEM,
    THEME_DARK,
    THEME_LIGHT,
    THEME_NEON,
)

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
        "overlay_backdrop": "rgba(10, 12, 16, 118)",
        "overlay_card": "#171B22",
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
        "overlay_backdrop": "rgba(241, 245, 251, 148)",
        "overlay_card": "#FFFFFF",
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
        "overlay_backdrop": "rgba(10, 10, 18, 128)",
        "overlay_card": "#111320",
        "menu_trigger_fg": "#F4F6FF",
        "menu_trigger_hover_bg": "rgba(255, 45, 120, 0.12)",
        "menu_trigger_pressed_bg": "rgba(255, 45, 120, 0.20)",
        "menu_trigger_disabled_fg": "#77819D",
        "footer_text": "#8891AF",
        "footer_logo_fg": "#F4F6FF",
    },
}


def resolve_theme_key(selected_theme, window_lightness):
    if selected_theme != THEME_SYSTEM:
        return selected_theme if selected_theme in THEMES else THEME_DARK
    return THEME_DARK if window_lightness < 128 else THEME_LIGHT


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
