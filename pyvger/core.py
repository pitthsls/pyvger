"""core pyvger objects."""
from decimal import Decimal
import warnings

import arrow

import cx_Oracle as cx

import pymarc

import six.moves.configparser as configparser

import sqlalchemy as sqla

from pyvger.constants import RELATIONS, TABLE_NAMES
from pyvger.exceptions import (
    BatchCatNotAvailableError,
    NoSuchItemException,
    PyVgerException,
)

try:
    from pyvger import batchcat
except BatchCatNotAvailableError:
    batchcat = None


class Voy(object):
    """
    Interface to Voyager system.

    :param oracle_database: database name prefix
    :param config: configuration file path
    :param oracleuser: user name for Voyager Oracle account
    :param oraclepass: password for oracleuser account
    :param oracledsn: DSN used to connect to Oracle
    :param voy_username: Voyager username to login via BatchCat
    :param voy_password: Voyager password to login via BatchCat
    :param voy_path: path to directory containing Voyager.ini for BatchCat
    :param cat_location: location name of cataloging location
    :param library_id: library ID number
    """

    def __init__(self, oracle_database="pittdb", config=None, **kwargs):
        self.connection = None
        self.oracle_database = oracle_database
        cfg = {}
        if config is not None:
            cf = configparser.ConfigParser()
            cf.read(config)
            config_keys = [
                "oracleuser",
                "oraclepass",
                "oracledsn",
                "voy_username",
                "voy_password",
                "voy_path",
                "cat_location",
                "library_id",
            ]
            for item in config_keys:
                val = cf.get("Voyager", item, fallback="", raw=True).strip('"')
                if val:
                    cfg[item] = val
            if cf.get("Voyager", "connectstring") and "oracledsn" not in cfg:
                cfg["oracledsn"] = cf.get("Voyager", "connectstring", raw=True).strip(
                    '"'
                )

        cfg.update(kwargs)

        if all(arg in cfg for arg in ["oracleuser", "oraclepass", "oracledsn"]):
            self.connection = cx.connect(
                cfg["oracleuser"], cfg["oraclepass"], cfg["oracledsn"]
            )
            self.engine = sqla.create_engine(
                "oracle://", creator=lambda: self.connection
            )
            metadata = sqla.MetaData()
            tables_to_load = TABLE_NAMES

            self.tables = {}
            for table_name in tables_to_load:
                self.tables[table_name] = sqla.Table(
                    table_name,
                    metadata,
                    schema=oracle_database,
                    autoload=True,
                    autoload_with=self.engine,
                )

            for parent, foreign in RELATIONS:
                parent_column = getattr(self.tables[parent[0]].c, parent[1])
                foreign_key = getattr(self.tables[foreign[0]].c, foreign[1])
                parent_column.append_foreign_key(sqla.ForeignKey(foreign_key))

        self.cat_location = cfg.get("cat_location")
        self.library_id = cfg.get("library_id")

        if "voy_path" not in cfg:
            cfg["voy_path"] = r"C:\Voyager"

        if batchcat is not None and all(
            arg in cfg for arg in ["voy_username", "voy_password"]
        ):
            self.batchcat = batchcat.BatchCatClient(
                username=cfg["voy_username"],
                password=cfg["voy_password"],
                voy_interface=self,
                apppath=cfg["voy_path"],
            )
        else:
            self.batchcat = None

    def get_raw_bib(self, bibid):
        """Get raw MARC for a bibliographic record.

        :param bibid:
        :return: bytes of bib record
        """
        if self.connection:
            curs = self.connection.cursor()
            res = curs.execute(
                """SELECT
            utl_i18n.string_to_raw(bib_data.record_segment)
            as record_segment
            FROM %(db)s.bib_data
            WHERE bib_data.bib_id=:bib ORDER BY seqnum"""
                % {"db": self.oracle_database},
                {"bib": bibid},
            )
            marc_segments = []
            for data in res:
                marc_segments.append(data[0])
            return b"".join(marc_segments)

    def get_bib(self, bibid):
        """Get a bibliographic record.

        :param bibid: Voyager bibliographic record ID
        :return: pyvger.core.BibRecord object
        """
        if self.connection:
            curs = self.connection.cursor()
            try:
                res = curs.execute(
                    """SELECT DISTINCT utl_i18n.string_to_raw(bib_data.record_segment) as record_segment,
                bib_master.suppress_in_opac, MAX(action_date) over (partition by bib_history.bib_id) maxdate,
                bib_data.seqnum FROM %(db)s.BIB_HISTORY JOIN %(db)s.bib_master
                on bib_history.bib_id = bib_master.bib_id JOIN %(db)s.bib_data
                ON bib_master.bib_id = bib_data.bib_id WHERE bib_history.BIB_ID = :bib
                ORDER BY seqnum"""
                    % {"db": self.oracle_database},
                    {"bib": bibid},
                )
                marc_segments = []
                data = None
                for data in res:
                    marc_segments.append(data[0])
                marc = b"".join(marc_segments)
                if not marc:
                    raise PyVgerException("No MARC data for bib %s" % bibid)
                rec = next(pymarc.MARCReader(marc))
                if data[1] == "Y":
                    suppress = True
                elif data[1] == "N":
                    suppress = False
                else:
                    raise PyVgerException(
                        "Bad suppression value %r for bib %s" % (data[1], bibid)
                    )
                last_date = arrow.get(data[2]).datetime
                return BibRecord(rec, suppress, bibid, self, last_date)

            except Exception:
                print("error for bibid |%r|" % bibid)
                raise

    def get_mfhd(self, mfhdid):
        """Get a HoldingsRecord object for the given Voyager mfhd number.

        :param mfhdid: Voyager holdings ID to fetch
        :return:
        """
        if self.connection:
            curs = self.connection.cursor()
            res = curs.execute(
                """SELECT DISTINCT utl_i18n.string_to_raw(record_segment)
             as record_segment,
             mfhd_master.suppress_in_opac,
             location.location_code,
             location.location_display_name,
             MAX(action_date) over (partition by mfhd_history.mfhd_id) maxdate,
             mfhd_data.seqnum
             FROM %(db)s.mfhd_data, %(db)s.mfhd_master, %(db)s.location, %(db)s.mfhd_history
             WHERE mfhd_data.mfhd_id=:mfhd
             AND mfhd_data.mfhd_id = mfhd_master.mfhd_id
             AND location.location_id = mfhd_master.location_id
             AND mfhd_history.mfhd_id = mfhd_master.mfhd_id
             ORDER BY seqnum"""
                % {"db": self.oracle_database},
                {"mfhd": mfhdid},
            )
            marc_segments = []
            data = None
            for data in res:
                marc_segments.append(data[0])
            marc = b"".join(marc_segments)
            if not marc:
                raise PyVgerException("No MARC data for MFHD %s" % mfhdid)
            rec = next(pymarc.MARCReader(marc))
            if data[1] == "Y":
                suppress = True
            elif data[1] == "N":
                suppress = False
            else:
                raise PyVgerException(
                    "Bad suppression value %r for mfhd %s" % (data[1], mfhdid)
                )
            last_date = arrow.get(data[4]).datetime
            return HoldingsRecord(
                rec, suppress, mfhdid, self, data[2], data[3], last_date
            )

    def iter_mfhds(self, locations=None, lib_id=None, include_suppressed=False):
        """Iterate over all of the holdings in the given locations.

        You must provide exactly one of locations or lib_id

        :param locations: list of locations to iterate over
        :param lib_id: library ID to iterate over instead of using locations
        :param include_suppressed: whether suppressed records should be included
        :return: iterator of HoldingsRecord objects

        """
        mm = self.tables["mfhd_master"]
        if locations and lib_id is None:
            where_clause = mm.c.location_id.in_(locations)
        elif lib_id:
            where_clause = sqla.and_(
                self.tables["location"].c.library_id == lib_id,
                mm.c.location_id == self.tables["location"].c.location_id,
            )
        else:
            raise ValueError("must provide locations or lib_id, and not both")
        if not include_suppressed:
            where_clause = sqla.and_(mm.c.suppress_in_opac == "N", where_clause)
        q = sqla.select([mm.c.mfhd_id], whereclause=where_clause).order_by(mm.c.mfhd_id)
        r = self.engine.execute(q)
        for row in r:
            try:
                yield self.get_mfhd(row[0])
            except PyVgerException:
                warnings.warn("Skipping record %s" % row[0])

    def iter_bibs(self, locations=None, lib_id=None, include_suppressed=False):
        """Iterate over all of the bibs in the given locations.

        You must provide exactly one of locations or lib_id.

        :param locations: list of locations to iterate over
        :param lib_id: library ID to iterate over instead of using locations
        :param include_suppressed: whether suppressed records should be included
        :return: iterator of BibRecord objects

        """
        bl = self.tables["bib_location"]
        bm = self.tables["bib_master"]
        if locations and lib_id is None:
            q = bl.select(bl.c.location_id.in_(locations))
        elif lib_id:
            q = bm.select(bm.c.library_id == lib_id)
        else:
            raise ValueError("must provide locations or lib_id, and not both")
        if not include_suppressed:
            q = q.where(
                sqla.and_(bm.c.suppress_in_opac == "N", bm.c.bib_id == bl.c.bib_id)
            )
        r = self.engine.execute(q)
        for row in r:
            try:
                yield self.get_bib(row[0])
            except UnicodeDecodeError:
                continue

    def iter_items(
        self, locations, include_temporary=False, include_suppressed_mfhd=False
    ):
        """Iterate over the item records in one or more locations.

        :param locations: list of locations to iterate over
        :param include_temporary: bool whether to include items with temporary locations in locations list
        :param include_suppressed_mfhd: bool, whether to include items attached to a suppressed MFHD
        """
        item_table = self.tables["item"]
        where_clause = item_table.c.perm_location.in_(locations)
        if include_temporary:
            where_clause = sqla.or_(
                where_clause, item_table.c.temp_location.in_(locations)
            )
        if not include_suppressed_mfhd:
            where_clause = sqla.and_(
                self.tables["mfhd_master"].c.suppress_in_opac == "N", where_clause
            )
        q = sqla.select(
            [item_table.c.item_id],
            whereclause=where_clause,
            from_obj=[
                item_table.join(self.tables["mfhd_item"]).join(
                    self.tables["mfhd_master"]
                )
            ],
        )
        r = self.engine.execute(q)
        for row in r:
            yield self.get_item(row[0])

    def get_item(self, item_id=None, barcode=None):
        """
        Get an item record from Voyager.

        :param int item_id:
        :param str barcode:
        :return: ItemRecord -- the item
        """
        if item_id is not None:
            return ItemRecord.from_id(item_id, self)
        else:
            return ItemRecord.from_barcode(barcode, self)

    def get_item_statuses(self, item_id):
        """
        Get the statuses from a single item.

        :param int item_id:
        :return: list(str) -- statuses
        """
        query = (
            sqla.sql.select([self.tables["item_status_type"].c.item_status_desc])
            .select_from(
                self.tables["item_status"].join(self.tables["item_status_type"])
            )
            .where(self.tables["item_status"].c.item_id == item_id)
        )
        r = self.engine.execute(query)
        return [row[0] for row in r]

    def bib_id_for_item(self, item_id):
        """
        Get the bibliographic record ID associated with an item record.

        :param int item_id: the Voyager item ID
        :return: int: the bib ID
        """
        query = (
            sqla.sql.select([self.tables["bib_mfhd"].c.bib_id])
            .select_from(self.tables["mfhd_item"].join(self.tables["bib_mfhd"]))
            .where(self.tables["mfhd_item"].c.item_id == item_id)
        )

        result = self.engine.execute(query)
        (row,) = result
        return row[0]

    def get_bib_create_datetime(self, bib_id):
        """Get date when a record was added.

        :param int bib_id: the Voyager bib id
        :return: datetime.datetime: when the record was added
        """
        bmt = self.tables["bib_master"]
        query = bmt.select().where(bmt.c.bib_id == bib_id)
        result = self.engine.execute(query)
        (row,) = result
        return row.create_date

    def get_location_id(self, location):
        """Get numeric ID for location.

        :param location: Voyager location code
        :return: int: numeric location id
        """
        query = (
            self.tables["location"]
            .select()
            .where(self.tables["location"].c.location_code == location)
        )
        result = self.engine.execute(query)
        (row,) = result
        return int(row.location_id)


class BibRecord(object):
    """
    A voyager bibliographic record.

    :param record: a valid MARC bibliographic record
    :param suppressed: boolean; whether the record is suppressed in OPAC
    :param bibid: bibliographic record ID
    :param voyager_interface: Voy object to which this record belongs
    :param last_date: datetime.datetime of last update from BIB_HISTORY table

    WARNING: last_date should have its tzinfo set to UTC even if the naive time in the database is "really"
    from another timezone. The Voyager database doesn't know what timezone is being used, and the
    win32com methods used for BatchCat will convert non-UTC datetimes to UTC, then the server
    will ignore the TZ and fail because it thinks your datetime is off by your local offset.
    """

    def __init__(self, record, suppressed, bibid, voyager_interface, last_date=None):
        self.record = record
        self.suppressed = suppressed
        self.bibid = bibid
        self.last_date = last_date
        self.interface = voyager_interface

    def __getattr__(self, item):
        """Pass on attributes of the pymarc record."""
        if hasattr(self.record, item):
            return getattr(self.record, item)

    def __getitem__(self, item):
        """Pass on item access for the pymarc record."""
        return self.record[item]

    def holdings(self):
        """Get the holdings for this bibliographic record.

        :return: a list of HoldingsRecord objects
        """
        curs = self.interface.connection.cursor()
        result = curs.execute(
            """SELECT mfhd_id
        FROM %(db)s.bib_mfhd
        WHERE bib_mfhd.bib_id=:bib"""
            % {"db": self.interface.oracle_database},
            {"bib": self.bibid},
        )

        rv = []
        for rec in result:
            rv.append(self.interface.get_mfhd(rec[0]))

        return rv


class HoldingsRecord(object):
    """
    A single Voyager holding.

    :param record: a valid MARC-encoded holdings record
    :param suppressed: boolean; whether record is suppressed in OPAC
    :param mfhdid: holdings ID in database
    :param voyager_interface: the Voy instance to which this record belongs
    :param location: textual code for the holding's location
    :param location_display_name: display name for the holding's location
    :param last_date: datetime.datetime of last update from BIB_HISTORY table

    WARNING: last_date should have its tzinfo set to UTC even if the naive time in the database is "really"
    from another timezone. The Voyager database doesn't know what timezone is being used, and the
    win32com methods used for BatchCat will convert non-UTC datetimes to UTC, then the server
    will ignore the TZ and fail because it thinks your datetime is off by your local offset.
    """

    def __init__(
        self,
        record,
        suppressed,
        mfhdid,
        voyager_interface,
        location,
        location_display_name,
        last_date,
    ):
        self.record = record
        self.suppressed = suppressed
        self.mfhdid = mfhdid
        self.interface = voyager_interface
        self.location = location
        self.location_display_name = location_display_name
        self.last_date = last_date

    def __getattr__(self, item):
        """Pass on attributes of the pymarc record."""
        if hasattr(self.record, item):
            return getattr(self.record, item)

    def __getitem__(self, item):
        """Pass on item access for the pymarc record."""
        return self.record[item]

    def get_items(self):
        """Return a list of ItemRecords for the holding's items."""
        mi_table = self.interface.tables["mfhd_item"]
        query = sqla.select([mi_table.c.item_id]).where(
            mi_table.c.mfhd_id == self.mfhdid
        )
        res = self.interface.engine.execute(query)
        try:
            return [self.interface.get_item(i[0]) for i in res]
        except NoSuchItemException:
            print("failed for mfhd %s" % self.mfhdid)
            raise

    def get_bib(self):
        """Return the bib record to which this holding is attached."""
        return self.interface.get_bib(self.record["004"].data)


class ItemRecord(object):
    """A Voyager item.

    :param int holding_id: indicates MFHD number for  an item being added
    :param int item_id: indicates Voyager number of item record being updated
    :param int item_type_id: indicates valid item type ID from item_type table
    :param int perm_location_id: indicates valid Voyager location of an item
    :param bool add_item_to_top:
    :param str caption:
    :param str chron:
    :param int copy_number:
    :param str enumeration:
    :param str free_text:
    :param int media_type_id:
    :param int piece_count:
    :param str price:
    :param str spine_label:
    :param int temp_location_id:
    :param int temp_type_id:
    :param str year:
    :param Voy voyager_interface:
    :param str note:
    """

    def __init__(
        self,
        holding_id=None,
        item_id=None,
        item_type_id=None,
        perm_location_id=None,
        add_item_to_top=False,
        caption="",
        chron="",
        copy_number=0,
        enumeration="",
        free_text="",
        media_type_id=None,
        piece_count=1,
        price="0",
        spine_label="",
        temp_location_id=None,
        temp_type_id=None,
        year="",
        voyager_interface=None,
        note="",
    ):
        self.holding_id = holding_id
        self.item_id = item_id
        self.item_type_id = item_type_id
        self.perm_location_id = perm_location_id
        self.add_item_to_top = add_item_to_top
        self.caption = caption
        self.chron = chron
        self.copy_number = copy_number
        self.enumeration = enumeration
        self.free_text = free_text
        self.media_type_id = media_type_id
        self.piece_count = piece_count
        self.price = price
        self.spine_label = spine_label
        self.temp_location_id = temp_location_id
        self.temp_type_id = temp_type_id
        self.year = year
        self.voyager_interface = voyager_interface
        self.note = note

    def get_mfhd(self):
        """Retrieve the holdings record to which this item is attached."""
        mi = self.voyager_interface.tables["mfhd_item"]
        q = mi.select(mi.c.item_id == self.item_id)
        r = self.voyager_interface.engine.execute(q)
        rows = list(r)
        if len(rows) > 1:
            raise PyVgerException("Multiple MFHDs attached to item %s", self.item_id)
        return self.voyager_interface.get_mfhd(rows[0]["mfhd_id"])

    @classmethod
    def from_id(cls, item_id, voyager_interface):
        """Get item given ID."""
        it = voyager_interface.tables["item"]
        mit = voyager_interface.tables["mfhd_item"]
        item_note_table = voyager_interface.tables["item_note"]

        columns = [
            it.c.item_id,
            it.c.perm_location,
            mit.c.item_enum,
            item_note_table.c.item_note,
            mit.c.chron,
            mit.c.mfhd_id,
            it.c.item_type_id,
            mit.c.caption,
            it.c.copy_number,
            mit.c.freetext,
            it.c.media_type_id,
            it.c.pieces,
            it.c.price,
            it.c.spine_label,
            it.c.temp_location,
            it.c.temp_item_type_id,
            mit.c.year,
        ]

        q = sqla.select(
            columns,
            it.c.item_id == item_id,
            from_obj=[it.join(mit).outerjoin(item_note_table)],
            use_labels=False,
        )
        result = voyager_interface.engine.execute(q)
        rows = [x for x in result]
        if not rows:
            raise NoSuchItemException("item %s not found" % item_id)
        if len(rows) != 1:
            print("many notes on item %s" % item_id)
            print(rows)

        data = rows[0]

        price = f'{Decimal(data["price"]) / 100:.2f}'

        return cls(
            item_id=data["item_id"],
            perm_location_id=data["perm_location"],
            enumeration=data["item_enum"],
            chron=data["chron"],
            note=data["item_note"],
            holding_id=data["mfhd_id"],
            item_type_id=data["item_type_id"],
            caption=data["caption"],
            copy_number=data["copy_number"],
            free_text=data["freetext"],
            media_type_id=data["media_type_id"],
            piece_count=data["pieces"],
            price=price,
            spine_label=data["spine_label"],
            temp_location_id=data["temp_location"],
            temp_type_id=data["temp_item_type_id"],
            year=data["year"],
            voyager_interface=voyager_interface,
        )

    @classmethod
    def from_barcode(cls, barcode, voyager_interface):
        """Get an item record given its barcode."""
        ib = voyager_interface.tables["item_barcode"]
        q = sqla.select([ib.c.item_id], ib.c.item_barcode == barcode)
        result = voyager_interface.engine.execute(q)
        rows = [x for x in result]
        if not rows:
            raise NoSuchItemException("item for barcode %s not found" % barcode)
        if len(rows) != 1:
            print("many items attached to barcode %s" % barcode)
            print(rows)

        item_id = rows[0][0]
        return cls.from_id(item_id, voyager_interface)

    def get_barcode(self):
        """Look up the active bacode for this item."""
        ib = self.voyager_interface.tables["item_barcode"]
        q = sqla.select(
            [ib.c.item_barcode],
            sqla.and_(ib.c.item_id == self.item_id, ib.c.barcode_status == "1"),
        )
        result = self.voyager_interface.engine.execute(q)
        rows = [x for x in result]
        if not rows:
            raise NoSuchItemException("barcode for item %s not found" % self.item_id)
        if len(rows) != 1:
            print("many active barcodes attached to item %s" % self.item_id)
            print(rows)

        return rows[0][0]

    def save(self):
        """Save the item record back to the database."""
        batchcat = self.voyager_interface.batchcat
        if batchcat is None:
            raise BatchCatNotAvailableError
        bc = batchcat.bc
        bc.cItem.HoldingId = self.holding_id
        bc.cItem.ItemID = self.item_id
        bc.cItem.ItemTypeID = self.item_type_id
        bc.cItem.PermLocationID = self.perm_location_id
        bc.cItem.Caption = self.caption or ""
        bc.cItem.Chron = self.chron or ""
        bc.cItem.CopyNumber = self.copy_number
        bc.cItem.Enumeration = self.enumeration or ""
        bc.cItem.FreeText = self.free_text or ""
        bc.cItem.MediaTypeID = self.media_type_id
        bc.cItem.PieceCount = self.piece_count
        bc.cItem.Price = self.price
        bc.cItem.SpineLabel = self.spine_label or ""
        bc.cItem.TempLocationID = self.temp_location_id
        bc.cItem.TempTypeID = self.temp_type_id
        bc.cItem.Year = self.year or ""
        result = bc.UpdateItemData(
            CatLocationID=self.voyager_interface.get_location_id(
                self.voyager_interface.cat_location
            )
        )
        if result[0]:
            raise PyVgerException("UpdateItemData error: {}".format(result))
