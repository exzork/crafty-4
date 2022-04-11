import peewee

database_proxy = peewee.DatabaseProxy()


class BaseModel(peewee.Model):
    class Meta:
        database = database_proxy
