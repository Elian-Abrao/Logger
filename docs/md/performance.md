# Desempenho e Escalabilidade

O logger possui suporte a profiling via `logger.profile` e `profile_report`, permitindo identificar gargalos.

Para habilitar profiling manualmente:

```python
with logger.profile_cm("Bloco"):
    executar()
```

Também é possível monitorar CPU e memória com `log_system_status`.
