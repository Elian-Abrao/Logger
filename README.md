# Logger

Biblioteca de logging estruturado. Veja `main.py` para um exemplo completo.

## Instalação

Com o Python instalado, instale o pacote e suas dependências em modo de
desenvolvimento:

```bash
pip install -e .
```

## Uso básico

Crie uma instância do logger chamando `start_logger`:

```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")
```

Para mais exemplos consulte `main.py`.

## Testes e qualidade de código

Instale as dependências do projeto com:

```bash
pip install -e .
```

Ou, se preferir, utilize o arquivo de requisitos:

```bash
pip install -r requirements.txt
```

Com as dependências instaladas, execute as ferramentas de verificação:

```bash
ruff check .
mypy .
pytest -q
```
