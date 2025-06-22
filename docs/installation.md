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

## Uso via Azure Artifacts
Para instalar a biblioteca a partir do feed privado `Logger-Seed`, crie um arquivo `~/.pip/pip.conf` com o seguinte conteudo:
```
[global]
index-url=https://pkgs.dev.azure.com/qualysystem/RPA/_packaging/Logger-Seed/pypi/simple/
```
Tambem e recomendado adicionar um `.pypirc` em seu diretorio home:
```
[distutils]
index-servers =
  Logger-Seed

[Logger-Seed]
repository = https://pkgs.dev.azure.com/qualysystem/RPA/_packaging/Logger-Seed/pypi/upload/
```
Essas configuracoes permitem usar `pip install logger` e `twine upload` diretamente no Azure.
