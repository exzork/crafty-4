import peewee
import datetime


def migrate(migrator, database, **kwargs):
    migrator.add_columns(
        "users", valid_tokens_from=peewee.DateTimeField(default=datetime.datetime.now)
    )
    migrator.drop_columns("users", ["api_token"])


def rollback(migrator, database, **kwargs):
    migrator.drop_columns("users", ["valid_tokens_from"])
    migrator.add_columns(
        "users", api_token=peewee.CharField(default="", unique=True, index=True)
    )
