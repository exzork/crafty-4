# pylint: skip-file
from datetime import datetime
import logging
import typing as t
import sys
import os
import re
from functools import wraps
from functools import cached_property
import peewee
from playhouse.migrate import (
    SqliteMigrator,
    Operation,
    SQL,
    SqliteDatabase,
    make_index_name,
)

from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)

MIGRATE_TABLE = "migratehistory"
MIGRATE_TEMPLATE = '''# Generated by database migrator
import peewee

def migrate(migrator, db):
    """
    Write your migrations here.
    """
{migrate}

def rollback(migrator, db):
    """
    Write your rollback migrations here.
    """
{rollback}'''


class MigrateHistory(peewee.Model):
    """
    Presents the migration history in a database.
    """

    name = peewee.CharField(unique=True)
    migrated_at = peewee.DateTimeField(default=datetime.utcnow)

    # noinspection PyTypeChecker
    def __unicode__(self) -> str:
        """
        String representation of this migration
        """
        return self.name

    class Meta:
        table_name = MIGRATE_TABLE


def get_model(method):
    """
    Convert string to model class.
    """

    @wraps(method)
    def wrapper(migrator, model, *args, **kwargs):
        if isinstance(model, str):
            return method(migrator, migrator.table_dict[model], *args, **kwargs)
        return method(migrator, model, *args, **kwargs)

    return wrapper


# noinspection PyProtectedMember
class Migrator(object):
    def __init__(self, database: t.Union[peewee.Database, peewee.Proxy]):
        """
        Initializes the migrator
        """
        if isinstance(database, peewee.Proxy):
            database = database.obj
        self.database: SqliteDatabase = database
        self.table_dict: t.Dict[str, peewee.Model] = {}
        self.operations: t.List[t.Union[Operation, callable]] = []
        self.migrator = SqliteMigrator(database)

    def run(self):
        """
        Runs operations.
        """
        for op in self.operations:
            if isinstance(op, Operation):
                op.run()
            else:
                op()
        self.clean()

    def clean(self):
        """
        Cleans the operations.
        """
        self.operations = list()

    def sql(self, sql: str, *params):
        """
        Executes raw SQL.
        """
        self.operations.append(SQL(sql, *params))

    def create_table(self, model: peewee.Model) -> peewee.Model:
        """
        Creates model and table in database.
        """
        self.table_dict[model._meta.table_name] = model
        model._meta.database = self.database
        self.operations.append(model.create_table)
        return model

    @get_model
    def drop_table(self, model: peewee.Model):
        """
        Drops model and table from database.
        """
        del self.table_dict[model._meta.table_name]
        self.operations.append(lambda: model.drop_table(cascade=False))

    @get_model
    def add_columns(self, model: peewee.Model, **fields: peewee.Field) -> peewee.Model:
        """
        Creates new fields.
        """
        for name, field in fields.items():
            model._meta.add_field(name, field)
            self.operations.append(
                self.migrator.add_column(
                    model._meta.table_name, field.column_name, field
                )
            )
            if field.unique:
                self.operations.append(
                    self.migrator.add_index(
                        model._meta.table_name, (field.column_name,), unique=True
                    )
                )
        return model

    @get_model
    def drop_columns(self, model: peewee.Model, names: str) -> peewee.Model:
        """
        Removes fields from model.
        """
        fields = [field for field in model._meta.fields.values() if field.name in names]
        for field in fields:
            self.__del_field__(model, field)
            if field.unique:
                # Drop unique index
                index_name = make_index_name(
                    model._meta.table_name, [field.column_name]
                )
                self.operations.append(
                    self.migrator.drop_index(model._meta.table_name, index_name)
                )
            self.operations.append(
                self.migrator.drop_column(
                    model._meta.table_name, field.column_name, cascade=False
                )
            )
        return model

    def __del_field__(self, model: peewee.Model, field: peewee.Field):
        """
        Deletes field from model.
        """
        model._meta.remove_field(field.name)
        delattr(model, field.name)
        if isinstance(field, peewee.ForeignKeyField):
            obj_id_name = field.column_name
            if field.column_name == field.name:
                obj_id_name += "_id"
            delattr(model, obj_id_name)
            delattr(field.rel_model, field.backref)

    @get_model
    def rename_column(
        self, model: peewee.Model, old_name: str, new_name: str
    ) -> peewee.Model:
        """
        Renames field in model.
        """
        field = model._meta.fields[old_name]
        if isinstance(field, peewee.ForeignKeyField):
            old_name = field.column_name
        self.__del_field__(model, field)
        field.name = field.column_name = new_name
        model._meta.add_field(new_name, field)
        if isinstance(field, peewee.ForeignKeyField):
            field.column_name = new_name = field.column_name + "_id"
        self.operations.append(
            self.migrator.rename_column(model._meta.table_name, old_name, new_name)
        )
        return model

    @get_model
    def rename_table(self, model: peewee.Model, new_name: str) -> peewee.Model:
        """
        Renames table in database.
        """
        old_name = model._meta.table_name
        del self.table_dict[model._meta.table_name]
        model._meta.table_name = new_name
        self.table_dict[model._meta.table_name] = model
        self.operations.append(self.migrator.rename_table(old_name, new_name))
        return model

    @get_model
    def add_index(
        self, model: peewee.Model, *columns: str, unique=False
    ) -> peewee.Model:
        """Create indexes."""
        model._meta.indexes.append((columns, unique))
        columns_ = []
        for col in columns:
            field = model._meta.fields.get(col)

            if len(columns) == 1:
                field.unique = unique
                field.index = not unique

            if isinstance(field, peewee.ForeignKeyField):
                col = col + "_id"

            columns_.append(col)
        self.operations.append(
            self.migrator.add_index(model._meta.table_name, columns_, unique=unique)
        )
        return model

    @get_model
    def drop_index(self, model: peewee.Model, *columns: str) -> peewee.Model:
        """Drop indexes."""
        columns_ = []
        for col in columns:
            field = model._meta.fields.get(col)
            if not field:
                continue

            if len(columns) == 1:
                field.unique = field.index = False

            if isinstance(field, peewee.ForeignKeyField):
                col = col + "_id"
            columns_.append(col)
        index_name = make_index_name(model._meta.table_name, columns_)
        model._meta.indexes = [
            (cols, _) for (cols, _) in model._meta.indexes if columns != cols
        ]
        self.operations.append(
            self.migrator.drop_index(model._meta.table_name, index_name)
        )
        return model

    @get_model
    def add_not_null(self, model: peewee.Model, *names: str) -> peewee.Model:
        """Add not null."""
        for name in names:
            field = model._meta.fields[name]
            field.null = False
            self.operations.append(
                self.migrator.add_not_null(model._meta.table_name, field.column_name)
            )
        return model

    @get_model
    def drop_not_null(self, model: peewee.Model, *names: str) -> peewee.Model:
        """Drop not null."""
        for name in names:
            field = model._meta.fields[name]
            field.null = True
            self.operations.append(
                self.migrator.drop_not_null(model._meta.table_name, field.column_name)
            )
        return model

    @get_model
    def add_default(
        self, model: peewee.Model, name: str, default: t.Any
    ) -> peewee.Model:
        """Add default."""
        field = model._meta.fields[name]
        model._meta.defaults[field] = field.default = default
        self.operations.append(
            self.migrator.apply_default(model._meta.table_name, name, field)
        )
        return model


# noinspection PyProtectedMember
class MigrationManager(object):
    filemask = re.compile(r"[\d]+_[^\.]+\.py$")

    def __init__(self, database: t.Union[peewee.Database, peewee.Proxy], helper):
        """
        Initializes the migration manager.
        """
        if not isinstance(database, (peewee.Database, peewee.Proxy)):
            raise RuntimeError("Invalid database: {}".format(database))
        self.database = database
        self.helper = helper

    @cached_property
    def model(self) -> t.Type[MigrateHistory]:
        """
        Initialize and cache the MigrationHistory model.
        """
        MigrateHistory._meta.database = self.database
        MigrateHistory._meta.table_name = "migratehistory"
        MigrateHistory._meta.schema = None
        MigrateHistory.create_table(True)
        return MigrateHistory

    @property
    def done(self) -> t.List[str]:
        """
        Scans migrations in the database.
        """
        return [mm.name for mm in self.model.select().order_by(self.model.id)]

    @property
    def todo(self):
        """
        Scans migrations in the file system.
        """
        if not os.path.exists(self.helper.migration_dir):
            logger.warning(
                "Migration directory: {} does not exist.".format(
                    self.helper.migration_dir
                )
            )
            os.makedirs(self.helper.migration_dir)
        return sorted(
            f[:-3]
            for f in os.listdir(self.helper.migration_dir)
            if self.filemask.match(f)
        )

    @property
    def diff(self) -> t.List[str]:
        """
        Calculates difference between the filesystem and the database.
        """
        done = set(self.done)
        return [name for name in self.todo if name not in done]

    @cached_property
    def migrator(self) -> Migrator:
        """
        Create migrator and setup it with fake migrations.
        """
        migrator = Migrator(self.database)
        for name in self.done:
            self.up_one(name, migrator, True)
        return migrator

    def compile(self, name, migrate="", rollback=""):
        """
        Compiles a migration.
        """
        name = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + name
        filename = name + ".py"
        path = os.path.join(self.helper.migration_dir, filename)
        with open(path, "w") as f:
            f.write(
                MIGRATE_TEMPLATE.format(
                    migrate=migrate, rollback=rollback, name=filename
                )
            )

        return name

    def create(self, name: str = "auto", auto: bool = False) -> t.Optional[str]:
        """
        Creates a migration.
        """
        migrate = rollback = ""
        if auto:
            raise NotImplementedError

        logger.info('Creating migration "{}"'.format(name))
        name = self.compile(name, migrate, rollback)
        logger.info('Migration has been created as "{}"'.format(name))
        return name

    def clear(self):
        """Clear migrations."""
        self.model.delete().execute()

    def up(self, name: t.Optional[str] = None):
        """
        Runs all unapplied migrations.
        """
        logger.info("Starting migrations")
        Console.info("Starting migrations")

        done = []
        diff = self.diff
        if not diff:
            logger.info("There is nothing to migrate")
            Console.info("There is nothing to migrate")
            return done

        migrator = self.migrator
        for mname in diff:
            done.append(self.up_one(mname, self.migrator))
            if name and name == mname:
                break

        return done

    def read(self, name: str):
        """
        Reads a migration from a file.
        """
        call_params = dict()
        if Helpers.is_os_windows() and sys.version_info >= (3, 0):
            # if system is windows - force utf-8 encoding
            call_params["encoding"] = "utf-8"
        with open(
            os.path.join(self.helper.migration_dir, name + ".py"), **call_params
        ) as f:
            code = f.read()
            scope = {}
            code = compile(code, "<string>", "exec", dont_inherit=True)
            exec(code, scope, None)
            return scope.get("migrate", lambda m, d: None), scope.get(
                "rollback", lambda m, d: None
            )

    def up_one(
        self, name: str, migrator: Migrator, fake: bool = False, rollback: bool = False
    ) -> str:
        """
        Runs a migration with a given name.
        """
        try:
            migrate_fn, rollback_fn = self.read(name)
            if fake:
                migrate_fn(migrator, self.database)
                migrator.clean()
                return name
            with self.database.transaction():
                if rollback:
                    logger.info('Rolling back "{}"'.format(name))
                    rollback_fn(migrator, self.database)
                    migrator.run()
                    self.model.delete().where(self.model.name == name).execute()
                else:
                    logger.info('Migrate "{}"'.format(name))
                    migrate_fn(migrator, self.database)
                    migrator.run()
                    if name not in self.done:
                        self.model.create(name=name)

                logger.info('Done "{}"'.format(name))
                return name

        except Exception:
            self.database.rollback()
            operation_name = "Rollback" if rollback else "Migration"
            logger.exception("{} failed: {}".format(operation_name, name))
            raise

    def down(self):
        """
        Rolls back migrations.
        """
        if not self.done:
            raise RuntimeError("No migrations are found.")

        name = self.done[-1]

        migrator = self.migrator
        self.up_one(name, migrator, False, True)
        logger.warning("Rolled back migration: {}".format(name))
