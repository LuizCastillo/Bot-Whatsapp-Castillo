import httpx


class StorageError(Exception):
    pass


class SupabaseStorage:
    """Storage privado do Supabase via REST. A service key nunca sai do backend."""

    def __init__(self, url: str, service_key: str, bucket: str, http: httpx.AsyncClient | None = None):
        self._url = url.rstrip("/")
        self._key = service_key
        self._bucket = bucket
        self._http = http or httpx.AsyncClient(timeout=30)

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "apikey": self._key}

    def _check(self) -> None:
        if not self._url or not self._key:
            raise StorageError("Supabase Storage não configurado.")

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        self._check()
        r = await self._http.post(f"{self._url}/storage/v1/object/{self._bucket}/{path}", content=data,
                                  headers={**self._headers, "Content-Type": content_type, "x-upsert": "false"})
        if r.status_code >= 400:
            raise StorageError(f"Upload falhou ({r.status_code})")

    async def signed_url(self, path: str, expires: int = 300) -> str:
        self._check()
        r = await self._http.post(f"{self._url}/storage/v1/object/sign/{self._bucket}/{path}",
                                  json={"expiresIn": expires}, headers=self._headers)
        if r.status_code >= 400:
            raise StorageError(f"Assinatura falhou ({r.status_code})")
        return f"{self._url}/storage/v1{r.json()['signedURL']}"


class InMemoryStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        self.files[path] = data

    async def signed_url(self, path: str, expires: int = 300) -> str:
        return f"memory://{path}"
