from sqlalchemy.engine import Engine


def migrar_sqlite_schema(engine: Engine) -> None:
    """Pequena migracao local para bancos SQLite criados em versoes anteriores.

    O MVP nao usa Alembic para manter a apresentacao simples. Esta rotina apenas
    garante que um banco local antigo continue funcionando apos mudancas de
    campos do prototipo.
    """

    if engine.url.get_backend_name() != "sqlite":
        return

    with engine.begin() as conn:
        _migrar_chamados(conn)
        _migrar_sugestoes(conn)


def _tabela_existe(conn, nome: str) -> bool:
    result = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (nome,),
    ).first()
    return result is not None


def _colunas(conn, tabela: str) -> set[str]:
    return {
        row[1]
        for row in conn.exec_driver_sql(f"PRAGMA table_info({tabela})").fetchall()
    }


def _migrar_chamados(conn) -> None:
    if not _tabela_existe(conn, "chamados"):
        return

    colunas = _colunas(conn, "chamados")

    if "chave_jira" not in colunas:
        conn.exec_driver_sql("ALTER TABLE chamados ADD COLUMN chave_jira TEXT")
    if "usuario_id" not in colunas:
        conn.exec_driver_sql("ALTER TABLE chamados ADD COLUMN usuario_id TEXT")
    if "organizacao_atual" not in colunas:
        conn.exec_driver_sql("ALTER TABLE chamados ADD COLUMN organizacao_atual TEXT")

    conn.exec_driver_sql(
        """
        UPDATE chamados
        SET chave_jira = 'LOCAL-' || id
        WHERE chave_jira IS NULL OR chave_jira = ''
        """
    )
    conn.exec_driver_sql(
        """
        UPDATE chamados
        SET usuario_id =
            CASE
                WHEN instr(email_solicitante, '@') > 1
                THEN substr(email_solicitante, 1, instr(email_solicitante, '@') - 1)
                ELSE 'usuario_' || id
            END
        WHERE usuario_id IS NULL OR usuario_id = ''
        """
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_chamados_chave_jira ON chamados(chave_jira)"
    )


def _migrar_sugestoes(conn) -> None:
    if not _tabela_existe(conn, "sugestoes_ia"):
        return

    colunas = _colunas(conn, "sugestoes_ia")
    precisa_recriar = (
        "resposta_bruta_llm" in colunas
        or "solucao_sugerida" not in colunas
        or "fontes_internas_usadas" not in colunas
    )
    if not precisa_recriar:
        return

    solucao_select = (
        "COALESCE(solucao_sugerida, 'Solucao nao registrada na versao anterior.')"
        if "solucao_sugerida" in colunas
        else "'Solucao nao registrada na versao anterior.'"
    )
    fontes_select = (
        "COALESCE(fontes_internas_usadas, '[\"Migracao da versao anterior\"]')"
        if "fontes_internas_usadas" in colunas
        else "'[\"Migracao da versao anterior\"]'"
    )

    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    conn.exec_driver_sql(
        """
        CREATE TABLE sugestoes_ia_nova (
            id INTEGER NOT NULL PRIMARY KEY,
            chamado_id INTEGER NOT NULL,
            organizacao_sugerida VARCHAR(255) NOT NULL,
            titulo_sugerido VARCHAR(255) NOT NULL,
            categoria_sugerida VARCHAR(100) NOT NULL,
            prioridade_sugerida VARCHAR(50) NOT NULL,
            solucao_sugerida TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            confianca FLOAT NOT NULL,
            fontes_internas_usadas JSON NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(chamado_id) REFERENCES chamados (id)
        )
        """
    )
    conn.exec_driver_sql(
        f"""
        INSERT INTO sugestoes_ia_nova (
            id,
            chamado_id,
            organizacao_sugerida,
            titulo_sugerido,
            categoria_sugerida,
            prioridade_sugerida,
            solucao_sugerida,
            justificativa,
            confianca,
            fontes_internas_usadas,
            created_at
        )
        SELECT
            id,
            chamado_id,
            organizacao_sugerida,
            titulo_sugerido,
            categoria_sugerida,
            prioridade_sugerida,
            {solucao_select},
            justificativa,
            confianca,
            {fontes_select},
            created_at
        FROM sugestoes_ia
        """
    )
    conn.exec_driver_sql("DROP TABLE sugestoes_ia")
    conn.exec_driver_sql("ALTER TABLE sugestoes_ia_nova RENAME TO sugestoes_ia")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_sugestoes_ia_id ON sugestoes_ia(id)")
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_sugestoes_ia_chamado_id ON sugestoes_ia(chamado_id)"
    )
    conn.exec_driver_sql("PRAGMA foreign_keys=ON")

