"""core pyvger objects"""
import cx_Oracle as cx
import pymarc
import sqlalchemy as sqla


class PyVgerException(Exception):
    pass


class BibRecord(object):
    """
    A voyager bibliographic record
    :param record: a valid MARC bibliographic record
    :param suppressed: boolean; whether the record is suppressed in OPAC
    :param bibid: bibliographic record ID
    :param voyager_interface: Voy object to which this record belongs
    """
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
        WHERE bib_mfhd.bib_id=:bib''' % {'db': self.interface.oracle_database},
                              {'bib': self.bibid})

        rv = []
        for rec in result:
            rv.append(self.interface.get_mfhd(rec[0]))

        return rv


class HoldingsRecord(object):
    """
    A single Voyager holding

    :param record: a valid MARC-encoded holdings record
    :param suppressed: boolean; whether record is suppressed in OPAC
    :param mfhdid: holdings ID in database
    :param voyager_interface: the Voy instance to which this record belongs
    :param location: textual code for the holding's location
    :param location_display_name: display name for the holding's location
    """

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
    """
    Interface to Voyager system

    :param oracle_database: database name prefix
    :param oracleuser: user name for Voyager Oracle account
    :param oraclepass: password for oracleuser account
    :param oracledsn: DSN used to connect to Oracle
    """

    def __init__(self, oracle_database="pittdb", **kwargs):
        self.connection = None
        self.oracle_database = oracle_database

        if all(arg in kwargs for arg in ['oracleuser', 'oraclepass',
                                         'oracledsn']):
            self.connection = cx.connect(kwargs['oracleuser'],
                                         kwargs['oraclepass'],
                                         kwargs['oracledsn'])
            self.engine = sqla.create_engine('oracle://',
                                             creator=lambda: self.connection)
        metadata = sqla.MetaData()
        tables_to_load = [
            'mfhd_master',
            'bib_location',
            'bib_master',
        ]
        self.tables = {}
        for table_name in tables_to_load:
            self.tables[table_name] = sqla.Table(table_name,
                                                 metadata,
                                                 schema=oracle_database,
                                                 autoload=True,
                                                 autoload_with=self.engine)

    def get_bib(self, bibid):
        """get a bibliographic record

        :param bibid: Voyager bibliographic record ID
        :return: pymarc.bib.VoyagerBib object
        """

        if self.connection:
            curs = self.connection.cursor()
            try:
                res = curs.execute('''SELECT
                utl_i18n.string_to_raw(bib_data.record_segment)
                as record_segment,
                bib_master.suppress_in_opac
                FROM %(db)s.bib_data, %(db)s.bib_master
                WHERE bib_data.bib_id = bib_master.bib_id AND
                bib_data.bib_id=:bib ORDER BY seqnum'''
                                   % {'db': self.oracle_database},
                                   {'bib': bibid})
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
                    raise PyVgerException("Bad suppression value %r for bib %s"
                                          % (data[1], bibid))
                return BibRecord(rec, suppress, bibid, self)

            except Exception:
                print("error for bibid |%r|" % bibid)
                raise

    def get_mfhd(self, mfhdid):
        """Get a HoldingsRecord object for the given Voyager mfhd number"""
        if self.connection:
            curs = self.connection.cursor()
            res = curs.execute('''SELECT utl_i18n.string_to_raw(record_segment)
             as record_segment,
             mfhd_master.suppress_in_opac,
             location.location_code,
             location.location_display_name
             FROM %(db)s.mfhd_data, %(db)s.mfhd_master, %(db)s.location
             WHERE mfhd_data.mfhd_id=:mfhd
             AND mfhd_data.mfhd_id = mfhd_master.mfhd_id
             AND location.location_id = mfhd_master.location_id
             ORDER BY seqnum''' % {'db': self.oracle_database},
                               {'mfhd': mfhdid})
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
                raise PyVgerException("Bad suppression value %r for mfhd %s" %
                                      (data[1], mfhdid))
            return HoldingsRecord(rec, suppress, mfhdid, self, data[2], data[3])

    def iter_mfhds(self, locations, include_suppressed=False):
        """Iterate over all of the holdings in the given locations

        :param locations: list of locations to iterate over
        :param include_suppressed: whether suppressed records should be included
        :return: iterator of HoldingsRecord objects

        """

        mm = self.tables['mfhd_master']
        q = mm.select(mm.c.location_id.in_(locations))
        if not include_suppressed:
            q = q.where(mm.c.suppress_in_opac == 'N')
        r = self.engine.execute(q)
        for row in r:
            yield self.get_mfhd(row[0])

    def iter_bibs(self, locations, include_suppressed=False):
        """Iterate over all of the bibs in the given locations

        :param locations: list of locations to iterate over
        :param include_suppressed: whether suppressed records should be included
        :return: iterator of BibRecord objects

        """

        bl = self.tables['bib_location']
        bm = self.tables['bib_master']
        q = bl.select(bl.c.location_id.in_(locations))
        if not include_suppressed:
            q = q.where(sqla.and_(bm.c.suppress_in_opac == 'N',
                                  bm.c.bib_id == bl.c.bib_id)
                        )
        r = self.engine.execute(q)
        for row in r:
            yield self.get_bib(row[0])
