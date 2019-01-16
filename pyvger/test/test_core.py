"""Test suite for core module."""

import pytest

import pyvger
import pyvger.exceptions


def test_vger(mocker):
    """Test creating the Voy object."""
    mocker.patch("pyvger.core.sqla")
    mocker.patch("pyvger.core.cx")
    pyvger.core.Voy(oracleuser="foo", oraclepass="bar", oracledsn="baz")
    assert pyvger.core.cx.connect.called


def test_voy_bc(mocker):
    """Test creating the Voy object with BatchCat available."""
    pytest.importorskip("win32com")
    mocker.patch("pyvger.batchcat.win32com", return_value=(0, []))
    pyvger.core.Voy(voy_username="test", voy_password="test")
    assert pyvger.batchcat.win32com.client.Dispatch.called
