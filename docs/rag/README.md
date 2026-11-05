# Comprobación coas táboas do conxugador da RAG

O conxugador da RAG (https://academia.gal/dicionario → ficha do verbo → «Conxugar»)
é a referencia. Pódese consultar automaticamente:

    python3 ferramentas/comparar_rag.py --rag moer reler        # verbos concretos
    python3 ferramentas/comparar_rag.py --rag --todos            # todos (unhas 2 h, 1 petición/s)
    python3 ferramentas/comparar_rag.py --rag --todos --aceptar  # e gardalos como referencia

As táboas descargadas quedan en `fontes/cache/rag/` e as diferenzas en
`docs/rag/diferenzas.tsv`. Se non hai acceso a academia.gal, a comparación
faise con táboas copiadas a man:

1. Abre o verbo no conxugador da RAG, selecciona toda a táboa e cópiaa.
2. Pégaa tal cal nun ficheiro `docs/rag/<verbo>.txt` (por exemplo `docs/rag/caber.txt`).
3. Executa:

       python3 ferramentas/comparar_rag.py docs/rag/

   Informa, verbo a verbo, das celas que non coinciden coas nosas táboas.

4. Se a táboa da RAG é a boa (normalmente o será), acéptaa:

       python3 ferramentas/comparar_rag.py --aceptar docs/rag/
       python3 ferramentas/importar.py && python3 ferramentas/capas.py

   Isto garda a táboa en `datos/correccions/referencia.json`, que manda sobre as
   regras de Hunspell-gl, e as probas (`probas/test_referencia.py`) comproban desde
   entón que os datos coincidan con ela.

Os ficheiros `.txt` quedan neste cartafol como rexistro do que se comprobou.

## Que verbos comprobar primeiro

Os irregulares e os modelos de cada familia xa están en `referencia.json`
(escritos desde as Normas). Primeiro de todo, **moer, roer, choer**, **reler, descrer** (*rele* ou *relé*?) e os
compostos de *traer* (*atraer, contraer, distraer*: pretérito regular *contraeu*?) (Hunspell-gl dá *moio/moia*; hai que
confirmar se a RAG dá *moo/moa*). Despois, os verbos de uso
frecuente con algunha irregularidade: compostos de *pór/ter/vir/dicir/facer*
(*supor, manter, convir, predicir, desfacer*), *ouvir, pracer, doer, choer,
roer, cocer, torcer, erguer, nacer, lucir, conducir, cuspir, tusir, bulir,
sumir, consumir, cubrir, descubrir, advertir, vestir, medir, repetir, espir,
competir, sufrir, cumprir, ferir, cinguir, tinguir, distinguir, argüír, posuír,
contribuír, delinquir, mercar, adquirir, ouvear, soer, xacer, pracer, prover,
reler, descrer, trasler*.
