"""Mise a jour complete des donnees depuis Wikipedia et Wikidata, puis reconstruction.

    python pipeline/run_update.py            # tout : verification des pages, decouverte, reconstruction
    python pipeline/run_update.py --offline  # reconstruction et rapport seulement (pas de reseau)

Les etapes reseau tournent avec PARTIS_FRESH=1 (le cache n'est pas relu : les reponses neuves
le remplacent). Seules les pages dont la revision a change sont retelechargees ; les nouveaux
candidats sont decouverts par s01 puis telecharges par s02 et s02b. A la fin, le rapport
data/review/CHANGEMENTS.md decrit ce qui a bouge depuis la construction precedente.
Comptez 15 a 30 minutes selon le nombre de pages modifiees.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETWORK = [
    "s00_refresh.py", "s01_discover.py", "s02_fetch_parties.py", "s03_parse_parties.py",
    "s04a_wikidata_people.py", "s04b_people.py", "s02b_snowball.py", "s03_parse_parties.py",
    "s04b_people.py", "s02b_snowball.py", "s02c_wikidata_entities.py",
]
BUILD = ["s05_build_graph.py", "s06_validate.py", "s07_export_site.py", "s08_review_list.py", "s09_diff_builds.py"]


def run(script: str, env):
    print(f"\n=== {script}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / script)], cwd=str(HERE), env=env)
    if r.returncode != 0:
        print(f"ECHEC de {script} (code {r.returncode})")
        sys.exit(r.returncode)


def main():
    offline = "--offline" in sys.argv
    env = {**os.environ, "PARTIS_FRESH": "1", "PYTHONIOENCODING": "utf-8"}
    if not offline:
        for s in NETWORK:
            run(s, env)
    env["PARTIS_FRESH"] = "0"
    for s in BUILD:
        run(s, env)
    print("\nMise a jour terminee : voir data/review/CHANGEMENTS.md et data/review/RAPPORT.md")


if __name__ == "__main__":
    main()
