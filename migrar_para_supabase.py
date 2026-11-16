"""Copia alianca_historico.db (SQLite) para o Postgres do Supabase.

A senha não fica no arquivo. Antes de rodar:

    $env:SUPABASE_DB_PASSWORD = "sua-senha"
    .\\_py\\python\\python.exe migrar_para_supabase.py

Ou defina a URL inteira em SUPABASE_DB_URL.
"""

import os
import sqlite3
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import BigInteger, Float, Text

ROOT = Path(__file__).resolve().parent
SQLITE_PATH = ROOT / "alianca_historico.db"
HOST = "db.bvwhqnhdnilglwrydzkx.supabase.co"


def supabase_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if url:
        return url
    senha = os.environ.get("SUPABASE_DB_PASSWORD", "").strip()
    if not senha or senha == "[YOUR-PASSWORD]":
        raise SystemExit(
            "Defina SUPABASE_DB_PASSWORD (ou SUPABASE_DB_URL) antes de migrar."
        )
    return (
        f"postgresql+psycopg://postgres:{quote_plus(senha)}"
        f"@{HOST}:5432/postgres?sslmode=require"
    )


def tipos_colunas(sqlite_conn, tabela: str) -> dict:
    info = sqlite_conn.execute(f'PRAGMA table_info("{tabela}")').fetchall()
    tipos = {}
    for _cid, nome, tipo, *_resto in info:
        tipo = (tipo or "").upper()
        if "INT" in tipo:
            tipos[nome] = BigInteger()
        elif any(marca in tipo for marca in ("REAL", "FLOA", "DOUB", "NUM")):
            tipos[nome] = Float()
        else:
            tipos[nome] = Text()
    return tipos


def preservar_inteiros(df: pd.DataFrame, tipos: dict) -> pd.DataFrame:
    for nome, tipo in tipos.items():
        if nome in df.columns and isinstance(tipo, BigInteger):
            df[nome] = pd.to_numeric(df[nome], errors="coerce").astype("Int64")
    return df


def migrar_dados() -> None:
    print(f"--> Conectando ao banco SQLite local ({SQLITE_PATH.name})...")
    if not SQLITE_PATH.exists():
        print(f"Erro: {SQLITE_PATH} não encontrado.")
        return

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    try:
        tabelas = [
            row[0]
            for row in sqlite_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            if row[0] != "sqlite_sequence"
        ]
        print(f"--> Tabelas encontradas localmente: {tabelas}")
        if not tabelas:
            print("--> Nenhuma tabela encontrada no banco local.")
            return

        print("--> Conectando ao Supabase (PostgreSQL)...")
        engine_pg = create_engine(supabase_url(), pool_pre_ping=True)
        try:
            with engine_pg.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("--> Conexão com o Supabase ok.")

            for tabela in tabelas:
                print(f"--> Migrando a tabela '{tabela}' para o Supabase...")
                try:
                    tipos = tipos_colunas(sqlite_conn, tabela)
                    df = pd.read_sql(f'SELECT * FROM "{tabela}"', sqlite_conn)
                    df = preservar_inteiros(df, tipos)
                    df.to_sql(
                        tabela,
                        engine_pg,
                        if_exists="replace",
                        index=False,
                        schema="public",
                        dtype=tipos,
                        chunksize=200,
                        method="multi",
                    )
                    print(
                        f"--> Tabela '{tabela}' migrada com sucesso "
                        f"({len(df)} registros)!"
                    )
                except Exception as exc:
                    print(f"--> Erro ao migrar a tabela '{tabela}': {exc}")
        finally:
            engine_pg.dispose()
    finally:
        sqlite_conn.close()

    print("\n--> Processo de migração concluído!")


if __name__ == "__main__":
    migrar_dados()
