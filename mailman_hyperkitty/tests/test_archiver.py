# -*- coding: utf-8 -*-
# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
#
# This file is part of HyperKitty.
#
# HyperKitty is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# HyperKitty is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# HyperKitty.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#

# pylint: disable=protected-access,too-few-public-methods,no-self-use

import json
from unittest import TestCase

from mock import patch
from mailman.email.message import Message

from mailman_hyperkitty import Archiver


class FakeResponse:
    """Fake a response from the "requests" library"""

    def __init__(self, status_code, result):
        self.status_code = status_code
        self.result = result

    def json(self):
        return self.result

    @property
    def text(self):
        return json.dumps(self.result)


class FakeList:
    """Fake a Mailman list implementing the IMailingList interface"""

    def __init__(self, name):
        self.fqdn_listname = name


class ArchiverTestCase(TestCase):

    def setUp(self):
        self.archiver = Archiver()
        self.archiver._base_url = "http://lists.example.com"
        self.archiver._api_key = "DummyKey"
        self.mlist = FakeList("list@lists.example.com")
        # Patch requests
        self.requests_patcher = patch("mailman_hyperkitty.requests")
        self.requests = self.requests_patcher.start()
        self.fake_response = None
        self.requests.get.side_effect =  lambda url, *a, **kw: self.fake_response
        self.requests.post.side_effect = lambda url, *a, **kw: self.fake_response

    def tearDown(self):
        self.requests_patcher.stop()

    def _get_msg(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["Message-ID-Hash"] = "QKODQBCADMDSP5YPOPKECXQWEQAMXZL3"
        msg.set_payload("Dummy message")
        return msg


    def test_list_url(self):
        self.fake_response = FakeResponse(
            200, {"url": "/list/list@lists.example.com/"})
        self.assertEqual(self.archiver.list_url(self.mlist),
            "http://lists.example.com/list/list@lists.example.com/"
            )
        #print(self.requests.get.call_args_list)
        self.requests.get.assert_called_with(
            "http://lists.example.com/api/mailman/urls",
            params={'key': 'DummyKey', 'mlist': 'list@lists.example.com'}
        )

    def test_permalink(self):
        msg = self._get_msg()
        relative_url = "/list/list@lists.example.com/message/{}/".format(
            msg["Message-ID-Hash"])
        self.fake_response = FakeResponse(200, {"url": relative_url})
        self.assertEqual(self.archiver.permalink(self.mlist, msg),
            "http://lists.example.com" + relative_url)
        #print(self.requests.get.call_args_list)
        self.requests.get.assert_called_with(
            "http://lists.example.com/api/mailman/urls",
            params={'key': 'DummyKey', 'msgid': 'dummy',
                    'mlist': 'list@lists.example.com'}
        )

    def test_archive_message(self):
        msg = self._get_msg()
        relative_url = "/list/list@lists.example.com/message/{}/".format(
            msg["Message-ID-Hash"])
        self.fake_response = FakeResponse(200, {"url": relative_url})
        with patch("mailman_hyperkitty.logger") as logger:
            url = self.archiver.archive_message(self.mlist, msg)
            self.assertTrue(logger.info.called)
        self.assertEqual(url, "http://lists.example.com" + relative_url)
        #print(self.requests.post.call_args_list)
        self.requests.post.assert_called_with( # pylint: disable=no-member
            "http://lists.example.com/api/mailman/archive",
            params={'key': 'DummyKey'},
            data={'mlist': 'list@lists.example.com'},
            files={'message': ('message.txt', msg.as_string())},
        )

    def test_list_url_permalink_error(self):
        # Don't raise exceptions for list_url and permalink
        self.fake_response = FakeResponse(500, "Fake error")
        with patch("mailman_hyperkitty.logger") as logger:
            self.assertEqual(self.archiver.list_url(self.mlist), "")
            self.assertEqual(
                self.archiver.permalink(self.mlist, self._get_msg()), "")
            self.assertEqual(logger.error.call_count, 2)

    def test_archive_message_error(self):
        self.fake_response = FakeResponse(500, "Fake error")
        with patch("mailman_hyperkitty.logger") as logger:
            self.assertRaises(ValueError, self.archiver.archive_message,
                              self.mlist, self._get_msg())
            self.assertTrue(logger.error.called)
