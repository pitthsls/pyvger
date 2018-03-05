"""Exceptions used by pyvger."""


class PyVgerException(Exception):
    """Generic exception."""

    pass


class BatchCatNotAvailableError(PyVgerException):
    """Batchcat isn't available; likely because extra wasn't installed."""

    pass


class NoSuchItemException(PyVgerException):
    """Item doesn't exist in Voyager."""

    pass
