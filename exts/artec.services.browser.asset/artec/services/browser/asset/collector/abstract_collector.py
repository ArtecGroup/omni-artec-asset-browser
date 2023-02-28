import abc
from typing import List
from ..models import AssetModel


class AbstractCollector(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    async def collect(self) -> List[AssetModel]:
        """
        Collect assets
        """
        return []
