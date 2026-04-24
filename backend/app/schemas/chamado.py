from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChamadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chave_jira: str
    usuario_id: str
    email_solicitante: str
    titulo_original: str
    descricao: str
    organizacao_atual: str | None
    status: str
    created_at: datetime


class SugestaoIARead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chamado_id: int
    organizacao_sugerida: str
    titulo_sugerido: str
    categoria_sugerida: str
    prioridade_sugerida: str
    solucao_sugerida: str
    justificativa: str
    confianca: float
    fontes_internas_usadas: list[str]
    created_at: datetime


class ValidacaoHumanaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chamado_id: int
    sugestao_id: int
    organizacao_final: str
    titulo_final: str
    categoria_final: str
    prioridade_final: str
    observacao: str | None
    created_at: datetime


class ChamadoDetalhe(ChamadoRead):
    sugestoes_ia: list[SugestaoIARead] = []
    validacoes_humanas: list[ValidacaoHumanaRead] = []


class JiraImportResult(BaseModel):
    total_encontrados: int
    importados: int
    atualizados: int
    campo_organizacao_usado: str
    mensagem: str
