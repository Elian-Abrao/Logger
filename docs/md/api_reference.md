# Referência de API

## `start_logger`

```python
def start_logger(
    name: str | None = None,
    log_dir: str = "Logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    capture_prints: bool = True,
    verbose: int = 0,
    *,
    show_all_leaks: bool = False,
    watch_objects: Iterable[str] | None = None,
) -> logging.Logger:
    ...
```

Cria e retorna uma instância de `Logger` já configurada. Os parâmetros permitem ajustar níveis de log, diretório de saída e verbosidade.

### Principais Métodos do Logger

- `progress(iterable, desc="", total=None)` → barra de progresso integrada.
- `timer(name="Tarefa")` → context manager para medir duração.
- `sleep(duration, unit="s")` → pausa com log.
- `log_environment()` → registra informações do ambiente.
- `check_connectivity(urls=None)` → testa conexão de rede.
- `log_system_status()` → CPU e memória atuais.
- `profile(func)` → decorador de profiling.
