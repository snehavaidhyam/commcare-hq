from __future__ import absolute_import, unicode_literals

import six
from django.http import HttpResponse
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from six.moves import range

from corehq.apps.case_search.const import (
    CASE_COMPUTED_METADATA,
    SPECIAL_CASE_PROPERTIES_MAP,
)
from corehq.apps.case_search.filter_dsl import CaseFilterError
from corehq.apps.es.case_search import CaseSearchES, flatten_result
from corehq.apps.reports.datatables import DataTablesColumn, DataTablesHeader
from corehq.apps.reports.exceptions import BadRequestError
from corehq.apps.reports.filters.case_list import CaseListFilter
from corehq.apps.reports.filters.select import (
    CaseTypeFilter,
    SelectOpenCloseFilter,
)
from corehq.apps.reports.standard.cases.basic import CaseListReport
from corehq.apps.reports.standard.cases.data_sources import SafeCaseDisplay
from corehq.apps.reports.standard.cases.filters import (
    CaseListExplorerColumns,
    XpathCaseSearchFilter,
)
from corehq.apps.reports.tasks import export_all_rows_with_progress
from corehq.elastic import iter_es_docs_from_query
from dimagi.utils.web import json_response
from soil import DownloadBase


class ExportProgressMixin(object):
    exportable = True
    exportable_all = True
    exportable_async = True

    progress_observer = None

    @property
    def export_response(self):
        task = export_all_rows_with_progress.delay(self.__class__, self.__getstate__())
        self.export_download_data.set_task(task)
        self.export_download_data.save()
        return HttpResponse()

    @property
    def export_download_data(self):
        download_data = DownloadBase.get(self.export_progress_key)
        if download_data is None:
            download_data = DownloadBase(download_id=self.export_progress_key)
        return download_data

    @property
    def export_progress_key(self):
        """Return a unique key for each "view" of the report
        """
        request_params = [
            (k, tuple(v) if isinstance(v, list) else v) for k, v in six.iteritems(self.request_params)
        ]
        download_id = "case_list_explorer.{domain}.{state}".format(
            domain=self.domain,
            state=hash(tuple(sorted(request_params)))
        )
        return download_id


class CaseListExplorer(ExportProgressMixin, CaseListReport):
    name = _('Case List Explorer')
    slug = 'case_list_explorer'
    search_class = CaseSearchES

    exportable = True
    exportable_all = True
    emailable = True
    _is_exporting = False

    fields = [
        XpathCaseSearchFilter,
        CaseListExplorerColumns,
        CaseListFilter,
        CaseTypeFilter,
        SelectOpenCloseFilter,
    ]

    def _build_query(self, sort=True):
        query = super(CaseListExplorer, self)._build_query()
        query = self._populate_sort(query, sort)
        xpath = XpathCaseSearchFilter.get_value(self.request, self.domain)
        if xpath:
            try:
                query = query.xpath_query(self.domain, xpath)
            except CaseFilterError as e:
                error = "<p>{}.</p>".format(escape(e))
                bad_part = "<p>{} <strong>{}</strong></p>".format(
                    _("The part of your search query we didn't understand is: "),
                    escape(e.filter_part)
                ) if e.filter_part else ""
                raise BadRequestError("{}{}".format(error, bad_part))
        return query

    def _populate_sort(self, query, sort):
        if not sort:
            # Don't sort on export
            query = query.set_sorting_block(['_doc'])
            return query

        num_sort_columns = int(self.request.GET.get('iSortingCols', 0))
        for col_num in range(num_sort_columns):
            descending = self.request.GET['sSortDir_{}'.format(col_num)] == 'desc'
            column_id = int(self.request.GET["iSortCol_{}".format(col_num)])
            column = self.headers.header[column_id]
            try:
                special_property = SPECIAL_CASE_PROPERTIES_MAP[column.prop_name]
                query = query.sort(special_property.sort_property, desc=descending)
            except KeyError:
                query = query.sort_by_case_property(column.prop_name, desc=descending)
        return query

    @property
    def columns(self):
        if self._is_exporting:
            persistent_cols = [
                DataTablesColumn(
                    "@case_id",
                    prop_name='@case_id',
                    sortable=True,
                )
            ]
        else:
            persistent_cols = [
                DataTablesColumn(
                    "case_name",
                    prop_name='case_name',
                    sortable=True,
                    visible=False,
                ),
                DataTablesColumn(
                    _("View Case"),
                    prop_name='_link',
                    sortable=False,
                )
            ]

        return persistent_cols + [
            DataTablesColumn(
                column,
                prop_name=column,
                sortable=column not in CASE_COMPUTED_METADATA,
            )
            for column in CaseListExplorerColumns.get_value(self.request, self.domain)
        ]

    @property
    def headers(self):
        column_names = [c.prop_name for c in self.columns]
        headers = DataTablesHeader(*self.columns)
        # by default, sort by name, otherwise we fall back to the case_name hidden column
        if "case_name" in column_names[1:]:
            headers.custom_sort = [[column_names[1:].index("case_name") + 1, 'asc']]
        elif "name" in column_names:
            headers.custom_sort = [[column_names.index("name"), 'asc']]
        else:
            headers.custom_sort = [[0, 'asc']]
        return headers

    @property
    def rows(self):
        data = self.es_results['hits'].get('hits', [])
        return self._get_rows(data)

    @property
    def get_all_rows(self):
        data = iter_es_docs_from_query(self._build_query(sort=False))
        return self._get_rows(data, update_progress=True)

    def _get_rows(self, data, update_progress=False):
        count = 0
        if update_progress:
            DownloadBase.set_progress(self.progress_observer, count, data.count)
        for case in (flatten_result(row) for row in data):
            case_display = SafeCaseDisplay(self, case)
            row = [
                case_display.get(column.prop_name)
                for column in self.columns
            ]
            count += 1
            if update_progress:
                DownloadBase.set_progress(self.progress_observer, count, data.count)
            yield row

    @property
    def export_table(self):
        self._is_exporting = True
        return super(CaseListExplorer, self).export_table


def get_export_progress(request, domain, download_id):
    return json_response(DownloadBase.get(download_id).get_progress())
