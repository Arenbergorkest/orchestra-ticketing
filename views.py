"""Overview of views."""
from secrets import token_urlsafe

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import translation
from django.utils.timezone import now
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_exempt

from .PAYnl import pay_start_transaction
from .email import _create_order_info, _send_order_payed, _create_data_and_pdf_order
from .forms import OnlineOrderForm, TicketsForm
from .models import Production, Performance, Ticket, Order, OnlineOrder, \
    PaperOrder


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


# HTTP pages
def overview(request):
    """Overview of all current ticket sales."""
    productions = Production.objects.filter(active=True)
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
    except ObjectDoesNotExist:
        raise Http404

    if not performance.is_open:
        raise Http404

    tform = TicketsForm(performance, request.POST or None)
    form = OnlineOrderForm(performance, request.POST or None,
                           initial={'hash': token_urlsafe(50)})

    if request.POST and form.is_valid() and tform.is_valid():
        # Create order
        order = form.save(commit=False)
        try:
            Order.objects.get(hash=order.hash)
            # Already posted
            return render(request, 'ticketing/order/repost.html', {
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

        # Close sales if needed
        _check_soldout(performance)

        order_price = order.total_price

        # Redirect
        payment_url, status_url, pay_order_id = pay_start_transaction(order_price,
                                                                      order.first_name, order.last_name,
                                                                      order.email,
                                                                      request.LANGUAGE_CODE, order.id,
                                                                      # todo: fix bug where language code seems to be EN all the time
                                                                      reverse("tickets:order_confirm",
                                                                              args=[order.pk]),
                                                                      reverse('tickets:order_exchange'),
                                                                      request.get_host())
        # todo: add concert_date to method call
        # todo: add event name to method call

        order.pay_order_id = pay_order_id
        order.save()

        return redirect(payment_url)

    elif request.POST:  # todo: fix an online order form not marking mistakes on the order form when it is not correctly filled in
        print('form not valid')
    else:
        return render(request, 'ticketing/order/form.html', {
            "form": form,
            "tform": tform,
            'performance': performance,
        })


def order_confirm(request, order_id):
    # todo: capture orderId=2404510245X251e7&orderStatusId=100&paymentSessionId=2404510245
    order = OnlineOrder.objects.get(id=order_id)

    return render(request, 'ticketing/order/confirm.html', {
        # Required info for the followup step:
        'order_id': order.id,
        'order_hash': order.hash,
        'total_price': order.total_price,
        'last_name': order.last_name,
        'payment_method': order.payment_method,
    })


def order_info(request, id, code):
    """Check order information."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    if order.hash != code:
        raise Http404

    ticket_amount = {}
    ticket_price = {}
    for ticket in order.tickets.all():
        if ticket.price_category.name not in ticket_amount:
            ticket_amount[ticket.price_category.name] = 1
        else:
            ticket_amount[ticket.price_category.name] += 1

        ticket_price[ticket.price_category.name] = ticket.price_category.price

    ticket_info = []
    for name in ticket_price:
        ticket_info.append([name, ticket_price[name], ticket_amount[name]])

    data = _create_order_info(order, ticket_info, order.performance)
    data['order'] = order
    return render(request, 'ticketing/order/info.html', data)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def send_order_payed(request, id):
    """set and order to "paid" and send that the order is paid including tickets."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    order.payed = True
    order.save()
    _send_order_payed(request, order)
    return render(request, 'ticketing/order/mail_send.html', {
        'id': id,
        'order': order
    })


def download_tickets(request, id, code):
    """Download tickets."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    if order.hash != code or not order.payed:
        raise Http404

    with translation.override(order.language):
        data, pdf_file = _create_data_and_pdf_order(request, order)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="tickets.pdf"'

    return response


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def test_qr(request, id):
    """Test creation QR code and PDF."""
    try:
        order = OnlineOrder.objects.get(id=id)
    except ObjectDoesNotExist:
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
    except ObjectDoesNotExist:
        raise Http404

    data, pdf_file = _create_data_and_pdf_order(request, order)
    return render(request, 'ticketing/mail/tickets.html', data)


@login_required
def order_paper(request, id):
    """Register a paper sales order."""
    # If it isn't an active performance, raise 404
    try:
        performance = Performance.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    if not performance.is_papersales_open:
        raise Http404

    tform = TicketsForm(performance, request.POST or None)
    if request.POST and tform.is_valid():
        paper_order = PaperOrder.objects.create(
            performance=performance, date=now(),
            seller=request.user
        )
        # Create tickets, should be created in bulk (TODO)
        tickets = []
        for categ in performance.price_categories.all():
            for i in range(tform.cleaned_data.get(categ.name)):
                tickets.append(Ticket.objects.create(
                    price_category=categ, order=paper_order
                ))
        # TODO: Give usefull response with ticket count
        return HttpResponseRedirect(reverse('tickets:stats_user'))
    return render(request, 'ticketing/order/form_paper.html',
                  {'tform': tform, "performance": str(performance)})


# QR codes
def qr_info(request, id, code):
    """QR information."""
    try:
        ticket = Ticket.objects.get(id=id)
    except ObjectDoesNotExist:
        raise Http404

    if code != ticket.code:
        raise Http404

    try:
        online_order = OnlineOrder.objects.get(id=ticket.order.id)
    except ObjectDoesNotExist:
        raise Http404

    if ("kassaticket" in code
            or online_order.performance.date.date() <= now().date()):
        # TODO: Add better redirect for program info...
        return redirect("./tickets/")

    return render(request, "ticketing/qr/info.html", {
        "ticket": ticket,
        "order": online_order,
    })


# Scanning
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def qr_scan(request):
    """Test a QR code."""
    return render(request, 'ticketing/qr/scan.html')


@csrf_exempt
def qr_reply(request):
    """Test a QR code."""
    code = request.POST.get('code', '')
    items = code.split("/")
    id = items[-3]
    hash_code = items[-2]
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
            elif ticket.order.performance.date.date() != now().date():
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
