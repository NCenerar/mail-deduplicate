# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2017 Kevin Deldycke <kevin@deldycke.com>
#                         and contributors.
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

from .case import CLITestCase


class TestCLI(CLITestCase):

    def test_main_help(self):
        result = self.invoke("--help")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--help", result.output)


class TestDeduplicateCLI(CLITestCase):

    def test_deduplicate_help(self):
        result = self.invoke("deduplicate", "--help")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--help", result.output)

    def test_nonexistent_directory(self):
        result = self.invoke("deduplicate", "./dummy_maildir/")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("""Path './dummy_maildir/' does not exist""", result.output)

    def test_invalid_maildir_as_file(self):
        result = self.invoke("deduplicate", "./__init__.py")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("""Path './__init__.py' does not exist""", result.output)

    def test_invalid_maildir_structure(self):
        result = self.invoke("deduplicate", ".")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("is not a maildir", result.output)
