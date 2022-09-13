INSERT INTO user (
  id,
  email,
  `password`,
  name_given,
  name_family
) VALUES
  (1, "martin@moegger.de", "test", "Martin", "Keßler"),
  (2, "magali@bonopera.fr", "test123", "Magali", "Bonopera");


INSERT INTO teacher_availability (
    teacher_id,
    day,
    time_from,
    time_to
) VALUES
  (
    2, -- Magalichette
    1, -- Monday
    "16:15",
    "19:30"
  ),
  (
    2,
    2, -- Tuesday
    "16:00",
    "19:30"
  ),
  (
    2,
    3, -- Wednesday
    "09:00",
    "14:50"
  ),
  (
    2,
    3, -- Wednesday
    "16:40",
    "19:00"
  ),
  (
    2,
    4, -- Thursday
    "14:00",
    "19:00"
  );

INSERT INTO student (
    id,
    name_given,
    name_family
) VALUES
  (1, "Anouk", "Spella"),
  (2, "Jonas", "Beaudier"),
  (3, "Vanille", "Megy");

INSERT INTO student_planning (
    student_id,
    `priority`,
    teacher_id,
    lesson_length,
    invite_code
) VALUES
  (1, 1, 2, 40, "810-177"),
  (2, 2, 2, 30, "133-337"),
  (3, 3, 2, 30, "921-056");

INSERT INTO student_availability (
  student_planning_id,
  `priority`,
  `day`,
  time_from,
  time_to
) VALUES
  (1,1,3,'14:00','15:00'),
  (1,2,3,'10:00','11:00'),
  (2,1,3,'14:00','15:00'),
  (2,2,1,'18:00','20:00');

INSERT INTO scheduling (
    id,
    teacher_id,
    range_attempts,
    range_increments,
    stage,
        -- 0: idle (nothing entered yet, don't bother checking it out)
        -- 1: ready (changes have been entered)
        -- 2: working (some worker is supposed to number-crunch this)
        -- 3: success (the result has been uploaded)
        -- 4: failure (calculating the result was not possible)
    revision
) VALUES
  (1, 2, 7, 2, 1, 1),
  (2, 2, 7, 1, 1, 1);
