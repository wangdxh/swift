# Copyright (c) 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest
import uuid

from swift.common.container_sync_realms import ContainerSyncRealms
from test.unit import FakeLogger, temptree


class TestUtils(unittest.TestCase):

    def test_no_file_there(self):
        unique = uuid.uuid4().hex
        logger = FakeLogger()
        csr = ContainerSyncRealms(unique, logger)
        self.assertEqual(
            logger.lines_dict,
            {'debug': [
                "Could not load '%s': [Errno 2] No such file or directory: "
                "'%s'" % (unique, unique)]})
        self.assertEqual(csr.mtime_check_interval, 300)
        self.assertEqual(csr.realms(), [])

    def test_os_error(self):
        fname = 'container-sync-realms.conf'
        fcontents = ''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            os.chmod(tempdir, 0)
            csr = ContainerSyncRealms(fpath, logger)
            try:
                self.assertEqual(
                    logger.lines_dict,
                    {'error': [
                        "Could not load '%s': [Errno 13] Permission denied: "
                        "'%s'" % (fpath, fpath)]})
                self.assertEqual(csr.mtime_check_interval, 300)
                self.assertEqual(csr.realms(), [])
            finally:
                os.chmod(tempdir, 0700)

    def test_empty(self):
        fname = 'container-sync-realms.conf'
        fcontents = ''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(logger.lines_dict, {})
            self.assertEqual(csr.mtime_check_interval, 300)
            self.assertEqual(csr.realms(), [])

    def test_error_parsing(self):
        fname = 'container-sync-realms.conf'
        fcontents = 'invalid'
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(
                logger.lines_dict,
                {'error': [
                    "Could not load '%s': File contains no section headers.\n"
                    "file: %s, line: 1\n"
                    "'invalid'" % (fpath, fpath)]})
            self.assertEqual(csr.mtime_check_interval, 300)
            self.assertEqual(csr.realms(), [])

    def test_one_realm(self):
        fname = 'container-sync-realms.conf'
        fcontents = '''
[US]
key = 9ff3b71c849749dbaec4ccdd3cbab62b
cluster_dfw1 = http://dfw1.host/v1/
'''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(logger.lines_dict, {})
            self.assertEqual(csr.mtime_check_interval, 300)
            self.assertEqual(csr.realms(), ['US'])
            self.assertEqual(csr.key('US'), '9ff3b71c849749dbaec4ccdd3cbab62b')
            self.assertEqual(csr.key2('US'), None)
            self.assertEqual(csr.clusters('US'), ['DFW1'])
            self.assertEqual(
                csr.endpoint('US', 'DFW1'), 'http://dfw1.host/v1/')

    def test_two_realms_and_change_a_default(self):
        fname = 'container-sync-realms.conf'
        fcontents = '''
[DEFAULT]
mtime_check_interval = 60

[US]
key = 9ff3b71c849749dbaec4ccdd3cbab62b
cluster_dfw1 = http://dfw1.host/v1/

[UK]
key = e9569809dc8b4951accc1487aa788012
key2 = f6351bd1cc36413baa43f7ba1b45e51d
cluster_lon3 = http://lon3.host/v1/
'''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(logger.lines_dict, {})
            self.assertEqual(csr.mtime_check_interval, 60)
            self.assertEqual(sorted(csr.realms()), ['UK', 'US'])
            self.assertEqual(csr.key('US'), '9ff3b71c849749dbaec4ccdd3cbab62b')
            self.assertEqual(csr.key2('US'), None)
            self.assertEqual(csr.clusters('US'), ['DFW1'])
            self.assertEqual(
                csr.endpoint('US', 'DFW1'), 'http://dfw1.host/v1/')
            self.assertEqual(csr.key('UK'), 'e9569809dc8b4951accc1487aa788012')
            self.assertEqual(
                csr.key2('UK'), 'f6351bd1cc36413baa43f7ba1b45e51d')
            self.assertEqual(csr.clusters('UK'), ['LON3'])
            self.assertEqual(
                csr.endpoint('UK', 'LON3'), 'http://lon3.host/v1/')

    def test_empty_realm(self):
        fname = 'container-sync-realms.conf'
        fcontents = '''
[US]
'''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(logger.lines_dict, {})
            self.assertEqual(csr.mtime_check_interval, 300)
            self.assertEqual(csr.realms(), ['US'])
            self.assertEqual(csr.key('US'), None)
            self.assertEqual(csr.key2('US'), None)
            self.assertEqual(csr.clusters('US'), [])
            self.assertEqual(csr.endpoint('US', 'JUST_TESTING'), None)

    def test_bad_mtime_check_interval(self):
        fname = 'container-sync-realms.conf'
        fcontents = '''
[DEFAULT]
mtime_check_interval = invalid
'''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(
                logger.lines_dict,
                {'error': [
                    "Error in '%s' with mtime_check_interval: invalid literal "
                    "for int() with base 10: 'invalid'" % fpath]})
            self.assertEqual(csr.mtime_check_interval, 300)

    def test_get_sig(self):
        fname = 'container-sync-realms.conf'
        fcontents = ''
        with temptree([fname], [fcontents]) as tempdir:
            logger = FakeLogger()
            fpath = os.path.join(tempdir, fname)
            csr = ContainerSyncRealms(fpath, logger)
            self.assertEqual(
                csr.get_sig(
                    'GET', '/some/path', '1387212345.67890', 'my_nonce',
                    'realm_key', 'user_key'),
                '5a6eb486eb7b44ae1b1f014187a94529c3f9c8f9')


if __name__ == '__main__':
    unittest.main()
