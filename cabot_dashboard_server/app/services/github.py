import httpx
import os


async def fetchSiteReleases(repository):
    async with httpx.AsyncClient() as client:
        repository = repository if "/" in repository else f"cmu-cabot/{repository}"
        url = f"https://api.github.com/repos/{repository}/releases"
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
        print(headers)
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return {
            "CABOT_SITE_REPO": repository,
            "CABOT_SITE_VERSION": [result["tag_name"] for result in response.json()],
            "CABOT_SITE": f"{os.path.basename(repository).replace('_sites_','_site_')}_3d",
        }


if __name__ == "__main__":
    import asyncio
    from pprint import pprint

    async def main():
        pprint(await fetchSiteReleases("cabot_sites_cmu"))
        pprint(await fetchSiteReleases("cmu-cabot/cabot_sites_miraikan"))
        pprint(await fetchSiteReleases("cabot_sites_expo2025"))

    asyncio.run(main())
