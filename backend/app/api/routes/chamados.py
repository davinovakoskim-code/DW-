from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chamado import (
    ChamadoDetalhe,
    ChamadoRead,
    SugestaoIARead,
    ValidacaoHumanaRead,
)
from app.schemas.validacao_humana import ValidacaoHumanaCreate
from app.services.chamado_service import ChamadoService

router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.get("", response_model=list[ChamadoRead])
def listar_chamados(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista os chamados cadastrados, com filtro simples por status."""
    return ChamadoService.listar(
        db=db,
        status_filtro=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{chamado_id}", response_model=ChamadoDetalhe)
def buscar_chamado(chamado_id: int, db: Session = Depends(get_db)):
    """Retorna um chamado com suas sugestoes de IA e validacoes humanas."""
    return ChamadoService.buscar_ou_404(db=db, chamado_id=chamado_id)


@router.post("/{chamado_id}/analisar", response_model=SugestaoIARead)
def analisar_chamado(chamado_id: int, db: Session = Depends(get_db)):
    """Executa a IA local e salva a sugestao gerada."""
    return ChamadoService.analisar(db=db, chamado_id=chamado_id)


@router.post("/{chamado_id}/validar", response_model=ValidacaoHumanaRead)
def validar_sugestao(
    chamado_id: int,
    payload: ValidacaoHumanaCreate,
    db: Session = Depends(get_db),
):
    """Salva a confirmacao ou correcao humana da sugestao da IA."""
    return ChamadoService.validar(db=db, chamado_id=chamado_id, payload=payload)
