"""Analizadores de ferramentas/wiktionary.py sobre mostras sintéticas (o
Wiktionary non se pode consultar desde o contorno de construción)."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
import wiktionary as W  # noqa: E402

PAXINA_GL = """
== {{-gl-}} ==
{{pron|gl|ˈkasa}}
=== Substantivo ===
{{gl-subst|f}}
# [[Edificio]] ou parte del [[destinado]] a [[vivenda]].
#: ''A miña '''casa''' é pequena.''
# {{lb|gl|xogos}} Cada unha das [[casa|casiñas]] dun [[taboleiro]].<ref>DRAG</ref>
=== Verbo ===
# Terceira persoa do presente de [[casar]].
==== Sinónimos ====
* [[fogar]]
== {{-es-}} ==
=== Substantivo ===
# Vivienda (en castelán, non debe entrar).
"""


class ProbasWiktionaryGl(unittest.TestCase):
    def test_pagina(self):
        entradas = W.analizar_pagina_gl("casa", PAXINA_GL)
        self.assertEqual([e["categoria"] for e in entradas], ["substantivo", "verbo"])
        subst = entradas[0]
        self.assertEqual(subst["acepcions"][0]["definicion"], "Edificio ou parte del destinado a vivenda")
        self.assertEqual(subst["acepcions"][0]["exemplos"], ["A miña casa é pequena"])
        self.assertEqual(subst["acepcions"][1]["definicion"], "(xogos) Cada unha das casiñas dun taboleiro")
        self.assertNotIn("Vivienda", str(entradas))

    def test_sen_seccion_galega(self):
        self.assertEqual(W.analizar_pagina_gl("house", "== {{-en-}} ==\n=== Noun ===\n# A building."), [])


class ProbasKaikki(unittest.TestCase):
    def test_entrada(self):
        obx = {"word": "cadeira", "lang_code": "gl", "pos": "noun",
               "senses": [{"glosses": ["chair"], "examples": [{"text": "Senta na cadeira."}]},
                          {"glosses": ["hip"], "tags": ["anatomy"]}]}
        e = W.analizar_kaikki(obx)
        self.assertEqual(e["categoria"], "substantivo")
        self.assertEqual([a["definicion"] for a in e["acepcions"]], ["chair", "hip"])
        self.assertEqual(e["acepcions"][0]["exemplos"], ["Senta na cadeira."])
        self.assertEqual(e["acepcions"][1]["etiquetas"], ["anatomy"])
        self.assertIsNone(W.analizar_kaikki({"word": "silla", "lang_code": "es", "pos": "noun", "senses": []}))


if __name__ == "__main__":
    unittest.main()
