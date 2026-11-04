"""Formata os ficheiros de correccións cunha cela por liña, para que sexan fáciles de ler e revisar."""

import json
import sys
from pathlib import Path


def formatar(datos: dict) -> str:
    liñas = ["{"]
    claves = list(datos)
    for i, clave in enumerate(claves):
        coma = "," if i < len(claves) - 1 else ""
        valor = datos[clave]
        if not isinstance(valor, dict):
            liñas.append(f"  {json.dumps(clave, ensure_ascii=False)}: {json.dumps(valor, ensure_ascii=False)}{coma}")
            continue
        liñas.append(f"  {json.dumps(clave, ensure_ascii=False)}: {{")
        if "nota" in valor:
            liñas.append(f'    "nota": {json.dumps(valor["nota"], ensure_ascii=False)},')
        liñas.append('    "celas": {')
        celas = list(valor.get("celas", {}).items())
        for j, (c, v) in enumerate(celas):
            coma2 = "," if j < len(celas) - 1 else ""
            liñas.append(f"      {json.dumps(c, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}{coma2}")
        liñas.append("    }")
        liñas.append(f"  }}{coma}")
    liñas.append("}")
    return "\n".join(liñas) + "\n"


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        p = Path(ruta)
        p.write_text(formatar(json.loads(p.read_text(encoding="utf-8"))), encoding="utf-8")
