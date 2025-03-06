import httpx
import json
from datetime import datetime, timezone
# import pytz
from typing import Dict, List, Optional
import logging
# from app.config import settings

logger = logging.getLogger(__name__)

CABOT_IMAGES = [
    "cabot-app-server",
    "cabot-bag",
    "cabot-dashboard-client",
    "cabot-driver",
    "cabot-influxdb-client",
    "cabot-localization",
    "cabot-location_tools",
    "cabot-map_server",
    "cabot-navigation",
    "cabot-people",
    "cabot-people-framos",
    "cabot-people-nuc",
]
EXCLUDED_TAGS = ["latest", "main"]

class DockerHubService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DockerHubService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._tags_cache: Dict[str, dict] = {
                'Dockerhub1': {
                    'name': 'cabot-bag',
                    'tags': [],
                    'last_updated': None
                },
            }
            self._base_url = "https://hub.docker.com/v2"
            self._initialized = True

    async def load_image_names(self, organization: str = "cmucal") -> List[str]:
        async with httpx.AsyncClient() as client:
            url = f"{self._base_url}/repositories/{organization}/"
            response = await client.get(url, params={"page_size": 100, "ordering": "name"})
            response.raise_for_status()
            return [result["name"] for result in response.json()["results"] if result['name'] in CABOT_IMAGES]

    async def load_image_tags(self, image_name: str, organization: str = "cmucal") -> List[str]:
        async with httpx.AsyncClient() as client:
            url = f"{self._base_url}/repositories/{organization}/{image_name}/tags"
            response = await client.get(url, params={"page_size": 100, "ordering": "last_updated"})
            response.raise_for_status()
            return [result["name"] for result in response.json()["results"] if result["name"] not in EXCLUDED_TAGS]

    async def fetch_tags(self, repository: str, organization: str = "cmucal") -> List[str]:
        common_tags = None
        for image_name in await self.load_image_names(organization):
            tags = set(await self.load_image_tags(image_name, organization))
            if common_tags is None:
                common_tags = tags
            else:
                common_tags &= tags

        tags = sorted(list(common_tags), reverse=True)
        # tz = pytz.timezone(settings.timezone)
        # current_time = datetime.now(tz).strftime('%Y/%m/%d %H:%M:%S')
        current_time = datetime.now(timezone.utc).isoformat()
        self._tags_cache[repository].update({
            "tags": tags,
            "last_updated": current_time
        })
        return tags
    
    def get_cached_tags(self, repository: str) -> Optional[dict]:
        logger.debug(f"Getting cached tags for {repository}: {json.dumps(self._tags_cache.get(repository), indent=2)}")
        return self._tags_cache.get(repository)
    
    def get_all_cached_data(self) -> Dict[str, dict]:
        logger.debug(f"Getting all cached data: {json.dumps(self._tags_cache, indent=2)}")
        return self._tags_cache
    
    def update_image_name(self, repository: str, name: str) -> bool:
        if repository not in self._tags_cache:
            return False
        
        # tz = pytz.timezone(settings.timezone)
        # current_time = datetime.now(tz).strftime('%Y/%m/%d %H:%M:%S')
        current_time = datetime.now(timezone.utc).isoformat()
        
        self._tags_cache[repository].update({
            'name': name,
            'last_updated': current_time
        })
        logger.debug(f"Updated image name for {repository}: {json.dumps(self._tags_cache[repository], indent=2)}")
        return True
