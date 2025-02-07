from asyncio import Queue, Event, wait_for, TimeoutError as asyncio_TimeoutError
from typing import Dict, Optional
from datetime import datetime
from app.utils.logger import logger
from app.config import Settings
import asyncio
import time
import uuid

class CommandQueueManager:
    def __init__(self):
        self.command_queues: Dict[str, asyncio.Queue] = {}
        self.command_requests: Dict[str, str] = {}
        self.POLL_TIMEOUT = Settings().polling_timeout
        logger.info(f"Initialized CommandQueueManager with poll timeout: {self.POLL_TIMEOUT}s")

    async def initialize_client(self, client_id: str) -> None:
        if client_id not in self.command_queues:
            self.command_queues[client_id] = asyncio.Queue()
            logger.info(f"Initialized queue for client {client_id}")

    async def add_command(self, client_id: str, command: dict) -> None:
        if client_id not in self.command_queues:
            await self.initialize_client(client_id)
        await self.command_queues[client_id].put(command)
        logger.debug(f"[ADD] Added command to queue for {client_id}")

    async def wait_for_update(self, client_id: str) -> Dict:
        if client_id not in self.command_queues:
            await self.initialize_client(client_id)
        request_id = uuid.uuid4().hex
        self.command_requests[client_id] = request_id
        logger.debug(f"[WAIT] Starting wait for {client_id}")
        started = time.time()
        while True:
            try:
                command = await asyncio.wait_for(
                    self.command_queues[client_id].get(),
                    timeout=1
                )
                logger.debug(f"[WAIT] Retrieved command for {client_id}: {command}")
                return command
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"Error in wait_for_update: {e}")
                raise ConnectionError(f"Client {client_id} connection error: {e}")
            if self.command_requests[client_id] != request_id:
                raise ConnectionError(f"Client {client_id} request {request_id} closed")
            if time.time() - started > self.POLL_TIMEOUT:
                logger.debug(f"[WAIT] Timeout for {client_id} after {self.POLL_TIMEOUT}s")
                raise asyncio.TimeoutError(f"Client {client_id} request {request_id} timeout")

    def remove_client(self, client_id: str) -> None:
        if client_id in self.command_queues:
            del self.command_queues[client_id]
        if client_id in self.command_requests:
            del self.command_requests[client_id]
        logger.info(f"Removed client {client_id}")

    def _validate_command(self, command: dict) -> bool:
        required_fields = {'command', 'commandOption'}
        return (
            isinstance(command, dict) and
            all(field in command for field in required_fields)
        )