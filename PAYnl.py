"""
Created on Sat 2024/03/16 by Bert Destoop

This module is used to perform the PAY.nl API calls.


"""
import json
import time
from datetime import datetime
from functools import lru_cache

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from orchestra_ticketing.email import _send_order_email
from orchestra_ticketing.models import OnlineOrder

CACHE_TTL_HRS = 6  # amounts to 120 calls/month < 1000


def _get_ttl_hash(seconds=3600 * CACHE_TTL_HRS):
    """
    Return the same value within `seconds` time period

    Note that the non-payment API calls (e.g., service:getConfig) are limited to 1000/month. PAY. recommends caching the
        result of the API invocations to avoid going over this limit. The ttl_hash solution is described on this
        (https://stackoverflow.com/questions/31771286/python-in-memory-cache-with-time-to-live) stackoverflow issue.
    """
    return round(time.time() / seconds)


@lru_cache()
def pay_get_config(ttl_hash=_get_ttl_hash()):
    """
    Performs the service:getConfig API call from PAY.

    @return: The JSON contained in the API response.
    """
    url = "https://rest.pay.nl/v2/services/config?serviceId=" + settings.PAY_SERVICE_ID

    headers = {
        "accept": "application/json",
        "authorization": "Basic " + settings.PAY_AUTH,
    }

    response = requests.get(url, headers=headers)

    json = {}
    if response.status_code == 200:
        json = response.json()

    # todo: if status code 200 was not received, e-mail the webmasters. The PAY. service could be down.

    return response.status_code, json


def pay_start_transaction(amount, first_name, last_name, email, language, order_id, return_path, exchange_path,
                          host_name, concert_date=None, event_name=None):
    """
    Performs the Transaction:create API call from PAY.
    https://developer.pay.nl/reference/post_transactions-1
    Info about requirements from PAY for (concert) tickets
    https://docs.pay.nl/developers?language=en#mandatory-data-ticketing
    @param exchange_path: path to the view for exchange calls - see pay.nl api documentation
    @param host_name: the hostname of the return and exchange urls. This is to be found with request.get_host() and allows for development using ngrok
    @param return_path: path of the view to return to after the user completed the transaction
    @param order_id: reference to the order
    @param event_name: name of the event (production) - required for tickets
    @param concert_date: date of the performance - required for tickets
    @param language: NL or ENG language code
    @param email: client order
    @param last_name: client first name
    @param first_name: client last name
    @param amount: the value of the transaction in €
    @return:
        The payment URL for the end user,
        The status URL that reports the status of the payment,
        The payment id from PAY
    """
    url = "https://rest.pay.nl/v2/transactions"

    payload = {
        "amount": {"value": amount * 100},  # api expects amount in cents
        "integration": {
            "testMode": True if settings.DEVELOPPING else False
        },
        "customer": {
            "firstName": first_name,  # John
            "lastName": last_name,  # Doe
            "email": email,  # sandbox@pay.nl
            "language": language  # NL
        },
        "order": {
            "countryCode": "BE",
            "deliveryDate": concert_date,  # 1999-02-15
            "invoiceDate": datetime.today().strftime('%Y-%m-%d'),  # 1999-02-15
        },
        "serviceId": settings.PAY_SERVICE_ID,
        "description": event_name,
        "reference": order_id,
        "returnUrl": 'https://' + host_name + return_path,
        "exchangeUrl": 'https://' + host_name + exchange_path
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Basic " + settings.PAY_AUTH,
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    payment_url = data["paymentUrl"]
    status_url = data["statusUrl"]
    pay_payment_id = data["orderId"]

    return payment_url, status_url, pay_payment_id


@csrf_exempt
def pay_exchange_view(request):
    """
    PAY calls this view to inform about updates to payment status.
    CSRF is not crucial since the post-request contains PAY signature.
    CSRF caused issues.
    @param request:
    @return:
    """
    if request.method != 'POST':
        return HttpResponse('FALSE')

    # get the POST json
    data = json.loads(request.body)
    print(f"Transaction:Exchange - {data}")

    # get the order
    pay_order_id = data['order_id']
    order = OnlineOrder.objects.get(pay_order_id=pay_order_id)

    # update the order according to the POST json information
    if order.payment_status is None:
        order.payment_method = 'x'

    order.payment_status = data['action']
    match order.payment_status:
        # https://docs.pay.nl/developers#exchange-calls
        case "new_ppt":
            order.payment_status = "complete"
            performance = order.performance
            _send_order_email(order, None, performance)  # the ticket_info parameter (None) seems unused?

        case "pending":
            pass
        case "cancel":
            # todo: figure out if we want to log this and what code therefore needs to change (e.g. total ticket counting)
            pass
        case "verify":
            pass
        case "transaction:fraudnotice":
            pass
        case _:
            pass
    order.save()

    return HttpResponse('TRUE')
