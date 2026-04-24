from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SugestaoIA(Base):
    __tablename__ = "sugestoes_ia"

    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), nullable=False, index=True)
    organizacao_sugerida = Column(String(255), nullable=False)
    titulo_sugerido = Column(String(255), nullable=False)
    categoria_sugerida = Column(String(100), nullable=False)
    prioridade_sugerida = Column(String(50), nullable=False)
    solucao_sugerida = Column(Text, nullable=False)
    justificativa = Column(Text, nullable=False)
    confianca = Column(Float, nullable=False)
    fontes_internas_usadas = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chamado = relationship("Chamado", back_populates="sugestoes_ia")
    validacoes_humanas = relationship(
        "ValidacaoHumana",
        back_populates="sugestao",
        cascade="all, delete-orphan",
    )
