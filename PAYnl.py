"""
Created on Sat 2024/03/16 by Bert Destoop

This module is used to perform the PAY.nl API calls.


"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from functools import lru_cache

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _

from orchestra_ticketing.email import send_order_email, send_order_payed
from orchestra_ticketing.models import OnlineOrder

CACHE_TTL_HRS = 6  # amounts to 120 calls/month < 1000


# --- payment method ids ---
class pay_method_id:
    TEST_MODE = 4
    BANCONTACT = 436
    PAYCONIQ = 2379
    PAY_BY_BANK = 2970


# --- private helper methods ---
def _get_ttl_hash(seconds=3600 * CACHE_TTL_HRS):
    """
    Return the same value within `seconds` time period

    Note that the non-payment API calls (e.g., service:getConfig) are limited to 1000/month. PAY. recommends caching the
        result of the API invocations to avoid going over this limit. The ttl_hash solution is described on this
        (https://stackoverflow.com/questions/31771286/python-in-memory-cache-with-time-to-live) stackoverflow issue.
    """
    return round(time.time() / seconds)


def _pay_check_signature(request):
    signature = request.headers.get('signature')
    signature_algorithm = request.headers.get('signature-algorithm')
    signature_keyid = request.headers.get('signature-keyid')
    signature_method = request.headers.get('signature-method')
    request_body = request.body

    secret = settings.PAY_SL_SECRET

    logger = logging.getLogger("PAY API")

    if signature_method != 'HMAC':
        logger.error(f'signature method {signature_method} not known')
        return False

    if signature_algorithm != 'sha512':
        logger.error(f'signature algorithm {signature_algorithm} not known')
        return False

    if signature_keyid != settings.PAY_SL_ID:
        logger.error(f'signature keyid was different from expected signature keyid')
        return False

    # perform HMAC authentication algorithm
    signature_check = hmac.new(bytes(secret.encode()), request_body, digestmod=hashlib.sha512).hexdigest()
    if signature_check != signature:
        logger.error(f'signature did not match')
        return False

    return True


def _check_response_code_transaction_start(response):
    """
    Checks if the response code of the transaction start request is 201, as it should be.
    Handles deviations from this.
    https://developer.pay.nl/reference/post_transactions-1
    @param response: The response object from the http request
    @return: True if the status code is 201, False if error code.
    """
    code = response.status_code
    logger = logging.getLogger("PAY API transaction:start")

    match code:
        case 201:  # 201 - Created
            return True
        case 400:
            logger.error('Transaction:start - 400 - Bad request, see response body for more information')
            logger.error(f'transaction body: {json.dumps(response.json(), indent=2)}', stack_info=True)
            pass
        case 401:
            logger.error('Transaction:start - 401 - Unauthorized. Supplied AT code/token or SL code/secret is invalid',
                         stack_info=True)
            pass
        case 403:
            logger.error('Transaction:start - 403 - Forbidden. Supplied credentials have no rights', stack_info=True)
            pass
        case 404:
            logger.error('Transaction:start - 404 - Not found', stack_info=True)
            pass
        case 405:
            logger.error('Transaction:start - 405 - Used HTTP method is not allowed', stack_info=True)
            pass
        case 406:
            logger.error('Transaction:start - 406 - Not acceptable. The supplied content type in the '
                         'accept parameter in the header is not supported', stack_info=True)
            pass
        case 415:
            logger.error('Transaction:start - 415 - Unsupported media. The supplied content type in '
                         'the content-type parameter in the header is not supported', stack_info=True)
            pass
        case 422:
            logger.error('Transaction:start - 422 - Unprocessable Entity, see response body for more information',
                         stack_info=True)
            pass
        case 429:
            logger.error('Transaction:start - 429 - Rate limit reached.', stack_info=True)
            pass
        case 500:
            logger.error('Transaction:start - 500 - An internal error occurred', stack_info=True)
            pass

    return False


# --- public  methods ---
@lru_cache()
def pay_get_config(ttl_hash=_get_ttl_hash()):
    """
    Performs the service:getConfig API call from PAY.

    @return: The JSON contained in the API response.
    """
    url = "https://rest.pay.nl/v2/services/config?serviceId=" + settings.PAY_SL_ID

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
        "serviceId": settings.PAY_SL_ID,
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
    if not _check_response_code_transaction_start(response):
        raise requests.exceptions.RequestException(response.status_code)

    data = response.json()

    payment_url = data["paymentUrl"]
    status_url = data["statusUrl"]
    pay_payment_id = data["orderId"]

    return payment_url, status_url, pay_payment_id


@csrf_exempt
def pay_order_exchange_view(request):
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

    # check the PAY exchange signature https://developer.pay.nl/docs/signing
    if not _pay_check_signature(request):
        return HttpResponse('FALSE')

    # get the order
    pay_order_id = data['order_id']
    order = OnlineOrder.objects.get(pay_order_id=pay_order_id)

    # update the order according to the POST json information
    match int(data['payment_method_id']):
        case pay_method_id.TEST_MODE:
            order.payment_method = "test modus"
        case pay_method_id.PAY_BY_BANK:
            order.payment_method = "payment by bank"
        case pay_method_id.PAYCONIQ:
            order.payment_method = "Payconiq"
        case pay_method_id.BANCONTACT:
            order.payment_method = "Bankcontact"
        case _:
            # if the payment_method is unknown because it was enabled in the PAY settings, but not implemented in
            # software, its method id is stored instead
            order.payment_method = f"meth_id={_}"
            pass

    order.payment_status = data['action']
    performance = order.performance
    match order.payment_status:
        # https://docs.pay.nl/developers#exchange-calls
        case "new_ppt":
            order.payed = True
            send_order_payed(request, order)

        case "pending":
            send_order_email(order, None, performance)  # the ticket_info parameter (None) seems unused?

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
