import abc
from typing import Optional, List

from omni import ui
from .style import POPUP_MENU_STYLE


class AbstractPopupMenu(ui.Window):
    """
    Represent a popup window to show popup menu with a title
    """

    def __init__(self, title: str):
        self._title = title
        window_flags = (
            ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        super().__init__(title, width=0, height=0, padding_x=0, padding_y=0, flags=window_flags)

        self.frame.set_build_fn(self._build_ui)
        self.frame.set_style(POPUP_MENU_STYLE)

    def destroy(self):
        self.visible = False

    def _build_ui(self) -> None:
        with self.frame:
            with ui.VStack(height=0):
                with ui.ZStack(height=0):
                    ui.Rectangle(height=40, style_type_name_override="Title.Background")
                    with ui.HStack():
                        ui.Spacer(width=10)
                        ui.Label(self._title, style_type_name_override="Title.Label")
                self._build_menu()

    @abc.abstractmethod
    def _build_menu(self) -> None:
        """Build menu items"""
        pass


class MenuRadioButton(ui.RadioButton):
    """
    Represent a menu radio button.
    """

    def __init__(self, **kwargs):
        super().__init__(
            width=120,
            height=30,
            image_width=24,
            image_height=24,
            spacing=5,
            style_type_name_override="MenuButton",
            **kwargs,
        )


class SortMenu(AbstractPopupMenu):
    """
    Represent the sort by menu.
    Args:
        on_sort_changed_fn: Callback when sort field or sort order changed. Function signure:
            void on_sort_changed_fn(sort_field: str, sort_order: str)
    """

    SORT_BY_FIELDS = ["Name", "Date", "Price"]
    SORT_BY_ORDERS = ["Ascending", "Descending"]

    def __init__(self, on_sort_changed_fn: callable):
        self._on_sort_changed_fn = on_sort_changed_fn
        super().__init__("SORT BY")
        self._sort_field = self.SORT_BY_FIELDS[0]
        self._sort_order = self.SORT_BY_ORDERS[0]

    def _build_menu(self) -> None:
        field_collection = ui.RadioCollection()
        with ui.VStack(height=0):
            for field in self.SORT_BY_FIELDS:
                MenuRadioButton(text=field, radio_collection=field_collection)
        ui.Line(alignment=ui.Alignment.BOTTOM, style_type_name_override="MenuSeparator")
        order_collection = ui.RadioCollection()
        with ui.VStack(height=0):
            for order in self.SORT_BY_ORDERS:
                MenuRadioButton(text=order, radio_collection=order_collection)

        field_collection.model.add_value_changed_fn(self._on_sort_field_changed)
        order_collection.model.add_value_changed_fn(self._on_sort_order_changed)

    def _on_sort_field_changed(self, model: ui.AbstractValueModel) -> None:
        self._sort_field = self.SORT_BY_FIELDS[model.as_int]
        self.visible = False
        if self._on_sort_changed_fn is not None:
            self._on_sort_changed_fn(self._sort_field, self._sort_order)

    def _on_sort_order_changed(self, model: ui.AbstractValueModel) -> None:
        self._sort_order = self.SORT_BY_ORDERS[model.as_int]
        self.visible = False
        if self._on_sort_changed_fn is not None:
            self._on_sort_changed_fn(self._sort_field, self._sort_order)


class FilterMenu(AbstractPopupMenu):
    """
    Represent the filter menu.
    Args:
        providers (List[str]): Provider list.
        on_filter_changed_fn: Callback when filter changed. Function signure:
            void on_filter_changed_fn(filter: str)
    """

    def __init__(self, providers: List[str], on_filter_changed_fn: callable):
        self._on_filter_changed_fn = on_filter_changed_fn
        self._filter_provider = ""
        self._container: Optional[ui.VStack] = None
        super().__init__("Filter")
        self.refresh(providers)

    def refresh(self, providers: List[str]):
        self._providers = providers
        self._providers.insert(0, "All")
        if self._filter_provider not in self._providers:
            self._filter_vendor = self._providers[0]

        if self._container is not None:
            self._container.clear()
            self._build_menu_internal()

    def _build_menu(self) -> None:
        self._container = ui.VStack(height=0)
        self._build_menu_internal()

    def _build_menu_internal(self) -> None:
        vendor_collection = ui.RadioCollection()
        with self._container:
            for field in self._providers:
                MenuRadioButton(text=field, radio_collection=vendor_collection)

        vendor_collection.model.add_value_changed_fn(self._on_filter_changed)

    def _on_filter_changed(self, model: ui.AbstractValueModel) -> None:
        self._filter_provider = self._providers[model.as_int]
        self.visible = False
        if self._on_filter_changed_fn is not None:
            self._on_filter_changed_fn(self._filter_provider)
