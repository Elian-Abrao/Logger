# Configurações Avançadas

| Variável | Default | Descrição |
|----------|---------|-----------|
| `LOG_DIR` | `Logs` | Diretório base para armazenamento dos arquivos de log |
| `LOGGER_VERBOSE` | `0` | Nível de verbosidade extra nos arquivos |

### Linha de comando

Ao instalar o pacote é criado o script `logger-demo` que executa `main.py`. Exemplo:

```bash
logger-demo
```

### Arquivo de Configuração

Opcionalmente é possível criar um arquivo YAML para centralizar opções e carregar com `pyyaml` antes de chamar `start_logger`.
