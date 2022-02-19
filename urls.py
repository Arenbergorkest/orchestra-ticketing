"""Urls for user management."""

from django.urls import path
from orchestra_season import views, view_stats

app_name = 'tickets'
urlpatterns = [
    path('', views.overview, name='overview'),
    path('order/<int:id>/', views.order, name='order'),
    path('order/<int:id>/member/', views.order_paper, name='order_paper'),
    path(r'sold/<int:id>/', view_stats.stats_user, name='stats_user'),
    path(r'stats/<int:id>/', view_stats.stats, name='stats'),

    # Scanning tickets
    path(r'qr/scan', views.qr_scan, name='qr_scan'),
    path(r'qr/reply', views.qr_reply, name='qr_reply'),
    path(r'qr/info/<int:id>/<slug:code>/', views.qr_info, name='qr_info'),

    # Set payed & send mail
    path(r'order/<int:id>/payed', views.send_order_payed, name='send_payed'),

    # Test mails
    path(r'test/<int:id>/', views.test_mail, name='test_mail'),
    path(r'test/<int:id>/qr', views.test_qr, name='test_qr'),
    path(r'test/<int:id>/qrmail', views.test_qr_mail, name='test_qr_mail'),
    # Export as CSV
    path(r'csv/<int:id>/', view_stats.csv_export, name='csv'),
]
