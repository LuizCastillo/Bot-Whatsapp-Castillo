# Bot WhatsApp — Oficina Castillo

> **O bot organiza. O banco registra. O painel dá controle à equipe.**

Sistema de primeiro atendimento por WhatsApp da Oficina Castillo. O bot **não usa IA** (máquina de estados
determinística) e **não faz orçamento, preço nem diagnóstico**: ele identifica o cliente, entende o interesse e
**agenda uma avaliação presencial**. O orçamento e a execução do serviço são da equipe.

```
Navegador ──▶ Next.js (Vercel) ──proxy──▶ FastAPI (Render) ──▶ Supabase (Postgres + Storage privado)
                                             ▲
                       WhatsApp Cloud API ───┘  (webhook)
```

| Pasta | O que é | Deploy |
|---|---|---|
| `backend/` | FastAPI, bot, API do painel, migrations (Alembic) | Render (Docker) |
| `frontend/` | Painel da equipe (Next.js, Tailwind, shadcn/ui) | Vercel |

Dependências separadas: `backend/requirements.txt` e `frontend/package.json`.

## Segurança

- O navegador **só conversa com o domínio da Vercel**. O Next.js encaminha `/api/*` → FastAPI `/panel/*`
  (`frontend/src/app/api/[...path]/route.ts`).
- Login: o FastAPI valida a senha (argon2) e devolve um token de sessão **apenas ao proxy**, que o guarda em cookie
  `HttpOnly; Secure; SameSite=Lax` (sem `Domain`). O JavaScript do navegador nunca vê o token.
- O FastAPI só aceita rotas do painel com o header `X-Proxy-Secret` (segredo compartilhado Vercel ↔ Render).
- Sessões ficam no banco (hash SHA-256) e podem ser revogadas (logout, desativar usuário, trocar senha).
- Autorização ADMIN/ATENDENTE é aplicada **no backend**; o frontend só esconde menus.
- CSRF: `SameSite=Lax` + checagem de `Origin` nas requisições que alteram dados.
- CORS restrito por `CORS_ORIGINS` (sem `*`, sem credenciais). Com o proxy, é só uma segunda camada.
- Webhook da Meta: assinatura `X-Hub-Signature-256` validada; mensagens de outro `phone_number_id` são ignoradas;
  reenvios são descartados (`wa_message_id` único).
- Fotos em bucket privado; o painel recebe URLs assinadas de 5 minutos. Nenhuma chave do Supabase vai ao frontend.
- Rate limit de login (5 falhas → bloqueio temporário; em memória, adequado a 1 instância).

## Variáveis de ambiente

Copie `backend/.env.example` e `frontend/.env.example`. **Nunca** commite `.env`.

**Render (backend):** `APP_ENV=production`, `CORS_ORIGINS` (URL do painel na Vercel), `PROXY_SHARED_SECRET`,
`DATABASE_URL` (pooler do Supabase), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`,
`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `META_APP_SECRET`, `ENDERECO_OFICINA`.
Opcionais: `SESSION_EXPIRE_MINUTES`, `CONVERSA_TIMEOUT_HORAS`, `AGENDAMENTO_STATUS_INICIAL` (`PENDENTE`|`CONFIRMADO`),
`CANCELAMENTO_ANTECEDENCIA_HORAS`, `MAX_FOTO_MB`.

**Vercel (frontend):** `BACKEND_URL` (URL do Render) e `PROXY_SHARED_SECRET` (mesmo valor do backend).
São variáveis **só de servidor**: não use `NEXT_PUBLIC_`. Opcional: `ALLOWED_ORIGINS`.

Trocar para o número oficial da oficina = trocar `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID`.

## Passo a passo do deploy

1. **Supabase:** crie o projeto e um bucket **privado** `fotos-avaliacoes` (Storage). Copie a connection string do
   *pooler* (porta 6543) para `DATABASE_URL`, a URL do projeto e a *service role key*.
2. **Render:** *New Web Service* apontando para este repositório, *Root Directory* `backend`, runtime Docker
   (ou use o `render.yaml`). Preencha as variáveis. As migrations rodam sozinhas no start (`alembic upgrade head`):
   criam as tabelas, os 9 serviços e o horário padrão, e ativam RLS. Health check: `/health`.
3. **Primeiro administrador** (Shell do Render):
   `python -m app.scripts.create_admin --email voce@exemplo.com --nome "Seu Nome"` (senha pedida no prompt; mín. 10 caracteres).
4. **Vercel:** importe o repositório, *Root Directory* `frontend`, defina `BACKEND_URL` e `PROXY_SHARED_SECRET`.
5. Volte ao Render e defina `CORS_ORIGINS` com a URL da Vercel (`https://xxx.vercel.app`).
6. **Meta (WhatsApp Cloud API):** em *Configuration → Webhook*, callback `https://SEU-BACKEND.onrender.com/webhook`,
   *Verify token* = `WHATSAPP_VERIFY_TOKEN`, e assine o campo `messages`.

> O plano gratuito do Render hiberna: a primeira mensagem pode demorar e a Meta reenvia (já tratado por idempotência).
> Em produção use plano sempre ligado. O plano Hobby da Vercel é para uso não comercial.

**Domínio futuro** (`painel.oficinacastillo.com.br`): adicione o domínio na Vercel e inclua a nova URL em
`CORS_ORIGINS` (e, se quiser, em `ALLOWED_ORIGINS`). Nada mais muda: o cookie não tem `Domain` e o navegador nunca chama o backend.

## Botão "Agendar serviço" no site

Envie um identificador estável (o slug) junto com o texto:

```js
const slug = "funilaria", nome = "Funilaria";
const texto = `Olá! Vim pelo site e gostaria de agendar o serviço de ${nome}. (ref: ${slug})`;
const url = `https://wa.me/55DDDNUMERO?text=${encodeURIComponent(texto)}`;
```

O backend lê `(ref: slug)`; sem ele, tenta reconhecer o nome do serviço no texto. Slugs:
`funilaria`, `recuperacao-de-colisoes`, `pintura-geral`, `pintura-localizada`, `preparo-de-superficie`,
`polimento-automotivo`, `polimento-de-farois`, `substituicao-de-pecas`, `revitalizacao-de-para-choques`.

## Desenvolvimento local

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # para testar sem Postgres: DATABASE_URL=sqlite+aiosqlite:///./dev.db
alembic upgrade head
uvicorn app.main:app --reload
pytest

# frontend (outro terminal)
cd frontend && npm install && cp .env.example .env.local && npm run dev
```

## Decisões assumidas (ajustáveis)

- Avaliação × agendamento em duas tabelas; "Rascunho" é derivado (avaliação sem agendamento = iniciada e não concluída).
- Horário padrão (editável em *Agenda → Configurar*): seg–sex 08–12 e 13–17, sáb 08–12; blocos de 60 min; capacidade 1 por
  horário; antecedência mínima 2 h; janela de 14 dias. A unicidade do horário é garantida por índice único parcial no banco.
- Status inicial `PENDENTE` (troque por `CONFIRMADO` via `AGENDAMENTO_STATUS_INICIAL`).
- Cliente cancela/reagenda até 2 h antes; depois disso o bot chama a equipe.
- Só o painel devolve a conversa ao bot; o bot fica calado em `HUMANO`/`AGUARDANDO_EQUIPE`.
- Resposta pelo painel só dentro da janela de 24 h do WhatsApp (fora dela, só templates aprovados pela Meta).
- Placa é opcional no cadastro pelo bot (formatos antigo e Mercosul são validados quando informada).

## Limitações conhecidas

- Processamento em `BackgroundTasks`: um restart do Render no meio de uma mensagem pode perdê-la. Se o volume crescer, migrar para fila (Redis + worker).
- Lock por conversa e rate limit de login são em memória (1 instância).
- Não implementado: lembretes automáticos (exigem template aprovado), consentimento LGPD e retenção de fotos, envio de templates fora da janela de 24 h.
- Capacidade por horário fixa em 1.
