from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

from sqlalchemy.orm import Session

from app.models.chamado import Chamado
from app.models.sugestao_ia import SugestaoIA


@dataclass(frozen=True)
class ItemBaseConhecimento:
    nome: str
    palavras_chave: tuple[str, ...]
    categoria: str
    prioridade: str
    solucao: str


BASE_CONHECIMENTO = [
    ItemBaseConhecimento(
        nome="Acesso",
        palavras_chave=("login", "senha", "acesso", "bloqueado"),
        categoria="Acesso",
        prioridade="Media",
        solucao=(
            "Verificar credenciais, permissoes do usuario e necessidade de "
            "redefinicao de senha."
        ),
    ),
    ItemBaseConhecimento(
        nome="Performance",
        palavras_chave=("lento", "lentidao", "travando", "demora", "performance"),
        categoria="Performance",
        prioridade="Alta",
        solucao=(
            "Verificar logs, consumo de recursos, horario do incidente e "
            "possiveis instabilidades no ambiente."
        ),
    ),
    ItemBaseConhecimento(
        nome="Incidente tecnico",
        palavras_chave=("erro 500", "exception", "tela branca", "falha interna"),
        categoria="Incidente tecnico",
        prioridade="Alta",
        solucao=(
            "Consultar logs da aplicacao, identificar stack trace e encaminhar "
            "para o time de desenvolvimento."
        ),
    ),
    ItemBaseConhecimento(
        nome="Fiscal",
        palavras_chave=("nota fiscal", "nfe", "nf-e", "xml", "emissao"),
        categoria="Fiscal",
        prioridade="Alta",
        solucao=(
            "Verificar integracao fiscal, dados da empresa, certificado digital "
            "e retorno da SEFAZ."
        ),
    ),
    ItemBaseConhecimento(
        nome="Financeiro",
        palavras_chave=("boleto", "pagamento", "cobranca", "financeiro"),
        categoria="Financeiro",
        prioridade="Media",
        solucao=(
            "Verificar status do pagamento, gateway financeiro, vencimento e "
            "dados de cobranca."
        ),
    ),
]

PALAVRAS_IGNORADAS = {
    "a",
    "ao",
    "as",
    "com",
    "da",
    "de",
    "do",
    "dos",
    "das",
    "e",
    "em",
    "na",
    "no",
    "nos",
    "nas",
    "o",
    "os",
    "para",
    "por",
    "que",
    "um",
    "uma",
}


class IALocalService:
    """Analise local com PLN simples, base interna e chamados parecidos."""

    @staticmethod
    def analisar_chamado(db: Session, chamado: Chamado) -> dict:
        texto_chamado = IALocalService._texto_chamado(chamado)
        texto_normalizado = normalizar(texto_chamado)

        item_base, palavras_encontradas, score_base = IALocalService._buscar_base_interna(
            texto_normalizado
        )
        chamados_parecidos = IALocalService._buscar_chamados_parecidos(
            db=db,
            chamado=chamado,
            texto_atual=texto_normalizado,
        )

        if item_base:
            return IALocalService._montar_sugestao_por_base(
                chamado=chamado,
                item=item_base,
                palavras_encontradas=palavras_encontradas,
                score_base=score_base,
                chamados_parecidos=chamados_parecidos,
            )

        if chamados_parecidos and chamados_parecidos[0]["score"] >= 0.35:
            return IALocalService._montar_sugestao_por_similaridade(
                chamado=chamado,
                chamado_referencia=chamados_parecidos[0],
                chamados_parecidos=chamados_parecidos,
            )

        return IALocalService._montar_sugestao_manual(chamado)

    @staticmethod
    def _buscar_base_interna(
        texto_normalizado: str,
    ) -> tuple[ItemBaseConhecimento | None, list[str], float]:
        melhor_item = None
        melhores_palavras: list[str] = []
        melhor_score = 0.0

        for item in BASE_CONHECIMENTO:
            palavras = [
                palavra
                for palavra in item.palavras_chave
                if normalizar(palavra) in texto_normalizado
            ]
            score = len(palavras) / len(item.palavras_chave)
            if score > melhor_score:
                melhor_item = item
                melhores_palavras = palavras
                melhor_score = score

        if melhor_item and melhores_palavras:
            return melhor_item, melhores_palavras, melhor_score
        return None, [], 0.0

    @staticmethod
    def _buscar_chamados_parecidos(
        db: Session,
        chamado: Chamado,
        texto_atual: str,
    ) -> list[dict]:
        chamados_antigos = (
            db.query(Chamado)
            .filter(Chamado.id != chamado.id)
            .order_by(Chamado.created_at.desc())
            .limit(100)
            .all()
        )

        similares = []
        for antigo in chamados_antigos:
            texto_antigo = normalizar(IALocalService._texto_chamado(antigo))
            score = calcular_similaridade(texto_atual, texto_antigo)
            if score >= 0.18:
                similares.append(
                    {
                        "chamado": antigo,
                        "score": score,
                        "categoria": IALocalService._categoria_historica(antigo),
                        "prioridade": IALocalService._prioridade_historica(antigo),
                        "solucao": IALocalService._solucao_historica(antigo),
                    }
                )

        return sorted(similares, key=lambda item: item["score"], reverse=True)[:3]

    @staticmethod
    def _montar_sugestao_por_base(
        chamado: Chamado,
        item: ItemBaseConhecimento,
        palavras_encontradas: list[str],
        score_base: float,
        chamados_parecidos: list[dict],
    ) -> dict:
        fontes = [
            f"Base interna DWPLUS: {item.nome} ({', '.join(palavras_encontradas)})"
        ]
        fontes.extend(formatar_fontes_similares(chamados_parecidos))

        confianca = min(0.95, 0.55 + (score_base * 0.25) + (0.1 if chamados_parecidos else 0))
        if chamado.organizacao_atual:
            confianca += 0.05

        similares_texto = ""
        if chamados_parecidos:
            similares_texto = (
                f" Tambem foram encontrados chamados parecidos: "
                f"{', '.join(item['chamado'].chave_jira for item in chamados_parecidos)}."
            )

        return {
            "organizacao_sugerida": chamado.organizacao_atual or "Organizacao a confirmar",
            "titulo_sugerido": IALocalService._titulo_sugerido(chamado, item.categoria),
            "categoria_sugerida": item.categoria,
            "prioridade_sugerida": item.prioridade,
            "solucao_sugerida": item.solucao,
            "justificativa": (
                f"A base interna encontrou as palavras-chave {', '.join(palavras_encontradas)} "
                f"e associou o chamado a categoria {item.categoria}.{similares_texto}"
            ),
            "confianca": round(min(confianca, 0.95), 2),
            "fontes_internas_usadas": fontes,
        }

    @staticmethod
    def _montar_sugestao_por_similaridade(
        chamado: Chamado,
        chamado_referencia: dict,
        chamados_parecidos: list[dict],
    ) -> dict:
        chamado_ref = chamado_referencia["chamado"]
        categoria = chamado_referencia["categoria"] or "Triagem"
        prioridade = chamado_referencia["prioridade"] or "Media"
        solucao = chamado_referencia["solucao"] or (
            f"Usar o chamado parecido {chamado_ref.chave_jira} como referencia "
            "e validar a tratativa com um atendente humano."
        )

        return {
            "organizacao_sugerida": chamado.organizacao_atual or chamado_ref.organizacao_atual or "Organizacao a confirmar",
            "titulo_sugerido": IALocalService._titulo_sugerido(chamado, categoria),
            "categoria_sugerida": categoria,
            "prioridade_sugerida": prioridade,
            "solucao_sugerida": solucao,
            "justificativa": (
                f"Nao houve correspondencia forte na base de palavras-chave, mas o chamado "
                f"{chamado_ref.chave_jira} possui texto parecido "
                f"(similaridade {chamado_referencia['score']:.2f})."
            ),
            "confianca": round(min(0.35 + chamado_referencia["score"], 0.75), 2),
            "fontes_internas_usadas": formatar_fontes_similares(chamados_parecidos),
        }

    @staticmethod
    def _montar_sugestao_manual(chamado: Chamado) -> dict:
        return {
            "organizacao_sugerida": chamado.organizacao_atual or "Organizacao a confirmar",
            "titulo_sugerido": IALocalService._titulo_sugerido(
                chamado,
                "Analise manual necessaria",
            ),
            "categoria_sugerida": "Analise manual necessaria",
            "prioridade_sugerida": "Media",
            "solucao_sugerida": (
                "Nao foi encontrada solucao confiavel na base interna. "
                "Encaminhar para analise humana."
            ),
            "justificativa": (
                "A analise local nao encontrou palavras-chave fortes nem chamados antigos "
                "com similaridade suficiente."
            ),
            "confianca": 0.25,
            "fontes_internas_usadas": ["Sem fonte interna confiavel encontrada"],
        }

    @staticmethod
    def _categoria_historica(chamado: Chamado) -> str | None:
        if chamado.validacoes_humanas:
            return chamado.validacoes_humanas[-1].categoria_final
        if chamado.sugestoes_ia:
            return chamado.sugestoes_ia[-1].categoria_sugerida
        return None

    @staticmethod
    def _prioridade_historica(chamado: Chamado) -> str | None:
        if chamado.validacoes_humanas:
            return chamado.validacoes_humanas[-1].prioridade_final
        if chamado.sugestoes_ia:
            return chamado.sugestoes_ia[-1].prioridade_sugerida
        return None

    @staticmethod
    def _solucao_historica(chamado: Chamado) -> str | None:
        if chamado.sugestoes_ia:
            return chamado.sugestoes_ia[-1].solucao_sugerida
        return None

    @staticmethod
    def _titulo_sugerido(chamado: Chamado, categoria: str) -> str:
        titulo = chamado.titulo_original.strip()
        if len(titulo) > 70:
            titulo = f"{titulo[:67]}..."
        return f"{categoria}: {titulo}"

    @staticmethod
    def _texto_chamado(chamado: Chamado) -> str:
        return " ".join(
            [
                chamado.email_solicitante or "",
                chamado.usuario_id or "",
                chamado.titulo_original or "",
                chamado.descricao or "",
                chamado.organizacao_atual or "",
            ]
        )


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower()


def tokenizar(texto: str) -> set[str]:
    palavras = "".join(char if char.isalnum() else " " for char in texto).split()
    return {palavra for palavra in palavras if len(palavra) > 2 and palavra not in PALAVRAS_IGNORADAS}


def calcular_similaridade(texto_a: str, texto_b: str) -> float:
    tokens_a = tokenizar(texto_a)
    tokens_b = tokenizar(texto_b)
    if not tokens_a or not tokens_b:
        return 0.0

    palavras_comuns = len(tokens_a.intersection(tokens_b))
    cobertura = palavras_comuns / max(len(tokens_a), 1)
    sequencia = SequenceMatcher(None, texto_a, texto_b).ratio()
    return round((cobertura * 0.7) + (sequencia * 0.3), 2)


def formatar_fontes_similares(chamados_parecidos: list[dict]) -> list[str]:
    return [
        f"Chamado parecido: {item['chamado'].chave_jira} (similaridade {item['score']:.2f})"
        for item in chamados_parecidos
    ]

