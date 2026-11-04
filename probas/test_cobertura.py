"""Cantidade: todos os verbos dos módulos da RAG teñen táboa. Precisa fontes/cache/."""

import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "fontes" / "cache" / "hunspell-gl" / "src"


@unittest.skipUnless(SRC.exists(), "precisa fontes/cache/")
class ProbasCobertura(unittest.TestCase):
    def test_verbos_da_rag(self):
        verbos_fonte = set()
        for ruta in ("rag/gl/correcto.dic", "rag/gl/tolerado.dic", "rag/volga/correcto.dic", "rag/volga/tolerado.dic"):
            for liña in (SRC / ruta).open(encoding="utf-8"):
                liña = liña.split("#", 1)[0].strip()
                if " po:verbo" in liña and "666" not in liña.split()[0]:
                    palabra = liña.split()[0].split("/")[0]
                    if re.fullmatch(r"[a-záéíóúñü]+", palabra):
                        verbos_fonte.add(palabra)
        nosos = {json.loads(l)["lema"] for l in (RAIZ / "datos" / "conxugacions.jsonl").open(encoding="utf-8")}
        self.assertEqual(sorted(verbos_fonte - nosos), [])
        self.assertGreater(len(nosos), 6500)


if __name__ == "__main__":
    unittest.main()
