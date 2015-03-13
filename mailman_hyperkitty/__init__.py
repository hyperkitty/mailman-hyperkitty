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

"""
Class implementation of Mailman's IArchiver interface
This will be imported by Mailman Core and must thus be Python3-compatible.
"""

from __future__ import absolute_import, unicode_literals

from urllib.parse import urljoin

from zope.interface import implementer
from mailman.interfaces.archiver import IArchiver
from mailman.config import config
from mailman.config.config import external_configuration
import requests

import logging
logger = logging.getLogger("mailman.archiver")


@implementer(IArchiver)
class Archiver(object):

    name = "hyperkitty"

    def __init__(self):
        self._base_url = None
        self._api_key = None

    @property
    def base_url(self):
        # Not running _load_conf() on init makes it easier to test:
        # no valid mailman config is required
        if self._base_url is None:
            self._load_conf()
        return self._base_url

    @property
    def api_key(self):
        # Not running _load_conf() on init makes it easier to test:
        # no valid mailman config is required
        if self._api_key is None:
            self._load_conf()
        return self._api_key

    def _load_conf(self):
        """
        Find the location of the Django settings module from Mailman's
        configuration file, and load it to get the store's URL.
        """
        # Read our specific configuration file
        archiver_config = external_configuration(
                config.archiver.hyperkitty.configuration)
        self._base_url = archiver_config.get("general", "base_url")
        if not self._base_url.endswith("/"): # pylint: disable=no-member
            self._base_url += "/"
        self._api_key = archiver_config.get("general", "api_key")

    def _get_url(self, params):
        params.update({"key": self.api_key})
        url = urljoin(self.base_url, "api/mailman/urls")
        result = requests.get(url, params=params)
        if result.status_code != 200:
            logger.error("HyperKitty failure on %s: %s (%s)",
                         url, result.text, result.status_code)
            return ""
        try:
            result = result.json()
        except ValueError as e:
            logger.exception(
                "Invalid response from HyperKitty on %s: %s", url, e)
            return ""
        return urljoin(self.base_url, result["url"])

    def list_url(self, mlist):
        """Return the url to the top of the list's archive.

        :param mlist: The IMailingList object.
        :returns: The url string.
        """
        return self._get_url({"mlist": mlist.fqdn_listname})

    def permalink(self, mlist, msg):
        """Return the url to the message in the archive.

        This url points directly to the message in the archive.  This method
        only calculates the url, it does not actually archive the message.

        :param mlist: The IMailingList object.
        :param msg: The message object.
        :returns: The url string or None if the message's archive url cannot
            be calculated.
        """
        msg_id = msg['Message-Id'].strip().strip("<>")
        return self._get_url({"mlist": mlist.fqdn_listname, "msgid": msg_id})

    def archive_message(self, mlist, msg):
        """Send the message to the archiver.

        :param mlist: The IMailingList object.
        :param msg: The message object.
        :returns: The url string or None if the message's archive url cannot
            be calculated.
        """
        url = urljoin(self.base_url, "api/mailman/archive")
        result = requests.post(url, params={"key": self.api_key},
            data={"mlist": mlist.fqdn_listname},
            files={"message": ("message.txt", msg.as_string())})
        if result.status_code != 200:
            logger.error("HyperKitty failure on %s: %s (%s)",
                         url, result.text, result.status_code)
            raise ValueError(result.text)
        try:
            result = result.json()
        except ValueError as e:
            logger.exception(
                "Invalid response from HyperKitty on %s: %s", url, e)
            raise
        archived_url = urljoin(self.base_url, result["url"])
        logger.info("HyperKitty archived message %s to %s",
                    msg['Message-Id'].strip(), archived_url)
        return archived_url
