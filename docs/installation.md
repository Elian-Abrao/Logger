# Guia de Instalação e Configuração

## Pré-requisitos
- Python >= 3.8
- Dependências do sistema listadas em `pyproject.toml`

## Instalação
```bash
pip install -e .[dev]
```

Ou para o ambiente exato usado pelo projeto:
```bash
pip install -r requirements.lock
```

## Configuração
A biblioteca não requer variáveis de ambiente específicas. Os logs são
salvos em `Logs/` por padrão, podendo ser alterado com o parâmetro
`log_dir` de `start_logger`.
