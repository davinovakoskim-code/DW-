from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ValidacaoHumana(Base):
    __tablename__ = "validacoes_humanas"

    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), nullable=False, index=True)
    sugestao_id = Column(Integer, ForeignKey("sugestoes_ia.id"), nullable=False, index=True)
    organizacao_final = Column(String(255), nullable=False)
    titulo_final = Column(String(255), nullable=False)
    categoria_final = Column(String(100), nullable=False)
    prioridade_final = Column(String(50), nullable=False)
    observacao = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chamado = relationship("Chamado", back_populates="validacoes_humanas")
    sugestao = relationship("SugestaoIA", back_populates="validacoes_humanas")
