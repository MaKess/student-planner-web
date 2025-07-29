dayname_fr = [
    "Dimanche",
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]

dayname_en = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

dayname = dayname_fr
dayname_int = {k: idx for idx, name in enumerate(dayname_en) for k in (name.upper(), idx)}

def sanitize_time(t):
    """
    reformat the time so that both the hour and minute are shown with two digits.
    this is required for SQLite. otherwise the comparison function "<", ">", "BETWEEN ... AND" don't work.
    """
    try:
        h, m, *_ = t.split(":")
        h = int(h)
        m = int(m)
        return f"{h:02d}:{m:02d}"
    except ValueError:
        return None
