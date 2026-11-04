"""Acentuación independente (ferramentas/acentuacion.py) e corrección dos
tiles de Hunspell nas formas con enclíticos."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))

import acentuacion as A  # noqa: E402

CASOS = [
    # regra xeral: a sílaba tónica non cambia; o til ponse segundo as Normas
    ("fala", "me", "fálame"), ("comer", "lo", "comelo"), ("dixen", "lle", "díxenlle"),
    ("falou", "me", "faloume"), ("cantade", "o", "cantádeo"), ("dixemos", "lo", "dixémolo"),
    ("dará", "lle", "daralle"), ("está", "che", "estache"), ("estás", "lle", "estaslle"),
    ("deu", "lle", "deulle"), ("cantei", "no", "canteino"), ("partiu", "no", "partiuno"),
    ("golpeabamos", "te", "golpeabámoste"), ("aterrásemos", "las", "aterrásemolas"),
    ("abrir", "lo", "abrilo"), ("seguir", "te", "seguirte"), ("erguede", "vos", "erguédevos"),
    # hiatos: i/u tónicos xunto a vogal levan sempre til
    ("saía", "me", "saíame"), ("oír", "lo", "oílo"), ("traía", "lle", "traíalle"),
    ("continúa", "o", "continúao"), ("abandonaría", "a", "abandonaríaa"), ("crían", "o", "críano"),
    ("construíu", "cha", "construíucha"), ("oíu", "no", "oíuno"), ("caín", "nos", "caínnos"),
    ("ri", "a", "ría"), ("argüír", "lo", "argüílo"),
    # ditongos e tritongos
    ("abriu", "lles", "abriulles"), ("abriu", "llela", "abríullela"), ("apoiaban", "a", "apoiábana"), ("caia", "che", "cáiache"),
    ("vaia", "o", "váiao"), ("vai", "no", "vaino"), ("odia", "a", "ódiaa"), ("irei", "no", "ireino"),
    ("apoiara", "me", "apoiárame"), ("muiñar", "lo", "muiñalo"), ("averigüe", "o", "averígüeo"),
    # pór e compostos: estiver, der
    ("estiver", "la", "estivela"), ("digamos", "lo", "digámolo"), ("digades", "me", "digádesme"),
]


class ProbasAcentuacion(unittest.TestCase):
    def test_casos(self):
        for base, pron, esperada in CASOS:
            with self.subTest(base=base, pron=pron):
                self.assertIn(esperada, A.predicir_todas(base, pron))

    def test_vogal_tonica(self):
        for palabra, pos in (("falar", 3), ("fala", 1), ("falou", 3), ("cantei", 4), ("comer", 3),
                             ("dixen", 1), ("saía", 2), ("abriu", 3), ("vaia", 1), ("muito", 1), ("ruín", 2)):
            with self.subTest(palabra=palabra):
                self.assertEqual(A.vogal_tonica(palabra), pos)


if __name__ == "__main__":
    unittest.main()
