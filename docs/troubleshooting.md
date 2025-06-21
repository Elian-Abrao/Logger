# Troubleshooting & FAQ

| Erro/Mensagem | Possível Solução |
|---------------|-----------------|
| `ModuleNotFoundError` | Verifique instalação das dependências |
| `Permission denied` ao gravar log | Confirme permissões da pasta `log_dir` |

**Perguntas frequentes**
- *Como alterar o diretório de logs?* Use o parâmetro `log_dir` em `start_logger`.
- *Como desativar a captura de prints?* Passe `capture_prints=False`.
