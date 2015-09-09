"""core pyvger objects"""
import cx_Oracle as cx
import pymarc


class PyVgerException(Exception):
    pass


class BibRecord(object):
    def __init__(self, record, suppressed, bibid, voyager_interface):
        self.record = record
        self.suppressed = suppressed
        self.bibid = bibid
        self.interface = voyager_interface

    def __getattr__(self, item):
        """Pass on attributes of the pymarc record"""
        if hasattr(self.record, item):
            return getattr(self.record, item)

    def __getitem__(self, item):
        """ Pass on item access for the pymarc record"""
        return self.record[item]

    def holdings(self):
        """get the holdings for this bibliographic record

        :return: a list of HoldingsRecord objects
        """
        curs = self.interface.connection.cursor()
        result = curs.execute('''SELECT mfhd_id
        FROM %(db)s.bib_mfhd
        WHERE bib_mfhd.bib_id=:bib''' % {'db': self.interface.oracle_database}, {'bib': self.bibid})

        rv = []
        for rec in result:
            rv.append(self.interface.get_mfhd(rec[0]))

        return rv


class HoldingsRecord(object):
    """A single Voyager holding"""

    def __init__(self, record, suppressed, mfhdid, voyager_interface, location,
                 location_display_name):
        self.record = record
        self.suppressed = suppressed
        self.mfhdid = mfhdid
        self.interface = voyager_interface
        self.location = location
        self.location_display_name = location_display_name

    def __getattr__(self, item):
        """Pass on attributes of the pymarc record"""
        if hasattr(self.record, item):
            return getattr(self.record, item)

    def __getitem__(self, item):
        """ Pass on item access for the pymarc record"""
        return self.record[item]


class Voy(object):
    """Interface to Voyager system"""

    def __init__(self, oracle_database="pittdb", *args, **kwargs):
        self.connection = None
        self.oracle_database = oracle_database

        if all(arg in kwargs for arg in ['oracleuser', 'oraclepass', 'oracledsn']):
            self.connection = cx.connect(kwargs['oracleuser'], kwargs['oraclepass'],
                                         kwargs['oracledsn'])


    def get_bib(self, bibid):
        """get a bibliographic record

        :param bibid: Voyager bibliographic record ID
        :return: pymarc.bib.VoyagerBib object
        """

        if self.connection:
            curs = self.connection.cursor()
            try:
                res = curs.execute('''SELECT utl_i18n.string_to_raw(bib_data.record_segment) as record_segment,
                bib_master.suppress_in_opac
                FROM %(db)s.bib_data, %(db)s.bib_master
                WHERE bib_data.bib_id = bib_master.bib_id AND bib_data.bib_id=:bib ORDER BY seqnum'''
                % {'db': self.oracle_database}, {'bib': bibid})
                marc_segments = []
                data = None
                for data in res:
                    marc_segments.append(data[0])
                marc = b''.join(marc_segments)
                rec = next(pymarc.MARCReader(marc))
                if data[1] == "Y":
                    suppress = True
                elif data[1] == "N":
                    suppress = False
                else:
                    raise PyVgerException("Bad suppression value %r for bib %s" % (data[1], bibid))
                return BibRecord(rec, suppress, bibid, self)

            except cx.DatabaseError:
                print("DB error for bibid |%r|" % bibid)
                raise

    def get_mfhd(self, mfhdid):
        """Get a HoldingsRecord object for the given Voyager mfhd number"""
        if self.connection:
            curs = self.connection.cursor()
            res = curs.execute('''SELECT utl_i18n.string_to_raw(record_segment) as record_segment,
             mfhd_master.suppress_in_opac,
             location.location_code,
             location.location_display_name
             FROM %(db)s.mfhd_data, %(db)s.mfhd_master, %(db)s.location
             WHERE mfhd_data.mfhd_id=:mfhd
             AND mfhd_data.mfhd_id = mfhd_master.mfhd_id
             AND location.location_id = mfhd_master.location_id
             ORDER BY seqnum'''% {'db': self.oracle_database}, {'mfhd': mfhdid})
            marc_segments = []
            for data in res:
                marc_segments.append(data[0])
            marc = b''.join(marc_segments)
            rec = next(pymarc.MARCReader(marc))
            if data[1] == "Y":
                suppress = True
            elif data[1] == "N":
                suppress = False
            else:
                raise PyVgerException("Bad suppression value %r for mfhd %s" % (data[1], mfhdid))
            return HoldingsRecord(rec, suppress, mfhdid, self, data[2], data[3])
