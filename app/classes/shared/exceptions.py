class CraftyException(Exception):
    pass


class DatabaseException(CraftyException):
    pass


class SchemaError(DatabaseException):
    pass
