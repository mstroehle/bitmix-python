#!/usr/bin/python3

__version__ = '0.0.3'

# API documentation: https://bitmix.biz/en/pages/api

import logging
from time import sleep
from random import randint

import aaargh
import requests
import pyqrcode

from . import validate


DEFAULT_ENDPOINT = 'https://bitmix.biz'
# Tor endpoint
# DEFAULT_ENDPOINT = 'http://bitmixbizymuphkc.onion'

DEFAULT_AFFILIATE = '1555109354-3YjJ-MfCa-aLkH'
# Sets a random fee between 2.1 and 2.9.
DEFAULT_FEE = float('2.{}'.format(randint(1, 9)))
DEFAULT_RETRY = False
# Minutes
DEFAULT_DELAY = randint(10, 70)

HEADERS = {'Accept': 'application/json'}

cli = aaargh.App()

logging.basicConfig(level=logging.WARNING)


def api_request(url, json_params=None, retry=False):
    headers = HEADERS
    try:
        if json_params is None:
            request = requests.get(url,
                                   headers=headers,
                                   timeout=60)
        else:
            request = requests.post(url,
                                    headers=headers,
                                    json=json_params,
                                    timeout=60)
    except Exception as e:
        if retry is True:
            logging.warning('Got an error, but retrying: {}'.format(e))
            sleep(5)
            # Try again.
            return api_request(url, json_params=json_params, retry=retry)
        else:
            raise

    status_code_first_digit = request.status_code // 100
    if status_code_first_digit == 2:
        try:
            request_dict = request.json()
            return request_dict
        except Exception:
            return request.content
    elif status_code_first_digit == 4:
        raise ValueError(request.content)
    elif status_code_first_digit == 5:
        if retry is True:
            logging.warning(request.content)
            logging.warning('Got a 500, retrying in 5 seconds...')
            sleep(5)
            # Try again if we get a 500
            return api_request(url, json_params=json_params, retry=retry)
        else:
            raise Exception(request.content)
    else:
        # Not sure why we'd get this.
        request.raise_for_status()
        raise Exception('Stuff broke strangely.')


@cli.cmd(name='mix')
@cli.cmd_arg('--currency', type=str, required=True)
@cli.cmd_arg('--output_address', type=str, required=True)
@cli.cmd_arg('--endpoint', type=str, default=DEFAULT_ENDPOINT)
def _mix_terminal(currency, output_address, endpoint=DEFAULT_ENDPOINT):
    output = mix(currency=currency,
                 output_address=output_address,
                 endpoint=endpoint)
    address = output['address']
    id = output['id']

    uri = '{}:{}'.format(currency, address)
    qr = pyqrcode.create(uri).terminal(module_color='black',
                                       background='white',
                                       quiet_zone=1)
    letter = letter_of_guarantee(id, endpoint=endpoint)
    msg = '{}\n{}\nID: {}\n{}'
    terminal_output = msg.format(qr,
                                 uri,
                                 id,
                                 letter)
    return terminal_output


def mix(currency,
        output_address,
        endpoint=DEFAULT_ENDPOINT,
        fee=DEFAULT_FEE,
        affiliate=DEFAULT_AFFILIATE,
        delay=DEFAULT_DELAY,
        retry=DEFAULT_RETRY):
    """
    currency must be one of: bitcoin
    output_address is destination for mixed coins.
    affiliate is None or string.

    output is a dict containing id and address.
    """
    validate.currency(currency)

    json_params = {'address': [output_address],
                   'delay': delay,
                   'tax': fee,
                   'coin': currency,
                   'ref': affiliate}

    url = '{}/api/order/create'.format(endpoint)
    output = api_request(url=url, json_params=json_params, retry=retry)
    if not isinstance(output, dict):
        raise ValueError(output)
    output_dict = {'id': output['id'],
                   'address': output['input_address']}
    return output_dict


@cli.cmd
@cli.cmd_arg('id', type=str)
@cli.cmd_arg('--endpoint', type=str, default=DEFAULT_ENDPOINT)
def check(id,
          endpoint=DEFAULT_ENDPOINT,
          retry=DEFAULT_RETRY):
    """
    Checks status of a mix.
    """
    url = '{}/api/order/view/{}'.format(endpoint, id)
    output = api_request(url)
    return output


@cli.cmd
@cli.cmd_arg('id', type=str)
@cli.cmd_arg('--endpoint', type=str, default=DEFAULT_ENDPOINT)
def letter_of_guarantee(id,
                        endpoint=DEFAULT_ENDPOINT,
                        retry=DEFAULT_RETRY):
    """
    Returns the letter of guarantee for a mix.
    """
    url = '{}/api/order/letter/{}'.format(endpoint, id)
    output = api_request(url)
    return output.decode('utf-8')


def main():
    output = cli.run()
    if output is True:
        exit(0)
    elif output is False:
        exit(1)
    else:
        print(output)
        exit(0)


if __name__ == '__main__':
    main
