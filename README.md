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
