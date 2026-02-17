# 🚀 Configuração Coolify (Atualização do GitHub)

Seu Coolify já está conectado ao GitHub `mmozil` (onde está o `tier-finance`). O problema é que o App do GitHub está configurado para ver **apenas** o repositório `tier-finance`. Precisamos dar permissão ao `maestro` também.

## Passo 1: Atualizar Permissões no GitHub (Ação Rápida)

1. **Acesse as Configurações do App no GitHub:**
   - Vá direto neste link (substitua `NOME-DO-SEU-APP` pelo nome do app instalado no GitHub, geralmente `Coolify` ou `Coolify-seu-nome`):
     - `https://github.com/settings/installations`
   - Localize o App do Coolify na lista e clique em **Configure**.

2. **Adicionar o Repositório Maestro:**
   - Role até a seção **Repository access**.
   - Você verá **Only select repositories** marcado.
   - Clique no dropdown **Select repositories**.
   - Digite `maestro` e selecione o repositório `mmozil/maestro`.
   - Clique em **Save**.

3. **Reload no Coolify:**
   - Volte ao painel do Coolify.
   - Vá em **Sources** (provavelmente chamado `github` ou `mmozil`).
   - Clique no botão **Reload** (ícone de recarregar) no canto superior direito da página da source.
   - Agora o Coolify "enxerga" o `maestro`.

## Passo 2: Criar o Projeto no Coolify

1. **Novo Recurso:**
   - No Coolify, vá em **Projects** -> **Default** (ou crie um novo projeto "Maestro").
   - Clique **+ New** -> **Application** -> **Public/Private Repository**.

2. **Selecionar Repositório:**
   - Escolha a Source `github` (que acabamos de atualizar).
   - O Coolify carregará os repositórios. Selecione `mmozil/maestro`.
   - Branch: `main`.

3. **Configurações Básicas:**
   - **Build Pack:** Dockerfile
   - **Port:** `8000`
   - **Health Check:** `/health`
   - **Domains:** Configure seu domínio (ex: `maestro.tier.finance` ou outro).

4. **Environment Variables (Secrets):**
   - Vá na aba **Environment Variables** e cole:
     ```env
     DATABASE_URL=postgresql+asyncpg://optimus:SUA_SENHA@postgres:5432/optimus
     REDIS_URL=redis://redis:6379/0
     GOOGLE_API_KEY=sua-chave-aqui
     ```

## Passo 3: Bancos de Dados (Postgres & Redis)

Como o Maestro precisa de Postgres com PGVector e Redis:

1. No mesmo projeto no Coolify, clique **+ New** -> **Database** -> **PostgreSQL**.
   - **Image:** `pgvector/pgvector:pg16` (IMPORTANTE: não use a padrão `postgres:16`)
   - **User/Password/DB:** Configure `optimus` / `SUA_SENHA` / `optimus`.
   - **Public Port:** Não precisa expor, deixe interno se quiser segurança máxima.

2. Clique **+ New** -> **Database** -> **Redis**.
   - **Image:** `redis:7-alpine`.
   - **Password:** Configure `SUA_SENHA_REDIS`.
   - **Environment Variable:** No App, atualize `REDIS_URL` para incluir a senha: `redis://:SENHA@redis:6379/0`.

## Passo 4: Deploy

- Na página do Application, clique **Deploy**.
- Acompanhe os logs. Se tudo der certo, o status ficará "Healthy".

---

**Observação:** Como você já tem acesso SSH, pode conferir no servidor se os containers subiram:
```bash
docker ps | grep optimus
```
Isso mostrará o banco e a aplicação rodando.
