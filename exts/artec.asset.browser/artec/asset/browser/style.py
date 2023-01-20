from omni import ui

from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


class Colors:
    Window = ui.color.shade(0xFF353535)
    Selected = ui.color.shade(0xFFDDDDDD)
    Text = ui.color.shade(0xFF929292)
    Hint = ui.color.shade(0xFF6A6A6A)
    Warn = ui.color.shade(0xCC2222FF)
    Image = ui.color.shade(0xFFA8A8A8)
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)


ARTEC_CLOUD_BROWSER_STYLE = {
    "Window": {"background_color": Colors.Window},
    "CollectionList": {"background_color": 0, "selected_color": 0, "color": 0, "border_radius": 1},
    "TreeView.Frame": {"background_color": 0, "padding": 10},
    "TreeView.Item.Image": {"color": Colors.Text},
    "TreeView.Item.Image:hovered": {"color": 0xFF131313},
    "TreeView.Item.Button": {"background_color": 0, "padding": 0, "margin": 0, "spacing": 0},
    "TreeView.Item.Button:hovered": {"background_color": 0xFF3A3A3A},
    "TreeView.Item.Button.Image": {"image_url": f"{ICON_PATH}/options.svg", "color": Colors.Text},
    "TreeView.Item.Name": {"background_color": 0, "color": Colors.Text},
    "TreeView.Item.Name:selected": {"color": 0xFFE39724},
    "GridView.Frame": {"background_color": Colors.Background},
    "GridView.Item": {"background_color": 0, "color": Colors.Selected, "font_size": 16},
    "GridView.Item.Selection": {"background_color": 0, "border_width": 0},
    "GridView.Item.Selection:selected": {"border_width": 2, "border_color": 0xFFFFC734, "border_radius": 3.0},
    "GridView.Image:selected": {"border_width": 2, "border_color": 0, "border_radius": 3.0},
    "SearchBar.Button.Image::sort": {"image_url": f"{ICON_PATH}/sort_by_dark.svg", "color": Colors.Image},
    "SearchBar.Button.Image::filter": {"image_url": f"{ICON_PATH}/filter.svg", "color": Colors.Image},
    "GridView.Item.Vendor.Background": {"background_color": 0xFF151515},
    "GridView.Item.Hover.Background": {"background_color": 0xFF131313},
    "GridView.Item.Hover.BackgroundAll:hovered": {"background_color": 0xFF131313},
    "GridView.Item.Hover.BackgroundAll": {"background_color": 0},
    "GridView.Item.Tips.Background": {"background_color": 0xFF363636},
    "GridView.Item.Tips.Text": {"background_color": 0xFFDADADA, "font_size": 14, "margin": 2, "color": 0xFFCCCCCC},
    "GridView.Item.Tips.Text::Download": {"color": 0xFF00B976},
    "GridView.Item.Tips.Text::ExternalLink": {"color": 0xFFF6A66B},
    "GridView.Item.Tips.Text::Normal": {"color": 0xFFCCCCCC},
    "GridView.Item.Price": {"color": Colors.Selected, "font_size": 12},
    "GridView.Item.Free": {"color": 0xFF328C6C, "font_size": 12},
    "GridView.Item.Frame": {"color": 0xFFFF0000},
    "GridView.Item.Download": {
        "background_color": 0xFF2A2825,
        "color": 0xFFE39724,
        "secondary_color": 0,
        "border_radius": 0,
        "font_size": 10,
        "padding": 0,
    },
}


POPUP_MENU_STYLE = {
    # "Window": {"background_color": 0xFFFF0000, "padding": 0, "margin": 0},
    "Title.Background": {"background_color": Colors.Window},
    "Title.Label": {"color": Colors.Selected, "font_size": 18},
    "MenuButton": {"background_color": 0xFF4A4A4A, "stack_direction": ui.Direction.LEFT_TO_RIGHT, "spacing": 20},
    "MenuButton.Image": {"image_url": f"{ICON_PATH}/none.svg"},
    "MenuButton.Image:checked": {"image_url": f"{ICON_PATH}/toggleCheck_dark.svg"},
    "MenuButton.Label": {"color": 0xFFD4D4D4, "alignment": ui.Alignment.LEFT_CENTER},
    "MenuSeparator": {"color": Colors.Window, "border_width": 4},
}

EMPTY_NOTIFICATION_STYLE = {
    "EmptyNotification.Frame": {"background_color": Colors.Window},
    "EmptyNotification.Label": {"background_color": Colors.Window, "color": 0xFF7C7C7C, "font_size": 20},
    "EmptyNotification.Image": {"background_color": Colors.Window, "color": 0xFF7C7C7C},
    "EmptyNotification.Button": {"background_color": 0xFF6C6C6C, "color": 0xFF9E9E9E},
}

HOVER_WINDOW_STYLE = {
    **ARTEC_CLOUD_BROWSER_STYLE,
    "Window": {"background_color": Colors.Window, "border_width": 0, "padding": 0},
}

AUTH_DIALOG_STYLE = {
    "Window": {"background_color": Colors.Window, "border_radius": 2, "border_width": 0.5, "border_color": 0x55ADAC9F},
    "Dialog": {"background_color": 0x0, "color": Colors.Text, "margin": 10},
    "Message": {"background_color": 0x0, "color": Colors.Text, "margin": 0, "alignment": ui.Alignment.LEFT_CENTER},
    "Label": {"background_color": 0x0, "color": Colors.Text, "margin": 0, "alignment": ui.Alignment.LEFT_CENTER},
    "Field": {
        "background_color": Colors.Background,
        "color": Colors.Text,
        "alignment": ui.Alignment.LEFT_CENTER,
        "margin_height": 0,
    },
    "Field::overlay": {"background_color": 0x0, "border_color": Colors.Warn, "border_width": 1},
    "Field::warn": {
        "background_color": 0x0,
        "margin_width": 8,
        "color": Colors.Warn,
        "alignment": ui.Alignment.RIGHT_CENTER,
    },
    "CheckBox": {
        "background_color": Colors.Background,
        "color": Colors.Text,
        "margin": 4,
        "alignment": ui.Alignment.LEFT_CENTER,
    },
    "Button": {
        "background_color": Colors.Background,
        "color": Colors.Text,
        "margin": 4,
        "alignment": ui.Alignment.CENTER,
    },
}
