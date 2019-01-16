"""BatchCat interface (Windows Only; requires Voyager installation)."""
from pyvger.exceptions import BatchCatNotAvailableError, PyVgerException

try:
    import win32com.client
except ImportError:
    win32com = None
    raise BatchCatNotAvailableError


class BatchCatClient(object):
    """
    A connected batchcat client.

    :param username: Voyager cataloging username
    :param password: Voyager password
    :param apppath: path to Voyager installation

    The object has a ".bc" attribute on which BatchCat methods
    can be called, for example:

    client.bc.AddItemStatus(ItemID=12345, ItemStatusID=8)

    (For a complete list of methods available see the BatchCat
    manual that comes with Voyager)
    """

    def __init__(self, username, password, voy_interface, apppath=r"C:\Voyager"):

        self.voy_interface = voy_interface
        self.bc = win32com.client.Dispatch("BatchCat.ClassBatchCat")
        result = self.bc.Connect(AppPath=apppath, UserName=username, Password=password)
        if result[0]:
            raise PyVgerException("Connect error {}".format(result[0:3]))
