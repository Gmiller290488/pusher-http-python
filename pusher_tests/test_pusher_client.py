# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import os
import six
import hmac
import json
import hashlib
import unittest
import time
from decimal import Decimal

from pusher.pusher_client import PusherClient
from pusher.http import GET
from pusher.signature import sign

try:
    import unittest.mock as mock
except ImportError:
    import mock

class TestPusherClient(unittest.TestCase):
    def setUp(self):
        self.pusher_client = PusherClient(app_id=u'4', key=u'key', secret=u'secret', host=u'somehost')

    def test_host_should_be_text(self):
        PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, host=u'foo')

        self.assertRaises(TypeError, lambda: PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, host=4))

    def test_cluster_should_be_text(self):
        PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, cluster=u'eu')

        self.assertRaises(TypeError, lambda: PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, cluster=4))

    def test_host_behaviour(self):
        conf = PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True)
        self.assertEqual(conf.host, u'api.pusherapp.com', u'default host should be correct')

        conf = PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, cluster=u'eu')
        self.assertEqual(conf.host, u'api-eu.pusher.com', u'host should be overriden by cluster setting')

        conf = PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, host=u'foo')
        self.assertEqual(conf.host, u'foo', u'host should be overriden by host setting')

        conf = PusherClient(app_id=u'4', key=u'key', secret=u'secret', ssl=True, cluster=u'eu', host=u'plah')
        self.assertEqual(conf.host, u'plah', u'host should be used in preference to cluster')

    def test_trigger_with_channels_list_success_case(self):
        json_dumped = u'{"message": "hello world"}'

        with mock.patch('json.dumps', return_value=json_dumped) as json_dumps_mock:
            request = self.pusher_client.trigger.make_request([u'some_channel'], u'some_event', {u'message': u'hello world'})

            self.assertEqual(request.path, u'/apps/4/events')
            self.assertEqual(request.method, u'POST')

            expected_params = {
                u'channels': [u'some_channel'],
                u'data': json_dumped,
                u'name': u'some_event'
            }

            self.assertEqual(request.params, expected_params)

        # FIXME: broken
        #json_dumps_mock.assert_called_once_with({u'message': u'hello world'})

    def test_trigger_with_channel_string_success_case(self):
        json_dumped = u'{"message": "hello worlds"}'

        with mock.patch('json.dumps', return_value=json_dumped) as json_dumps_mock:

            request = self.pusher_client.trigger.make_request(u'some_channel', u'some_event', {u'message': u'hello worlds'})

            expected_params = {
                u'channels': [u'some_channel'],
                u'data': json_dumped,
                u'name': u'some_event'
            }

            self.assertEqual(request.params, expected_params)

    def test_trigger_batch_success_case(self):
        json_dumped = u'{"message": "something"}'

        with mock.patch('json.dumps', return_value=json_dumped) as json_dumps_mock:

            request = self.pusher_client.trigger_batch.make_request([{
                        u'channel': u'my-chan',
                        u'name': u'my-event',
                        u'data': {u'message': u'something'}
                    }])

            expected_params = {
                u'batch': [{
                    u'channel': u'my-chan',
                    u'name': u'my-event',
                    u'data': json_dumped
                }]
            }

            self.assertEqual(request.params, expected_params)


    def test_trigger_disallow_non_string_or_list_channels(self):
        self.assertRaises(TypeError, lambda:
            self.pusher_client.trigger.make_request({u'channels': u'test_channel'}, u'some_event', {u'message': u'hello world'}))

    def test_trigger_disallow_invalid_channels(self):
        self.assertRaises(ValueError, lambda:
            self.pusher_client.trigger.make_request([u'so/me_channel!'], u'some_event', {u'message': u'hello world'}))

    def test_channels_info_default_success_case(self):
        request = self.pusher_client.channels_info.make_request()

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels')
        self.assertEqual(request.params, {})

    def test_channels_info_with_prefix_success_case(self):
        request = self.pusher_client.channels_info.make_request(prefix_filter='test')

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels')
        self.assertEqual(request.params, {u'filter_by_prefix': u'test'})

    def test_channels_info_with_attrs_success_case(self):
        request = self.pusher_client.channels_info.make_request(attributes=[u'attr1', u'attr2'])

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels')
        self.assertEqual(request.params, {u'info': u'attr1,attr2'})

    def test_channel_info_success_case(self):
        request = self.pusher_client.channel_info.make_request(u'some_channel')

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels/some_channel')
        self.assertEqual(request.params, {})

    def test_channel_info_with_attrs_success_case(self):
        request = self.pusher_client.channel_info.make_request(u'some_channel', attributes=[u'attr1', u'attr2'])

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels/some_channel')
        self.assertEqual(request.params, {u'info': u'attr1,attr2'})

    def test_user_info_success_case(self):
        request = self.pusher_client.users_info.make_request(u'presence-channel')

        self.assertEqual(request.method, GET)
        self.assertEqual(request.path, u'/apps/4/channels/presence-channel/users')
        self.assertEqual(request.params, {})

    def test_authenticate_for_private_channels(self):
        pusher = Pusher.from_url(u'http://foo:bar@host/apps/4')

        expected = {
            u'auth': u"foo:89955e77e1b40e33df6d515a5ecbba86a01dc816a5b720da18a06fd26f7d92ff"
        }

        self.assertEqual(pusher.authenticate(u'private-channel', u'345.23'), expected)

    def test_authenticate_types(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        self.assertRaises(TypeError, lambda: pusher.authenticate(2423, u'34554'))
        self.assertRaises(TypeError, lambda: pusher.authenticate(u'plah', 234234))
        self.assertRaises(ValueError, lambda: pusher.authenticate(u'::', u'345345'))

    def test_authenticate_for_presence_channels(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        custom_data = {
            u'user_id': u'fred',
            u'user_info': {
                u'key': u'value'
            }
        }

        expected = {
            u'auth': u"foo:e80ba6439492c2113022c39297a87a948de14061cc67b5788e045645a68b8ccd",
            u'channel_data': u"{\"user_id\":\"fred\",\"user_info\":{\"key\":\"value\"}}"
        }

        with mock.patch('json.dumps', return_value=expected[u'channel_data']) as dumps_mock:
            actual = pusher.authenticate(u'presence-channel', u'345.43245', custom_data)

        self.assertEqual(actual, expected)
        dumps_mock.assert_called_once_with(custom_data, cls=None)

    def test_validate_webhook_success_case(self):
        pusher = Pusher.from_url(u'http://foo:bar@host/apps/4')

        body = u'{"time_ms": 1000000}'
        signature = six.text_type(hmac.new(pusher.secret.encode('utf8'), body.encode('utf8'), hashlib.sha256).hexdigest())

        with mock.patch('time.time', return_value=1200):
            self.assertEqual(pusher.validate_webhook(pusher.key, signature, body), {u'time_ms': 1000000})

    def test_validate_webhook_bad_types(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        pusher.validate_webhook(u'key', u'signature', u'body')

        # These things are meant to be human readable, so enforcing being text is
        # sensible.

        with mock.patch('time.time') as time_mock:
            self.assertRaises(TypeError, lambda: pusher.validate_webhook(4, u'signature', u'body'))
            self.assertRaises(TypeError, lambda: pusher.validate_webhook(u'key', 4, u'body'))
            self.assertRaises(TypeError, lambda: pusher.validate_webhook(u'key', u'signature', 4))

        time_mock.assert_not_called()

    def test_validate_webhook_bad_key(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        body = u'some body'
        signature = six.text_type(hmac.new(pusher.secret.encode(u'utf8'), body.encode(u'utf8'), hashlib.sha256).hexdigest())

        with mock.patch('time.time') as time_mock:
            self.assertEqual(pusher.validate_webhook(u'badkey', signature, body), None)

        time_mock.assert_not_called()

    def test_validate_webhook_bad_signature(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        body = u'some body'
        signature = u'some signature'

        with mock.patch('time.time') as time_mock:
            self.assertEqual(pusher.validate_webhook(pusher.key, signature, body), None)

        time_mock.assert_not_called()

    def test_validate_webhook_bad_time(self):
        pusher = PusherClient.from_url(u'http://foo:bar@host/apps/4')

        body = u'{"time_ms": 1000000}'
        signature = six.text_type(hmac.new(pusher.secret.encode('utf8'), body.encode('utf8'), hashlib.sha256).hexdigest())

        with mock.patch('time.time', return_value=1301):
            self.assertEqual(pusher.validate_webhook(pusher.key, signature, body), None)

if __name__ == '__main__':
    unittest.main()
