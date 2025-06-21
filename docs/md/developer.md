# Manual do Desenvolvedor

## Estrutura de Pastas

```
logger/
  core/        # Configuração principal e contexto
  extras/      # Funcionalidades adicionais (metrics, network, monitoring)
  formatters/  # Formatadores de log coloridos
  handlers/    # Handlers customizados
  tests/       # Suite de testes com pytest
```

A função principal é `start_logger` em `logger.core.logger_core`. Os módulos em `extras` estendem o logger com métricas, monitoramento de rede, captura de prints, entre outros.

## Convenções de Código

- Estilo formatado com **ruff** e **black**.
- Docstrings em português.
- Utilização opcional de emojis nas mensagens 😄.
- Progressos impressos via `LoggerProgressBar`.

## Versionamento

O projeto utiliza o padrão **SemVer**. O branch principal é `main` e as contribuições são feitas via Pull Request.

## Contribuição

1. Crie um fork e branch para sua feature.
2. Execute os testes: `pytest --cov=logger`.
3. Abra o PR seguindo o template do repositório.
