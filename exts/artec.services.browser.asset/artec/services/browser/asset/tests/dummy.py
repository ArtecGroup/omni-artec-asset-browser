# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
from ..models import AssetModel

from ..store.local import StaticAssetStore


class DummyAssetStore(StaticAssetStore):
    """ Hard coded data set of assets.

        This is a hardcoded list of assets used as a reference implementation.

        This store gets instantiated as part of the extension and passed through as a facility to the various endpoints.
        More advanced implementations can be added and as long as the API of the facility is followed they can be swapped without futher changes needed.
    """

    def __init__(self) -> None:

        data = [
            AssetModel(
                identifier="1c54053d-49dd-4e18-ba46-abbe49a905b0",
                name="car-suv-1",
                version="1.0.1-beta",
                published_at="2020-12-15T17:49:22+00:00",
                categories=["/vehicles/cars/suv"],
                tags=["vehicle", "cars", "suv"],
                vendor="NVIDIA",
                download_url="https://acme.org/downloads/vehicles/cars/suv/car-suv-1.zip",
                product_url="https://acme.org/products/purchase/car-suv-1",
                price=10.99,
                thumbnail="https://images.com/thumbnails/256x256/car-suv-1.png",
            ),
            AssetModel(
                identifier="3708fe73-6b82-449a-8e6f-96c6f443a93c",
                name="car-suv-2",
                version="1.0.1-beta",
                published_at="2020-12-15T17:49:22+00:00",
                categories=["/vehicles/cars/suv"],
                tags=["vehicle", "cars", "suv"],
                vendor="NVIDIA",
                download_url="https://acme.org/downloads/vehicles/cars/suv/car-suv-2.zip",
                product_url="https://acme.org/products/purchase/car-suv-2",
                price=12.99,
                thumbnail="https://images.com/thumbnails/256x256/car-suv-2.png",
            ),
            AssetModel(
                identifier="9dcf54e8-76f5-49e0-8155-c4529b5ed059",
                name="car-sedan-1",
                version="1.0.1-beta",
                published_at="2020-12-15T17:49:22+00:00",
                categories=["/vehicles/cars/sedan"],
                tags=["vehicle", "cars", "sedan"],
                vendor="NVIDIA",
                download_url="https://acme.org/downloads/vehicles/cars/suv/car-sedan-1.zip",
                product_url="https://acme.org/products/purchase/car-sedan-1",
                price=13.99,
                thumbnail="https://images.com/thumbnails/256x256/car-sedan-1.png",
            ),
            AssetModel(
                identifier="fc6d47b9-8243-4694-8c44-3b66cbbd7d24",
                name="car-sedan-2",
                version="1.0.1-beta",
                published_at="2020-12-15T17:49:22+00:00",
                categories=["/vehicles/cars/sedan"],
                tags=["vehicle", "cars", "sedan"],
                vendor="NVIDIA",
                download_url="https://acme.org/downloads/vehicles/cars/suv/car-sedan-2.zip",
                product_url="https://acme.org/products/purchase/car-sedan-2",
                price=14.99,
                thumbnail="https://images.com/thumbnails/256x256/car-sedan-2.png",
            ),
            AssetModel(
                identifier="fc6d47b9-8243-4694-8c44-3b66cbbd7d24",
                name="car-sedan-3",
                version="1.0.1-beta",
                published_at="2020-12-15T17:49:22+00:00",
                categories=["/vehicles/cars/sedan"],
                tags=["vehicle", "cars", "sedan"],
                vendor="NVIDIA",
                download_url="https://acme.org/downloads/vehicles/cars/suv/car-sedan-3.zip",
                product_url="https://acme.org/products/purchase/car-sedan-3",
                price=15.99,
                thumbnail="https://images.com/thumbnails/256x256/car-sedan-3.png",
            ),
        ]

        super().__init__("DUMMY", data)
