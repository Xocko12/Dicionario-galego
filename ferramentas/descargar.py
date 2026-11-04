"""Descarga as fontes externas en fontes/cache/ (non se suben ao repositorio).

Para Hunspell-gl descárgase o código fonte na versión fixada en fontes.json
e xúntanse as regras do módulo «norma» nun único fontes/cache/hunspell-gl/gl.aff,
como fai o seu SConstruct. Todos os módulos (.dic) quedan en src/.
"""

import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "fontes" / "cache"
HUNSPELL = CACHE / "hunspell-gl"


def descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"descargando {url}")
    peticion = urllib.request.Request(url, headers={"User-Agent": "dicionario-galego"})
    with urllib.request.urlopen(peticion) as resposta:
        destino.write_bytes(resposta.read())


def preparar_hunspell(fonte: dict, forzar: bool) -> None:
    marca = HUNSPELL / "VERSION"
    if marca.exists() and marca.read_text().strip() == fonte["versión"] and not forzar:
        print(f"xa existe  hunspell-gl {fonte['versión'][:8]}")
        return
    arquivo = CACHE / "hunspell-gl.tar.gz"
    descargar(fonte["arquivo"], arquivo)
    HUNSPELL.mkdir(parents=True, exist_ok=True)
    with tarfile.open(arquivo) as tar:
        for membro in tar.getmembers():
            partes = Path(membro.name).parts[1:]       # quitar o cartafol raíz
            if not partes or not (partes[0] in ("LICENSE", "README.rst", "CHANGELOG.rst") or partes[0] == "src"):
                continue
            membro.name = str(Path(*partes))
            tar.extract(membro, HUNSPELL, filter="data")
    arquivo.unlink()

    montar_aff()

    # gl.dic: todo o vocabulario da RAG, para validar con outras ferramentas (spylls)
    entradas = []
    for dic in ["norma/xeral.dic", "rag/gl/correcto.dic", "rag/gl/tolerado.dic",
                "rag/volga/correcto.dic", "rag/volga/tolerado.dic"]:
        for liña in (HUNSPELL / "src" / dic).open(encoding="utf-8"):
            liña = liña.split("#", 1)[0].strip()
            if liña:
                entradas.append(" ".join(liña.split()))
    entradas = list(dict.fromkeys(entradas))
    (HUNSPELL / "gl.dic").write_text(f"{len(entradas)}\n" + "\n".join(entradas) + "\n", encoding="utf-8")
    marca.write_text(fonte["versión"] + "\n")


def montar_aff() -> None:
    """gl.aff = norma/xeral.base + norma/xeral.aff, sen comentarios (como SConstruct),
    cos parches de fontes/parches.json."""
    parches = json.loads((RAIZ / "fontes" / "parches.json").read_text(encoding="utf-8"))["aff"]
    liñas = []
    for nome in ("xeral.base", "xeral.aff"):
        for liña in (HUNSPELL / "src" / "norma" / nome).open(encoding="utf-8"):
            liña = liña.split("#", 1)[0].strip()
            if liña:
                liñas.append(" ".join(liña.split()))
    for parche in parches:
        patron = re.compile(parche["buscar"])
        cambios = sum(1 for l in liñas if patron.search(l))
        liñas = [patron.sub(parche["substituir"], l) for l in liñas]
        print(f"parche: {cambios} regras corrixidas ({parche['nota'][:60]}...)")
    (HUNSPELL / "gl.aff").write_text("\n".join(liñas) + "\n", encoding="utf-8")


def extraer_arquivo(nome: str, arquivo: str, cfg: dict, forzar: bool) -> None:
    """Descarga un .tar.* e extrae só os cartafoles indicados en fontes/cache/<nome>/."""
    destino = CACHE / nome
    marca = destino / ".extraido"
    if marca.exists() and not forzar:
        print(f"xa existe  {destino.relative_to(RAIZ)}")
        return
    ruta = CACHE / arquivo
    descargar(cfg["url"], ruta)
    destino.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ruta) as tar:
        for membro in tar.getmembers():
            if any(membro.name.startswith(prefixo) for prefixo in cfg["extraer"]):
                membro.name = "/".join(membro.name.split("/")[1:])   # sen o cartafol raíz
                tar.extract(membro, destino, filter="data")
    ruta.unlink()
    marca.write_text(cfg["url"] + "\n")


def main() -> None:
    forzar = "--forzar" in sys.argv
    fontes = json.loads((RAIZ / "fontes" / "fontes.json").read_text(encoding="utf-8"))
    preparar_hunspell(fontes["hunspell-gl"], forzar)
    montar_aff()   # sempre, por se cambiaron os parches
    for nome, fonte in fontes.items():
        for arquivo, cfg in fonte.get("arquivos", {}).items():
            extraer_arquivo(nome, arquivo, cfg, forzar)
        for ficheiro, url in fonte.get("ficheiros", {}).items():
            destino = CACHE / nome / ficheiro
            if destino.exists() and not forzar:
                print(f"xa existe  {destino.relative_to(RAIZ)}")
                continue
            descargar(url, destino)


if __name__ == "__main__":
    main()
