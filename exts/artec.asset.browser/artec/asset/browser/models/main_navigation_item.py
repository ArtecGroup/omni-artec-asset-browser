from typing import List, Union
from omni.kit.browser.core import CategoryItem


class MainNavigationItem(CategoryItem):
    def __init__(self, name: str, url: str, provider: Union[str, List[str], None]):
        super().__init__(name)
        self.url = url
        self.thumbnail = None
        self.configurable = False
        self.providers: List[str] = []
        if provider is None:
            self.providers = []
        elif isinstance(provider, str):
            self.providers = [provider]
        else:
            self.providers = provider

    def add_provider(self, provider):
        if provider not in self.providers:
            self.providers.append(provider)
