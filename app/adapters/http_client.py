import httpx


async def get(http_client: httpx.AsyncClient | None, url: str, params: dict) -> httpx.Response:
    if http_client is not None:
        response = await http_client.get(url, params=params)
    else:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
    response.raise_for_status()
    return response


async def post(
    http_client: httpx.AsyncClient | None,
    url: str,
    json: dict,
    headers: dict | None = None,
    timeout: float | None = None,
) -> httpx.Response:
    # timeout=None keeps the client's own timeout (httpx's 5s default for a fresh client).
    kwargs = {"json": json, "headers": headers}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if http_client is not None:
        response = await http_client.post(url, **kwargs)
    else:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, **kwargs)
    response.raise_for_status()
    return response
