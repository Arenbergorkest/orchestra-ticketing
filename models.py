"""
Models for an orchestra season.

A orchestra season exist of one or more productions.
Each production having multiple performances.
"""

from django.db import models
from django.db.models import Model, CharField, ImageField, BooleanField, \
    ForeignKey, ManyToManyField, IntegerField, FloatField, DateTimeField, \
    TextField, EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import get_current_timezone, now
from django.utils import timezone
from model_utils.managers import InheritanceManager
from orchestra_members.models import User
from string import ascii_lowercase
from random import choices


# Base classes
class Season(Model):
    """Everything starts with a season."""

    name = CharField(max_length=50, unique=True)
    short_description = CharField(max_length=300, help_text=_(
        "Short internal description for users."
    ))
    active = BooleanField(default=True)

    def __str__(self):
        """Representation."""
        return self.name


class Location(Model):
    """There are several locations where a production can take place."""

    name = CharField(max_length=50, unique=True)
    latitude = FloatField(blank=True, null=True)
    longitude = FloatField(blank=True, null=True)
    address = CharField(max_length=300)
    description = CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        """Representation."""
        return self.name


# Classes for sales
class PriceCategory(Model):
    """A named price class for tickets."""

    class Meta:
        """Some meta information."""

        verbose_name_plural = 'price categories'

    name = CharField(max_length=200, unique=True)
    price = FloatField()

    def __str__(self):
        """Format."""
        return '{}: €{:g}'.format(self.name, self.price)


class Production(Model):
    """Once rehearsed, production can start."""

    name = CharField(max_length=100, unique=True)
    season = ForeignKey(Season, on_delete=models.CASCADE)
    description = CharField(max_length=5000, help_text=_(
        "Promotional material, can contain html code."
    ))
    image = ImageField(blank=True, null=True, upload_to='static/upload')
    partners = CharField(max_length=255, blank=True, null=True)
    active = BooleanField(default=True)

    def __str__(self):
        """Representation."""
        return self.name


class Performance(Model):
    """A single performance."""

    production = ForeignKey(Production, related_name='performances',
                            on_delete=models.CASCADE)
    date = DateTimeField(_('Date and time of performance'))
    location = ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    seats = IntegerField(help_text=_("Number of seats"), default=750)
    price_categories = ManyToManyField(PriceCategory)
    # Data for performance
    active = BooleanField(default=True)
    open_sales = DateTimeField('Start ticket sales', default=now)
    close_transfer_sales = DateTimeField(
        'Close transfer payment method', default=now)
    close_sales = DateTimeField('Close ticket sales', default=now)
    close_paper_sales = DateTimeField(
        'Close paper sales (by members)', default=now)

    @property
    def price_categories_as_string(self):
        """Price categories."""
        return ", ".join([str(p) for p in self.price_categories.all()])

    @property
    def is_closed_forever(self):
        """Check if it is closed forever."""
        return (not self.active or self.close_sales < timezone.now())

    @property
    def is_open(self):
        """Open sales."""
        return (self.active
                and self.open_sales <= timezone.now()
                and self.close_sales >= timezone.now())

    def __str__(self):
        """Format."""
        return '{} on {:%b %d} @ {}'.format(self.production.name, self.date,
                                            self.location)


class Order(Model):
    """Abstract model for an Order."""

    performance = ForeignKey(
        Performance, related_name='orders', on_delete=models.CASCADE)
    date = DateTimeField(_("Date of order"))
    # Referred musician
    seller = ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    remarks = TextField(blank=True, null=True)
    payed = BooleanField(default=False)
    hash = CharField(max_length=128)
    # Extra information
    objects = InheritanceManager()

    @property
    def num_tickets(self):
        """Count all tickets."""
        return len(self.tickets.all())

    @property
    def total_price(self):
        """Total price of the order."""
        return sum([ticket.price_category.price
                    for ticket in self.tickets.all()])

    def __str__(self):
        """Represent an order."""
        return "Order for {} sold by {} on {:%d-%m-%Y %H:%M:%S}.".format(
            self.performance,
            self.seller, self.date.astimezone(get_current_timezone()))


class OnlineOrder(Order):
    """Model for online order."""

    first_name = CharField(max_length=75)
    last_name = CharField(max_length=75)
    email = EmailField()
    TRANSFER, CASH = 'transfer', 'cash'
    payment_method_choices = (
        (TRANSFER, _('By bank transfer')),
        (CASH, _('At the register (using bancontact or payconic)'))
    )
    payment_method = CharField(
        max_length=8, choices=payment_method_choices, default=TRANSFER)
    # BooleanField is allowed to be null
    first_concert = BooleanField(null=True)
    marketing_feedback = CharField(max_length=120, null=True, blank=True)
    language = CharField(max_length=5, default='nl')

    @property
    def payment_message(self):
        """Payment message."""
        return "Tickets %s - %d" % (self.last_name, self.id)

    @property
    def payment_method_str(self):
        """Payment method string."""
        for option, text in OnlineOrder.payment_method_choices:
            if option == self.payment_method:
                return text

        return OnlineOrder.payment_method_choices[0][1]

    def __str__(self):
        """Represent an online order."""
        return "Online order by {} {} on {:%d-%m-%Y %H:%M:%S}.".format(
            self.first_name,
            self.last_name, self.date.astimezone(get_current_timezone()))


def random_key():
    """Random key."""
    return ''.join(choices(ascii_lowercase, k=18))


class Ticket(Model):
    """A ticket in a certain price category and part of a certain order."""

    price_category = ForeignKey(PriceCategory, on_delete=models.CASCADE)
    order = ForeignKey(Order, related_name='tickets',
                       on_delete=models.CASCADE)
    code = CharField(max_length=18, default=random_key)
    used = BooleanField(default=False)

    def __str__(self):
        """Represent an online order."""
        return 'Ticket of €{:g} for {}, part of {}'.format(
            self.price_category.price, self.order.performance, str(self.order))

    @property
    def qr_code(self):
        """QR code."""
        return 'https://alumniarenbergorkest.be' + (
            reverse('tickets:qr_info', kwargs={
            'id': self.id,
            'code': self.code,
        }))
