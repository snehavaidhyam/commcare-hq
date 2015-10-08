from collections import namedtuple
from dimagi.utils.decorators.memoized import memoized
from django.utils.translation import ugettext as _, ugettext_lazy
from django.utils.decorators import method_decorator
from no_exceptions.exceptions import Http400

from corehq.toggles import SUPPLY_REPORTS
from corehq.apps.commtrack.models import StockState
from corehq.apps.locations.models import SQLLocation
from corehq.apps.products.models import SQLProduct
from corehq.apps.reports.datatables import DataTablesHeader, DataTablesColumn

from .const import STOCK_SECTION_TYPE
from corehq.apps.reports.generic import GenericTabularReport
from corehq.apps.reports.commtrack.standard import CommtrackReportMixin

LocationLedger = namedtuple('Row', "location stock")


class LedgersByLocationDataSource(object):
    """
    Data source for a report showing ledger values at each location.

                   | Product 1 | Product 2 |
        Location 1 |        76 |        11 |
        Location 2 |       132 |        49 |
    """

    def __init__(self, domain, section_id):
        self.domain = domain
        self.section_id = section_id

    @property
    @memoized
    def products(self):
        if SQLProduct.objects.filter(domain=self.domain).count() > 20:
            raise Http400("This domain has too many products.")
        return list(SQLProduct.objects.filter(domain=self.domain).order_by('name'))

    @property
    @memoized
    def location_ledgers(self):
        def get_location_ledger(location):
            stock = (StockState.objects
                     .filter(section_id=self.section_id,
                             sql_location=location)
                     .values_list('sql_product__product_id', 'stock_on_hand'))
            return LocationLedger(
                location,
                {product_id: soh for product_id, soh in stock}
            )

        locations = SQLLocation.objects.filter(domain=self.domain).order_by('name')
        return map(get_location_ledger, locations)

    @property
    def rows(self):
        for ledger in self.location_ledgers:
            yield [ledger.location.name] + [
                ledger.stock.get(p.product_id, 0) for p in self.products
            ]

    @property
    def headers(self):
        return [_("Location")] + [p.name for p in self.products]


class LedgersByLocationReport(GenericTabularReport, CommtrackReportMixin):
    name = ugettext_lazy('Ledgers By Location')
    slug = 'ledgers_by_location'
    ajax_pagination = False
    fields = [
        'corehq.apps.reports.filters.fixtures.AsyncLocationFilter',
        'corehq.apps.reports.dont_use.fields.SelectProgramField',
    ]

    @method_decorator(SUPPLY_REPORTS.required_decorator())
    def dispatch(self, *args, **kwargs):
        return super(LedgersByLocationReport, self).dispatch(*args, **kwargs)

    @staticmethod
    def show_in_navigation(domain, project, user=None):
        return project.commtrack_enabled and SUPPLY_REPORTS.enabled(domain)

    @property
    @memoized
    def data(self):
        return LedgersByLocationDataSource(
            domain=self.domain,
            section_id=STOCK_SECTION_TYPE,
        )

    @property
    def headers(self):
        return DataTablesHeader(
            *[DataTablesColumn(header) for header in self.data.headers]
        )

    @property
    def rows(self):
        return self.data.rows
