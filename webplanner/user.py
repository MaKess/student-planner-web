from flask import Blueprint, flash, g, redirect, render_template, url_for, send_file
from webplanner.db import get_db
from webplanner.index import login_required
from webplanner.defines import dayname
from collections import namedtuple


bp = Blueprint('user', __name__, url_prefix='/user')

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

@bp.route('/availability')
@login_required
def availability():
    return render_template(
        "user/availability.html",
        availabilities=get_teacher_availability(),
        dayname=dayname
    )

def get_plannings():
    return get_db().execute("""
        SELECT
            id,
            range_attempts,
            range_increments
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
        teacher_id = ?
    """, (teacher_id,))

@bp.route('/planning')
@login_required
def planning_index():
    plannings = get_plannings()
    first_planning_id = int(plannings[0]["id"])
    return redirect(url_for("user.planning", planning_id=first_planning_id))

PlanningSlot = namedtuple("PlanningSlot", ["id", "name_given", "name_family", "day", "time_from", "time_to", "slots"])

def make_planning_table(planning_id: int):
    student_scheduling = get_db().execute("""
        SELECT
            s.id,
            s.name_given,
            s.name_family,
            ss.day,
            ss.time_from,
            ss.time_to
        FROM
            student_scheduling ss
        JOIN
            student s ON ss.student_id = s.id
        JOIN
            scheduling x on x.teacher_id = ? AND x.id = ss.scheduling_id AND x.stage = 3
        WHERE
            ss.scheduling_id = ?
    """, (g.user["id"], planning_id))

    slot_increment = 10

    min_slot = None
    max_slot = None

    days_per_week = 7
    slots_per_day = 24 * 60 // slot_increment

    slots = [[None for _ in range(slots_per_day)] for _ in range(days_per_week)]

    for s_id, name_given, name_family, day, time_from, time_to in student_scheduling:
        from_hour, from_minute = time_from.split(":")
        to_hour, to_minute = time_to.split(":")

        from_minute_of_day = int(from_hour) * 60 + int(from_minute)
        to_minute_of_day = int(to_hour) * 60 + int(to_minute)


        from_slot, offset = divmod(from_minute_of_day, slot_increment)
        assert offset == 0

        to_slot, offset = divmod(to_minute_of_day, slot_increment)
        assert offset == 0


        if min_slot is None or from_slot < min_slot:
            min_slot = from_slot

        if max_slot is None or to_slot > max_slot:
            max_slot = to_slot


        slots[day][from_slot] = PlanningSlot(s_id, name_given, name_family, day, time_from, time_to, to_slot - from_slot)

        for i in range(from_slot + 1, to_slot):
            slots[day][i] = False

    times = []
    for s in range(slots_per_day):
        hour, minute = divmod(s * slot_increment, 60)
        times.append(f"{hour:02d}:{minute:02d}")

    return slots, min_slot, max_slot, times

@bp.route('/planning/<int:planning_id>')
@login_required
def planning(planning_id:int):
    slots, min_slot, max_slot, times = make_planning_table(planning_id)

    if min_slot is None:
        return render_template("user/noplanning.html")

    return render_template(
        "user/planning.html",
        planning_id=planning_id,
        plannings=get_plannings(),
        slots=slots,
        min_slot=min_slot,
        max_slot=max_slot,
        times=times,
        dayname=dayname
    )

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.platypus.paragraph import Paragraph

from io import BytesIO

@bp.route('/planning/<int:planning_id>/pdf')
@login_required
def planning_export_pdf(planning_id:int):

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

    slots, min_slot, max_slot, times = make_planning_table(planning_id)
    for s in range(min_slot, max_slot + 1):
        line = [times[s]] # the first cell is is the time (e.g. "11:30")

        for d in r:
            slot = slots[d][s]

            if slot:
                line.append(f"{slot.name_given} {slot.name_family}\n({ slot.time_from } - { slot.time_to })")

                a = (d, s - min_slot + 1)
                b = (d, s - min_slot + slot.slots)

                if slot.slots > 1:
                    style.append(("SPAN", a, b))
                    style.append(("BACKGROUND", a, b, colors.lightblue))

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
        #download_name=f'planning_{planning_id}.pdf',
        mimetype='application/pdf'
    )