"""
Created on Sat 2024/03/16 by Bert Destoop

This module is used to perform the PAY.nl API calls.


"""
import time
import requests
from django.conf import settings
from functools import lru_cache
import json

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


def pay_start_transaction(amount, first_name, last_name, email, language, order_id,
                          return_url, concert_date=None, event_name=None):
    """
    Performs the Transaction:create API call from PAY.
    https://developer.pay.nl/reference/post_transactions-1
    Info about requirements from PAY for (concert) tickets
    https://docs.pay.nl/developers?language=en#mandatory-data-ticketing
    @param return_url: the URL to return to after the user completed the transaction
    @param order_id: reference to the order
    @param event_name: name of the event (production) - required for tickets
    @param concert_date: date of the performance - required for tickets
    @param language: NL or ENG language code
    @param email: client order
    @param last_name: client first name
    @param first_name: client last name
    @param amount: the value of the transaction
    @return: The payment URL for the end user
    """
    url = "https://rest.pay.nl/v2/transactions"

    payload = {
        "amount": {"value": amount},
        "integration": {"testMode": True},  # todo: make this not hard coded
        "customer": {
            "firstName": first_name,  # John
            "lastName": last_name,  # Doe
            "email": email,  # sandbox@pay.nl
            "language": language  # NL
        },
        "order": {
            "countryCode": "BE",
            "deliveryDate": concert_date,  # 1999-02-15
            "invoiceDate": "Today"  # 1999-02-15 todo
        },
        "serviceId": settings.PAY_SERVICE_ID,
        "description": event_name,
        "reference": order_id,
        # "returnUrl": return_url,
        "returnUrl": "https://arenbergorkest.be",
        "exchangeUrl": "https://demo.pay.nl/exchange.php"

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
    pay_payment_id = data["id"]

    return payment_url


'''
{
  "id": "EX-0385-8552-1121",
  "serviceId": "SL-7045-9043",
  "description": "should contain name of event",
  "reference": "ThisIsReferenceAlphaNumeric",
  "manualTransferCode": "9000 0023 9316 6561",
  "orderId": "2393166561Xee7c8",
  "paymentUrl": "https://api.pay.nl/controllers/payments/issuer.php?orderId=2393166561Xee7c8&entranceCode=3781c93e1375cf0b1d20ce0d37387d5e5bc6f97e&profileID=613&lang=NL",
  "statusUrl": "https://rest.pay.nl/v2/transactions/EX-0385-8552-1121/status",
  "orderStatusUrl": null,
  "amount": {
    "value": 10,
    "currency": "EUR"
  },
  "uuid": "ac387d5e-5bc6-f97e-2393-166561aee7c8",
  "hash": null,
  "cancelUrl": null,
  "expire": 1713381385,
  "expiresAt": "2024-04-17T21:16:25+02:00",
  "created": "2024-03-20T21:16:25+01:00",
  "createdAt": "2024-03-20T21:16:25+01:00",
  "createdBy": "AT-0095-4198",
  "modified": "2024-03-20T21:16:25+01:00",
  "modifiedAt": "2024-03-20T21:16:25+01:00",
  "modifiedBy": "AT-0095-4198",
  "_links": [
    {
      "href": "/transactions/EX-0385-8552-1121",
      "rel": "details",
      "type": "GET"
    },
    {
      "href": "/transactions",
      "rel": "self",
      "type": "POST"
    }
  ]
}
'''
