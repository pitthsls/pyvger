"""core pyvger objects"""
import cx_Oracle as cx
import pymarc


class Voy(object):
    """Interface to Voyager system"""
    def __init__(self, *args, **kwargs):
        self._connection = None

        if all(arg in kwargs for arg in ['oracleuser', 'oraclepass', 'oracledsn']):
            self._connection = cx.connect(kwargs['oracleuser'], kwargs['oraclepass'],
                                   kwargs['oracledsn'])

    def get_bib(self, bibid):
        """Get a pymarc.record.Record object for the given Voyager bib number"""
        if self._connection:
            curs = self._connection.cursor()
            try:
                res = curs.execute('''SELECT utl_i18n.string_to_raw(record_segment) as record_segment
                FROM pittdb.bib_data
                WHERE bib_id=:bib ORDER BY seqnum''', {'bib': bibid})
                marc = b''.join(data[0] for data in res)
                rec = next(pymarc.MARCReader(marc))
                return rec
            except cx.DatabaseError:
                print("DB error for bibid |%r|" % bibid)
                raise

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
