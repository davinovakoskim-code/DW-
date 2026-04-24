from pydantic import BaseModel, Field, field_validator


class ValidacaoHumanaCreate(BaseModel):
    sugestao_id: int
    organizacao_final: str = Field(min_length=2, max_length=255)
    titulo_final: str = Field(min_length=3, max_length=255)
    categoria_final: str = Field(min_length=3, max_length=100)
    prioridade_final: str = Field(min_length=3, max_length=50)
    observacao: str | None = None

    @field_validator(
        "organizacao_final",
        "titulo_final",
        "categoria_final",
        "prioridade_final",
    )
    @classmethod
    def remover_espacos(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("campo nao pode ficar vazio")
        return value

    @field_validator("observacao")
    @classmethod
    def limpar_observacao(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

