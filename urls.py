"""Urls for user management."""

from django.conf.urls import url, re_path
from orchestra_season import views, view_stats

app_name = 'tickets'
urlpatterns = [
    url(r'^$', views.overview, name='overview'),
    url(r'^order/(?P<id>\d+)/$', views.order, name='order'),
    url(r'^order/(?P<id>\d+)/member$', views.order_paper,
        name='order_paper'),
    url(r'^sold/(?P<id>\d+)/$', view_stats.stats_user, name='stats_user'),
    url(r'^stats/(?P<id>\d+)/$', view_stats.stats, name='stats'),

    # Scanning tickets
    url(r'^qr/scan$', views.qr_scan, name='qr_scan'),
    url(r'^qr/reply$', views.qr_reply, name='qr_reply'),
    re_path(r'^qr/info/(?P<id>\d+)/(?P<code>[a-z]+)$', views.qr_info,
            name='qr_info'),

    # Set payed & send mail
    url(r'^order/(?P<id>\d+)/payed$', views.send_order_payed,
        name='send_payed'),

    # Test mails
    url(r'^test/(?P<id>\d+)/$', views.test_mail, name='test_mail'),
    url(r'^test/(?P<id>\d+)/qr$', views.test_qr, name='test_qr'),
    url(r'^test/(?P<id>\d+)/qrmail$', views.test_qr_mail, name='test_qr_mail'),
    # Export as CSV
    url(r'^csv/(?P<id>\d+)/$', view_stats.csv_export, name='csv'),
]
