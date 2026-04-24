from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Chamado(Base):
    __tablename__ = "chamados"

    id = Column(Integer, primary_key=True, index=True)
    chave_jira = Column(String(100), nullable=False, unique=True, index=True)
    usuario_id = Column(String(255), nullable=False, index=True)
    email_solicitante = Column(String(255), nullable=False, index=True)
    titulo_original = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=False)
    organizacao_atual = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="novo", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sugestoes_ia = relationship(
        "SugestaoIA",
        back_populates="chamado",
        cascade="all, delete-orphan",
    )
    validacoes_humanas = relationship(
        "ValidacaoHumana",
        back_populates="chamado",
        cascade="all, delete-orphan",
    )
