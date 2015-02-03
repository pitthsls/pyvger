"""core pyvger objects"""
import cx_Oracle as cx
import pymarc


class PyVgerException(Exception):
    pass


class BibRecord(object):
    def __init__(self, record, suppressed, bibid, voyagerinterface):
        self.record = record
        self.suppressed = suppressed
        self.bibid = bibid
        self.interface = voyagerinterface

    def __getattr__(self, item):
        '''Pass on attributes of the pymarc record'''
        if hasattr(self.record, item):
            return getattr(self.record, item)

    def __getitem__(self, item):
        ''' Pass on item access for the pymarc record'''
        return self.record[item]


class Voy(object):
    """Interface to Voyager system"""
    def __init__(self, *args, **kwargs):
        self._connection = None

        if all(arg in kwargs for arg in ['oracleuser', 'oraclepass', 'oracledsn']):
            self._connection = cx.connect(kwargs['oracleuser'], kwargs['oraclepass'],
                                   kwargs['oracledsn'])


    def load_bib(self, bibid):
        """Get a pymarc.bib.VoyagerBib object for a given bib number"""
        if self._connection:
            curs = self._connection.cursor()
            try:
                res = curs.execute('''SELECT utl_i18n.string_to_raw(bib_data.record_segment) as record_segment,
                bib_master.suppress_in_opac
                FROM pittdb.bib_data, pittdb.bib_master
                WHERE bib_data.bib_id = bib_master.bib_id AND bib_data.bib_id=:bib ORDER BY seqnum''', {'bib': bibid})
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
                    raise PyVgerException("Bad suppression value %r for bib %s" % (data[1], bibid))
                return BibRecord(rec, suppress, bibid, self)

            except cx.DatabaseError:
                print("DB error for bibid |%r|" % bibid)
                raise

    def get_bib(self, bibid):
        """Get a pymarc.record.Record object for the given Voyager bib number"""
        bib_obj = self.load_bib(bibid)
        return bib_obj.record

    def get_mfhd(self, mfhdid):
        """Get a pymarc.record.Record object for the given Voyager mfhd number"""
        if self._connection:
            curs = self._connection.cursor()
            res = curs.execute('''SELECT utl_i18n.string_to_raw(record_segment) as record_segment
            FROM pittdb.mfhd_data
            WHERE mfhd_id=:mfhd ORDER BY seqnum''', {'mfhd': mfhdid})
            marc = b''.join(data[0] for data in res)
            rec = next(pymarc.MARCReader(marc))
            return rec
