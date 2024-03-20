from django.test import TestCase
from .PAYnl import *


# Create your tests here.


class PAYTestCase(TestCase):
    def setUp(self):
        pass

    def test_service_get_config(self):
        response_code, response = pay_get_config()
        self.assertEqual(response_code, 200)
        payment_options = response['checkoutOptions']
        self.assertIn("Overboeking", str(payment_options))
        self.assertIn("Payconiq", str(payment_options))
        self.assertIn("Pay By Bank", str(payment_options))
        self.assertIn("Bancontact", str(payment_options))

