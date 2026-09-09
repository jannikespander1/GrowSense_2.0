import sensor_reader

_tilstand = {
    "pumpe":       False,
    "lysprofil":   "standard",
    "soil_min_p1": 50,
    "soil_max_p1": 70,
    "soil_min_p2": 50,
    "soil_max_p2": 70,
}


def set_pumpe(state: bool):
    _tilstand["pumpe"] = state
    sensor_reader.send("indstil:pumpe={}".format("TIL" if state else "FRA"))


def set_profiler(profil_p1: dict, profil_p2: dict, lysprofil: str = "standard"):
    _tilstand["soil_min_p1"] = profil_p1["soil_min"]
    _tilstand["soil_max_p1"] = profil_p1["soil_max"]
    _tilstand["soil_min_p2"] = profil_p2["soil_min"]
    _tilstand["soil_max_p2"] = profil_p2["soil_max"]
    _tilstand["lysprofil"]   = lysprofil

    sensor_reader.send("indstil:soil_min_p1={},soil_max_p1={},soil_min_p2={},soil_max_p2={},lysprofil={}".format(
        profil_p1["soil_min"], profil_p1["soil_max"],
        profil_p2["soil_min"], profil_p2["soil_max"],
        lysprofil,
    ))


def set_lysprofil(navn: str):
    if navn in ("seedling", "standard"):
        _tilstand["lysprofil"] = navn
        sensor_reader.send("indstil:lysprofil={}".format(navn))


def set_lys_tilladt(state: bool):
    sensor_reader.send("indstil:lys={}".format("TIL" if state else "FRA"))


def get_tilstand() -> dict:
    return _tilstand.copy()
