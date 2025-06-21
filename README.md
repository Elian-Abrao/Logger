# Logger

![CI](https://github.com/Elian-Abrao/Logger/actions/workflows/ci.yml/badge.svg)

Biblioteca de logging estruturado. Veja `main.py` para um exemplo completo.

## Instalação

Com o Python instalado, instale o pacote e suas dependências em modo de
desenvolvimento:

```bash
pip install -e .[dev]
```

## Uso básico

Crie uma instância do logger chamando `start_logger`:

```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")
```

O método ``logger.end()`` é chamado automaticamente ao término do programa, mas pode ser invocado manualmente caso deseje encerrar o logger antecipadamente. Ao finalizar, um banner de resumo exibe métricas.
O detalhamento completo do profiling, com cadeia de chamadas e tempos, é registrado apenas nos arquivos de log.


Para mais exemplos consulte `main.py`.

## Testes e qualidade de código

Instale as dependências do projeto com:

```bash
pip install -e .[dev]
```

Para reproduzir exatamente o ambiente utilizado, instale a partir do arquivo
`requirements.lock` gerado via `pip freeze`:

```bash
pip install -r requirements.lock
```

Sempre que atualizar as dependências, execute:

```bash
pip freeze > requirements.lock
```
para sincronizar o arquivo de lock.

Com as dependências instaladas, execute as ferramentas de verificação:

```bash
ruff check .
mypy .
pytest --cov=logger
bandit -r logger
safety check -r requirements.lock || true
```

## Documentação

A documentação completa é gerada com **Sphinx** e publicada automaticamente no
GitHub Pages. Para gerar a versão local instale o Sphinx e execute:

```bash
pip install sphinx
```

```bash
make -C docs html
```

Para gerar os pacotes de distribuição execute:

```bash
python -m build
```

Os arquivos HTML serão gerados em `docs/build/html`.
