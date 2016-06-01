import unittest
from unittest import mock

from pyvger import core


class CoreTests(unittest.TestCase):
    @mock.patch('pyvger.core.sqla')
    @mock.patch('pyvger.core.cx')
    def test_vger(self, mockcx, mocksqla):
        vobj = core.Voy(oracleuser='foo', oraclepass='bar', oracledsn='baz')
        self.assertTrue(mockcx.connect.called)
