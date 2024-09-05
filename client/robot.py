# This code simulates three robots, each sending random status updates.
# Finally, we create a simulation code for the dashboard:

import asyncio
import websockets
import random
import os
import logging
import sys

import asyncio
import websockets
import random
import os
import logging
import sys

# Log configuration
def setup_logger():
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    if os.environ.get('LOG_TO_FILE', 'false').lower() == 'true':
        log_file = os.environ.get('LOG_FILE', 'robot.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(file_handler)
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(stream_handler)

    return logger

logger = setup_logger()

async def robot(robot_id):
    uri = os.environ.get("SERVER_URL", "ws://localhost:8000/ws")
    uri = f"{uri}/{robot_id}"
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=60) as websocket:
                while True:
                    status = random.choice(["Moving", "Stopped", "Charging"])
                    try:
                        await websocket.send(f"Status: {status}")
                        await asyncio.sleep(5)
                    except websockets.exceptions.ConnectionClosedError:
                        logger.info(f"Robot {robot_id}: Connection closed. Attempting to reconnect.")
                        break
                    except Exception as e:
                        logger.error(f"Robot {robot_id}: An error occurred while sending message: {e}")
                        break
        except websockets.exceptions.ConnectionClosedError:
            logger.info(f"Robot {robot_id}: Connection closed. Attempting to reconnect.")
        except Exception as e:
            logger.error(f"Robot {robot_id}: A connection error occurred: {e}")
        
        logger.info(f"Robot {robot_id}: Attempting to reconnect in 5 seconds...")
        await asyncio.sleep(5)

async def main():
    tasks = [robot(f"robot_{i}") for i in range(3)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")