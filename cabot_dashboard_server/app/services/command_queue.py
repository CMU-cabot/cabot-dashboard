from asyncio import Queue, Event, wait_for, TimeoutError as asyncio_TimeoutError
from typing import Dict, Optional
from datetime import datetime
from app.utils.logger import logger
from app.config import Settings
import asyncio

class CommandQueueManager:
    def __init__(self):
        self.command_queues: Dict[str, asyncio.Queue] = {}
        self.command_events: Dict[str, asyncio.Event] = {}
        self.POLL_TIMEOUT = Settings().polling_timeout
        logger.info(f"Initialized CommandQueueManager with poll timeout: {self.POLL_TIMEOUT}s")

    async def initialize_client(self, client_id: str) -> None:
        if client_id not in self.command_queues:
            self.command_queues[client_id] = asyncio.Queue()
            self.command_events[client_id] = asyncio.Event()
            logger.info(f"Initialized queue for client {client_id}")

    async def add_command(self, client_id: str, command: dict) -> None:
        """Add command to queue and fire event"""
        if client_id not in self.command_queues:
            await self.initialize_client(client_id)

        # First add to queue
        await self.command_queues[client_id].put(command)
        logger.debug(f"[ADD] Added command to queue for {client_id}")
        
        # Set event
        self.command_events[client_id].set()
        logger.debug(f"[ADD] Event set for {client_id}")

    async def wait_for_update(self, client_id: str) -> Dict:
        """Wait for command to be added (with timeout)"""
        if client_id not in self.command_queues:
            await self.initialize_client(client_id)

        logger.debug(f"[WAIT] Starting wait for {client_id}")
        
        # Clear event
        self.command_events[client_id].clear()
        logger.debug(f"[WAIT] Event cleared for {client_id}")

        try:
            # Wait for event with timeout
            await asyncio.wait_for(
                self.command_events[client_id].wait(),
                timeout=self.POLL_TIMEOUT
            )
            logger.debug(f"[WAIT] Event received for {client_id}")

            # Get command from queue
            command = await self.command_queues[client_id].get()
            logger.debug(f"[WAIT] Retrieved command for {client_id}: {command}")
            return command

        except asyncio.TimeoutError:
            logger.debug(f"[WAIT] Timeout for {client_id} after {self.POLL_TIMEOUT}s")
            raise

    def remove_client(self, client_id: str) -> None:
        """Remove client's queue and event"""
        if client_id in self.command_queues:
            del self.command_queues[client_id]
        if client_id in self.command_events:
            del self.command_events[client_id]
        logger.info(f"Removed client {client_id}")

    def _validate_command(self, command: dict) -> bool:
        """Validate command format"""
        required_fields = {'command', 'commandOption'}
        return (
            isinstance(command, dict) and
            all(field in command for field in required_fields)
        )