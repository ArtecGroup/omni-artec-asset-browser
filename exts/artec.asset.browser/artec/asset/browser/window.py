import omni.ui as ui
from .browser_widget import ArtecCloudBrowserWidget
from .models import AssetStoreModel
from .category_delegate import MainNavigationDelegate
from .detail_delegate import AssetDetailDelegate
from .overview_delegate import OverviewDelegate
from .style import ARTEC_CLOUD_BROWSER_STYLE


ARTEC_CLOUD_WINDOW_NAME = "Artec Cloud models"


class ArtecCloudWindow(ui.Window):
    """
    Represent a window to show Artec Cloud Models
    """

    def __init__(self):
        super().__init__(ARTEC_CLOUD_WINDOW_NAME, width=500, height=600)
        self._widget = None

        self.frame.set_build_fn(self._build_ui)
        self.frame.set_style(ARTEC_CLOUD_BROWSER_STYLE)

        # Dock it to the same space where Stage is docked, make it active.
        self.deferred_dock_in("Content", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def destroy(self):
        if self._widget is not None:
            self._widget.destroy()
        super().destroy()

    def _build_ui(self):
        self._browser_model = AssetStoreModel()

        with self.frame:
            with ui.VStack(spacing=5):
                self._widget = ArtecCloudBrowserWidget(
                    self._browser_model,
                    min_thumbnail_size=128,
                    category_delegate=MainNavigationDelegate(self._browser_model, tree_mode=True),
                    category_tree_mode=True,
                    detail_delegate=AssetDetailDelegate(self._browser_model),
                    overview_delegate=OverviewDelegate(model=self._browser_model),
                    style=ARTEC_CLOUD_BROWSER_STYLE,
                    always_select_category=False,
                    show_category_splitter=True,
                    category_width=150,
                )

        self._widget.show_widgets(collection=True)
