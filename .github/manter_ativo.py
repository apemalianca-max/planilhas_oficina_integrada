"""Visita o painel e consulta o Supabase para eles não pararem por inatividade.

A senha fica só no segredo SUPABASE_URL do GitHub. Este arquivo não a contém.
"""

import os
import re
import sys

from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, text

PAINEL_URL = os.environ.get(
    "PAINEL_URL",
    "https://planilhasoficinaintegrada-3qrhgcdbmi2meududc.streamlit.app/",
)


def _sem_segredo(mensagem: str) -> str:
    return re.sub(r"://[^@\s/]+@", "://***@", str(mensagem))


def visitar_painel() -> None:
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        pagina = navegador.new_page()
        pagina.goto(PAINEL_URL, wait_until="domcontentloaded", timeout=120_000)
        botao = pagina.get_by_role(
            "button",
            name=re.compile(r"get this app back up", re.IGNORECASE),
        )
        if botao.count():
            print("O painel estava adormecido. Acordando.")
            botao.first.click()
        else:
            print("O painel já estava no ar.")
        pagina.get_by_text(re.compile(r"Aliança")).first.wait_for(timeout=180_000)
        print(f"Painel respondeu: {pagina.title()}")
        navegador.close()


def _url_banco() -> str:
    url = os.environ.get("SUPABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "Falta o segredo SUPABASE_URL no GitHub. "
            "Use o mesmo endereço do pooler já gravado nos segredos do Streamlit."
        )
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def consultar_banco() -> None:
    banco = create_engine(_url_banco(), pool_pre_ping=True)
    with banco.connect() as conexao:
        conexao.execute(text("SELECT 1"))
    print("Supabase respondeu.")


def main() -> None:
    falhas: list[str] = []
    for etapa in (visitar_painel, consultar_banco):
        try:
            etapa()
        except Exception as erro:
            falhas.append(f"{etapa.__name__}: {_sem_segredo(erro)}")
    if falhas:
        print("\n".join(falhas))
        sys.exit(1)


if __name__ == "__main__":
    main()
