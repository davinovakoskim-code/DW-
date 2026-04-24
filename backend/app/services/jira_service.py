from typing import Any

from fastapi import HTTPException, status
from jira import JIRA
from jira.exceptions import JIRAError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chamado import Chamado


ORGANIZATION_FIELD_NAMES = {"Organizations", "Organização", "Organizacao"}
ORGANIZATION_FIELD_FALLBACK = "customfield_10002"
JQL_ULTIMOS_90_DIAS = "created >= -90d ORDER BY created DESC"


class JiraImportService:
    @staticmethod
    def importar_chamados(db: Session) -> dict:
        jira = JiraImportService._conectar()
        campo_organizacao = JiraImportService._descobrir_campo_organizacao(jira)

        try:
            issues = jira.search_issues(
                JQL_ULTIMOS_90_DIAS,
                maxResults=50,
                fields=f"summary,description,reporter,{campo_organizacao}",
            )
        except JIRAError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Falha ao buscar chamados no Jira: {getattr(exc, 'text', str(exc))}",
            ) from exc

        importados = 0
        atualizados = 0

        for issue in issues:
            dados = JiraImportService._extrair_issue(issue, campo_organizacao)
            chamado_existente = (
                db.query(Chamado)
                .filter(Chamado.chave_jira == dados["chave_jira"])
                .first()
            )

            if chamado_existente:
                for campo, valor in dados.items():
                    setattr(chamado_existente, campo, valor)
                atualizados += 1
            else:
                db.add(Chamado(**dados))
                importados += 1

        db.commit()

        return {
            "total_encontrados": len(issues),
            "importados": importados,
            "atualizados": atualizados,
            "campo_organizacao_usado": campo_organizacao,
            "mensagem": "Importacao concluida com sucesso.",
        }

    @staticmethod
    def _conectar() -> JIRA:
        if not settings.jira_email or not settings.jira_api_token or not settings.jira_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Credenciais do Jira nao configuradas. Preencha JIRA_EMAIL, "
                    "JIRA_API_TOKEN e JIRA_URL no arquivo .env."
                ),
            )

        try:
            return JIRA(
                server=settings.jira_url,
                basic_auth=(settings.jira_email, settings.jira_api_token),
            )
        except JIRAError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Falha ao conectar no Jira: {getattr(exc, 'text', str(exc))}",
            ) from exc

    @staticmethod
    def _descobrir_campo_organizacao(jira: JIRA) -> str:
        try:
            for campo in jira.fields():
                if campo.get("name") in ORGANIZATION_FIELD_NAMES:
                    return campo["id"]
        except JIRAError:
            pass
        return ORGANIZATION_FIELD_FALLBACK

    @staticmethod
    def _extrair_issue(issue: Any, campo_organizacao: str) -> dict:
        reporter = getattr(issue.fields, "reporter", None)
        email = getattr(reporter, "emailAddress", None) or "email-nao-disponivel@jira.local"
        usuario_id = email.split("@", 1)[0]
        descricao = JiraImportService._descricao_para_texto(
            getattr(issue.fields, "description", None)
        )
        organizacao = JiraImportService._formatar_organizacao(
            getattr(issue.fields, campo_organizacao, None)
        )

        return {
            "chave_jira": issue.key,
            "usuario_id": usuario_id,
            "email_solicitante": email,
            "titulo_original": getattr(issue.fields, "summary", "Sem titulo"),
            "descricao": descricao or "Sem descricao informada.",
            "organizacao_atual": organizacao,
            "status": "importado",
        }

    @staticmethod
    def _descricao_para_texto(valor: Any) -> str:
        if valor is None:
            return "Sem descricao informada."
        if isinstance(valor, str):
            return valor
        if isinstance(valor, dict):
            textos = JiraImportService._extrair_textos_adf(valor)
            return "\n".join(textos).strip() or str(valor)
        return str(valor)

    @staticmethod
    def _extrair_textos_adf(no: Any) -> list[str]:
        textos: list[str] = []
        if isinstance(no, dict):
            if no.get("type") == "text" and no.get("text"):
                textos.append(no["text"])
            for filho in no.get("content", []):
                textos.extend(JiraImportService._extrair_textos_adf(filho))
        elif isinstance(no, list):
            for item in no:
                textos.extend(JiraImportService._extrair_textos_adf(item))
        return textos

    @staticmethod
    def _formatar_organizacao(valor: Any) -> str | None:
        if not valor:
            return None
        if isinstance(valor, list):
            partes = [JiraImportService._formatar_organizacao(item) for item in valor]
            return ", ".join(parte for parte in partes if parte) or None
        if isinstance(valor, dict):
            return (
                valor.get("name")
                or valor.get("displayName")
                or valor.get("value")
                or str(valor)
            )
        return (
            getattr(valor, "name", None)
            or getattr(valor, "displayName", None)
            or getattr(valor, "value", None)
            or str(valor)
        )
