"""Lance toute la chaine, dans l'ordre. Chaque etape est reprenable (cache local).

    python pipeline/run_all.py            # tout
    python pipeline/run_all.py 5 6        # seulement les etapes 5 et 6 (construction + controle)

Etapes : 1 decouverte | 2 pages de partis | 3 analyse infobox | 4 personnes, relations Wikidata, dirigeants |
         5 elargissement | 6 enrichissement Wikidata | 7 construction du graphe | 8 controle |
         9 export du site | 10 liste des cas a valider
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = {
    1: ["s01_discover.py"],
    2: ["s02_fetch_parties.py"],
    3: ["s03_parse_parties.py"],
    4: ["s04a_wikidata_people.py", "s04c_wikidata_relations.py", "s04d_leaders.py", "s04b_people.py"],
    5: ["s02b_snowball.py", "s03_parse_parties.py", "s04d_leaders.py", "s04b_people.py", "s02b_snowball.py"],
    6: ["s02c_wikidata_entities.py", "s04e_external_data.py"],
    7: ["s05_build_graph.py"],
    8: ["s06_validate.py"],
    9: ["s07_export_site.py"],
    10: ["s08_review_list.py"],
}


def main():
    wanted = [int(a) for a in sys.argv[1:]] or sorted(STEPS)
    for n in wanted:
        for script in STEPS[n]:
            args = []
            print(f"\n=== etape {n} : {script} {' '.join(args)}", flush=True)
            r = subprocess.run([sys.executable, str(HERE / script), *args], cwd=str(HERE))
            if r.returncode != 0:
                print(f"ECHEC de {script} (code {r.returncode})")
                sys.exit(r.returncode)
    print("\nTermine.")


if __name__ == "__main__":
    main()
