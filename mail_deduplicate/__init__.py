# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
# All Rights Reserved.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

""" Expose package-wide elements. """

import logging
import sys
from operator import methodcaller
from pathlib import Path

from boltons.ecoutils import get_profile
from boltons.iterutils import unique

# Canonical name of the CLI.
CLI_NAME = "mdedup"

__version__ = "6.2.1"


# Environment data.
env_data = get_profile(scrub=True)


# Initialize global logger.
logger = logging.getLogger(CLI_NAME)


# Ordered list of headers to use by default to compute the hash of a mail.
HASH_HEADERS = (
    "Date",
    "From",
    "To",
    # No Cc since mailman apparently sometimes trims list members from the Cc
    # header to avoid sending duplicates: https://mail.python.org/pipermail
    # /mailman-developers/2002-September/013233.html . But this means that
    # copies of mail reflected back from the list server will have a different
    # Cc to the copy saved by the MUA at send-time.
    # 'Cc',
    # No Bcc either since copies of the mail saved by the MUA at send-time
    # will have Bcc, but copies reflected back from the list server won't.
    # 'Bcc',
    # No Reply-To since a mail could be Cc'd to two lists with different
    # Reply-To munging options set.
    # 'Reply-To',
    "Subject",
    "MIME-Version",
    "Content-Type",
    "Content-Disposition",
    "User-Agent",
    "X-Priority",
    "Message-ID",
)


# Below this value, we consider not having enough data to compute a solid hash.
MINIMAL_HEADERS_COUNT = 4


# Since we're ignoring the Content-Length header for the reasons stated above,
# we limit the allowed difference between the sizes of the message payloads. If
# this is exceeded, a warning is issued and the messages are not considered
# duplicates, because this could point to message corruption somewhere, or a
# false positive. Note that the headers are not counted towards this threshold,
# because many headers can be added by mailing list software such as mailman,
# or even by the process of sending the mail through various MTAs - one copy
# could have been stored by the sender's MUA prior to sending, without any
# Received: headers, and another copy could be reflected back via a Cc-to-self
# mechanism or mailing list server. But this threshold has to be at least large
# enough to allow for footers added by mailing list servers.
DEFAULT_SIZE_THRESHOLD = 512  # bytes


# Similarly, we generated unified diffs of duplicates and ensure that the diff
# is not greater than a certain size.
DEFAULT_CONTENT_THRESHOLD = 768  # bytes


# Sources from which we compute a mail's canonical timestamp.
DATE_HEADER = "date-header"
CTIME = "ctime"
TIME_SOURCES = frozenset([DATE_HEADER, CTIME])


class TooFewHeaders(Exception):

    """ Not enough headers were found to produce a solid hash. """


class SizeDiffAboveThreshold(Exception):

    """ Difference in mail size is greater than threshold. """


class ContentDiffAboveThreshold(Exception):

    """ Difference in mail content is greater than threshold. """


class Config:

    """ Holds global configuration. """

    # Keep these defaults in sync with CLI option definitions.
    default_conf = {
        "dry_run": False,
        "input_format": False,
        "force_unlock": False,
        "hash_only": False,
        "hash_headers": HASH_HEADERS,
        "hash_body": None,
        "size_threshold": DEFAULT_SIZE_THRESHOLD,
        "content_threshold": DEFAULT_CONTENT_THRESHOLD,
        "show_diff": False,
        "strategy": None,
        "time_source": None,
        "regexp": None,
        "action": None,
        "export": None,
        "export_format": "mbox",
        "export_append": False,
    }

    def __init__(self, **kwargs):
        """ Validates configuration parameter types and values. """
        # Load default values.
        self.conf = self.default_conf.copy()

        unrecognized_options = set(kwargs) - set(self.default_conf)
        if unrecognized_options:
            raise ValueError(f"Unrecognized {unrecognized_options} options.")

        # Replace defaults values with our config.
        self.conf.update(kwargs)

        # Check thresholds.
        assert self.size_threshold >= -1
        assert self.content_threshold >= -1

        # Headers are case-insensitive in Python implementation.
        normalized_headers = [h.lower() for h in self.hash_headers]
        # Remove duplicate entries.
        normalized_headers = unique(normalized_headers)
        # Mail headers are composed of ASCII characters between 33 and 126
        # (both inclusive) according the RFC-5322.
        for hid in normalized_headers:
            ascii_indexes = set(map(ord, hid))
            assert max(ascii_indexes) <= 126
            assert min(ascii_indexes) >= 33
        self.hash_headers = tuple(normalized_headers)

        # Export mail box will always be created from scratch and is not
        # expected to exists in the first place.
        if self.export:
            self.export = Path(self.export).resolve()
            if self.export.exists() and self.export_append is not True:
                raise FileExistsError(self.export)

    def __getattr__(self, attr_id):
        """ Expose configuration entries as properties. """
        if attr_id in self.conf:
            return self.conf[attr_id]
