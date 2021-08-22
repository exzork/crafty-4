# Database change guide for contributors

When updating a database schema modify the schema in `app/classes/shared/models.py` and create a new migration with the `migrations add <name>` command (in Crafty's prompt).

A full list of helper functions you can find in `app/classes/shared/models.py`

## Example migration files

### Rename column/field

```py
def migrate(migrator, database, **kwargs):
    migrator.rename_column('my_table', 'old_name', 'new_name') # First argument can be model class OR table name



def rollback(migrator, database, **kwargs):
    migrator.rename_column('my_table', 'new_name', 'old_name') # First argument can be model class OR table name

```

### Rename table/model

```py
def migrate(migrator, database, **kwargs):
    migrator.rename_table('old_name', 'new_name') # First argument can be model class OR table name



def rollback(migrator, database, **kwargs):
    migrator.rename_table('new_name', 'old_name') # First argument can be model class OR table name

```

### Create table/model

```py
import peewee


def migrate(migrator, database, **kwargs):
    db = database
    #Copy Paste here the class of the New Table from models.py
    class NewTable(peewee.Model):
        my_id = peewee.IntegerField(unique=True, primary_key=True)

        class Meta:
            table_name = 'new_table'
            database = db
            
    migrator.create_table(NewTable)



def rollback(migrator, database, **kwargs):
    migrator.drop_table('new_table') # Can be model class OR table name

```

### Add columns/fields

```py
import peewee


def migrate(migrator, database, **kwargs):
    migrator.add_columns('table_name', new_field_name=peewee.CharField(default="")) # First argument can be model class OR table name



def rollback(migrator, database, **kwargs):
    migrator.drop_columns('table_name', ['new_field_name']) # First argument can be model class OR table name

```
