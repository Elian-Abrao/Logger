# Referência de API

## logger.start_logger
`start_logger(name, log_dir='Logs', console_level='INFO', file_level='DEBUG', capture_prints=True, verbose=0, *, show_all_leaks=False, watch_objects=None) -> logging.Logger`

Cria e configura uma instância de `logging.Logger` com recursos adicionais.

Principais parâmetros:
- **name**: nome base do logger
- **log_dir**: pasta onde os arquivos serão salvos
- **console_level**: nível exibido no console
- **file_level**: nível gravado nos arquivos

Retorna um logger com métodos extras como `progress`, `screen`, `timer` e outros.

Consulte os módulos em `logger/extras` para detalhes.
