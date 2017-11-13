import sqlalchemy as sqla

raw = sqla.sql.expression.func.utl_i18n.string_to_raw
nc = sqla.sql.expression.func.utl_i18n.raw_to_nchar


def recode(column, encoding='utf8'):
    """Generate Oracle function to decode bytes stored incorrectly as another encoding"""
    return nc(raw(column), encoding)
