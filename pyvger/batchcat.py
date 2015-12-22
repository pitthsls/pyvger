"""BatchCat interface (Windows Only; requires Voyager installation"""


class BatchCatNotAvailableError(Exception):
    pass


try:
    import win32com.client
except ImportError:
    raise BatchCatNotAvailableError


class BatchCatClient(object):
    def __init__(self, username, password, apppath=r'C:\Voyager'):
        """
        a connected batchcat client
        :param username: Voyager cataloging username
        :param password: Voyager password
        :param apppath: path to Voyager installation
        """
        self.bc = win32com.client.Dispatch("BatchCat.ClassBatchCat")
        self.bc.Connect(AppPath=apppath, UserName=username, Password=password)
