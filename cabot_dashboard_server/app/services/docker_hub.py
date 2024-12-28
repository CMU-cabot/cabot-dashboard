import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional

class DockerHubService:
    def __init__(self):
        self._tags_cache: Dict[str, dict] = {
            'image1': {
                'name': '',
                'tags': [],
                'last_updated': None
            },
            'image2': {
                'name': '',
                'tags': [],
                'last_updated': None
            },
            'image3': {
                'name': '',
                'tags': [],
                'last_updated': None
            }
        }
        self._base_url = "https://hub.docker.com/v2"
        
    async def fetch_tags(self, repository: str, organization: str = "cmucal") -> List[str]:
        image_name = self._tags_cache[repository]['name'] or repository
        
        async with httpx.AsyncClient() as client:
            url = f"{self._base_url}/repositories/{organization}/{image_name}/tags"
            response = await client.get(url, params={"page_size": 10, "ordering": "last_updated"})
            response.raise_for_status()
            
            data = response.json()
            tags = [result["name"] for result in data["results"]]
            
            self._tags_cache[repository].update({
                "tags": tags,
                "last_updated": datetime.now().isoformat()
            })
            
            return tags
    
    def get_cached_tags(self, repository: str) -> Optional[dict]:
        return self._tags_cache.get(repository)
    
    def get_all_cached_data(self) -> Dict[str, dict]:
        return self._tags_cache
    
    def update_image_name(self, repository: str, name: str) -> bool:
        if repository not in self._tags_cache:
            return False
        
        self._tags_cache[repository]['name'] = name
        return True 