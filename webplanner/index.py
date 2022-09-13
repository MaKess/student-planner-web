from crypt import methods
import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from webplanner.db import get_db

bp = Blueprint('index', __name__, url_prefix='/')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute("""
        SELECT
            id, email, name_given, name_family
        FROM
            user
        WHERE
            id = ?
        LIMIT 1
    """, (user_id,)).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('index.index'))
        return view(**kwargs)
    return wrapped_view

def index_default():
    if request.method != 'POST':
        return

    login = request.form["login"]
    if login == "student":
        code = request.form['code']

        if not code:
            flash("need to fill in code!")
            return

        student = get_db().execute("""
            SELECT
                1
            FROM
                student s
            JOIN
                student_planning p ON p.student_id = s.id
            WHERE
                p.invite_code = ?
            LIMIT 1
        """, (code,)).fetchone()

        if student:
            return redirect(url_for("student.show", code=code))

        flash("this code seems to be invalid! check for the precise format.")

    elif login == "staff":
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash("need to enter E-Mail and Password")
            return

        user = get_db().execute("""
            SELECT
                id, email, name_given, name_family
            FROM
                user
            WHERE
                email = ? AND password = ?
            LIMIT 1
        """, (email, password)).fetchone()

        if user:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for("user.show"))

        flash("login credentions not valid")
    
    else:
        flash("invalid login method")

@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("index.index"))

@bp.route('/', methods=("GET", "POST"))
def index():
    if ret := index_default():
        return ret

    return render_template('index.html')
