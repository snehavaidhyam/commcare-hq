from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url
from corehq.apps.export.views.download import (
    DownloadNewFormExportView,
    BulkDownloadNewFormExportView,
    DownloadNewCaseExportView,
    DownloadNewSmsExportView,
    add_export_email_request,
    has_multimedia,
    poll_custom_export_download,
    prepare_custom_export,
    prepare_form_multimedia,
)
from corehq.apps.export.views.edit import (
    EditNewCustomFormExportView,
    EditNewCustomCaseExportView,
    EditCaseFeedView,
    EditCaseDailySavedExportView,
    EditFormFeedView,
    EditFormDailySavedExportView,
)
from corehq.apps.export.views.list import (
    DailySavedExportListView,
    FormExportListView,
    CaseExportListView,
    commit_filters,
    DashboardFeedListView,
    DeIdFormExportListView,
    DeIdDailySavedExportListView,
    DeIdDashboardFeedListView,
    download_daily_saved_export,
    get_app_data_drilldown_values,
    get_saved_export_progress,
    submit_app_data_drilldown_form,
    toggle_saved_export_enabled,
    update_emailed_export_data,
)
from corehq.apps.export.views.new import (
    CreateNewCustomFormExportView,
    CreateNewCustomCaseExportView,
    CreateNewDailySavedCaseExport,
    CreateNewDailySavedFormExport,
    CreateNewCaseFeedView,
    CreateNewFormFeedView,
    CopyExportView,
    DeleteNewCustomExportView,
)
from corehq.apps.export.views.utils import (
    DashboardFeedPaywall,
    DailySavedExportPaywall,
    DataFileDownloadList,
    DataFileDownloadDetail,
)

urlpatterns = [
    # Export list views
    url(r"^custom/form/$",
        FormExportListView.as_view(),
        name=FormExportListView.urlname),
    url(r"^custom/form_deid/$",
        DeIdFormExportListView.as_view(),
        name=DeIdFormExportListView.urlname),
    url(r"^custom/daily_saved_deid/$",
        DeIdDailySavedExportListView.as_view(),
        name=DeIdDailySavedExportListView.urlname),
    url(r"^custom/feed_deid/$",
        DeIdDashboardFeedListView.as_view(),
        name=DeIdDashboardFeedListView.urlname),
    url(r"^custom/case/$",
        CaseExportListView.as_view(),
        name=CaseExportListView.urlname),
    url(r"^custom/daily_saved/$",
        DailySavedExportListView.as_view(),
        name=DailySavedExportListView.urlname),
    url(r"^custom/dashboard_feed/$",
        DashboardFeedListView.as_view(),
        name=DashboardFeedListView.urlname),
    url(r"^custom/download_data_files/$",
        DataFileDownloadList.as_view(),
        name=DataFileDownloadList.urlname),
    url(r"^custom/download_data_files/(?P<pk>[\w\-]+)/(?P<filename>.*)$",
        DataFileDownloadDetail.as_view(),
        name=DataFileDownloadDetail.urlname),

    # New export configuration views
    url(r"^custom/new/form/create$",
        CreateNewCustomFormExportView.as_view(),
        name=CreateNewCustomFormExportView.urlname),
    url(r"^custom/new/form_feed/create$",
        CreateNewFormFeedView.as_view(),
        name=CreateNewFormFeedView.urlname),
    url(r"^custom/new/form_daily_saved/create$",
        CreateNewDailySavedFormExport.as_view(),
        name=CreateNewDailySavedFormExport.urlname),
    url(r"^custom/new/case/create$",
        CreateNewCustomCaseExportView.as_view(),
        name=CreateNewCustomCaseExportView.urlname),
    url(r"^custom/new/case_feed/create$",
        CreateNewCaseFeedView.as_view(),
        name=CreateNewCaseFeedView.urlname),
    url(r"^custom/new/case_daily_saved/create$",
        CreateNewDailySavedCaseExport.as_view(),
        name=CreateNewDailySavedCaseExport.urlname),

    # Download views
    url(r"^custom/new/form/download/bulk/$",
        BulkDownloadNewFormExportView.as_view(),
        name=BulkDownloadNewFormExportView.urlname),
    url(r"^custom/new/form/download/(?P<export_id>[\w\-]+)/$",
        DownloadNewFormExportView.as_view(),
        name=DownloadNewFormExportView.urlname),
    url(r"^custom/new/case/download/(?P<export_id>[\w\-]+)/$",
        DownloadNewCaseExportView.as_view(),
        name=DownloadNewCaseExportView.urlname),
    url(r"^custom/dailysaved/download/(?P<export_instance_id>[\w\-]+)/$",
        download_daily_saved_export,
        name="download_daily_saved_export"),
    url(r"^custom/new/sms/download/$",
        DownloadNewSmsExportView.as_view(),
        name=DownloadNewSmsExportView.urlname),

    # Edit export views
    url(r"^custom/new/form/edit/(?P<export_id>[\w\-]+)/$",
        EditNewCustomFormExportView.as_view(),
        name=EditNewCustomFormExportView.urlname),
    url(r"^custom/form_feed/edit/(?P<export_id>[\w\-]+)/$",
        EditFormFeedView.as_view(),
        name=EditFormFeedView.urlname),
    url(r"^custom/form_daily_saved/edit/(?P<export_id>[\w\-]+)/$",
        EditFormDailySavedExportView.as_view(),
        name=EditFormDailySavedExportView.urlname),
    url(r"^custom/new/case/edit/(?P<export_id>[\w\-]+)/$",
        EditNewCustomCaseExportView.as_view(),
        name=EditNewCustomCaseExportView.urlname),
    url(r"^custom/case_feed/edit/(?P<export_id>[\w\-]+)/$",
        EditCaseFeedView.as_view(),
        name=EditCaseFeedView.urlname),
    url(r"^custom/case_daily_saved/edit/(?P<export_id>[\w\-]+)/$",
        EditCaseDailySavedExportView.as_view(),
        name=EditCaseDailySavedExportView.urlname),
    url(r"^custom/copy/(?P<export_id>[\w\-]+)/$",
        CopyExportView.as_view(),
        name=CopyExportView.urlname),
    url(r'^add_export_email_request/$', add_export_email_request, name='add_export_email_request'),
    url(r'^commit_filters/$', commit_filters, name='commit_filters'),
    url(r'^get_app_data_drilldown_values/$', get_app_data_drilldown_values, name='get_app_data_drilldown_values'),
    url(r'^get_saved_export_progress/$', get_saved_export_progress, name='get_saved_export_progress'),
    url(r'^has_multimedia/$', has_multimedia, name='has_multimedia'),
    url(r'^poll_custom_export_download/$', poll_custom_export_download, name='poll_custom_export_download'),
    url(r'^prepare_custom_export/$', prepare_custom_export, name='prepare_custom_export'),
    url(r'^prepare_form_multimedia/$', prepare_form_multimedia, name='prepare_form_multimedia'),
    url(r'^submit_app_data_drilldown_form/$', submit_app_data_drilldown_form,
        name='submit_app_data_drilldown_form'),
    url(r'^toggle_saved_export_enabled/$', toggle_saved_export_enabled, name='toggle_saved_export_enabled'),
    url(r'^update_emailed_export_data/$', update_emailed_export_data, name='update_emailed_export_data'),

    # Delete export views
    url(r"^custom/new/(?P<export_type>[\w\-]+)/delete/(?P<export_id>[\w\-]+)/$",
        DeleteNewCustomExportView.as_view(),
        name=DeleteNewCustomExportView.urlname),

    # Paywalls
    url(r"^dashboard_feed/paywall/$",
        DashboardFeedPaywall.as_view(),
        name=DashboardFeedPaywall.urlname),
    url(r"^daily_saved/paywall/$",
        DailySavedExportPaywall.as_view(),
        name=DailySavedExportPaywall.urlname),

    url(r"^build_full_schema/$",
        GenerateSchemaFromAllBuildsView.as_view(),
        name=GenerateSchemaFromAllBuildsView.urlname),
]
