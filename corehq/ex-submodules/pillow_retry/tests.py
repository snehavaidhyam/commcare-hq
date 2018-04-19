from __future__ import absolute_import
import sys
import uuid
from datetime import datetime

from django.conf import settings
from django.test import TestCase
from mock import MagicMock

from pillow_retry.models import PillowError
from pillowtop import get_all_pillow_configs
from pillowtop.checkpoints.manager import PillowCheckpoint
from pillowtop.dao.exceptions import DocumentMissingError
from pillowtop.feed.couch import change_from_couch_row
from pillowtop.feed.interface import Change, ChangeMeta
from pillowtop.feed.mock import RandomChangeFeed
from pillowtop.processors import PillowProcessor
from pillowtop.tests.utils import make_fake_constructed_pillow, FakeConstructedPillow
from six.moves import range


def get_ex_tb(message, ex_class=None):
    ex_class = ex_class if ex_class else ExceptionA
    try:
        raise ex_class(message)
    except Exception as e:
        return e, sys.exc_info()[2]


def FakePillow():
    return make_fake_constructed_pillow('FakePillow', 'fake-checkpoint')


def GetDocPillow():
    return FakeConstructedPillow(
        name='GetDocPillow',
        checkpoint=PillowCheckpoint('get_doc_processor', 'text'),
        change_feed=RandomChangeFeed(10),
        processor=GetDocProcessor(),
    )

class GetDocProcessor(PillowProcessor):
    """
    Processor that does absolutely nothing.
    """

    def process_change(self, pillow_instance, change):
        doc = change.get_document()
        if not change.deleted and not doc:
            raise Exception('missing doc')


def create_error(change, message='message', attempts=0, pillow=None, ex_class=None):
    change.metadata = ChangeMeta(data_source_type='couch', data_source_name='test_commcarehq', document_id=change.id)
    return PillowError.get_or_create(change, pillow or FakePillow())


class PillowRetryTestCase(TestCase):

    def setUp(self):
        PillowError.objects.all().delete()
        self._pillowtops = settings.PILLOWTOPS
        settings.PILLOWTOPS = {
            'tests': [
                'pillow_retry.tests.FakePillow',
                'pillow_retry.tests.GetDocPillow',
            ]
        }

    def tearDown(self):
        settings.PILLOWTOPS = self._pillowtops

    def test_id(self):
        id = '12345'
        change = Change(id=id, sequence_id=54321)
        error = create_error(change)
        self.assertEqual(error.doc_id, id)
        self.assertEqual(error.pillow, 'FakePillow')
        self.assertEqual(error.change_object.id, id)
        self.assertEqual(error.change_object.sequence_id, 54321)

    def test_get_or_create(self):
        message = 'abcd'
        id = '12335'
        error = create_error(_change(id=id), message=message, attempts=2)
        error.save()

        get = PillowError.get_or_create(_change(id=id), FakePillow())
        self.assertEqual(get.total_attempts, 2)
        self.assertEqual(get.current_attempt, 2)
        self.assertTrue(message in error.error_traceback)

        another_pillow = make_fake_constructed_pillow('FakePillow1', '')
        new = PillowError.get_or_create(_change(id=id), another_pillow)
        self.assertIsNone(new.id)
        self.assertEqual(new.current_attempt, 0)

    def test_deleted_doc(self):
        id = 'test_doc'
        error = create_error(_change(id))
        error.save()
        # this used to error out
        # process_pillow_retry(error.id) TODO

    def test_pillow_not_found(self):
        error = PillowError.objects.create(
            doc_id='missing-pillow',
            pillow='NotARealPillow',
            date_created=datetime.utcnow(),
            date_last_attempt=datetime.utcnow()
        )
        # make sure this doesn't error
        # process_pillow_retry(error.id) TODO

    def test_empty_metadata(self):
        change = _change(id='123')
        error = PillowError.get_or_create(change, GetDocPillow())
        error.save()

        # process_pillow_retry(error.id) TODO

        error = PillowError.objects.get(pk=error.id)
        self.assertEquals(error.total_attempts, 1)


class ExceptionA(Exception):
    pass


class PillowtopRetryAllPillowsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PillowtopRetryAllPillowsTests, cls).setUpClass()
        cls._PILLOWTOPS = settings.PILLOWTOPS
        if not settings.PILLOWTOPS:
            # assumes HqTestSuiteRunner, which blanks this out and saves a copy here
            settings.PILLOWTOPS = settings._PILLOWTOPS

    @classmethod
    def tearDownClass(cls):
        settings.PILLOWTOPS = cls._PILLOWTOPS
        super(PillowtopRetryAllPillowsTests, cls).tearDownClass()

    def tearDown(self):
        PillowError.objects.all().delete()

    def test_all_pillows_handle_errors(self):
        all_pillow_configs = list(get_all_pillow_configs())
        for pillow_config in all_pillow_configs:
            self._test_error_logging_for_pillow(pillow_config)

    def _test_error_logging_for_pillow(self, pillow_config):
        pillow = _pillow_instance_from_config_with_mock_process_change(pillow_config)
        if pillow.retry_errors:
            exc_class = Exception
            exc_class_string = 'exceptions.Exception'
        else:
            exc_class = DocumentMissingError
            exc_class_string = 'pillowtop.dao.exceptions.DocumentMissingError'

        pillow.process_change = MagicMock(side_effect=exc_class(pillow.pillow_id))
        doc = self._get_random_doc()
        pillow.process_with_error_handling(_change(doc['id'], doc))

        errors = PillowError.objects.filter(pillow=pillow.pillow_id).all()
        self.assertEqual(1, len(errors), pillow_config)
        error = errors[0]
        self.assertEqual(error.doc_id, doc['id'], pillow_config)
        self.assertEqual(exc_class_string, error.error_type)
        self.assertIn(pillow.pillow_id, error.error_traceback)

    def _get_random_doc(self):
        return {
            'id': uuid.uuid4().hex,
            'doc_type': 'CommCareCase',
            'type': 'mother',
            'domain': 'pillow-retry-domain',
        }


def _pillow_instance_from_config_with_mock_process_change(pillow_config):
    pillow_class = pillow_config.get_class()
    if pillow_config.instance_generator is None:
        instance = pillow_class()
    else:
        instance = pillow_config.get_instance()

    return instance


def _change(id, doc=None):
    return Change(id=id, sequence_id=None, document=doc, metadata=ChangeMeta(
        document_id=id,
        data_source_type='couch',
        data_source_name='commcarehq',
    ))
