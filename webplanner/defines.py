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
