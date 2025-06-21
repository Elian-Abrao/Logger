# Guia de Uso Rápido

Crie um logger minimalista:
```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")
```

O método `logger.end()` é acionado automaticamente ao finalizar o
programa. Para progress bar integrada:
```python
for i in logger.progress(range(5), desc="Trabalhando"):
    logger.debug(f"Passo {i}")
```
