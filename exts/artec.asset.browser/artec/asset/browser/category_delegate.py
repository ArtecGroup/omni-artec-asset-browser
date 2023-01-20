from omni import ui
from omni.kit.browser.core import CategoryDelegate, CategoryItem
from .models import MainNavigationItem, AssetStoreModel


class MainNavigationDelegate(CategoryDelegate):
    def __init__(self, model: AssetStoreModel, **kwargs):
        self._model = model
        super().__init__(kwargs)

    def get_label(self, item: CategoryItem) -> str:
        return item.name.upper()

    def build_widget(
        self,
        model: ui.AbstractItemModel,
        item: MainNavigationItem,
        index: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """
        Create a widget per catetory item
        Args:
            model (AbstractItemModel): Category data model
            item (CategoryItem): Category item
            index (int): ignore
            level (int): ignore
            expand (int): ignore
        """
        if item.configurable:
            with ui.HStack():
                ui.Label(
                    self.get_label(item),
                    width=0,
                    alignment=ui.Alignment.LEFT_CENTER,
                    style_type_name_override="TreeView.Item.Name",
                )
                ui.Spacer()
                # with ui.VStack():
                #    ui.Spacer()
                #    ui.Image(f"{ICON_PATH}/options.svg", width=12, height=12, style_type_name_override="TreeView.Item.Image", mouse_pressed_fn=lambda x, y, btn, flag, item=item: self._on_config(item))
                #    ui.Spacer()
                ui.Button(
                    "",
                    width=16,
                    height=16,
                    clicked_fn=lambda model=model, item=item: self._on_config(model, item),
                    style_type_name_override="TreeView.Item.Button",
                )
            return

        super().build_widget(model, item, index=index, level=level, expanded=expanded)

    def _on_config(self, model: AssetStoreModel, item: MainNavigationItem) -> None:
        # Here item name is provider id
        self._model.config_provider(item.name)
