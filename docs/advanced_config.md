# Configurações Avançadas

`start_logger` aceita parâmetros opcionais para customizar o comportamento:

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `verbose` | `0` | Define detalhamento do log de arquivos |
| `capture_prints` | `True` | Redireciona chamadas `print` |
| `show_all_leaks` | `False` | Mostra todas as diferenças na checagem de memória |
| `watch_objects` | `None` | Tipos de objetos monitorados em vazamento |

Também é possível modificar níveis de log e diretórios via argumentos.
