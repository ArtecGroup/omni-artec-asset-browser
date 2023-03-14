# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
from typing import List, Dict, Optional, Tuple, Callable

import pydantic


class ProviderModel(pydantic.BaseModel):
    name: str = pydantic.Field(..., title="Provider name", description="Name of the provider")
    icon: str = pydantic.Field("", title="Provider icon", description="Icon of the provider")
    enable_common_categories: bool = pydantic.Field(
        True, title="Use common categories", description="Use common categories for this provider"
    )
    private: bool = pydantic.Field(
        False,
        title="If private provider",
        description="Search in private provider's category will not search other providers",
    )
    configurable: bool = pydantic.Field(
        False, title="If provider could be configed", description="True to call /config to config the provider"
    )
    refresh_setting: str = pydantic.Field(
        "", title="Provider refresh setting path", description="Setting path to notify refresh provider"
    )
    enable_setting: str = pydantic.Field(
        "", title="Provider enable setting path", description="Setting path to notify provider enable"
    )


class ConfigModel(pydantic.BaseModel):
    vendor: str = pydantic.Field(..., title="Vendor", description="Vendor providing the assets")


class AssetModel(pydantic.BaseModel):
    identifier: str = pydantic.Field(
        ..., title="Asset identifier", description="Unique ID code, used for downloading and caching"
    )
    name: str = pydantic.Field(..., title="Asset name", description="Name of the asset")
    version: str = pydantic.Field("", title="Asset version", description="Version of the asset")
    published_at: str = pydantic.Field(
        ..., title="Publication date", description="Date the asset was published (in ISO-8601 format)."
    )
    categories: List[str] = pydantic.Field(
        ..., title="Asset categories", description="List of categories this asset is a part of"
    )
    tags: List[str] = pydantic.Field(list(), title="Asset tags", description="Tags describing the asset")
    vendor: str = pydantic.Field(..., title="Vendor", description="Vendor providing the assets")
    download_url: Optional[str] = pydantic.Field(
        "", title="Download location", description="Location from where to download the asset"
    )
    product_url: str = pydantic.Field(
        "", title="Product url", description="Product url for assets that might not be available to download directly"
    )
    price: float = pydantic.Field(0.0, title="Price", description="Price of the asset in US Dollars")
    thumbnail: str = pydantic.Field(..., title="Thumbnail path", description="Public endpoint for the thumbnail")
    user: str = pydantic.Field(..., title="Asset suer name", description="Name of the user of the asset")
    fusions: List[dict] = pydantic.Field(
        ..., title="Fusions", description="Dict of name and download url"
    )

    class Config:
        schema_extra = {
            "example": {
                "identifier": "1c54053d-49dd-4e18-ba46-abbe49a905b0",
                "name": "Astronaut",
                "version": "1.0.1-beta",
                "published_at": "2020-12-15T17:49:22+00:00",
                "categories": ["/characters/clothing/work"],
                "tags": ["space", "astronaut", "human"],
                "vendor": "NVIDIA",
                "download_url": "https://acme.org/downloads/character/astronaut.zip",
                "product_url": "https://acme.org/products/purchase/astronaut",
                "price": 10.99,
                "thumbnail": "https://images.com/thumbnails/256x256/astronaut.png",
                "fusions": [{"name": "Test", "download_url": "https://images.com/thumbnails/256x256/astronaut.png"}]
            }
        }

    def to_dict(self) -> Dict:
        return self.__dict__


class _Page(pydantic.BaseModel):
    number: int = pydantic.Field(0, title="Page number", description="Page number to return from paginated search")
    size: int = pydantic.Field(50, title="Number of results to return per page", ge=1, le=100)


class _Filter(pydantic.BaseModel):
    categories: List[str] = pydantic.Field(
        None, title="Filter by Category", description="List of categories to filter search results by"
    )


class SearchCriteria(pydantic.BaseModel):
    keywords: List[str] = pydantic.Field(None, title="Search terms", description="List of keywords for searching")
    page: _Page = pydantic.Field(_Page(), title="Pagination options")
    sort: Tuple = pydantic.Field(None, title="Sort order", description="Tuple sort order (ie: price,desc or price,asc")
    filter: _Filter = pydantic.Field(_Filter(), title="Filter Options")
    vendors: List[str] = pydantic.Field(
        None, title="List of vendors", description="Query a subset of available vendors"
    )
    search_timeout: int = pydantic.Field(
        60, title="Search timeout", description="Stop searches after timeout has been reached"
    )

    class Config:
        schema_extra = {
            "example": {
                "keywords": ["GPU", "RTX"],
                "page": {"number": 5, "size": 75},
                "sort": ["price", "desc"],
                "filter": {"categories": ["hardware", "electronics"]},
                "vendors": ["Vendor1", "Vendor2"],
                "search_timeout": 60,
            }
        }
