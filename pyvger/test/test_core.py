import pytest

import pyvger
import pyvger.exceptions


def test_vger(mocker):
    mocker.patch('pyvger.core.sqla')
    mocker.patch('pyvger.core.cx')
    pyvger.core.Voy(oracleuser='foo', oraclepass='bar', oracledsn='baz')
    assert pyvger.core.cx.connect.called


def test_voy_bc(mocker):
    pytest.importorskip('win32com')
    mocker.patch('pyvger.batchcat.win32com')
    pyvger.core.Voy(voy_username='test', voy_password='test')
    assert pyvger.batchcat.win32com.client.Dispatch.called
