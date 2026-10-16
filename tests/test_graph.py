"""Tests de non-régression du graphe : invariants de structure et cas de référence.

    python -m unittest discover -s tests -v

Ils lisent data/graph/ et data/review/ (produits par pipeline/run_all.py) et ne font aucun appel réseau.
"""
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G = ROOT / "data" / "graph"
ISO = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def load(name):
    return json.loads((G / name).read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load("nodes.json")
        cls.edges = load("edges.json")
        cls.by_id = {n["id"]: n for n in cls.nodes}
        cls.orgs = {n["title"]: n for n in cls.nodes if n["type"] == "org"}
        cls.people = {n["title"]: n for n in cls.nodes if n["type"] == "person"}


class TestStructure(Base):
    def test_volumes_minimaux(self):
        self.assertGreater(len(self.orgs), 600)
        self.assertGreater(len(self.people), 2000)
        self.assertGreater(len([e for e in self.edges if e["layer"] == "org_org"]), 500)

    def test_identifiants_uniques_et_aretes_valides(self):
        self.assertEqual(len(self.by_id), len(self.nodes))
        for e in self.edges:
            self.assertIn(e["source"], self.by_id, e)
            self.assertIn(e["target"], self.by_id, e)

    def test_dates_bien_formees_et_ordonnees(self):
        for n in self.orgs.values():
            for k in ("start", "end"):
                if n[k]:
                    self.assertRegex(n[k], ISO, (n["title"], k, n[k]))
            if n["start"] and n["end"]:
                self.assertLessEqual(n["start"][:4], n["end"][:4], n["title"])
        for e in self.edges:
            if e["layer"] == "person_org":
                for k in ("start", "end"):
                    if e[k]:
                        self.assertRegex(e[k], ISO, e)
                if e["start"] and e["end"]:
                    self.assertLessEqual(e["start"][:4], e["end"][:4], e)

    def test_positions_dans_l_echelle(self):
        for n in self.orgs.values():
            if n["position_value"] is not None:
                self.assertTrue(-3 <= n["position_value"] <= 3, n["title"])

    def test_pas_de_cycle_de_scission_ni_de_succession(self):
        for typ in ("split", "succession"):
            adj = {}
            for e in self.edges:
                if e["layer"] == "org_org" and e["type"] == typ:
                    adj.setdefault(e["source"], []).append(e["target"])
            state = {}

            def dfs(u):
                state[u] = 1
                for v in adj.get(u, []):
                    self.assertNotEqual(state.get(v), 1, f"cycle {typ} via {u} -> {v}")
                    if not state.get(v):
                        dfs(v)
                state[u] = 2

            for u in list(adj):
                if not state.get(u):
                    dfs(u)

    def test_couverture_des_organisations_attendues(self):
        with (ROOT / "data" / "review" / "coverage_check.csv").open(encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))[1:]
        self.assertEqual([r[0] for r in rows if r[1] == "ABSENT"], [])


class TestCasDeReference(Base):
    def test_rassemblement_national(self):
        rn = self.orgs["Rassemblement national"]
        self.assertEqual(rn["start"][:4], "1972")
        self.assertEqual([c["label"] for c in rn["name_changes"]], ["FN", "RN"])
        self.assertEqual(rn["position_codes"], ["extreme_droite"])

    def test_lignee_gaulliste_sur_une_meme_ligne(self):
        titres = ("Rassemblement pour la République", "Union pour un mouvement populaire", "Les Républicains")
        lignees = {self.orgs[t]["lineage"]["id"] for t in titres}
        self.assertEqual(len(lignees), 1)

    def test_parti_socialiste(self):
        ps = self.orgs["Parti socialiste (France)"]
        self.assertEqual(ps["start"][:4], "1969")
        self.assertEqual(ps["status"], "actif")
        courants = [e for e in self.edges if e["type"] == "current_of" and e["target"] == ps["id"]]
        self.assertGreaterEqual(len(courants), 10)
        chefs = [e for e in self.edges if e["layer"] == "person_org" and e["type"] == "leader" and e["target"] == ps["id"]]
        self.assertGreaterEqual(len(chefs), 15)

    def test_parcours_de_philippot(self):
        p = self.people["Florian Philippot"]
        cibles = {self.by_id[e["target"]]["title"] for e in self.edges
                  if e["layer"] == "person_org" and e["source"] == p["id"]}
        self.assertIn("Rassemblement national", cibles)
        self.assertIn("Les Patriotes (parti politique)", cibles)

    def test_resultats_electoraux_repartis_dans_la_lignee(self):
        annees = lambda t: {e["date"][:4] for e in self.orgs[t]["elections"] if e["type"] == "parliament"}
        self.assertTrue({"2002", "2007", "2012"} <= annees("Union pour un mouvement populaire"))
        self.assertTrue({"2017", "2022"} <= annees("Les Républicains"))
        self.assertGreaterEqual(len(annees("Parti socialiste (France)")), 10)
        self.assertIn("1986", annees("Rassemblement national"))

    def test_positions_d_experts(self):
        pcf = self.orgs["Parti communiste français"]
        self.assertTrue(pcf["expert_positions"])
        self.assertTrue(all(-3 <= e["lrgen"] <= 3 for e in pcf["expert_positions"]))

    def test_scission_npa_revolution_permanente(self):
        a = self.orgs["Nouveau Parti anticapitaliste"]["id"]
        b = self.orgs["Révolution permanente (parti politique)"]["id"]
        self.assertTrue(any(e["type"] == "split" and e["source"] == a and e["target"] == b for e in self.edges))


if __name__ == "__main__":
    unittest.main()
