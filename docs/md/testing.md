# Testes & Qualidade

Execute a suíte de testes com cobertura:

```bash
pytest --cov=logger
```

Ferramentas adicionais:

```bash
ruff check .
mypy .
bandit -r logger
safety check -r requirements.lock || true
```
