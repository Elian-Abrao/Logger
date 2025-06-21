# Visão de Arquitetura

```mermaid
graph TD
    A[Aplicação Usuário] --> B[start_logger]
    B --> C[Logger Core]
    C --> D[Extras]
    C --> E[Handlers]
    D --> F[Metrics / Monitoring / Network]
    E --> G[Console]
    E --> H[Arquivos de Log]
```

O diagrama acima mostra o fluxo principal: a aplicação inicializa o logger com `start_logger`, que configura o núcleo e adiciona funcionalidades extras. As mensagens são enviadas para o console e para arquivos de log.

```mermaid
sequenceDiagram
    participant App
    participant Logger
    App->>Logger: start_logger("Demo")
    Logger-->>App: objeto Logger
    App->>Logger: info("Processo iniciado")
    App->>Logger: progress(range(5))
    App->>Logger: end()
```

Nesta sequência, a aplicação cria o logger, registra mensagens e encerra a execução.
