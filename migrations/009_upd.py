"""Peewee migrations -- 006_upd.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    @migrator.create_model
    class Owner(pw.Model):
        id = pw.IntegerField(primary_key=True)

        class Meta:
            table_name = "owners"

    migrator.add_fields(
        'settings',
        token=pw.TextField(default=None, null=True),
        owner_id=pw.ForeignKeyField(Owner, backref="owners", default=None, null=True),
        username=pw.TextField(default=None, null=True),
        messages=pw.TextField(default="[]", null=True),
        mails=pw.TextField(default="[]", null=True),
        captcha_is_on=pw.BooleanField(default=False, null=True),
        captcha_after=pw.BooleanField(default=False, null=True),
        captcha_first_delay=pw.IntegerField(default=30, null=True),
        captcha_buttons=pw.TextField(default="[]", null=True)
    )

    migrator.remove_fields('settings', "start_kb")
    migrator.remove_fields('settings', "start_msg_id")
    migrator.remove_fields('settings', "send_start")
    migrator.remove_fields('settings', "start_delete")
    migrator.remove_fields('settings', "start_from_user_id")
    migrator.remove_fields('settings', "mail_after")
    migrator.remove_fields('settings', "capcha_btn_apply")
    migrator.remove_fields('settings', "capcha_btn_decline")


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    migrator.add_fields(
        'settings',
        start_kb=pw.TextField(default=None, null=True),
        start_delete=pw.TextField(default=None, null=True),
        mail_after=pw.TextField(default="", null=True),
        send_start=pw.IntegerField(default=1, null=True),
        start_from_user_id=pw.IntegerField(default=0, null=True),
        start_msg_id=pw.IntegerField(default=0, null=True),
        capcha_btn_apply=pw.TextField(default="", null=True),
        capcha_btn_decline=pw.TextField(default="", null=True)
    )

    migrator.remove_fields('settings', "token")
    migrator.remove_fields('settings', "owner")
    migrator.remove_fields('settings', "username")
    migrator.remove_fields('settings', "messages")
    migrator.remove_fields('settings', "mails")
    migrator.remove_fields('settings', "mail_after")
    migrator.remove_fields('settings', "captcha_is_on")
    migrator.remove_fields('settings', "captcha_after")
    migrator.remove_fields('settings', "captcha_first_delay")
    migrator.remove_fields('settings', "captcha_buttons")
