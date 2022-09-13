from flask import Flask, send_from_directory
from pathlib import Path

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    instance_path = Path(app.instance_path)
    static_folder = Path(app.static_folder)

    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=str(instance_path / 'webplanner.sqlite'),
    )

    # TODO: can the Jinja lines below be moved to the configuration?
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    instance_path.mkdir(parents=True, exist_ok=True)

    from . import index, student, user, jobs, db

    app.register_blueprint(index.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(jobs.bp)
    #app.add_url_rule('/', endpoint='index.index')
    app.add_url_rule('/favicon.ico', view_func=lambda: send_from_directory(str(static_folder / "images"), "calendar.ico", mimetype='image/vnd.microsoft.icon'))

    # register the database with this app
    db.init_app(app)

    return app
