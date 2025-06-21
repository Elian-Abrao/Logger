# Casos de Uso e Exemplos

## Timer
```python
with logger.timer("Carga de dados"):
    carregar_dados()
```

## Captura de prints
```python
with logger.capture_prints(logger, level="WARNING"):
    print("não use prints! :) ")
```
