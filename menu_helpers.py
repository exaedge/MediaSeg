from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QProxyStyle, QStyle

from themes import THEME_DARK, THEME_KEYS, THEME_LIGHT, THEME_NEON, THEME_SYSTEM
from ui_strings import LANG_EN, LANG_JA, LANG_SYSTEM, LANG_VI


class InstantSubmenuStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_Menu_SubMenuPopupDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)


def create_utility_actions(parent, handlers):
    actions = {}

    actions["how_to_use"] = QAction(parent)
    actions["how_to_use"].triggered.connect(handlers["how_to_use"])

    actions["setup_ffmpeg"] = QAction(parent)
    actions["setup_ffmpeg"].triggered.connect(handlers["setup_ffmpeg"])

    actions["common_issues"] = QAction(parent)
    actions["common_issues"].triggered.connect(handlers["common_issues"])

    actions["licenses"] = QAction(parent)
    actions["licenses"].triggered.connect(handlers["licenses"])

    actions["about"] = QAction(parent)
    actions["about"].setMenuRole(QAction.MenuRole.AboutRole)
    actions["about"].triggered.connect(handlers["about"])

    actions["support_feedback"] = QAction(parent)
    actions["support_feedback"].triggered.connect(handlers["support_feedback"])
    return actions


def create_theme_actions(parent, callback):
    action_group = QActionGroup(parent)
    action_group.setExclusive(True)
    actions = {}

    for theme_key in THEME_KEYS:
        action = QAction(parent)
        action.setCheckable(True)
        action.triggered.connect(lambda checked=False, key=theme_key: callback(key))
        action_group.addAction(action)
        actions[theme_key] = action

    return action_group, actions


def create_language_actions(parent, callback):
    action_group = QActionGroup(parent)
    action_group.setExclusive(True)
    actions = {}

    for language_key in (LANG_SYSTEM, LANG_EN, LANG_JA, LANG_VI):
        action = QAction(parent)
        action.setCheckable(True)
        action.triggered.connect(lambda checked=False, key=language_key: callback(key))
        action_group.addAction(action)
        actions[language_key] = action

    return action_group, actions


def create_help_menu(menu_bar, actions):
    help_menu = menu_bar.addMenu("Help")
    help_menu.clear()
    for key in ("how_to_use", "setup_ffmpeg", "common_issues", "licenses", "support_feedback", "about"):
        help_menu.addAction(actions[key])
    return help_menu


def build_utility_menu(parent, button, theme_actions, language_actions, utility_actions):
    utility_menu = QMenu(parent)
    utility_menu.setStyle(InstantSubmenuStyle(utility_menu.style()))
    utility_menu.setMinimumWidth(250)

    theme_menu = QMenu(utility_menu)
    theme_menu.setStyle(InstantSubmenuStyle(theme_menu.style()))
    theme_menu.setMinimumWidth(180)
    for theme_key in THEME_KEYS:
        theme_menu.addAction(theme_actions[theme_key])
    utility_menu.addMenu(theme_menu)

    language_menu = QMenu(utility_menu)
    language_menu.setStyle(InstantSubmenuStyle(language_menu.style()))
    language_menu.setMinimumWidth(180)
    for language_key in (LANG_SYSTEM, LANG_EN, LANG_JA, LANG_VI):
        language_menu.addAction(language_actions[language_key])
    utility_menu.addMenu(language_menu)

    utility_menu.addSeparator()
    for key in ("support_feedback", "how_to_use", "setup_ffmpeg", "common_issues", "licenses", "about"):
        utility_menu.addAction(utility_actions[key])

    button.setMenu(utility_menu)
    return utility_menu, theme_menu, language_menu


def update_action_texts(
    translator,
    selected_theme,
    selected_language,
    help_menu,
    theme_menu,
    language_menu,
    utility_actions,
    theme_actions,
    language_actions,
):
    if help_menu is not None:
        help_menu.setTitle("Help")
    if theme_menu is not None:
        theme_menu.setTitle(translator("menu_theme"))
    if language_menu is not None:
        language_menu.setTitle(translator("menu_language"))

    utility_actions["support_feedback"].setText(translator("menu_support_feedback"))
    utility_actions["how_to_use"].setText(translator("menu_how_to_use"))
    utility_actions["setup_ffmpeg"].setText(translator("menu_setup_ffmpeg"))
    utility_actions["common_issues"].setText(translator("menu_common_issues"))
    utility_actions["licenses"].setText(translator("menu_licenses"))
    utility_actions["about"].setText(translator("menu_about"))

    theme_labels = {
        THEME_SYSTEM: translator("theme_system"),
        THEME_DARK: translator("theme_dark"),
        THEME_LIGHT: translator("theme_light"),
        THEME_NEON: translator("theme_neon"),
    }
    for key, action in theme_actions.items():
        action.setText(theme_labels[key])
        action.setChecked(selected_theme == key)

    language_labels = {
        LANG_SYSTEM: translator("lang_system"),
        LANG_EN: translator("lang_english"),
        LANG_JA: translator("lang_japanese"),
        LANG_VI: translator("lang_vietnamese"),
    }
    for key, action in language_actions.items():
        action.setText(language_labels[key])
        action.setChecked(selected_language == key)
