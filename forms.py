"""Forms for orchestra seasons."""

from django.forms import ModelForm, Form, IntegerField, HiddenInput
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from django.conf import settings
from .models import OnlineOrder


class TicketsForm(Form):
    """Order tickets."""

    def __init__(self, performance, *args, **kwargs):
        """Initialize the online order."""
        super(TicketsForm, self).__init__(*args, **kwargs)
        self.price_categories = performance.price_categories.all()
        for categ in self.price_categories:
            self.fields[categ.name] = IntegerField(
                required=True, min_value=0, max_value=20, initial=0,
                label=str(categ)
            )

    class Meta:
        """Meta data."""

        model = OnlineOrder
        exclude = ['performance', 'date', 'tickets']
        fields = ('first_name', 'last_name', 'email',
                  'payment_method', 'first_concert',
                  'marketing_feedback', 'remarks')

    def get_total_tickets(self):
        """Get total tickets."""
        total_tickets = 0
        for categ in self.price_categories:
            if self.data[categ.name]:
                total_tickets += int(self.data[categ.name])

        return total_tickets

    def is_valid(self):
        """
        Validate the form.

        Returns True if the form has no errors. Otherwise, False. If errors are
        being ignored, returns False.
        """
        super(TicketsForm, self).is_valid()
        if self.get_total_tickets() == 0:
            self.add_error(None, _(
                "To place an order, you have to order at least one ticket."
            ))
        return self.is_bound and not self.errors


class OnlineOrderForm(ModelForm):
    """An online order."""

    def __init__(self, performance, *args, **kwargs):
        """Initialize the online order."""
        super(OnlineOrderForm, self).__init__(*args, **kwargs)
        # self.fields['seller'].queryset = User.get_filter_gdpr_compliant(
        #     is_active=True
        # )
        # self.fields['seller'].label = _(
        #     "Who is your favorite alumni arenberg orchestra player?"
        # )
        self.fields['first_name'].label = _("First name")
        self.fields['last_name'].label = _("Last name")
        self.fields['email'].label = _("E-mail")
        self.fields['first_concert'].label = _(
            "Is this your first concert?"
        )
        self.fields['marketing_feedback'].label = _(
            "How did you find us?"
        )
        self.fields['remarks'].label = _(
            "Do you have any remarks or special requests?"
        )
        self.fields['hash'].widget = HiddenInput()
        # Close transfer sales
        if performance.close_transfer_sales < now():
            orig = dict(OnlineOrder.payment_method_choices)
            self.fields['payment_method'].choices = (
                (OnlineOrder.CASH, orig[OnlineOrder.CASH]),
            )
            self.fields['payment_method'].label = _(
                "Your payment method will be:"
            )
        elif not settings.TICKETING_ALLOW_CASH:
            orig = dict(OnlineOrder.payment_method_choices)
            self.fields['payment_method'].choices = (
                (OnlineOrder.TRANSFER, orig[OnlineOrder.TRANSFER]),
            )
            self.fields['payment_method'].label = _(
                "Your payment method will be:"
            )
        else:
            self.fields['payment_method'].label = _(
                "How do you want to pay?"
            )

    class Meta:
        """Meta data."""

        model = OnlineOrder
        exclude = ['performance', 'date', 'tickets']
        fields = ('first_name', 'last_name', 'email',
                  'first_concert', 'payment_method',
                  'marketing_feedback', 'remarks', 'hash')
