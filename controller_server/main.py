import logging
from datetime import datetime
from typing import Any, Dict, AnyStr, List, Union
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
import requests
import asyncio

INTERVAL = 10
logging.basicConfig()
logger = logging.getLogger('CONTROLLER_SERVER')
logger.setLevel(logging.INFO)
app = FastAPI()


class SortedDisplayDict(dict):
    """
    Sort dictionary keys
    """
    def __str__(self):
        return "{" + ", ".join("%r: %r" % (key, self[key]) for key in sorted(self)) + "}"


def fetch_last_position_quantity(last_position: dict) -> int:
    """
    Calculate last trade fill quantity based on last position provided by position server
    :param last_position: dictionary with last position values
    :return: last trade fill quantity
    """
    return sum(last_position.values())


def calculate_overall_quantity(last_position: dict, new_position_quantity: int) -> int:
    """
    Calculate how many stocks each account should have given overall number of stocks after new transaction would
    be made
    :param last_position: dictionary with last position values
    :param new_position_quantity: quantity of stocks for new transaction
    :return: overall quantity after new transaction will be made
    """
    last_position_quantity = fetch_last_position_quantity(last_position)
    return last_position_quantity + new_position_quantity


def calculate_expected_positions(last_position: dict, new_position_quantity: int, accounts_split: dict) -> dict:
    """
    Calculate expected positions. By this it means calculate number of expected quantity each account should have
    according to associated percentage by AUM server
    :param last_position: dictionary with last position values
    :param new_position_quantity: quantity of stocks for new transaction
    :param accounts_split: accounts and its associated % share
    :return: expected positions
    """
    # Calculate overall quantity
    overall_quantity = calculate_overall_quantity(last_position, new_position_quantity)
    expected_positions = {}

    # Calculate quantity for each account given overall quantity and dedicated % share
    for _account, _percentage in accounts_split.items():
        expected_positions[_account] = round(overall_quantity * float(_percentage.strip('%'))/100)

    return expected_positions


def distinguish_positions(last_position: dict, new_position_quantity: int, accounts_split: dict):
    """
    Distinguish which account should have more stocks allocated to current state and which ones should not be taken into
    account during algorithm execution

    :param last_position: dictionary with last position values
    :param new_position_quantity: quantity of stocks for new transaction
    :param accounts_split: accounts and its associated % share
    :return: positions_to_freeze, positions_to_change
    """

    expected_positions = calculate_expected_positions(last_position, new_position_quantity, accounts_split)
    positions_to_change = {}
    positions_to_freeze = {}

    # Compare last position share for given account with expected position to be made with new transaction
    for (last_account, last_quantity), (new_account, new_quantity) in zip(last_position.items(),
                                                                          expected_positions.items()):
        # If account had already more that new % share in given transaction it should not have allocated any more
        # stocks in that round
        if new_quantity <= last_quantity:
            positions_to_freeze[last_account] = last_quantity

        # Accounts that miss some stocks to reach expected % share will be taken into account while allocating
        # stocks resources in the next steps
        else:
            positions_to_change[new_account] = new_quantity - last_quantity

    return positions_to_freeze, positions_to_change


def establish_new_positions(last_position: dict, new_position_quantity: int, accounts_split: dict):
    """
    Calculate the closest possible values in line with the percentage determined by the AUM server
    :param last_position: dictionary with last position values
    :param new_position_quantity: quantity of stocks for new transaction
    :param accounts_split: accounts and its associated % share
    :return: final positions for the accounts that have been chosen to be changed
    """

    _, positions_to_change = distinguish_positions(last_position, new_position_quantity, accounts_split)
    final_positions = {}

    # Decrease number of stocks until they reach new quantity
    while sum(positions_to_change.values()) > new_position_quantity:
        for _account, quantity in positions_to_change.items():
            positions_to_change[_account] = quantity - 1

    return final_positions


def concatenate_positions(last_position: dict, new_position_quantity: int, accounts_split: dict):
    """
    Concatenate dictionaries with accounts that have been changed and those which have not
    :param last_position: dictionary with last position values
    :param new_position_quantity: quantity of stocks for new transaction
    :param accounts_split: accounts and its associated % share
    :return:
    """
    new_accounts_positions = establish_new_positions(last_position, new_position_quantity, accounts_split)
    positions_to_freeze, _ = distinguish_positions(last_position, new_position_quantity, accounts_split)

    # Append adjusted position values with frozen accounts values sorted by accounts name
    return SortedDisplayDict({**positions_to_freeze, **new_accounts_positions})


async def calculate_trade_positions() -> dict:
    """
    Calculate trade positions based on AUM and Fill servers response
    :return: trade positions to be sent to Position server
    """

    # TODO repair here, so that values wll be wrapped to variables and algorithm could be executed
    # TODO change approach to take last account split if new trade fill come earlier than new AUM response
    # TODO change approach to take overall number of stocks accumulated so far (not from previous transaction)
    accounts_split = await get_last_accounts()
    trade_fill = await get_last_fill()
    new_position_quantity = trade_fill['quantity']
    stock_ticker = trade_fill['stock_ticker']
    last_position = await get_previous_allocated_position(trade_fill)

    # First transaction for given stock_ticker e.i. KRUK for given accounts
    trade_positions = {}
    if not last_position:
        for account, split in accounts_split.items():
            stock_ticker = trade_fill['stock_ticker']
            percentage = float(split.strip('%'))/100
            quantity_split = trade_fill['quantity'] * percentage
            trade_positions[account] = f'{quantity_split} {stock_ticker}'

        return trade_positions

    trade_positions = concatenate_positions(last_position, new_position_quantity, accounts_split)
    # Update combined dictionary with stock_ticker
    trade_positions.values = [f'{val} {stock_ticker}' for val in trade_positions.values()]

    return trade_positions


@app.get("/send_fill_to_controller")
async def get_last_fill(trade_fill: dict) -> dict:
    """
    Get last trade fill from Fill server (interval 30secs)
    :param trade_fill: key,value pairs with stock_ticker,price, quantity names and values
    :return: trade_fill
    trade_fill = {
        'stock_ticker': <stock_ticker>, str
        'price': <price$>>, str
        'quantity': <quantity>> int
    }
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"New trade_fill get at {current_time}. Following trade_fill found: {trade_fill}")

    return trade_fill


@app.get("/send_accounts_to_controller")
async def get_last_accounts(accounts_split: dict) -> dict:
    """
    Get last accounts split from AUM server (interval 30secs)
    :param accounts_split: key,value pairs with account name and its associated random percentage share
    :return: accounts_split
    """
    if accounts_split is not None:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"New transaction made at {current_time}. Following accounts split archived: {accounts_split}")

        return accounts_split


@app.get("/send_position_to_controller_server")
async def get_previous_allocated_position(positions: dict) -> dict:
    """
    Get trade positions from position server from the last transaction to calculate new stocks allocation in next
    algorithm round
    positions = {
        'account1': '<quantity> <stock_ticker>', str
        'account2': '<quantity> <stock_ticker>', str
        'accountn': '<quantity> <stock_ticker>', str
    }

    :param positions: key,value pairs with accounts name and associated quantity of given stock ticker
    :return: positions
    """

    for account, position in positions.items():
        positions[account] = int(position.split()[0])

    return positions


@app.on_event("startup")
@repeat_every(seconds=10, wait_first=True)
@app.get("/send_position_to_position_server")
async def send_positions():
    """
    Send trade positions to position server calculated based on accounts split get from AUM server and trade fill get
    from Fill server. Repeat every 10 seconds
    :return: positions
    :type: dict
    return trade_positions = {
        'account1': '<quantity> <stock_ticker>',
        'account2': '<quantity> <stock_ticker>',
        'accountn': '<quantity> <stock_ticker>',
        }
    """
    trade_positions = await calculate_trade_positions()
    logger.info(f"New position available will be sent to position server {trade_positions}")

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    headers = {
            'accept': 'application/json',
        }

    if trade_positions is not None:
        requests.get('http://position_server:8000/send_position_to_position_server', headers=headers, json=trade_positions)

        logger.info(f"New position available will be sent to position server {current_time}")
        return trade_positions
