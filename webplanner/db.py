import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db() -> sqlite3.Connection:
    db = g.get("db", None)
    if db is None:
        db = g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        db.row_factory = sqlite3.Row

    return db


def close_db(e=None) -> None:
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db(filename='schema.sql') -> None:
    with current_app.open_resource(filename) as f:
        get_db().executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    "Clear the existing data and create new tables."

    init_db()
    click.echo('Initialized the database.')


@click.command('test-db')
@with_appcontext
def test_db_command():
    "Clear the existing data and create new tables with test data."

    init_db()
    init_db("test_data.sql")
    click.echo('Initialized the database.')


@click.command('real-db')
@with_appcontext
def real_db_command():
    "Clear the existing data and create new tables with the real data."

    init_db()
    init_db("real_data.sql")
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(test_db_command)
    app.cli.add_command(real_db_command)
