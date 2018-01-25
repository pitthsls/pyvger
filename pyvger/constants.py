"""constants for mapping Oracle tables to sqlalchemy"""

RELATIONS = [
    (('item', 'item_id'), ('mfhd_item', 'item_id')),
    (('item', 'item_id'), ('item_note', 'item_id')),
    (('item', 'item_id'), ('item_status', 'item_id')),
    (('item', 'item_id'), ('item_barcode', 'item_id')),
    (('bib_master', 'bib_id'), ('bib_location', 'bib_id')),
    (('bib_master', 'bib_id'), ('bib_text', 'bib_id')),
    (('bib_master', 'bib_id'), ('bib_mfhd', 'bib_id')),
    (('bib_master', 'bib_id'), ('bib_index', 'bib_id')),
    (('item_status', 'item_status'), ('item_status_type', 'item_status_type')),
    (('mfhd_master', 'mfhd_id'), ('bib_mfhd', 'mfhd_id')),
    (('mfhd_master', 'mfhd_id'), ('mfhd_item', 'mfhd_id')),
    (('bib_mfhd', 'mfhd_id'), ('mfhd_item', 'mfhd_id')),
    (('location', 'location_id'), ('mfhd_master', 'location_id')),
    (('location', 'location_id'), ('bib_location', 'location_id')),
]
TABLE_NAMES = (
    'mfhd_master',
    'bib_location',
    'bib_master',
    'bib_index',
    'item',
    'mfhd_item',
    'item_note',
    'bib_text',
    'bib_mfhd',
    'item_status',
    'item_status_type',
    'location',
    'item_barcode',
)