import random
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
import requests

STOCKS = (
    'AXA', '08OCTAVA', '11BIT', '3RGAMES', 'ABPL', 'ACAUTOGAZ', 'ACTION', 'ADIUVO', 'AGORA', 'AGROTON'
)

MAX_QUANTITY = 100000000
MIN = 1
MAX_INTERVAL = 10
PRECISION = 2
logging.basicConfig()
logger = logging.getLogger('FILL_SERVER')
logger.setLevel(logging.INFO)
random_interval = random.randint(MIN, MAX_INTERVAL)
app = FastAPI()


@app.on_event("startup")
@repeat_every(seconds=random_interval)
#@repeat_every(seconds=10)
@app.get("/send_fill_to_controller")
async def send_to_controller() -> dict:
    """
    Sends POST request at random interval time to controller server about trade fill with given stock name, price and
    quantity
    :return: trade_fill
    :type: dict
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade_fill = {
        'stock_ticker': random.choice(STOCKS),
        'price': f'{round(random.random(), PRECISION)}$',
        'quantity': random.randint(MIN, MAX_QUANTITY)
    }
    logger.info(f"New trade fills sent at {current_time} with following values: {trade_fill}")

    headers = {
        'accept': 'application/json',
    }

    requests.get('http://controller_server:8000/send_fill_to_controller', headers=headers, json=trade_fill)
    return trade_fill
