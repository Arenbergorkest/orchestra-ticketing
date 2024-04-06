from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.http import Http404
from django.shortcuts import render
from django.template.loader import render_to_string, get_template
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from weasyprint import HTML

from orchestra_ticketing.models import OnlineOrder


def send_order_email(order: OnlineOrder, ticket_info, performance):
    """Send a mail to confirm the order."""
    subject = _("Bevestiging bestelling %s") % order.performance.production.name
    data = create_order_info(order, ticket_info, performance)
    message_plain = render_to_string('ticketing/mail/order_plain.html', data)
    message_html = render_to_string('ticketing/mail/order.html', data)
    sender = "Arenbergorkest <noreply-ticketing@arenbergorkest.be>"
    email = EmailMultiAlternatives(
        subject, message_plain,
        from_email=sender,
        to=[data['email']],
        cc=[settings.EMAIL_WEBTEAM, settings.EMAIL_BESTUUR],
    )
    email.attach_alternative(message_html, "text/html")
    try:
        email.send()
    except Exception:
        import logging
        log = logging.getLogger('django.request.mail')
        log.error(
            "Mail couldn't be send for order: %d" % order.id
        )
        log.info(message_plain)

    return data


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def test_mail(request, id):
    """Buy a ticket."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    # Send the mail in the language of the original user
    with translation.override(order.language):
        names = []
        prices = []
        numbers = []
        for categ in order.performance.price_categories.all():
            names.append(categ.name)
            prices.append(categ.price)
            numbers.append(order.tickets.filter(price_category=categ).count())

        ticket_info = []
        for name, price, number in zip(names, prices, numbers):
            if number > 0:
                ticket_info.append([name, price, number])

        data = create_order_info(order, ticket_info, order.performance)
        send_order_email(order, ticket_info, order.performance)

    return render(request, 'ticketing/mail/order.html', data)


def create_order_info(order, ticket_info, performance):
    """Create order info."""
    return {
        "email": order.email,
        'first_name': order.first_name,
        'last_name': order.last_name,
        'production_name': performance.production.name,
        'date': performance.date.date(),
        'time': performance.date.time(),
        'location': performance.location,
        'address': performance.location.address,
        'payment_method': order.payment.get_payment_method_str,
        'total_tickets': order.num_tickets,
        'total_price': order.total_price,
        'performance': performance.date,
        # 'tickets': ticket_info,
        'transfer_to': settings.TARGET_BANK_ACCOUNT,
        'order_id': order.id,
        'order_hash': order.hash,
    }


def send_order_payed(request, order: OnlineOrder):
    """Send payment information."""
    with translation.override(order.language):
        data, pdf_file = create_data_and_pdf_order(request, order)
        message_plain = render_to_string(
            'ticketing/mail/tickets_plain.html', data)
        message_html = render_to_string(
            'ticketing/mail/tickets.html', data)
        sender = (
            "Arenbergorkest <noreply-ticketing@arenbergorkest.be>"
        )
        subject = _("Betaalbevestiging %s") % order.performance.production.name
        email = EmailMultiAlternatives(
            subject, message_plain,
            from_email=sender,
            to=[order.email],
            cc=[settings.EMAIL_WEBTEAM, settings.EMAIL_BESTUUR],
        )
        email.attach_alternative(message_html, "text/html")
        email.attach("tickets.pdf", pdf_file, 'application/pdf')

    try:
        email.send()
    except Exception:
        import logging
        log = logging.getLogger('django.request.mail')
        log.error(
            "Mail couldn't be send for order: %d" % order.id
        )
        log.info(message_plain)


def create_data_and_pdf_order(request, order: OnlineOrder):
    """Create data and pdf for an order."""
    ticket_info = []
    for ticket in order.tickets.all():
        ticket_info.append((str(ticket.price_category), ticket.qr_code))

    data = {
        'order_id': order.id,
        'tickets': ticket_info,
        'first_name': order.first_name,
        'last_name': order.last_name,
        'performance': order.performance,
        'payment': str(order.payment.get_payment_method_str),
        'production_name': order.performance.production.name,
        'location': order.performance.location,
        'address': order.performance.location.address,
        'date': order.performance.date.date(),
        'time': order.performance.date.time(),
    }

    html_template = get_template('ticketing/mail/tickets_pdf.html')
    pdf_file = HTML(
        string=html_template.render(data),
        base_url=request.build_absolute_uri()
    ).write_pdf()
    return data, pdf_file
