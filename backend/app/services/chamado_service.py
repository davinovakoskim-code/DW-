from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chamado import Chamado
from app.models.sugestao_ia import SugestaoIA
from app.models.validacao_humana import ValidacaoHumana
from app.schemas.validacao_humana import ValidacaoHumanaCreate
from app.services.ia_local_service import IALocalService


class ChamadoService:
    @staticmethod
    def listar(db: Session, status_filtro: str | None, limit: int, offset: int) -> list[Chamado]:
        query = db.query(Chamado)
        if status_filtro:
            query = query.filter(Chamado.status == status_filtro.strip().lower())
        return query.order_by(Chamado.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def buscar_ou_404(db: Session, chamado_id: int) -> Chamado:
        chamado = db.query(Chamado).filter(Chamado.id == chamado_id).first()
        if chamado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chamado nao encontrado.",
            )
        return chamado

    @staticmethod
    def analisar(db: Session, chamado_id: int) -> SugestaoIA:
        chamado = ChamadoService.buscar_ou_404(db=db, chamado_id=chamado_id)
        sugestao_data = IALocalService.analisar_chamado(db=db, chamado=chamado)

        sugestao = SugestaoIA(chamado_id=chamado.id, **sugestao_data)
        chamado.status = "analisado"

        db.add(sugestao)
        db.commit()
        db.refresh(sugestao)
        return sugestao

    @staticmethod
    def validar(
        db: Session,
        chamado_id: int,
        payload: ValidacaoHumanaCreate,
    ) -> ValidacaoHumana:
        chamado = ChamadoService.buscar_ou_404(db=db, chamado_id=chamado_id)

        sugestao = (
            db.query(SugestaoIA)
            .filter(
                SugestaoIA.id == payload.sugestao_id,
                SugestaoIA.chamado_id == chamado.id,
            )
            .first()
        )
        if sugestao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sugestao nao encontrada para este chamado.",
            )

        validacao = ValidacaoHumana(chamado_id=chamado.id, **payload.model_dump())
        chamado.status = "validado"

        db.add(validacao)
        db.commit()
        db.refresh(validacao)
        return validacao
