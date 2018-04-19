from __future__ import absolute_import

from datetime import datetime

from django.db import models
from django.db.models.aggregates import Count
from jsonfield.fields import JSONField

from pillowtop.feed.interface import ChangeMeta, Change

ERROR_MESSAGE_LENGTH = 512


def _get_extra_args(limit, reduce, skip):
    extra_args = dict()
    if not reduce and limit is not None:
            extra_args.update(
                limit=limit,
                skip=skip
            )
    return extra_args


def path_from_object(obj):
    path = "{0}.{1}".format(obj.__class__.__module__, obj.__class__.__name__)
    return path


class PillowError(models.Model):
    doc_id = models.CharField(max_length=255, null=False, db_index=True)
    pillow = models.CharField(max_length=255, null=False, db_index=True)
    date_created = models.DateTimeField()
    date_last_attempt = models.DateTimeField()
    total_attempts = models.IntegerField(default=0)
    error_type = models.CharField(max_length=255, null=True, db_index=True)
    error_traceback = models.TextField(null=True)
    change = JSONField(null=True)
    change_metadata = JSONField(null=True)

    @property
    def change_object(self):
        from corehq.apps.change_feed.data_sources import get_document_store
        change_meta = document_store = None
        if self.change_metadata:
            change_meta = ChangeMeta.wrap(self.change_metadata)
            document_store = get_document_store(
                data_source_type=change_meta.data_source_type,
                data_source_name=change_meta.data_source_name,
                domain=change_meta.domain
            )
            document_store = document_store

        change_dict = self.change or {}
        return Change(
            id=self.doc_id,
            sequence_id=change_dict.get('seq'),
            deleted=change_dict.get('deleted'),
            document_store=document_store,
            metadata=change_meta
        )

    class Meta(object):
        app_label = 'pillow_retry'
        unique_together = ('doc_id', 'pillow',)

    @classmethod
    def get_or_create(cls, change, pillow):
        change.document = None
        doc_id = change.id
        try:
            error = cls.objects.get(doc_id=doc_id, pillow=pillow.pillow_id)
        except cls.DoesNotExist:
            error = PillowError(
                doc_id=doc_id,
                pillow=pillow.pillow_id,
                date_created=datetime.utcnow(),
                change=change.to_dict()
            )

        error.date_last_attempt = change.metadata.date_last_attempt
        error.total_attempts = change.metadata.attempts
        error.error_type = change.metadata.last_error_type
        error.error_traceback = change.metadata.last_error_traceback
        error.change_metadata = change.metadata.to_json()

        error.save()
        return error

    @classmethod
    def get_pillows(cls):
        results = PillowError.objects.values('pillow').annotate(count=Count('pillow'))
        return (p['pillow'] for p in results)

    @classmethod
    def get_error_types(cls):
        results = PillowError.objects.values('error_type').annotate(count=Count('error_type'))
        return (e['error_type'] for e in results)


# Stub models file, also used in tests
from dimagi.ext.couchdbkit import Document


class Stub(Document):
    pass
