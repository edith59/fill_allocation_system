import logging
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from datetime import datetime
from typing import Any, Dict, AnyStr, List, Union
import requests
import asyncio

INTERVAL = 10
logging.basicConfig()
logger = logging.getLogger('POSITION_SERVER')
logger.setLevel(logging.INFO)
app = FastAPI()


@app.get("/send_position_to_controller_server")
def get_previous_position(previous_positions: dict):
    """
    Sends info about previous position back to controller server to calculate properly allocation for next transaction
    :param previous_positions: - key,value pairs with information about which account had how many stocks assigned
    :type dict
    :return previous_positions
    """
    headers = {
        'accept': 'application/json',
    }
    # TODO add positions to DB

    requests.get('http://controller_server:8000/send_position_to_controller_server', headers=headers, json=previous_positions)

    logger.info(f"Previous position observed: {previous_positions}")
    return previous_positions


@app.on_event("startup")
@app.get("/send_position_to_position_server")
async def position_server(trade_positions: dict = None):
    """
    Prints out info about trade position
    :param trade_positions - obtained from controller server every 10 seconds
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"New transaction made at {current_time}. Following positions archived: {trade_positions}")

    # Send last position back to controller for next transaction
    get_previous_position(trade_positions)
