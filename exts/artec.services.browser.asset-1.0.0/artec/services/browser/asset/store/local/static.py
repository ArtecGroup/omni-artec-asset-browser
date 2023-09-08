# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from StaticAssetStore from omni.services.browser.asset

from typing import List, Tuple

from ...models import AssetModel, SearchCriteria
from ..base import BaseAssetStore


class StaticAssetStore(BaseAssetStore):
    def __init__(self, store_id, data=List[AssetModel]) -> None:
        super().__init__(store_id=store_id)
        self._data: List[AssetModel] = data

    async def _search(self, search_criteria: SearchCriteria) -> Tuple[List[AssetModel], bool]:
        keywords = search_criteria.keywords or []
        categories = search_criteria.filter.categories or []
        page = search_criteria.page
        sort = search_criteria.sort

        filtered = self._filter_by_category(categories)

        selected: List[AssetModel] = []
        if keywords:
            for item in filtered:
                if any(keyword in item.name for keyword in keywords) or any(
                    keyword in item.tags for keyword in keywords
                ):
                    selected.append(item)
        else:
            selected = filtered

        if sort:
            key, order = sort
            reverse = True if order == "desc" else False
            if key == "created_at":
                key = "published_at"
            selected = sorted(selected, key=lambda item: getattr(item, key), reverse=reverse)

        start_index = 0
        end_index = page.size
        # For consistency with external vendors, page count starts at 1, not 0.
        if page.number > 1:
            start_index = page.size * (page.number - 1)
            end_index = start_index + page.size

        assets = selected[start_index:end_index]
        return (assets, len(assets) == page.size)

    def _filter_by_category(self, categories: List[str]) -> List[AssetModel]:
        filtered: List[AssetModel] = []
        if categories:
            for item in self._data:
                for item_category in item.categories:
                    if any(category.lower() in item_category.lower() for category in categories):
                        filtered.append(item)
                        break
        else:
            filtered = self._data

        return filtered
