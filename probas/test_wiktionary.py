"""Analizadores de ferramentas/wiktionary.py sobre mostras sintéticas (o
Wiktionary non se pode consultar desde o contorno de construción)."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
import wiktionary as W  # noqa: E402

PAXINA_GL = """{{-glref-}}
{{etim|do {{orixe|la|gl}} ''{{la|casa}}''.}}
{{pronuncia|/ˈka.sa/}}
{{-substf-}}
'''{{PAGENAME}}'''<br> {{VarN|casa||s}}
#{{Gl|lugar}} {{gl|no}} {{gl|que}} {{gl|ser|se}} {{gl|habitar|habita}}.
#({{sem|Arquitectura}}) {{Gl|edificación}} {{gl|destinar|destinada}} a {{gl|vivenda}}.<ref>DRAG</ref>
#*{{exemplo|A miña <u>casa</u> é pequena.}}
#*{{sin|{{gl|fogar}}, {{gl|lar}}.}}
#*{{ant|{{gl|intemperie}}.}}
{{-obs-}}
{{Gl|na}} 1ª acepción son sinónimos {{gl|domicilio}}.
{{-verbo-|gl}}
'''{{PAGENAME}}'''
# Terceira persoa do presente de {{gl|casar}}.
{{-trad-}}
{{T|es}} {{t|es|casa}}.
{{-es-}}
{{-substf-|es}}
# Vivienda (en castelán, non debe entrar).
"""


class ProbasWiktionaryGl(unittest.TestCase):
    def test_pagina(self):
        entradas = W.analizar_pagina_gl("casa", PAXINA_GL)
        self.assertEqual([e["categoria"] for e in entradas], ["substantivo", "verbo"])
        subst = entradas[0]
        self.assertEqual(subst["xenero"], "feminino")
        self.assertEqual(subst["acepcions"][0]["definicion"], "Lugar no que se habita")
        self.assertEqual(subst["acepcions"][1]["definicion"], "(Arquitectura) Edificación destinada a vivenda")
        self.assertEqual(subst["acepcions"][1]["exemplos"], ["A miña casa é pequena"])
        self.assertEqual(subst["acepcions"][1]["sinonimos"], ["fogar", "lar"])
        self.assertEqual(subst["acepcions"][1]["antonimos"], ["intemperie"])
        self.assertEqual(entradas[1]["acepcions"][0]["definicion"], "Terceira persoa do presente de casar")
        self.assertNotIn("Vivienda", str(entradas))

    def test_sen_seccion_galega(self):
        self.assertEqual(W.analizar_pagina_gl("house", "{{-en-}}\n{{-subst-|en}}\n# A building."), [])


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
        self.assertNotIn("capa", e)       # intermedia: en inglés non se garda

    def test_traducir_entrada(self):
        obx = {"word": "cadeira", "lang_code": "gl", "pos": "noun",
               "senses": [{"glosses": ["chair"], "tags": ["feminine"], "examples": [{"text": "Senta na cadeira.\nSit on the chair."}]},
                          {"glosses": ["hip"], "tags": ["feminine", "figuratively"]},
                          {"glosses": ["seat"]},
                          {"glosses": ["professorship"]}]}
        e = W.analizar_kaikki(obx)
        traducions = {("cadeira", "substantivo", W.clave_glosa("chair")): "Asento con respaldo para unha persoa",
                      ("cadeira", "substantivo", W.clave_glosa("hip")): "Parte do corpo onde se unen a perna e o tronco",
                      ("cadeira", "substantivo", W.clave_glosa("seat")): "(Mobiliario) Asento con respaldo, para unha persoa."}
        existentes = {"cadeira": {W._normal("Parte do corpo onde se unen a perna e o tronco")}}
        t = W.traducir_entrada(e, traducions, existentes)
        self.assertEqual(t["capa"], "definicions-traducidas")
        # fóra a que xa está en definicions-gl, a repetida e a que non ten tradución
        self.assertEqual([a["definicion"] for a in t["acepcions"]], ["Asento con respaldo para unha persoa"])
        self.assertEqual(t["acepcions"][0]["exemplos"], ["Senta na cadeira."])
        self.assertNotIn("etiquetas", t["acepcions"][0])
        self.assertIsNone(W.traducir_entrada(e, {}, {}))

    def test_regras(self):
        self.assertEqual(W.traducir_por_regra("a parish of O Corgo, Lugo, Galicia"),
                         "Parroquia do concello do Corgo, na provincia de Lugo")
        self.assertEqual(W.traducir_por_regra("a village in Senra parish, Ortigueira, A Coruña, Galicia"),
                         "Lugar da parroquia de Senra, no concello de Ortigueira, na provincia da Coruña")
        self.assertEqual(W.traducir_por_regra("reintegrationist spelling of cartilla"), "Grafía reintegracionista de cartilla")
        self.assertEqual(W.traducir_por_regra("third-person plural preterite/pluperfect indicative of ser"), "")
        self.assertIsNone(W.traducir_por_regra("chair"))
        self.assertIsNone(W.analizar_kaikki({"word": "silla", "lang_code": "es", "pos": "noun", "senses": []}))


if __name__ == "__main__":
    unittest.main()
