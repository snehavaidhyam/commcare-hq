from __future__ import absolute_import
from __future__ import unicode_literals

import io

import six
from couchexport.export import export_raw
from couchexport.models import Format
from couchexport.shortcuts import export_response
from dimagi.utils.decorators.view import get_file
from dimagi.utils.logging import notify_exception
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext as _

from corehq.apps.app_manager.const import APP_TRANSLATION_UPLOAD_FAIL_MESSAGE
from corehq.apps.app_manager.dbaccessors import get_app
from corehq.apps.app_manager.decorators import no_conflict_require_POST, \
    require_can_edit_apps
from corehq.apps.app_manager.models import LinkedApplication
from corehq.apps.app_manager.ui_translations import process_ui_translation_upload, \
    build_ui_translation_download_file
from corehq.apps.translations.app_translations import (
    expected_bulk_app_sheet_headers,
    expected_bulk_app_sheet_rows,
    process_bulk_app_translation_upload,
    validate_bulk_app_translation_upload,
    read_uploaded_app_translation_file,
)
from corehq.util.workbook_json.excel import InvalidExcelFileException


@no_conflict_require_POST
@require_can_edit_apps
@get_file("bulk_upload_file")
def upload_bulk_ui_translations(request, domain, app_id):

    def _html_message(header_text, messages):
        message = header_text + "<br>"
        for prop in messages:
            message += "<li>%s</li>" % prop
        return message

    success = False
    try:
        app = get_app(domain, app_id)
        trans_dict, error_properties, warnings = process_ui_translation_upload(
            app, request.file
        )
        if error_properties:
            message = _html_message(_("Upload failed. We found problems with the following translations:"),
                                    error_properties)
            messages.error(request, message, extra_tags='html')
        else:
            # update translations only if there were no errors
            if isinstance(app, LinkedApplication):
                app.linked_app_translations.update(dict(trans_dict))
            app.translations.update(dict(trans_dict))
            app.save()
            success = True
            if warnings:
                message = _html_message(_("Upload succeeded, but we found following issues for some properties"),
                                        warnings)
                messages.warning(request, message, extra_tags='html')
    except InvalidExcelFileException as e:
        messages.error(request, _(APP_TRANSLATION_UPLOAD_FAIL_MESSAGE).format(e))
    except Exception:
        notify_exception(request, 'Bulk Upload Translations Error')
        messages.error(request, _("Something went wrong! Update failed. We're looking into it"))

    if success:
        messages.success(request, _("UI Translations Updated!"))

    # In v2, languages is the default tab on the settings page
    view_name = 'app_settings'
    return HttpResponseRedirect(reverse(view_name, args=[domain, app_id]))


@require_can_edit_apps
def download_bulk_ui_translations(request, domain, app_id):
    app = get_app(domain, app_id)
    temp = build_ui_translation_download_file(app)
    filename = '{app_name} v.{app_version} - CommCare Translations'.format(
        app_name=app.name,
        app_version=app.version)
    return export_response(temp, Format.XLS_2007, filename)


@require_can_edit_apps
def download_bulk_app_translations(request, domain, app_id):
    app = get_app(domain, app_id)
    headers = expected_bulk_app_sheet_headers(app)
    rows = expected_bulk_app_sheet_rows(app)
    temp = io.BytesIO()
    data = [(k, v) for k, v in six.iteritems(rows)]
    export_raw(headers, data, temp)
    filename = '{app_name} v.{app_version} - App Translations'.format(
        app_name=app.name,
        app_version=app.version)
    return export_response(temp, Format.XLS_2007, filename)


@no_conflict_require_POST
@require_can_edit_apps
@get_file("bulk_upload_file")
def upload_bulk_app_translations(request, domain, app_id):
    validate = request.POST.get('validate')
    app = get_app(domain, app_id)
    workbook, msgs = read_uploaded_app_translation_file(request.file)
    if workbook:
        if validate:
            msgs = validate_bulk_app_translation_upload(app, workbook, request.user.email)
        else:
            msgs = process_bulk_app_translation_upload(app, workbook)
            app.save()
    for msg in msgs:
        # Add the messages to the request object.
        # msg[0] should be a function like django.contrib.messages.error .
        # msg[1] should be a string.
        msg[0](request, msg[1])

    # In v2, languages is the default tab on the settings page
    view_name = 'app_settings'
    return HttpResponseRedirect(
        reverse(view_name, args=[domain, app_id])
    )
