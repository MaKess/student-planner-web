DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS teacher_availability;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS student_planning;
DROP TABLE IF EXISTS student_availability;
DROP TABLE IF EXISTS scheduling;
DROP TABLE IF EXISTS student_scheduling;

-- users that are teacher or administration and can check the availability
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    `password` TEXT NOT NULL,
    name_given TEXT NOT NULL,
    name_family TEXT NOT NULL
);

CREATE TABLE teacher_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    day INTEGER NOT NULL,
    time_from TIME NOT NULL,
    time_to TIME NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES user (id)
);

-- table of students that can enter their availability
CREATE TABLE student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_given TEXT NOT NULL,
    name_family TEXT NOT NULL,
    email TEXT,
    phone TEXT
);

CREATE TABLE student_planning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    `priority` INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    lesson_length INTEGER NOT NULL,
    invite_code TEXT NOT NULL UNIQUE,
    priority_family BOOLEAN,
    fm_day INTEGER,
    fm_time_from TIME,
    fm_time_to TIME,
    FOREIGN KEY (teacher_id) REFERENCES user (id),
    FOREIGN KEY (student_id) REFERENCES student (id),
    UNIQUE(student_id, teacher_id),
    UNIQUE(invite_code)
    --, UNIQUE(`priority`, teacher_id)
);

CREATE TABLE student_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_planning_id INTEGER NOT NULL,
    `priority` INTEGER NOT NULL,
    `day` INTEGER NOT NULL,
    time_from TIME NOT NULL,
    time_to TIME NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_planning_id) REFERENCES student_planning (id),
    UNIQUE(student_planning_id, `priority`)
);

CREATE TABLE scheduling (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    range_attempts INTEGER NOT NULL DEFAULT 10,
    range_increments INTEGER NOT NULL DEFAULT 1,
    minimize_wishes_prio BOOLEAN NOT NULL DEFAULT TRUE,
    minimize_holes BOOLEAN NOT NULL DEFAULT TRUE,
    availability_index_scale INTEGER NOT NULL DEFAULT 5,
    lunch_time_from TIME NOT NULL DEFAULT '12:00',
    lunch_time_to TIME NOT NULL DEFAULT '13:00',
    lunch_hole_neg_prio INTEGER NOT NULL DEFAULT 10,
    non_lunch_hole_prio INTEGER NOT NULL DEFAULT 150,

    locked BOOLEAN NOT NULL DEFAULT 0,

    stage INTEGER NOT NULL DEFAULT 0,
        -- 0: idle (nothing entered yet, don't bother checking it out)
        -- 1: ready (changes have been entered)
        -- 2: working (some worker is supposed to number-crunch this)
        -- 3: success (the result has been uploaded)
        -- 4: failure (calculating the result was not possible)

    revision INTEGER NOT NULL,

    last_update TIMESTAMP,

    FOREIGN KEY (teacher_id) REFERENCES user (id)
);

CREATE TABLE student_scheduling (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduling_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    day INTEGER NOT NULL,
    time_from TIME NOT NULL,
    time_to TIME NOT NULL,

    FOREIGN KEY (scheduling_id) REFERENCES scheduling (id),
    FOREIGN KEY (student_id) REFERENCES student (id)
);
