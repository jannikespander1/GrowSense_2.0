import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io, base64
from datetime import datetime

def _til_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

def _timestamps(raekker):
    tider = []
    for r in raekker:
        try:
            tider.append(datetime.strptime(r["timestamp"], "%d-%m-%Y %H:%M:%S"))
        except Exception:
            tider.append(None)
    return tider

def _lav_linje_graf(tider, vaerdier, titel, ylabel, farve, ymax=None):
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(tider, vaerdier, color=farve, marker="o", markersize=3, linewidth=1.5)
    ax.fill_between(tider, vaerdier, alpha=0.15, color=farve)
    ax.set_title(titel)
    ax.set_xlabel("Tidspunkt")
    ax.set_ylabel(ylabel)
    if ymax is not None:
        ax.set_ylim(0, ymax)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate(rotation=45)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _til_base64(fig)

def _varighed(tider, vaerdier):
    """Returnerer (minutter_fuld, minutter_tom) ud fra step-data."""
    fuld_sek = 0.0
    tom_sek = 0.0
    for i in range(1, len(tider)):
        if tider[i] is None or tider[i - 1] is None:
            continue
        dt = (tider[i] - tider[i - 1]).total_seconds()
        if vaerdier[i - 1] == 1:
            fuld_sek += dt
        else:
            tom_sek += dt
    return fuld_sek / 60.0, tom_sek / 60.0

def _lav_vandstand_graf(tider, vaerdier):
    fuld_min, tom_min = _varighed(tider, vaerdier)
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.step(tider, vaerdier, where="post", color="#0288D1", linewidth=1.8)
    ax.fill_between(tider, vaerdier, step="post", alpha=0.25, color="#0288D1")
    ax.set_title("Vandstand over tid  (Fuld: {:.1f} min  |  Tom: {:.1f} min)".format(fuld_min, tom_min))
    ax.set_xlabel("Tidspunkt")
    ax.set_ylabel("Beholder")
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Tom", "Fuld"])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate(rotation=45)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _til_base64(fig)

def lav_alle_grafer(raekker):
    tom = {"soil1": None, "soil2": None, "light": None, "vandstand": None}
    if not raekker:
        return tom

    tider       = _timestamps(raekker)
    soil1_vals  = []
    soil2_vals  = []
    light_vals  = []
    vand_vals   = []

    for r in raekker:
        try:
            soil1_vals.append(float(r.get("soil1", r.get("soil", 0))))
        except Exception:
            soil1_vals.append(0.0)
        try:
            soil2_vals.append(float(r.get("soil2", r.get("soil", 0))))
        except Exception:
            soil2_vals.append(0.0)
        try:
            light_vals.append(int(float(r.get("light", 0))))
        except Exception:
            light_vals.append(0)
        v = r.get("vandstand", "")
        vand_vals.append(1 if ("Massere" in v or v == "OK") else 0)

    return {
        "soil1":     _lav_linje_graf(tider, soil1_vals, "Jordfugtighed — Plante 1", "Fugtighed %",      "#2E7D32", ymax=100),
        "soil2":     _lav_linje_graf(tider, soil2_vals, "Jordfugtighed — Plante 2", "Fugtighed %",      "#1565C0", ymax=100),
        "light":     _lav_linje_graf(tider, light_vals, "Sollys over tid (%)",   "Lysintensitet %",  "#F9A825", ymax=100),
        "vandstand": _lav_vandstand_graf(tider, vand_vals),
    }