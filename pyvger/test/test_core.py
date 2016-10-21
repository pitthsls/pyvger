import mock

from pyvger import core


@mock.patch('pyvger.core.sqla')
@mock.patch('pyvger.core.cx')
def test_vger(mockcx, mocksqla):
    core.Voy(oracleuser='foo', oraclepass='bar', oracledsn='baz')
    assert mockcx.connect.called
