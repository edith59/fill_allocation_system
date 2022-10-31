import logging
from datetime import datetime
from random import randint
from fastapi_utils.tasks import repeat_every
from typing import List
from fastapi import FastAPI
import random
import requests

MAX_NR_ACCOUNT = 10
TOTAL = 100
logging.basicConfig()
logger = logging.getLogger('AUM_SERVER')
logger.setLevel(logging.INFO)
app = FastAPI()


def draw_percentage(accounts: int) -> List[int]:
    """
    Return a randomly chosen list of n positive integers summing to total.
    :return: random numbers
    :type: list
    """
    dividers = sorted(random.sample(range(1, TOTAL), accounts - 1))
    return [a - b for a, b in zip(dividers + [TOTAL], [0] + dividers)]


def split_accounts_randomly() -> dict:
    """
    Splits randomly 100% by number of accounts that were randomly generated
    :return: key,value pairs with account name and its associated number
    :type: dict
    """

    nr_account = randint(1, MAX_NR_ACCOUNT)
    drawn_percentage_numbers = draw_percentage(nr_account)
    accounts_split = {}

    for i in range(1, nr_account+1):
        accounts_split[f'account{i}'] = int(drawn_percentage_numbers[i-1])

    return accounts_split


@app.on_event("startup")
@repeat_every(seconds=30)
@app.get("/send_accounts_to_controller")
async def send_to_controller() -> dict:
    """
    Sends POST request to controller server with info about split accounts and its associated percentage value every
    30 seconds
    :return: key,value pairs with account name and its associated number
    :return type: dictionary
    """
    accounts_split = split_accounts_randomly()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"New account splits sent at {current_time} with the following random percentage: {accounts_split}")

    headers = {
        'accept': 'application/json',
    }

    requests.get('http://controller_server:8000/send_accounts_to_controller', headers=headers, json=accounts_split)
    return accounts_split
