from flask import Blueprint, flash, redirect, render_template, request, url_for
from webplanner.db import get_db
from webplanner.defines import dayname
from webplanner.user import increment_scheduling_revision

bp = Blueprint('student', __name__, url_prefix='/student')

def sanitize_time(t):
    """
    reformat the time so that both the hour and minute are shown with two digits.
    this is required for SQLite. otherwise the comparison function "<", ">", "BETWEEN ... AND" don't work.
    """
    h, m, *_ = t.split(":")
    h = int(h)
    m = int(m)
    return f"{h:02d}:{m:02d}"

def get_student(db, code):
    return db.execute("""
        SELECT
            s.id AS student_id,
            t.id AS teacher_id,
            s.name_given AS student_name_given,
            s.name_family AS student_name_family,
            s.email AS student_email,
            s.phone AS student_phone,
            t.name_given AS teacher_name_given,
            t.name_family AS teacher_name_family,
            p.id AS student_planning_id,
            p.priority_family AS priority_family,
            p.fm_day AS fm_day,
            p.fm_time_from AS fm_time_from,
            p.fm_time_to AS fm_time_to,
            p.lesson_length AS lesson_length
        FROM
            student s
        JOIN
            student_planning p ON p.student_id = s.id,
            user t ON p.teacher_id = t.id
        WHERE
            p.invite_code = ?
        LIMIT 1
    """, (code,)).fetchone()

def get_student_availabilities(db, student):
    return db.execute("""
        SELECT
            id,
            priority,
            `day`,
            time_from,
            time_to
        FROM
            student_availability
        WHERE
            student_planning_id = ?
        ORDER BY
            priority ASC,
            day ASC,
            time(time_from) ASC
    """, (student["student_planning_id"],)).fetchall()

@bp.route('/<code>')
def show(code: str):
    db = get_db()
    student = get_student(db, code)

    if not student:
        return redirect(url_for("index.index"))

    student_availability = get_student_availabilities(db, student)

    different_days = len(set(s["day"] for s in student_availability))

    teacher_availability = db.execute("""
        SELECT
            day,
            time_from,
            time_to
        FROM
            teacher_availability
        WHERE
            teacher_id = ?
        ORDER BY
            day ASC,
            time(time_from) ASC
    """, (student["teacher_id"],)).fetchall()

    teacher_availability_days = sorted(set(availability["day"] for availability in teacher_availability))

    return render_template(
        'student.html',
        student=student,
        student_availability=student_availability,
        teacher_availability=teacher_availability,
        teacher_availability_days=teacher_availability_days,
        dayname=dayname,
        max_student_availability=3,
        min_different_days=2,
        different_days=different_days,
        code=code
    )

@bp.route('/<code>/set_personal_data', methods=("POST",))
def set_personal_data(code: str):
    db = get_db()
    student = get_student(db, code)

    if not student:
        return redirect(url_for("index.index"))

    email = request.form['email']
    phone = request.form['phone']
    priority_family = bool(request.form.get('priority_family'))
    fm_day = int(request.form['fm_day'])
    fm_time_from = sanitize_time(request.form['fm_time_from'])
    fm_time_to = sanitize_time(request.form['fm_time_to'])

    db.execute("""
        UPDATE
            student
        SET
            email = ?,
            phone = ?
        WHERE
            id = ?
    """, (email, phone, student["student_id"]))

    db.execute("""
        UPDATE
            student_planning
        SET
            priority_family = ?,
            fm_day = ?,
            fm_time_from = ?,
            fm_time_to = ?
        WHERE
            id = ?
    """, (priority_family, fm_day, fm_time_from, fm_time_to, student["student_planning_id"]))

    db.commit()

    return redirect(url_for("student.show", code=code))

@bp.route('/<code>/add', methods=("POST",))
def add_availability(code: str):
    db = get_db()
    student = get_student(db, code)

    if not student:
        return redirect(url_for("index.index"))

    day = int(request.form['day'])
    time_from = sanitize_time(request.form['time_from'])
    time_to = sanitize_time(request.form['time_to'])

    # TODO: check that "time_from" to "time_to" is at least the lesson length

    teacher_id = student["teacher_id"]

    # check if provided availability is compatible with `teacher_availability`
    teacher_availability = db.execute("""
        SELECT
            id
        FROM
            teacher_availability
        WHERE
            teacher_id = ? AND
            day = ? AND
            time(?) BETWEEN time(time_from) AND time(time_to) AND
            time(?) BETWEEN time(time_from) AND time(time_to)
        LIMIT 1
    """, (teacher_id, day, time_from, time_to)).fetchone()

    if not teacher_availability:
        flash(f"les heures donné ne sont pas possible")
        return redirect(url_for("student.show", code=code))

    student_planning_id = student["student_planning_id"]

    # add availability to `student_availability`
    try:
        db.execute("""
            INSERT INTO
                student_availability
                (student_planning_id, priority, day, time_from, time_to)
            VALUES
                (?, (SELECT COUNT(id) + 1 FROM student_availability WHERE student_planning_id = ?), ?, ?, ?)
        """, (student_planning_id, student_planning_id, day, time_from, time_to))
        increment_scheduling_revision(db, teacher_id)
        db.commit()
    except db.IntegrityError:
        # the only integrity error that we can have for now is to register two entries with the same priority
        flash("tu peux specifier chaque priority qu'une seule fois")

    return redirect(url_for("student.show", code=code))

@bp.route('/<code>/delete', methods=("POST",))
def delete_priority(code: str):
    db = get_db()
    student = get_student(db, code)

    if not student:
        return redirect(url_for("index.index"))

    student_planning_id = student["student_planning_id"]
    priority = request.form['priority']
    teacher_id = student["teacher_id"]

    db.execute("""
        DELETE FROM
            student_availability
        WHERE
            student_planning_id = ? AND
            priority = ?
    """, (student_planning_id, priority))

    db.execute("""
        UPDATE
            student_availability
        SET
            priority = priority - 1
        WHERE
            student_planning_id = ? AND
            priority > ?
    """, (student_planning_id, priority))
    increment_scheduling_revision(db, teacher_id)
    db.commit()

    return redirect(url_for("student.show", code=code))

@bp.route('/<code>/swap', methods=("POST",))
def swap_priority(code: str):
    db = get_db()
    student = get_student(db, code)

    if not student:
        return redirect(url_for("index.index"))

    student_planning_id = student["student_planning_id"]
    priority1 = request.form['priority1']
    priority2 = request.form['priority2']
    teacher_id = student["teacher_id"]

    db.executemany("""
        UPDATE
            student_availability
        SET
            priority = ?
        WHERE
            student_planning_id = ? AND
            priority = ?
    """, ((0,         student_planning_id, priority1),
          (priority1, student_planning_id, priority2),
          (priority2, student_planning_id, 0)))
    increment_scheduling_revision(db, teacher_id)
    db.commit()

    return redirect(url_for("student.show", code=code))
