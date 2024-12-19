"""Urls for user management."""
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import path
from django.views.generic import RedirectView

import orchestra_ticketing.email
from payments import PAYnl
from . import views, view_stats, views_postermap

app_name = 'tickets'
urlpatterns = [
    path('', views.overview, name='overview'),
    path('concerts/', RedirectView.as_view(
        pattern_name='tickets:overview',
        permanent=False
    )),
    path('concerts/<str:name>/', views.production_overview, name='production_overview'),
    path('order/<int:id>/', views.order, name='order'),
    path('order/<int:id>/member/', views.order_paper, name='order_paper'),
    path('order/exchange', PAYnl.pay_order_exchange_view, name='order_exchange'),
    path('confirmation/<int:order_id>/', views.order_confirm, name='order_confirm'),
    path('stats/personal/', view_stats.stats_user, name='stats_user'),
    path('stats/', view_stats.stats, name='stats'),
    path('conditions', RedirectView.as_view(
        url=staticfiles_storage.url('ticketing/Algemene-verkoopsvoorwaarden-tickets.pdf'),
        permanent=False), name='order_conditions'),

    # Scanning tickets
    path(r'qr/scan', views.qr_scan, name='qr_scan'),
    path(r'qr/reply', views.qr_reply, name='qr_reply'),
    path(r'qr/info/<int:id>/<slug:code>/', views.qr_info, name='qr_info'),

    # Set paid & send mail
    path(r'order/<int:id>/paid', views.send_order_paid, name='send_paid'),
    path(r'order/<int:id>/<slug:code>/', views.order_info, name='order_info'),
    path(r'order/download/<int:id>/<slug:code>/',
         views.download_tickets, name='order_download'),

    # Test mails
    path(r'test/<int:id>/', orchestra_ticketing.email.test_mail, name='test_mail'),
    path(r'test/<int:id>/qr', views.test_qr, name='test_qr'),
    path(r'test/<int:id>/qrmail', views.test_qr_mail, name='test_qr_mail'),

    # Export as CSV
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv'),
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv_online'),
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv_paper'),  # TODO

    path(r'postermap/', views_postermap.posters, name='posters'),
    path(r'postermap/add', views_postermap.add_poster, name='add_poster'),
]
