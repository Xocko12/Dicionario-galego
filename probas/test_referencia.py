"""As táboas dos datos coinciden coa referencia (Normas / conxugador da RAG)."""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
import conxugacion as C  # noqa: E402


def taboas():
    saida = {}
    for ruta in [RAIZ / "datos" / "conxugacions.jsonl"] + sorted((RAIZ / "datos" / "capas").glob("*.jsonl")):
        for liña in ruta.open(encoding="utf-8"):
            r = json.loads(liña)
            if "taboa" in r:
                saida.setdefault(r["lema"], r["taboa"])
    return saida


class ProbasReferencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taboas = taboas()
        cls.referencia = json.loads((RAIZ / "datos" / "correccions" / "referencia.json").read_text(encoding="utf-8"))
        cls.referencia.pop("_descricion", None)

    def test_todos_os_verbos_de_referencia_existen(self):
        self.assertEqual([l for l in self.referencia if l not in self.taboas], [])

    def test_celas(self):
        for lema, ref in self.referencia.items():
            taboa = self.taboas.get(lema)
            if not taboa:
                continue
            for clave, valor in ref["celas"].items():
                base, _, persoa = clave.rpartition(".")
                if persoa in C.PERSOAS:
                    pares = [(clave, valor, taboa[base][C.PERSOAS.index(persoa)])]
                elif clave in ("participio", "xerundio", "infinitivo"):
                    pares = [(clave, valor, taboa[clave])]
                else:
                    pares = [(f"{clave}.{C.PERSOAS[p]}", c, taboa[clave][p]) for p, c in enumerate(valor)]
                for nome, esperado, obtido in pares:
                    with self.subTest(lema=lema, cela=nome):
                        self.assertEqual(set(obtido), set(esperado))


if __name__ == "__main__":
    unittest.main()
