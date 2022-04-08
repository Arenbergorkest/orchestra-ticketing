"""Statistics pages."""

from datetime import datetime
import django.utils.timezone as django_tz
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.http import Http404, HttpResponse
from .models import Production, Performance, OnlineOrder, PaperOrder
from io import StringIO
import csv
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model


def to_timestamp(dt):
    """
    Convert to Javascript Date.UTC.

    Author: Thijs Boehme (Arenberg Orchestra)

    Function to convert Python time to Javascript Date.UTC()
    (milliseconds) for highcharts js.
    """
    epoch = django_tz.make_aware(
        datetime(1970, 1, 1), django_tz.get_default_timezone())
    return int((dt - epoch).total_seconds() * 1000)


@login_required
def stats_user(request):
    """
    Show personal statistics.

    Personal ticket dashboard:
        how many tickets did YOU sell?
        Only for performances of active productions.
    """
    data = {'orders': OnlineOrder.objects.filter(
        seller=request.user, performance__production__active=True),
        'total_price_orders': sum(
            [o.total_price for o in OnlineOrder.objects.filter(
                seller=request.user, performance__production__active=True)]),
        'total_num_orders': sum(
            [o.num_tickets for o in
             OnlineOrder.objects.filter(
                 seller=request.user, performance__production__active=True)]),
        'paid_paperorders': PaperOrder.objects.filter(
            seller=request.user, paid=True,
            performance__production__active=True),
        'total_price_paid_paperorders': sum(
            [o.total_price for o in PaperOrder.objects.filter(
                seller=request.user, paid=True,
                performance__production__active=True)]),
        'total_num_paid_paperorders': sum(
            [o.num_tickets for o in PaperOrder.objects.filter(
                seller=request.user, paid=True,
                performance__production__active=True)]),
        'unpaid_paperorders': PaperOrder.objects.filter(
            seller=request.user, paid=False),
        'total_price_unpaid_paperorders': sum(
            [o.total_price for o in PaperOrder.objects.filter(
                seller=request.user, paid=False)]),
        'total_num_unpaid_paperorders': sum(
            [o.num_tickets for o in PaperOrder.objects.filter(
                seller=request.user, paid=False)])}
    return render(request, 'ticketing/stats/user.html', data)


@login_required
def stats(request):
    """Stats for a performance."""
    graph_labels = []
    graph_datasets = []
    performances = []
    user_counts = {}

    productions = Production.objects.filter(active=True).prefetch_related(
        'performances__orders__tickets', 'performances__orders__seller')

    for production in productions:
        performances += list(production.performances.all())
    performances = sorted(performances, key=lambda obj: obj.date)

    # Getting ticket count for each of those performances, and the total count
    performance_ticket_counts = []
    performance_info = []

    for performance in performances:
        performance_ticket_count = 0

        for order in performance.orders.all():
            performance_ticket_count += len(order.tickets.all())

            # Getting user ranking
            if order.seller:
                if order.seller in user_counts:
                    user_counts[order.seller] += len(order.tickets.all())
                else:
                    user_counts[order.seller] = len(order.tickets.all())

        performance_ticket_counts.append(performance_ticket_count)
        performance_info.append([performance.date.strftime(
            '%d/%m'
        ), performance_ticket_count, performance.date.strftime('%a')])

        # Getting graph data
        graph_dataset = []
        total_tickets = 0
        orders = performance.orders.all()
        orders = sorted(orders, key=lambda obj: obj.date)
        if orders:
            graph_start = to_timestamp(orders[0].date)
        else:
            graph_start = to_timestamp(performance.date) - 5270400000
        graph_end = to_timestamp(performance.date)
        for order in orders:
            total_tickets += len(order.tickets.all())
            graph_dataset.append({
                'timestamp': to_timestamp(order.date),
                'num_new_tickets': order.num_tickets,
                'total_tickets': total_tickets,
                'order': order,
            })
        graph_datasets.append([
            performance.seats,
            performance.date.strftime('%a'),
            graph_dataset, graph_start, graph_end
        ])
        graph_labels.append(performance.date.strftime('%a'))

    # Getting user ranking
    user_ranks = []
    for user in user_counts.keys():
        user_ranks.append([str(user), user_counts[user]])
    user_ranks = sorted(user_ranks, key=lambda user: -user[1])[0:20]

    # Render template and pass all processed data
    return render(request, 'ticketing/stats/total.html', {
        'performance_counts': performance_info, 'user_counts': user_ranks,
        'graph_datasets': graph_datasets, 'graph_labels': graph_labels
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='inactive')
def csv_export(request, id):
    """CSV export."""
    try:
        performance = Performance.objects.get(id=id)
    except Exception:
        raise Http404

    online_orders = OnlineOrder.objects.filter(
        performance__id=id
    ).prefetch_related(
        'performance__price_categories', 'tickets__price_category'
    )
    price_categories = performance.price_categories.all()
    price_categories_names_list = list(
        map(lambda c: str(c.name).upper(), price_categories))

    # create the list/matrix which is to be written in the csv file,
    # and create the column titles
    list_output = [['voornaam', 'achternaam'] + price_categories_names_list +
                   ['totaaltickets', 'totaalprijs', 'betaalmethode', 'betaald',
                    'eerste concert',
                    'marketing feedback', 'verkoper',
                    'opmerkingen', 'email']]
    bool_words = {
        True: "ja", False: "neen", None: "?"
    }

    for online_order in online_orders:
        next_row = [online_order.first_name, online_order.last_name]

        # get count for sorts of tickets
        category_count_dictionary = dict((c, 0) for c in price_categories)
        for pricecategory in price_categories:
            for ticket in online_order.tickets.all():
                if ticket.price_category == pricecategory:
                    category_count_dictionary[pricecategory] += 1
        next_row += list(category_count_dictionary.values())
        next_row += [online_order.num_tickets, online_order.total_price,
                     online_order.payment_method,
                     online_order.payed,
                     bool_words.get(online_order.first_concert,
                                    online_order.first_concert),
                     online_order.marketing_feedback, online_order.seller,
                     online_order.remarks, online_order.email]
        # append the list_output with a list of the current order
        list_output.append(next_row)

    # create file like object in memory,
    # which can be written to and be returned
    buff = StringIO()
    writer = csv.writer(buff, delimiter=';')
    writer.writerows(list_output)
    response = HttpResponse(buff.getvalue(), content_type='text/csv')
    response[
        'content-disposition'
    ] = 'attachment; filename="online orders - {0}.csv"'.format(performance)
    return response


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/accessrestricted')
@user_passes_test(lambda u: u.is_active, login_url='/inactive')
def csv_paper_export(request, performance_id):
    """
    Create CSV paper payments.

    Creates a CSV file containing all needed ticketing information
    of the paper sales for a given performance.
    Passes a download response, without an accompanying template.
    """
    # If it isn't an active performance, raise 404
    try:
        performance = Performance.objects.filter(
            active=True).get(id=performance_id)
    except ObjectDoesNotExist:
        raise Http404

    paperOrders = PaperOrder.objects.filter(
        performance__id=performance_id).select_related(
            'performance__production', 'seller').prefetch_related(
                'performance__price_categories', 'tickets__price_category')
    price_categories = performance.price_categories.all()
    price_categories_names_list = list(
        map(lambda c: str(c.name).upper(), price_categories))

    # Create the list/matrix which is to be written in the csv file,
    # and create the column titles
    list_output = [['VERKOPER'] + price_categories_names_list +
                   ['TOTAALTICKETS', 'TOTAALPRIJS', 'TOTAAL REEDS BETAALD']]

    userDictionary = {}
    all_users = get_user_model().objects.all()

    for user in all_users:
        if user not in userDictionary:
            userDictionary[user] = {
                'tickets': {},
                'totalTickets': 0,
                'totalPrice': 0,
                'pricePaid': 0
            }
            userDictionary[user]['tickets'] = dict(
                (c, 0) for c in price_categories)

    for paperOrder in paperOrders:
        seller = paperOrder.seller
        if seller not in userDictionary:
            userDictionary[seller] = {
                'tickets': {},
                'totalTickets': 0,
                'totalPrice': 0,
                'pricePaid': 0
            }
            userDictionary[seller]['tickets'] = dict(
                (c, 0) for c in price_categories)

        category_count_dictionary = userDictionary[seller]['tickets']
        totalTickets = userDictionary[seller]['totalTickets']
        totalPrice = userDictionary[seller]['totalPrice']
        pricePaid = userDictionary[seller]['pricePaid']
        for priceCategory in price_categories:
            for ticket in paperOrder.tickets.all():
                if ticket.price_category == priceCategory:
                    category_count_dictionary[priceCategory] += 1
                    totalTickets += 1
                    totalPrice += ticket.price_category.price
        userDictionary[seller]['tickets'] = category_count_dictionary
        userDictionary[seller]['totalTickets'] = totalTickets
        userDictionary[seller]['totalPrice'] = totalPrice

        if paperOrder.paid:
            pricePaid += paperOrder.total_price
        userDictionary[seller]['pricePaid'] = pricePaid

    for user in sorted(
        userDictionary.keys(), key=lambda u: (u.first_name, u.last_name)
    ):
        next_row = [str(user)]
        for ticketCount in userDictionary[user]['tickets'].values():
            next_row += [ticketCount]
        next_row += [
            userDictionary[user]['totalTickets'],
            userDictionary[user]['totalPrice'],
            userDictionary[user]['pricePaid']
        ]

        list_output.append(next_row)

    # Create file like object in memory,
    # which can be written to and be returned
    buff = StringIO()
    writer = csv.writer(buff, delimiter=';')
    writer.writerows(list_output)
    response = HttpResponse(buff.getvalue(), content_type='text/csv')
    response[
        'Content-Disposition'
    ] = 'attachment; filename="Paper Orders - {0}.csv"'.format(performance)
    return response
