import os
import requests

NTFY_EMNE = "growsense-grp5-7f2ab91"


def send_notifikation(besked: str, titel: str = "GrowSense"):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_EMNE}",
            data=besked.encode("utf-8"),
            headers={"Title": titel},
            timeout=5,
        )
    except Exception as e:
        print(f"Kunne ikke sende notifikation: {e}")


def send_billede(billede_sti: str, besked: str, titel: str = "GrowSense"):
    try:
        with open(billede_sti, "rb") as f:
            billede_data = f.read()

        requests.put(
            f"https://ntfy.sh/{NTFY_EMNE}",
            data=billede_data,
            headers={
                "Title": titel,
                "Message": besked,
                "Filename": os.path.basename(billede_sti),
            },
            timeout=10,
        )
    except Exception as e:
        print(f"Kunne ikke sende billede-notifikation: {e}")
