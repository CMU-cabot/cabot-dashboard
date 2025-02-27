from fastapi import WebSocket
from typing import List
from app.services.docker_hub import DockerHubService
from app.utils.logger import logger
from app.services.github import fetchSiteReleases

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.docker_hub_service = DockerHubService()

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            if websocket not in self.active_connections:
                self.active_connections.append(websocket)
                logger.info("New WebSocket connection established")
        except Exception as e:
            logger.error(f"Error during WebSocket connection: {str(e)}")
            try:
                await websocket.close()
            except:
                pass

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info("WebSocket connection removed")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnection: {str(e)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {str(e)}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def handle_refresh_tags(self, data: dict) -> dict:
        try:
            image_id = data.get("image_id")
            tags = await self.docker_hub_service.fetch_tags(image_id)
            return {
                "type": "refresh_tags_response",
                "image_id": image_id,
                "status": "success",
                "tags": tags
            }
        except Exception as e:
            logger.error(f"Failed to fetch tags for {image_id}: {str(e)}")
            return {
                "type": "refresh_tags_response",
                "image_id": image_id,
                "status": "error",
                "message": f"Failed to fetch tags: {str(e)}"
            }

    async def handle_update_image_name(self, data: dict) -> dict:
        try:
            image_id = data.get("image_id")
            image_name = data.get("image_name")
            
            success = self.docker_hub_service.update_image_name(image_id, image_name)
            if not success:
                return {
                    "type": "update_image_name_response",
                    "image_id": image_id,
                    "status": "error",
                    "message": "Repository not found"
                }
            
            await self.docker_hub_service.fetch_tags(image_id)
            
            return {
                "type": "update_image_name_response",
                "image_id": image_id,
                "status": "success",
                "image_name": image_name
            }
        except Exception as e:
            logger.error(f"Failed to update image name: {str(e)}")
            return {
                "type": "update_image_name_response",
                "image_id": image_id,
                "status": "error",
                "message": f"Failed to update image name: {str(e)}"
            }

    async def handle_refresh_site(self, data: dict) -> dict:
        try:
            repository = data.get("repository")
            info = await fetchSiteReleases(repository)
            return {
                "type": "refresh_site_response",
                "repository": repository,
                "status": "success",
                "info": info
            }
        except Exception as e:
            logger.error(f"Failed to fetch site info for {repository}: {str(e)}")
            return {
                "type": "refresh_site_response",
                "repository": repository,
                "status": "error",
                "message": f"Failed to fetch repository: {str(e)}"
            }

manager = ConnectionManager() 