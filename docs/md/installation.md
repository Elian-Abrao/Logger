# Instalação e Configuração

## Pré-requisitos

- Python >= 3.8
- Dependências de sistema: pacotes de desenvolvimento do Python e bibliotecas padrões.
- Variáveis de ambiente opcionais:
  - `LOG_DIR` para definir o diretório padrão de logs.

## Instalação via `pip`

```bash
pip install logger
```

Para ambiente de desenvolvimento:

```bash
pip install -e .[dev]
```

Se desejar reproduzir exatamente o ambiente usado nos testes:

```bash
pip install -r requirements.lock
```

## Configuração

Crie um arquivo `.env` (opcional) ou defina as variáveis de ambiente necessárias. O diretório de logs é criado automaticamente.

Para gerar a documentação local via Sphinx:

```bash
pip install sphinx
make -C docs html
```
