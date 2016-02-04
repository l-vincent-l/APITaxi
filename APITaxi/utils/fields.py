# -*- coding: utf-8 -*-
from flask.ext.restplus import fields as basefields

class FromSQLAlchemyColumnMixin(object):
    def __init__(self, *args, **kwargs):
        column = kwargs.pop("column", None)
        super(FromSQLAlchemyColumnMixin, self).__init__(*args, **kwargs)
        if column is not None:
            self.required = not column.nullable
            self.description = column.description


class Integer(FromSQLAlchemyColumnMixin, basefields.Integer):
    pass

class Boolean(FromSQLAlchemyColumnMixin, basefields.Boolean):
    pass

class DateTime(FromSQLAlchemyColumnMixin, basefields.DateTime):
    def __init__(self, dt_format='rfc822', **kwargs):
        super(DateTime, self).__init__(dt_format, **kwargs)

class Float(FromSQLAlchemyColumnMixin, basefields.Float):
    pass

class String(FromSQLAlchemyColumnMixin, basefields.String):
    pass

class Nested(FromSQLAlchemyColumnMixin, basefields.Nested):
    pass

class List(FromSQLAlchemyColumnMixin, basefields.List):
    pass

class Date(FromSQLAlchemyColumnMixin, basefields.Raw):
    __schema_type__ = 'date'
    __schema_format__ = None

    def schema(self):
        return {
            'type': self.__schema_type__,
            'format': self.__schema_format__,
            'title': self.title,
            'description': self.description,
            'readOnly': self.readonly,
        }

    def format(self):
        return self.isoformat()

    def output(self, key, value):
        if isinstance(value, dict):
            value = value[key]
        if isinstance(value, str):
            return value
        date = getattr(value, key)
        return date.isoformat() if date else None


