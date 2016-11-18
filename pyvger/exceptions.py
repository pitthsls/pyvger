"""exceptions used by pyvger"""


class PyVgerException(Exception):
    pass


class BatchCatNotAvailableError(PyVgerException):
    pass


class NoSuchItemException(PyVgerException):
    pass
