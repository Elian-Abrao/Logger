"""extras.py
-----------
Nome: Extras
Descricao: Funcionalidades adicionais como timer e barra de progresso.
Funcionalidades:
- Context manager para medir tempo
- Gerador de progresso simples
Uso:
    with Timer(logger, "passo"):
        ...
    for item in progress(items, desc="Iterando"):
        ...
"""

import time
from contextlib import contextmanager
from typing import Iterable, Iterator
from tqdm import tqdm


@contextmanager
def Timer(logger, name: str):
    """Context manager que mede a duracao de um bloco."""
    start = time.time()
    logger.info(f"Inicio {name}")
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.info(f"Fim {name} em {elapsed:.2f}s")


def progress(iterable: Iterable, desc: str = "") -> Iterator:
    """Iterador que mostra barra de progresso no console."""
    for item in tqdm(iterable, desc=desc):
        yield item
