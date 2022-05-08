"""Urls for user management."""

from django.urls import path
from . import views, view_stats, views_postermap
from django.views.generic import RedirectView

app_name = 'tickets'
urlpatterns = [
    path('', views.overview, name='overview'),
    path('concerts/', RedirectView.as_view(
        pattern_name='tickets:overview',
        permanent=False
    )),
    path('order/<int:id>/', views.order, name='order'),
    path('order/<int:id>/member/', views.order_paper, name='order_paper'),
    path('stats/personal/', view_stats.stats_user, name='stats_user'),
    path('stats/', view_stats.stats, name='stats'),

    # Scanning tickets
    path(r'qr/scan', views.qr_scan, name='qr_scan'),
    path(r'qr/reply', views.qr_reply, name='qr_reply'),
    path(r'qr/info/<int:id>/<slug:code>/', views.qr_info, name='qr_info'),

    # Set payed & send mail
    path(r'order/<int:id>/payed', views.send_order_payed, name='send_payed'),
    path(r'order/<int:id>/<slug:code>/', views.order_info, name='order_info'),
    path(r'order/download/<int:id>/<slug:code>/',
         views.download_tickets, name='order_download'),

    # Test mails
    path(r'test/<int:id>/', views.test_mail, name='test_mail'),
    path(r'test/<int:id>/qr', views.test_qr, name='test_qr'),
    path(r'test/<int:id>/qrmail', views.test_qr_mail, name='test_qr_mail'),

    # Export as CSV
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv'),
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv_online'),
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv_paper'),  # TODO

    path(r'postermap/', views_postermap.posters, name='posters'),
    path(r'postermap/add', views_postermap.add_poster, name='add_poster'),
]
