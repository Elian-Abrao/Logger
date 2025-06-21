# Logger

![CI](https://github.com/Elian-Abrao/Logger/actions/workflows/ci.yml/badge.svg)

Biblioteca de logging estruturado com barra de progresso, métricas e monitoramento.

## Sumário

- [Instalação](#instala%c3%a7%c3%a3o)
- [Uso básico](#uso-b%c3%a1sico)
- [Testes e qualidade](#testes-e-qualidade)
- [Documentação](#documenta%c3%a7%c3%a3o)

## Instalação

```bash
pip install -e .[dev]
```

## Uso básico

```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")
for i in logger.progress(range(5), desc="Trabalhando"):
    logger.debug(f"Passo {i}")
```

`logger.end()` é chamado automaticamente no encerramento do programa, exibindo um banner resumo.

## Testes e qualidade

```bash
ruff check .
mypy .
pytest --cov=logger
bandit -r logger
safety check -r requirements.lock || true
```

## Documentação

Os guias completos estão em [docs/md/index.md](docs/md/index.md). Para gerar o site Sphinx localmente:

```bash
make -C docs html
```
