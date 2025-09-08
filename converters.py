"""Converters for paths."""


class BooleanConverter:
    regex = '0|1|true|false|True|False'

    def to_python(self, value):
        return value.lower() in ('1', 'true')

    def to_url(self, value):
        return '1' if value else '0'
