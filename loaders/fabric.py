import httpx

FABRIC_META = "https://meta.fabricmc.net/v2"

async def get_loader_versions(mc_version: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{FABRIC_META}/versions/loader/{mc_version}")
        r.raise_for_status()
        return r.json()

    async def get_installer_versions():
        async with httpx.AsyncClient() as client:
                r = await client.get(f"{FABRIC_META}/versions/installer")
                r.raise_for_status()
                versions = r.json()
                return versions[0]["version"]

    async def download_server_jar(mc_version: str, loader_version: str, installer_version: str, dest_path: str):
         url = (
              f"{FABRIC_META}/version/loader/"
              f"{mc_version}/{loader_version}/{installer_version}/server/jar"
         )
         async with httpx.AsyncClient() as client:
              async with client.stream("GET", url) as r:
                   r.raise_for_status()
                   with open(dest_path, "wb") as f:
                        async for chunk in r.aiter_bytes():
                             f.write(chunk)

