# Guia de Uso Rápido

```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")

for i in logger.progress(range(5), desc="Trabalhando"):
    logger.debug(f"Passo {i}")

logger.end()
```

A função `start_logger` retorna um objeto `Logger` já configurado com cores, níveis personalizados e handlers de arquivo. Ao final da execução, `logger.end()` é chamado automaticamente, exibindo um banner de resumo.
