from crypt import methods
from math import floor, ceil
from io import BytesIO

from typing import Optional
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, send_file
from webplanner.db import get_db
from webplanner.index import login_required
from webplanner.defines import dayname
from collections import namedtuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.platypus.paragraph import Paragraph


bp = Blueprint('user', __name__, url_prefix='/user')

slot_increment = 10
days_per_week = 7
slots_per_day = 24 * 60 // slot_increment

def make_minute_of_day(time_raw: str):
    hour, minute = time_raw.split(":")
    return int(hour) * 60 + int(minute)

def make_time_from_minutes(minutes: int):
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}"

def get_students():
    return get_db().execute("""
        SELECT
            s.id,
            s.name_given,
            s.name_family,
            p.lesson_length,
            p.invite_code,
            COUNT(a.id) AS planning_responses
        FROM
            student s
        JOIN
            student_planning p ON p.student_id = s.id
        LEFT JOIN
            student_availability a ON a.student_planning_id = p.id
        WHERE
            p.teacher_id = ?
        GROUP BY
            s.id
        ORDER BY
            s.name_family COLLATE NOCASE ASC,
            s.name_given COLLATE NOCASE ASC
    """, (g.user["id"],)).fetchall()

def get_teacher_availability():
    return get_db().execute("""
        SELECT
            id,
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
    """, (g.user["id"],)).fetchall()

@bp.route('/')
@login_required
def show():
    return render_template(
        "user/index.html",
        availabilities=get_teacher_availability(),
        students=get_students(),
        dayname=dayname
    )

@bp.route('/students')
@login_required
def students():
    return render_template(
        "user/students.html",
        students=get_students(),
        dayname=dayname
    )

@bp.route('/availability', methods=("GET",))
@login_required
def availability():
    return render_template(
        "user/availability.html",
        availabilities=get_teacher_availability(),
        dayname=dayname
    )

@bp.route('/availability', methods=("POST",))
@login_required
def availability_add():
    db = get_db()

    teacher_id = g.user["id"]

    day = int(request.form['day'])
    time_from = request.form['time_from']
    time_to = request.form['time_to']

    overlap = db.execute("""
        SELECT
            id,
            time_from,
            time_to
        FROM
            teacher_availability
        WHERE
            teacher_id = ? AND
            day = ? AND
            time(time_from) <= time(?) AND
            time(time_to) >= time(?)
    """, (teacher_id, day, time_to, time_from)).fetchall()

    if overlap:
        minutes_from_new = make_minute_of_day(time_from)
        minutes_to_new = make_minute_of_day(time_to)
        existing_ids = []

        for existing_id, existing_time_from, existing_time_to in overlap:
            existing_ids.append(int(existing_id))
            minutes_from_new = min(minutes_from_new, make_minute_of_day(existing_time_from))
            minutes_to_new = max(minutes_to_new, make_minute_of_day(existing_time_to))

        reuse_existing_id = existing_ids.pop()

        if existing_ids:
            db.executemany("DELETE FROM teacher_availability WHERE id = ?", ((i,) for i in existing_ids))

        time_from = make_time_from_minutes(minutes_from_new)
        time_to = make_time_from_minutes(minutes_to_new)

        db.execute("""
            UPDATE
                teacher_availability
            SET
                time_from = ?,
                time_to = ?
            WHERE
                id = ?
        """, (time_from, time_to, reuse_existing_id))
    else:
        db.execute("""
            INSERT INTO
                teacher_availability
                (teacher_id, day, time_from, time_to)
            VALUES
                (?, ?, ?, ?)
        """, (teacher_id, day, time_from, time_to))

    db.commit()

    return redirect(url_for(".availability"))

@bp.route('/availability/delete', methods=("POST",))
@login_required
def availability_delete():
    availability_id = int(request.form['id'])

    db = get_db()
    db.execute("""
        DELETE FROM
            teacher_availability
        WHERE
            id = ? AND
            teacher_id = ?
    """, (availability_id, g.user["id"]))
    db.commit()

    return redirect(url_for(".availability"))

def get_plannings():
    return get_db().execute("""
        SELECT
            id,
            range_attempts,
            range_increments,
            stage,
            revision,
            last_update
        FROM
            scheduling
        WHERE
            teacher_id = ?
        ORDER BY
            id
    """, (g.user["id"],)).fetchall()

def increment_scheduling_revision(db, teacher_id: int):
    db.execute("""
    UPDATE
        scheduling
    SET
        revision = revision + 1,
        stage = 1
    WHERE
        teacher_id = ? AND NOT locked
    """, (teacher_id,))

@bp.route('/planning')
@login_required
def planning_index():
    plannings = get_plannings()
    first_planning_id = int(plannings[0]["id"])
    return redirect(url_for(".planning", planning_id=first_planning_id))

PlanningSlot = namedtuple("PlanningSlot", ["id", "name_given", "name_family", "day", "time_from", "time_to", "slots", "priority", "student_planning_id"])

def make_planning_table(planning_id: int, exclude:Optional[int]=None):
    teacher_id = g.user["id"]
    student_scheduling = get_db().execute("""
        SELECT
            s.id,
            s.name_given,
            s.name_family,
            ss.day,
            ss.time_from,
            ss.time_to,
            a.priority,
            p.id
        FROM
            student_scheduling ss
        JOIN
            student s ON ss.student_id = s.id
        JOIN
            scheduling x ON x.teacher_id = ? AND x.id = ss.scheduling_id AND x.stage = 3
        LEFT JOIN
            student_planning p ON p.student_id = s.id AND p.teacher_id = ?
        LEFT JOIN
            student_availability a ON a.student_planning_id = p.id
                                  AND ss.day = a.day
                                  AND time(ss.time_from) BETWEEN time(a.time_from) AND time(a.time_to)
                                  AND time(ss.time_to) BETWEEN time(a.time_from) AND time(a.time_to)
        WHERE
            ss.scheduling_id = ?
    """, (teacher_id, teacher_id, planning_id))

    slots = [[None for _ in range(slots_per_day)] for _ in range(days_per_week)]

    min_slot = None
    max_slot = None

    for s_id, name_given, name_family, day, time_from, time_to, priority, student_planning_id in student_scheduling:
        from_slot, offset = divmod(make_minute_of_day(time_from), slot_increment)
        assert offset == 0

        to_slot, offset = divmod(make_minute_of_day(time_to), slot_increment)
        assert offset == 0


        if min_slot is None or from_slot < min_slot:
            min_slot = from_slot

        if max_slot is None or to_slot > max_slot:
            max_slot = to_slot

        student_planning_id = int(student_planning_id)
        if exclude is not None and student_planning_id == exclude:
            continue

        slots[day][from_slot] = PlanningSlot(s_id, name_given, name_family, day, time_from, time_to, to_slot - from_slot, priority, student_planning_id)

        for i in range(from_slot + 1, to_slot):
            slots[day][i] = False

    return slots, min_slot, max_slot

def make_times():
    times = []
    for s in range(slots_per_day):
        hour, minute = divmod(s * slot_increment, 60)
        times.append(f"{hour:02d}:{minute:02d}")
    return times

@bp.route('/planning/<int:planning_id>')
@login_required
def planning(planning_id:int):
    slots, min_slot, max_slot = make_planning_table(planning_id)

    if min_slot is None:
        return render_template(
            "user/planning/unavailable.html",
            planning_id=planning_id,
            plannings=get_plannings()
        )

    return render_template(
        "user/planning/result.html",
        planning_id=planning_id,
        plannings=get_plannings(),
        slots=slots,
        min_slot=min_slot,
        max_slot=max_slot,
        times=make_times(),
        dayname=dayname,
        editstart=False,
        altslots=None
    )

def single_color(_):
    return colors.lightblue

def prio_to_color(priority):
    if priority is None:
        # this should not happen, but it does when the provided student availability was shorter than the lesson length
        return colors.lightblue
    elif priority <= 1:
        return colors.lightgreen
    elif priority <= 2:
        return colors.lightyellow
    elif priority >= 3:
        return colors.pink
    else:
        return colors.lightblue

@bp.route('/planning/<int:planning_id>.pdf')
@login_required
def planning_export_pdf(planning_id:int):

    mode = request.args.get("mode")
    if mode == "single":
        color_lookup = single_color
    else:
        color_lookup = prio_to_color

    title = "Planning" # TODO: make this dynamic

    fd = BytesIO()
    doc = SimpleDocTemplate(fd,
                            pagesize=A4,
                            title=title,
                            author="",
                            subject="",
                            producer="",
                            creator="",
                            topMargin=35,
                            bottomMargin=35)

    styles = getSampleStyleSheet()
    style_h1 = styles['Heading1']

    style = [
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]

    r = range(1, 7)

    headline = [""] + [dayname[d] for d in r]

    data = [headline]

    slots, min_slot, max_slot = make_planning_table(planning_id)
    times = make_times()
    for s in range(min_slot, max_slot + 1):
        line = [times[s]] # the first cell is is the time (e.g. "11:30")

        for d in r:
            slot = slots[d][s]

            if slot:
                line.append(f"{slot.name_given} {slot.name_family}\n({ slot.time_from } - { slot.time_to })")

                a = (d, s - min_slot + 1)
                b = (d, s - min_slot + slot.slots)

                if slot.slots > 1:
                    c = color_lookup(slot.priority)
                    style.append(("SPAN", a, b))
                    style.append(("BACKGROUND", a, b, c))

            else:
                line.append(None)

        data.append(line)

    elements = []
    if title:
        elements.append(Paragraph(title, style=style_h1))
    elements.append(Table(data, style=style))
    doc.build(elements)

    fd.seek(0)
    return send_file(
        fd,
        #as_attachment=True,
        #attachment_filename=f'planning_{planning_id}.pdf',
        mimetype='application/pdf'
    )

@bp.route('/planning/<int:planning_id>/settings', methods=("GET",))
@login_required
def planning_settings(planning_id:int):
    planning = get_db().execute("""
        SELECT
            id,
            range_attempts,
            range_increments,
            locked,
            stage,
            revision,
            last_update
        FROM
            scheduling
        WHERE
            id = ? AND
            teacher_id = ?
    """, (planning_id, g.user["id"])).fetchone()

    return render_template(
        "user/planning/settings.html",
        planning=planning,
    )

@bp.route('/planning/<int:planning_id>/settings', methods=("POST",))
@login_required
def planning_settings_save(planning_id:int):
    db = get_db()

    range_attempts = int(request.form['range_attempts'])
    range_increments = int(request.form['range_increments'])
    locked = bool(request.form.get('locked'))

    db.execute("""
        UPDATE
            scheduling
        SET
            range_attempts = ?,
            range_increments = ?,
            locked = ?
        WHERE
            id = ? AND
            teacher_id = ?
    """, (range_attempts, range_increments, locked, planning_id, g.user["id"]))

    db.commit()

    return redirect(url_for(".planning_settings", planning_id=planning_id))

@bp.route('/planning/<int:planning_id>/edit')
@login_required
def planning_edit(planning_id:int):
    slots, min_slot, max_slot = make_planning_table(planning_id)

    if min_slot is None:
        return render_template(
            "user/planning/unavailable.html",
            planning_id=planning_id,
            plannings=get_plannings()
        )

    return render_template(
        "user/planning/result.html",
        planning_id=planning_id,
        plannings=get_plannings(),
        slots=slots,
        min_slot=min_slot,
        max_slot=max_slot,
        times=make_times(),
        dayname=dayname,
        editstart=True,
        altslots=None
    )

AltSlot = namedtuple("AltSlot", ["student_planning_id", "priority", "length_slots"])

def make_altslots(student_planning_id: int, slots):
    teacher_id = g.user["id"]
    student_planning = get_db().execute("""
        SELECT
            a.priority,
            a.day,
            a.time_from,
            a.time_to,
            p.lesson_length
        FROM
            student_planning p
        JOIN
            student_availability a ON a.student_planning_id = p.id
        WHERE
            p.id = ? AND
            p.teacher_id = ?
    """, (student_planning_id, teacher_id))

    altslots = [[None for _ in range(slots_per_day)] for _ in range(days_per_week)]

    for priority, day, time_from, time_to, lesson_length in student_planning:
        lesson_length = int(lesson_length)
        length_slots, offset = divmod(lesson_length, slot_increment)
        assert offset == 0

        from_slot = ceil(make_minute_of_day(time_from) / slot_increment)
        to_slot = floor(make_minute_of_day(time_to) / slot_increment)

        for s in range(from_slot, to_slot - length_slots + 1):
            if not any(slots[day][s + i] for i in range(length_slots)) and (altslots[day][s] is None or altslots[day][s].priority > priority):
                altslots[day][s] = AltSlot(student_planning_id, priority, length_slots)

    return altslots

@bp.route('/planning/<int:planning_id>/edit/<int:student_planning_id>', methods=("GET",))
@login_required
def planning_edit_student(planning_id:int, student_planning_id:int):
    slots, min_slot, max_slot = make_planning_table(planning_id, exclude=student_planning_id)

    if min_slot is None:
        return render_template(
            "user/unavailable.html",
            planning_id=planning_id,
            plannings=get_plannings()
        )

    return render_template(
        "user/planning/result.html",
        planning_id=planning_id,
        plannings=get_plannings(),
        slots=slots,
        min_slot=min_slot,
        max_slot=max_slot,
        times=make_times(),
        dayname=dayname,
        editstart=False,
        altslots=make_altslots(student_planning_id, slots)
    )

@bp.route('/planning/<int:planning_id>/edit/<int:student_planning_id>', methods=("POST",))
@login_required
def planning_place_student(planning_id:int, student_planning_id:int):
    teacher_id = g.user["id"]

    db = get_db()

    day = int(request.form['day'])
    slot = int(request.form['slot'])
    length_slots = int(request.form['length'])

    student_id, = get_db().execute("""
        SELECT
            student_id
        FROM
            student_planning
        WHERE
            id = ? AND
            teacher_id = ?
    """, (student_planning_id, teacher_id)).fetchone()

    time_from = make_time_from_minutes(slot * slot_increment)
    time_to = make_time_from_minutes((slot + length_slots) * slot_increment)

    db.execute("""
        UPDATE
            student_scheduling
        SET
            day = ?,
            time_from = ?,
            time_to = ?
        WHERE
            scheduling_id = ? AND
            student_id = ?
    """, (day, time_from, time_to, planning_id, student_id))

    db.commit()

    return redirect(url_for(".planning_edit", planning_id=planning_id))
