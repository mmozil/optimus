# 🚀 Configuração CI/CD no Coolify (Painel Web)

Você já tem o `github/mmozil` conectado. Para adicionar o `maestro` e ter deploy automático igual ao `tier-finance`, siga estes 3 passos simples no navegador (não no terminal):

## 1️⃣ Dar Permissão no GitHub
O Coolify só vê o que você autoriza.
1. Vá para: [GitHub App Settings](https://github.com/settings/installations)
2. Encontre o App do **Coolify** e clique **Configure**.
3. Em "Repository access":
   - Se estiver "Only select repositories", selecione `mmozil/maestro` na lista.
   - Clique em **Save**.

## 2️⃣ Adicionar Projeto no Coolify
1. No painel do Coolify: **Projects** -> Selecione seu projeto (ou crie um novo).
2. Clique **+ New** -> **Application** -> **Public/Private Repository**.
3. Selecione a Source `github` ou `mmozil`.
4. Agora o repositório `mmozil/maestro` vai aparecer na lista! Selecione-o.
5. Branch: `main`.
6. Configurações:
   - **Build Pack:** Dockerfile
   - **Port:** 8000
   - **Health Check:** `/health`
   - **Environment Variables:**
     ```env
     DATABASE_URL=postgresql+asyncpg://optimus:SENHA@postgres:5432/optimus
     REDIS_URL=redis://redis:6379/0
     GOOGLE_API_KEY=sua-chave
     ```
7. Clique **Deploy**.

## 3️⃣ Bancos de Dados (Essencial)
O Maestro precisa de Postgres e Redis para funcionar.
1. No mesmo projeto, clique **+ New** -> **Database** -> **PostgreSQL**.
   - Use a imagem: `pgvector/pgvector:pg16` (IMPORTANTE ser essa!)
   - User/Pass/DB: `optimus` / `SENHA` / `optimus`
2. Clique **+ New** -> **Database** -> **Redis**.
   - Imagem: `redis:7-alpine`

Pronto! Dê deploy nos bancos primeiro, depois na aplicação.
