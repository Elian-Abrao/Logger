# Manual do Desenvolvedor

## Estrutura de Pastas
```
logger/
  core/        # núcleo de configuração
  extras/      # funcionalidades auxiliares
  handlers/    # handlers customizados
  formatters/  # formatadores de log
  tests/       # suíte de testes
```

## Convenções
- Código formatado com **black** e verificado por **ruff**
- Tipagem estática com **mypy**
- Utilize emojis nos logs para facilitar a leitura 😄
- Barras de progresso opcionais via `logger.progress`

## Fluxo de Contribuição
1. Crie uma branch a partir de `main`
2. Escreva testes para novas features
3. Execute `ruff`, `mypy` e `pytest`
4. Abra um Pull Request descrevendo a mudança

Política de versionamento: **SemVer** seguindo `pyproject.toml`.
