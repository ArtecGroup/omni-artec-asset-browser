# Asset browser service [omni.services.browsers.asset]

## About

Asset browser microservice.

To use from inside Kit omni.services.client can be used.
If the service runs within the same app:

```
from omni.services.core import main
from omni.services.client import AsyncClient

self._client = AsyncClient(f"local:///{api_version}", app=main.get_app())

await self._client.assets.search.post(<search_criteria>)
```

If the services runs outside of the kit app:

```
from omni.services.client import AsyncClient

self._client = AsyncClient(f"http://{remote_server}/{api_version}")

await self._client.assets.search.post(<search_criteria>)
```