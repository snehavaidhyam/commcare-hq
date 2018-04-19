from __future__ import absolute_import
from __future__ import unicode_literals
from couchdbkit import ChangesStream

from corehq.util.exceptions import DocumentClassNotFound
from pillowtop.dao.couch import CouchDocumentStore
from pillowtop.feed.interface import ChangeFeed, Change
from pillowtop.utils import force_seq_int


class CouchChangeFeed(ChangeFeed):

    def __init__(self, couch_db, couch_filter=None, extra_couch_view_params=None):
        self._couch_db = couch_db
        self._document_store = CouchDocumentStore(couch_db)
        self._couch_filter = couch_filter
        self._extra_couch_view_params = extra_couch_view_params or {}
        self._last_processed_seq = None

    def iter_changes(self, since, forever):
        extra_args = {'feed': 'continuous'} if forever else {}
        extra_args.update(self._extra_couch_view_params)
        self._last_processed_seq = since
        changes_stream = ChangesStream(
            db=self._couch_db,
            heartbeat=True,
            since=since,
            filter=self._couch_filter,
            include_docs=True,
            **extra_args
        )
        for couch_change in changes_stream:
            yield change_from_couch_row(couch_change, document_store=self._document_store)
            self._last_processed_seq = couch_change.get('seq', None)

    def get_processed_offsets(self):
        return {self._couch_db.dbname: force_seq_int(self._last_processed_seq)}

    def get_latest_offsets(self):
        return {self._couch_db.dbname: force_seq_int(get_current_seq(self._couch_db))}

    def get_latest_offsets_as_checkpoint_value(self):
        return str(get_current_seq(self._couch_db))

    @property
    def couch_db(self):
        return self._couch_db


def change_from_couch_row(couch_change, document_store=None):
    from corehq.apps.change_feed.data_sources import COUCH
    from corehq.apps.change_feed.document_types import (
        get_doc_meta_object_from_document, change_meta_from_doc_meta_and_document
    )
    from corehq.apps.change_feed.exceptions import MissingMetaInformationError
    from corehq.util.couchdb_management import couch_config

    doc_id = couch_change['id']
    document = couch_change.get('doc', None)
    if not document:
        assert document_store, "Document store required if doc not provided"
        document = document_store.get_document(doc_id)

    doc_meta = get_doc_meta_object_from_document(document)
    if document_store:
        data_source_name = document_store.data_source_name
    else:
        doc_type = doc_meta.raw_doc_type.split('-')[0]
        db = couch_config.get_db_for_doc_type(doc_type)
        data_source_name = db.dbname

    try:
        change_meta = change_meta_from_doc_meta_and_document(doc_meta, document, COUCH, data_source_name)
    except MissingMetaInformationError:
        change_meta = None

    return Change(
        id=doc_id,
        sequence_id=couch_change.get('seq', None),
        document=document,
        deleted=couch_change.get('deleted', False),
        document_store=document_store,
        metadata=change_meta
    )


def get_current_seq(couch_db):
    return couch_db.info()['update_seq']
