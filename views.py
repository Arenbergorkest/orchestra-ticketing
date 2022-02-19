"""Overview of views."""

from django.http import JsonResponse
from django.shortcuts import render
from django.http import Http404
from django.utils.timezone import now
from django.template.loader import render_to_string
from django.utils import translation
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required, user_passes_test
from secrets import token_urlsafe
from .models import Production, Performance, Ticket, Order, OnlineOrder
from .forms import OnlineOrderForm, TicketsForm
from django.views.decorators.csrf import csrf_exempt
from weasyprint import HTML
from django.template.loader import get_template
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import redirect

# Auxillary functions


def _check_soldout(performance: Performance):
    """Check if a performance is sold out or not."""
    total_tickets = 0
    performance_object_orders = Order.objects.filter(performance=performance)
    for order in performance_object_orders:
        total_tickets += order.num_tickets

    if total_tickets >= performance.seats:
        performance.active = False
        performance.save()


def _create_order_info(order, ticket_info, performance):
    """Create order info."""
    return {
        "email": order.email,
        'first_name': order.first_name,
        'last_name': order.last_name,
        'payment_method_str': order.payment_method_str,
        'production_name': performance.production.name,
        'date': performance.date.date(),
        'time': performance.date.time(),
        'location': performance.location,
        'address': performance.location.address,
        'payment_method': order.payment_method,
        'total_tickets': order.num_tickets,
        'total_price': order.total_price,
        'performance': performance.date,
        'tickets': ticket_info,
        'transfer_to': settings.TARGET_BANK_ACCOUNT,
        'order_id': order.id,
    }


def _send_order_email(order: OnlineOrder, ticket_info, performance):
    """Send a mail to confirm the order."""
    subject = _("Confirmation Order Tickets: %s") % (
        order.performance.production.name
    )
    data = _create_order_info(order, ticket_info, performance)
    message_plain = render_to_string('ticketing/mail/order_plain.html', data)
    message_html = render_to_string('ticketing/mail/order.html', data)
    sender = (
        "Alumni Arenbergorkest <noreply-ticketing@alumniarenbergorkest.be>"
    )
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


# HTTP pages
def overview(request):
    """Overview of all current ticket sales."""
    productions = Production.objects.filter(active=True, season__active=True)
    subdata = []
    for production in productions:
        performances = list(sorted(
            Performance.objects.filter(production=production),
            key=lambda obj: obj.date
        ))
        subdata.append({
            "production": production,
            "performances": performances
        })

    data = {
        "data": subdata,
        "available": len(productions) > 0
    }
    return render(request, 'ticketing/overview.html', data)


def order(request, id):
    """Buy a ticket."""
    try:
        performance = Performance.objects.get(id=id)
    except Exception:
        raise Http404

    if not performance.is_open:
        raise Http404

    tform = TicketsForm(performance, request.POST or None)
    form = OnlineOrderForm(performance, request.POST or None,
                           initial={'hash': token_urlsafe(50)})
    if (request.POST and form.is_valid() and tform.is_valid()):
        # Create order
        order = form.save(commit=False)
        try:
            Order.objects.get(hash=order.hash)
            # Already posted
            return render(request, 'ticketing/order_repost.html', {
                'performance': performance
            })
        except ObjectDoesNotExist:
            pass

        order.date = now()
        order.performance = performance
        order.language = get_language()
        order.save()

        # Add tickets
        tickets = []
        ticket_info = []
        for categ in performance.price_categories.all():
            if tform.cleaned_data[categ.name]:
                nr = tform.cleaned_data[categ.name]
                ticket_info.append([categ.name, categ.price, nr])
                for i in range(nr):
                    tickets.append(Ticket(price_category=categ, order=order))

        Ticket.objects.bulk_create(tickets)

        # Confirm & close sales if needed
        _send_order_email(order, ticket_info, performance)
        _check_soldout(performance)

        # Redirect
        return render(request, 'ticketing/order_confirm.html', {
            'performance': performance,
            'nr_of_tickets': len(tickets),
            # Required info for followup step:
            'order_id': order.id,
            'order_hash': order.hash,
        })
    else:
        return render(request, 'ticketing/order.html', {
            "form": form,
            "tform": tform,
            'performance': performance
        })


def _create_data_and_pdf_order(request, order: OnlineOrder):
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
        'payment': order.payment_method,
        'production_name': order.performance.production.name,
        'location': order.performance.location,
        'address': order.performance.location.address,
        'date': order.performance.date.date(),
        'time': order.performance.date.time(),
    }

    html_template = get_template('ticketing/mail/tickets_pdf.html')
    pdf_file = HTML(
        string=html_template.render(data),
        base_url=request.build_absolute_uri()).write_pdf()
    return data, pdf_file


def _send_order_payed(request, order: OnlineOrder, subject: str):
    """Send payment information."""
    with translation.override(order.language):
        data, pdf_file = _create_data_and_pdf_order(request, order)
        message_plain = render_to_string(
            'ticketing/mail/tickets_plain.html', data)
        message_html = render_to_string(
            'ticketing/mail/tickets.html', data)
        sender = (
            "Alumni Arenbergorkest <noreply-ticketing@alumniarenbergorkest.be>"
        )
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


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def send_order_payed(request, id):
    """Send that the order is payed including tickets."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except Exception:
        raise Http404

    subject = _("Tickets: %s") % (
        order.performance.production.name
    )
    order.payed = True
    order.save()
    _send_order_payed(request, order, subject)
    return render(request, 'ticketing/mail_send.html', {
        'id': id,
        'order': order
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def test_mail(request, id):
    """Buy a ticket."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except Exception:
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

        data = _create_order_info(order, ticket_info, order.performance)
        _send_order_email(order, ticket_info, order.performance)

    return render(request, 'ticketing/mail/order.html', data)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def test_qr(request, id):
    """Test creation QR code and PDF."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except Exception:
        raise Http404

    with translation.override(order.language):
        data, pdf_file = _create_data_and_pdf_order(request, order)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="tickets.pdf"'

    return response


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def test_qr_mail(request, id):
    """Test creation QR code and PDF."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except Exception:
        raise Http404

    data, pdf_file = _create_data_and_pdf_order(request, order)
    return render(request, 'ticketing/mail/tickets.html', data)


@login_required
def order_paper(request, id):
    """Register a paper sales order."""
    # TODO
    raise Http404


# QR codes
def qr_info(request, id, code):
    """QR information."""
    try:
        ticket = Ticket.objects.get(id=id)
    except Exception:
        raise Http404

    if code != ticket.code:
        raise Http404

    try:
        online_order = OnlineOrder.objects.get(id=ticket.order.id)
    except Exception:
        raise Http404

    if ("kassaticket" in code
            or online_order.performance.date.date() <= datetime.now().date()):
        # TODO: Add better redirect for program info...
        return redirect("./tickets/")

    return render(request, "ticketing/qr_page.html", {
        "ticket": ticket,
        "order": online_order,
    })


# Scanning
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def qr_scan(request):
    """Test a QR code."""
    return render(request, 'ticketing/scan.html')


@csrf_exempt
def qr_reply(request):
    """Test a QR code."""
    code = request.POST.get('code', '')
    items = code.split("/")
    id = items[-2]
    hash_code = items[-1]
    message = "Unknown (%s)" % code
    valid = False
    # TODO: Take into account unpayed tickets & clean up code!
    # Use an enumerator to assign the state!
    try:
        ticket = Ticket.objects.get(id=id)
        if ticket.code == hash_code:
            try:
                last_name = ticket.order.onlineorder.last_name
                first_name = ticket.order.onlineorder.first_name
                message = "%s, %s - %s (%d)" % (
                    last_name, first_name,
                    ticket.price_category.name,
                    ticket.id
                )
            except ObjectDoesNotExist:
                message = "?? - %s (%d)" % (
                    ticket.price_category.name,
                    ticket.id
                )

            valid = True
            already_scanned = ticket.used
            if "kassaticket" in ticket.code:
                valid = True
                already_scanned = False
                message = "KASSA TICKET!"
            elif ticket.order.performance.date.date() != datetime.now().date():
                message += " WRONG DAY - Ticket for concert %s on %s" % (
                    ticket.order.performance,
                    ticket.order.performance.date.strftime("%a %d/%m/%y")
                )
                if already_scanned:
                    message += " AND SCANNED!"
                valid = False
            elif not already_scanned and valid:
                ticket.used = True
                ticket.save()
        else:
            already_scanned = False
            message = "Ticket is invalid!"
            valid = False

    except Exception as e:
        valid = False
        already_scanned = False
        message += " " + str(e)

    return JsonResponse({
        "valid": valid,
        "already_scanned": already_scanned,
        "text": message,
    })
