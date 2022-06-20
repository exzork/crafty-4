import peewee
import datetime


def migrate(migrator, db):
    class CraftySettings(peewee.Model):
        secret_api_key = peewee.CharField(default="")

        class Meta:
            table_name = "crafty_settings"

    migrator.create_table(CraftySettings)


def rollback(migrator, db):
    migrator.drop_table("crafty_settings")
