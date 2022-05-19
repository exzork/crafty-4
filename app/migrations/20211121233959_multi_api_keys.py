import peewee
import datetime
from app.classes.models.users import Users


def migrate(migrator, db):
    class ApiKeys(peewee.Model):
        token_id = peewee.AutoField()
        name = peewee.CharField(default="", unique=True, index=True)
        created = peewee.DateTimeField(default=datetime.datetime.now)
        user = peewee.ForeignKeyField(Users, backref="api_token", index=True)
        server_permissions = peewee.CharField(default="00000000")
        crafty_permissions = peewee.CharField(default="000")
        superuser = peewee.BooleanField(default=False)

        class Meta:
            table_name = "api_keys"

    migrator.create_table(ApiKeys)


def rollback(migrator, db):
    migrator.drop_table("api_keys")
