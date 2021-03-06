"""Admin for a orchestra season."""

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from alumnisite.tools import ExportCsvMixin
from .models import Location, PriceCategory, Production, Performance, \
    Ticket, OnlineOrder


def change_active(parent, request, queryset, target_state=True,
                  single_word='item', multiple_word='items'):
    """Make active."""
    rows_updated = queryset.update(active=target_state)
    if rows_updated == 1:
        message_part = _("1 {name} was").format(name=single_word)
    else:
        message_part = _("{rows} {name} were").format(
            rows=rows_updated, name=multiple_word
        )

    if target_state:
        parent.message_user(
            request, _("{something} succesfully marked as active.").format(
                something=message_part
            )
        )
    else:
        parent.message_user(
            request, _("{something} succesfully marked as inactive.").format(
                something=message_part
            )
        )


@admin.register(Location)
class LocationAdmin(ModelAdmin):
    """Location."""

    list_display = ('name', 'description', 'address')


@admin.register(PriceCategory)
class PriceCategoryAdmin(ModelAdmin):
    """A Price category."""

    list_display = ('name', 'price')


class PerformanceInline(admin.TabularInline):
    """An inline performance."""

    model = Performance
    extra = 0


@admin.register(Production)
class ProductionAdmin(ModelAdmin):
    """A production."""

    list_display = ('name', 'description', 'active')
    inlines = [
        PerformanceInline,
    ]

    def make_active(self, request, queryset):
        """Make active."""
        change_active(self, request, queryset, True,
                      _('production'), _('productions'))

    def make_inactive(self, request, queryset):
        """Make inactive."""
        change_active(self, request, queryset, False,
                      _('production'), _('productions'))

    make_active.short_description = _("Make active")
    make_inactive.short_description = _("Make inactive")


@admin.register(Performance)
class PerformanceAdmin(ModelAdmin):
    """A performance."""

    list_display = ('production', 'date', 'location', 'seats', 'active')

    def make_active(self, request, queryset):
        """Make active."""
        change_active(self, request, queryset, True,
                      _('performance'), _('performances'))

    def make_inactive(self, request, queryset):
        """Make inactive."""
        change_active(self, request, queryset, False,
                      _('performance'), _('performances'))

    make_active.short_description = _("Make active")
    make_inactive.short_description = _("Make inactive")


class TicketInline(admin.TabularInline):
    """An inline ticket."""

    model = Ticket
    extra = 0


@admin.register(OnlineOrder)
class OnlineOrderAdmin(ModelAdmin, ExportCsvMixin):
    """Online order."""

    list_display = ('id', 'last_name', 'first_name', 'performance',
                    'num_tickets', 'total_price', 'payed', 'set_payed')
    search_fields = ('last_name', 'first_name', 'email')
    list_filter = ('performance', 'payed', 'performance__active')
    inlines = [
        TicketInline,
    ]
    actions = ['export_as_csv']

    def set_payed(self, obj):
        return format_html(
            "<a href='{url}'>Set Payed</a>", url=reverse(
                'tickets:send_payed', kwargs={'id': obj.id}
            )
        )

@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    """Tickets."""

    list_display = ('id', 'price_category', 'used')
    list_filter = ('order__performance', 'used')


