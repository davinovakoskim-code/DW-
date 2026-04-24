# DWPLUS Ticket Triage - MVP academico

Sistema web simples para triagem e enriquecimento automatico de chamados da
DWPLUS. O MVP importa chamados reais do Jira, analisa os textos localmente com
tecnicas simples de PLN e salva a validacao humana no banco local.

## Objetivo do projeto

Demonstrar um fluxo academico de apoio a triagem inicial de chamados:

1. conectar no Jira;
2. importar chamados dos ultimos 90 dias;
3. listar chamados importados localmente;
4. analisar um chamado com IA local;
5. sugerir organizacao, titulo, categoria, prioridade, solucao, justificativa e confianca;
6. permitir que uma pessoa confirme ou corrija a sugestao;
7. salvar a validacao humana no SQLite.

## Tecnologias usadas

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- python-dotenv
- jira
- HTML, CSS e JavaScript puro

## Como a IA funciona neste MVP

Este MVP nao usa API externa de LLM. A inteligencia foi implementada localmente
com uma combinacao de:

- base de conhecimento interna da DWPLUS;
- busca por palavras-chave no titulo e na descricao;
- comparacao com chamados antigos usando similaridade textual simples;
- validacao humana para confirmar ou corrigir a sugestao.

A base interna inicial cobre temas como acesso, performance, incidente tecnico,
fiscal e financeiro. Quando a IA local nao encontra evidencia suficiente, ela
retorna `Analise manual necessaria` com baixa confianca.

## Configurar o `.env`

Copie o arquivo de exemplo:

```powershell
copy .env.example .env
```

Preencha:

```env
JIRA_EMAIL=seu-email@empresa.com
JIRA_API_TOKEN=seu-token-do-jira
JIRA_URL=https://dwplus.atlassian.net
```

O arquivo `.env` nao deve ser versionado. Ele ja esta ignorado no `.gitignore`.

## Instalar dependencias

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Rodar o backend

```powershell
uvicorn app.main:app --reload
```

Depois abra:

- Frontend: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

O banco SQLite `dwplus.db` e criado automaticamente dentro da pasta `backend`.

## Importar chamados do Jira

Na tela inicial, clique em `Importar chamados do Jira`.

O endpoint usado e:

```txt
POST /jira/importar-chamados
```

A importacao usa:

```txt
created >= -90d ORDER BY created DESC
```

Para facilitar a apresentacao, o MVP busca no maximo 50 chamados. A aplicacao
evita duplicidade usando `chave_jira`.

## Analisar com IA

Selecione um chamado importado e clique em `Analisar com IA`.

O endpoint usado e:

```txt
POST /chamados/{id}/analisar
```

A IA local recebe:

- e-mail do solicitante;
- usuario extraido do e-mail;
- titulo original;
- descricao;
- organizacao atual, quando existir.

A resposta inclui:

```json
{
  "organizacao_sugerida": "",
  "titulo_sugerido": "",
  "categoria_sugerida": "",
  "prioridade_sugerida": "",
  "solucao_sugerida": "",
  "justificativa": "",
  "confianca": 0.0,
  "fontes_internas_usadas": []
}
```

## Por que existe validacao humana

A IA local nao toma a decisao final. Regras por palavras-chave e similaridade
textual podem errar ou ser insuficientes. Por isso, o atendente revisa a
sugestao e salva a versao final na tabela `validacoes_humanas`.

## Endpoints principais

```txt
GET  /health
POST /jira/importar-chamados
GET  /chamados
GET  /chamados/{id}
POST /chamados/{id}/analisar
POST /chamados/{id}/validar
```

## Tabelas do MVP

- `chamados`
- `sugestoes_ia`
- `validacoes_humanas`

## Limitacoes do MVP

- Nao possui login.
- Nao atualiza dados no Jira.
- Nao faz paginacao completa de todos os chamados.
- Importa no maximo 50 chamados para apresentacao.
- Nao usa embeddings nem modelo generativo externo.
- Usa SQLite local.
- Depende apenas de credenciais validas do Jira para importar chamados reais.

## Proximos passos

- Adicionar autenticacao.
- Criar paginacao da importacao do Jira.
- Atualizar campos do Jira somente apos validacao humana.
- Criar logs de auditoria.
- Evoluir a base de conhecimento com dados validados.
- Adicionar TF-IDF, embeddings locais ou busca semantica.
- Criar dashboard com metricas de aceite e correcao das sugestoes.

