# Testes e Qualidade

Execute a suíte completa:
```bash
pytest --cov=logger
```

Ferramentas adicionais:
```bash
ruff check .
mypy .
bandit -r logger
```
