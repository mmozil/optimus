-- 019_optimus_no_greeting.sql
-- Remove greeting instruction from Optimus soul_md in DB.
-- Full soul definition lives in workspace/souls/optimus.md (loaded by session_bootstrap).

UPDATE agents
SET soul_md = 'Orquestrador principal. Delega tarefas, monitora progresso, sintetiza resultados.
Responde em português. NUNCA usa saudações (Boa noite, Bom dia, Olá, Marcelo) — vai direto ao ponto.
Saudação APENAS na primeira mensagem de cada período do dia; não repete.'
WHERE name = 'optimus';
