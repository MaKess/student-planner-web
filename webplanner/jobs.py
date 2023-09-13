from crypt import methods
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, jsonify, abort
from webplanner.db import get_db
from webplanner.index import login_required
from webplanner.defines import dayname_en, dayname_int

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/')
def list_jobs():
    return jsonify([dict(row) for row in get_db().execute("""
        SELECT
            id AS job_id,
            range_attempts,
            range_increments
            revision
        FROM
            scheduling
        WHERE
            stage = 1 AND NOT locked
        ORDER BY
            last_update ASC
    """)])

@bp.route("/<int:job_id>", methods=("GET",))
def get_job(job_id: int):
    db = get_db()

    if True:
        rowcount = db.execute("""
            UPDATE
                scheduling
            SET
                stage = 2
            WHERE
                id = ? AND stage = 1
        """, (job_id,)).rowcount
        db.commit()

        #if rowcount != 1:
        #    abort(410)  # 410 = Gone: job has already been claimed

    teacher_id, range_attempts, range_increments, revision = db.execute("""
        SELECT
            teacher_id,
            range_attempts,
            range_increments,
            revision
        FROM
            scheduling
        WHERE
            id = ?
        LIMIT 1
    """, (job_id,)).fetchone()

    teacher_id = int(teacher_id)
    range_attempts = int(range_attempts)
    range_increments = int(range_increments)
    revision = int(revision)

    availability = db.execute("""
        SELECT
            s.id AS id,
            s.name_given AS name_given,
            s.name_family AS name_family,
            p.lesson_length AS lesson_length,
            a.day AS day,
            a.time_from AS time_from,
            a.time_to AS time_to
        FROM
            student s
        JOIN
            student_planning p ON p.student_id = s.id
        JOIN
            student_availability a ON a.student_planning_id = p.id
        WHERE
            p.teacher_id = ?
        ORDER BY
            p.priority ASC,
            p.id ASC, -- only necessary when multiple students can have the same priority
            a.priority ASC
    """, (teacher_id,))

    last_s_id = None
    availabilities = None

    student_availabilities = []
    ret = {
        "job_id": job_id,
        "teacher_id": teacher_id,
        "range_attempts": range_attempts,
        "range_increments": range_increments,
        "revision": revision,
        "student_availabilities": student_availabilities
    }
    for s_id, s_name_given, s_name_family, p_lesson_length, a_day, a_time_from, a_time_to in availability:
        from_hour, from_minute = a_time_from.split(":")
        to_hour, to_minute = a_time_to.split(":")
        availability = {
                "day": dayname_en[a_day].upper(),
                "from_hour": int(from_hour),
                "from_minute": int(from_minute),
                "to_hour": int(to_hour),
                "to_minute": int(to_minute)
            }

        if s_id == last_s_id:
            availabilities.append(availability)
        else:
            availabilities = [availability]
            student_availabilities.append({
                "id": s_id,
                "name": f"{s_name_given} {s_name_family.upper()}",
                "lesson_duration": p_lesson_length,
                "availabilities": availabilities
            })
            last_s_id = s_id

    return jsonify(ret)

@bp.route("/<int:job_id>", methods=("POST",))
def post_job(job_id: int):
    request_data = request.get_json()

    request_options = request_data["options"]

    assert job_id == request_options["job_id"]

    cur = get_db().cursor()
    cur.execute("BEGIN")
    old_revision, = cur.execute("SELECT revision FROM scheduling WHERE id = ?", (job_id,)).fetchone()
    assert int(old_revision) == request_options["revision"]
    cur.execute("DELETE FROM student_scheduling WHERE scheduling_id = ?", (job_id,))

    if request_options["success"]:
        cur.executemany("INSERT INTO student_scheduling (scheduling_id, student_id, day, time_from, time_to) VALUES (?, ?, ?, ?, ?)",
            (
                (
                    job_id,
                    schedule_data["id"],
                    dayname_int[schedule_data["day"]],
                    f"{schedule_data['from_hour']:02d}:{schedule_data['from_minute']:02d}",
                    f"{schedule_data['to_hour']:02d}:{schedule_data['to_minute']:02d}"
                ) for schedule_data in request_data["schedule"]
            )
        )
        new_stage = 3  # success
    else:
        new_stage = 4  # failure

    cur.execute("UPDATE scheduling SET stage = ?, last_update = CURRENT_TIMESTAMP WHERE id = ?", (new_stage, job_id))
    cur.execute("COMMIT")

    return ""
