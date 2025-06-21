# Casos de Uso e Exemplos

## Monitoramento de Sistema

```python
from logger import start_logger

logger = start_logger("Monitor")
logger.log_system_status()
logger.end()
```

## Verificação de Conectividade

```python
logger.check_connectivity(["https://www.google.com", "https://pypi.org"])
```
