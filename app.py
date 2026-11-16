"""Painel da Auto Peças & Mecânica Aliança sobre o Postgres do Supabase."""

from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

TITULO = "Auto Peças & Mecânica Aliança"

ABA_GERAL = "Visão geral"
ABA_OS = "Ordens de Serviço"
ABA_FIN = "Financeiro"
ABA_CLI = "Clientes"
ABA_NF = "Notas Fiscais (NFS-e)"
ABAS = [ABA_GERAL, ABA_OS, ABA_FIN, ABA_CLI, ABA_NF]

OS_RESUMO_COLS = [
    "id_os",
    "nome_cliente",
    "placa",
    "veiculo",
    "data_entrada",
    "situacao",
]
OS_RESUMO_NOMES = {
    "id_os": "Número da O.S.",
    "nome_cliente": "Cliente",
    "placa": "Placa",
    "veiculo": "Veículo",
    "data_entrada": "Data de Entrada",
    "situacao": "Situação",
}
OS_DETALHE_COLS = [
    "descricao",
    "mecanico",
    "quantidade",
    "valor_unitario",
    "valor_total",
]
OS_DETALHE_NOMES = {
    "descricao": "Descrição",
    "mecanico": "Mecânico",
    "quantidade": "Quantidade",
    "valor_unitario": "Valor unitário",
    "valor_total": "Total",
}
FIN_COLS = [
    "os",
    "nome",
    "quitado",
    "vencimento",
    "valor",
    "valor_pago",
    "tipo",
    "forma_pagamento",
    "parcela",
    "dt_pagamento",
    "descricao",
    "obs_conta",
    "desconto",
    "data_lancamento",
    "emissao",
    "departamento",
    "documento",
    "conta",
]
ABERTAS_COLS = [
    "id",
    "os",
    "nome",
    "quitado",
    "vencimento",
    "dias_vencidos",
    "valor",
    "valor_pago",
    "saldo",
    "dt_pagamento",
    "obs_conta",
    "forma_pagamento",
    "parcela",
    "descricao",
]
CAMPOS_BAIXA = ["quitado", "valor_pago", "dt_pagamento", "obs_conta"]
DIAS_EDICAO_BAIXA = 7
NF_COLS = [
    "numero_nf",
    "id_nf",
    "nome_cliente",
    "id_cliente",
    "placa",
    "tipo_nf",
    "ref_nf",
    "ref_id",
    "data_cadastro",
    "status_nf",
    "motivo_nf",
    "date_recebimento_status",
    "pdf_nf",
    "xml_nf",
]
MONEY_COLS = {
    "valor",
    "valor_pago",
    "saldo",
    "desconto",
    "valor_unitario",
    "valor_total",
    "total_itens",
    "orc_desconto",
    "Valor unitário",
    "Total",
}
DATE_COLS = {
    "data_entrada",
    "Data de Entrada",
    "data_saida",
    "prev_atend_data",
    "previsao_atend_data",
    "vencimento",
    "dt_pagamento",
    "data_lancamento",
    "emissao",
    "data_cadastro",
    "date_recebimento_status",
}
SITUACAO_SQL = (
    "CASE WHEN situacao LIKE 'AGUARDANDO APROVA%' "
    "THEN 'AGUARDANDO APROVAÇÃO' ELSE situacao END"
)
ABERTO_SQL = "tipo = 'Receita' AND lower(IFNULL(quitado, '')) <> 'sim'"


def brl(value) -> str:
    if value is None or pd.isna(value):
        return "R$ 0,00"
    text = f"{float(value):,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def inteiro(value) -> str:
    if value is None or pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def like(text: str) -> str:
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def termos_busca(texto: str) -> list[str]:
    bruto = texto.strip()
    if not bruto:
        return []
    limpo = "".join(caractere for caractere in bruto if caractere.isalnum())
    termos = [bruto]
    if limpo and limpo.casefold() != bruto.casefold():
        termos.append(limpo)
    return termos


def numero_os(valor) -> int | None:
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except TypeError:
        pass
    texto = str(valor).strip()
    if not texto or texto.lower() == "none":
        return None
    try:
        return int(float(texto))
    except ValueError:
        return None


def data_br(valor) -> str:
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except TypeError:
        pass
    texto = str(valor).strip()
    if not texto or texto.lower() == "none":
        return ""
    parsed = pd.to_datetime(texto, errors="coerce")
    if pd.isna(parsed):
        return texto
    if parsed.strftime("%H:%M:%S") == "00:00:00":
        return parsed.strftime("%d/%m/%Y")
    return parsed.strftime("%d/%m/%Y %H:%M")


def texto_limpo(valor) -> str:
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except TypeError:
        pass
    if not isinstance(valor, str):
        return str(valor).strip()
    return str(repair_text(valor)).strip()


def clausula_pesquisa_oficina(termo: str, params: list) -> str:
    termos = termos_busca(termo)
    if not termos:
        return ""
    partes = []
    for campo in ("CAST(os AS TEXT)", "IFNULL(nome, '')"):
        for item in termos:
            partes.append(f"{campo} LIKE ? ESCAPE '\\'")
            params.append(like(item))
    existe = []
    for campo in (
        "CAST(o.id_os AS TEXT)",
        "IFNULL(o.nome_cliente, '')",
        "IFNULL(o.placa, '')",
        "IFNULL(o.placa_veiculo, '')",
        "IFNULL(o.mecanico, '')",
        "IFNULL(o.obs, '')",
    ):
        for item in termos:
            existe.append(f"{campo} LIKE ? ESCAPE '\\'")
            params.append(like(item))
    partes.append(
        "EXISTS (SELECT 1 FROM oficina_os o WHERE o.id_os = oficina_financeiro.os AND ("
        + " OR ".join(existe)
        + "))"
    )
    return " AND (" + " OR ".join(partes) + ")"


def repair_text(value):
    if not isinstance(value, str) or "Ã" not in value:
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def format_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if out[column].dtype == object:
            out[column] = out[column].map(repair_text)
        if column in DATE_COLS:
            parsed = pd.to_datetime(out[column], errors="coerce")
            has_time = parsed.dt.strftime("%H:%M:%S").fillna("00:00:00").ne("00:00:00")
            formatted = parsed.dt.strftime("%d/%m/%Y")
            formatted = formatted.where(~has_time, parsed.dt.strftime("%d/%m/%Y %H:%M"))
            out[column] = formatted.where(parsed.notna(), "")
        elif column not in MONEY_COLS and pd.api.types.is_numeric_dtype(out[column]):
            numeric = pd.to_numeric(out[column], errors="coerce")
            inteiros = numeric.dropna()
            if not inteiros.empty and inteiros.mod(1).eq(0).all():
                out[column] = numeric.map(lambda valor: "" if pd.isna(valor) else str(int(valor)))
    for column in out.columns:
        if out[column].dtype == object:
            out[column] = out[column].where(out[column].notna(), "")
    return out


def column_config(columns: list[str]) -> dict:
    config = {}
    for column in columns:
        if column in MONEY_COLS:
            config[column] = st.column_config.NumberColumn(column.replace("_", " "), format="R$ %.2f")
        elif column == "dias_vencidos":
            config[column] = st.column_config.TextColumn("Dias vencidos")
        elif column in {"pdf_nf", "xml_nf"}:
            config[column] = st.column_config.LinkColumn(column.replace("_", " "), display_text="abrir")
        else:
            config[column] = st.column_config.Column(column.replace("_", " "))
    return config


def _round_numeric(sql: str) -> str:
    """PostgreSQL só aceita ROUND(numeric, int); o SQLite aceitava double."""
    marca = "ROUND("
    saida = []
    inicio = 0
    while True:
        posicao = sql.find(marca, inicio)
        if posicao < 0:
            saida.append(sql[inicio:])
            break
        saida.append(sql[inicio:posicao])
        profundidade = 0
        virgula = None
        cursor = posicao + len(marca) - 1
        while cursor < len(sql):
            caractere = sql[cursor]
            if caractere == "(":
                profundidade += 1
            elif caractere == ")":
                profundidade -= 1
                if profundidade == 0:
                    break
            elif caractere == "," and profundidade == 1 and virgula is None:
                virgula = cursor
            cursor += 1
        if virgula is None or cursor >= len(sql):
            saida.append(sql[posicao : cursor + 1])
        else:
            expressao = sql[posicao + len(marca) : virgula]
            escala = sql[virgula:cursor]
            saida.append(f"ROUND(({expressao})::numeric{escala})")
        inicio = cursor + 1
    return "".join(saida)


def _sql_pg(sql: str, params: tuple = ()) -> tuple[str, dict]:
    sql = _round_numeric(sql.replace("IFNULL(", "COALESCE("))
    partes = sql.split("?")
    if len(partes) - 1 != len(params):
        raise ValueError(
            f"A consulta tem {len(partes) - 1} marcadores e {len(params)} parâmetros."
        )
    bind = {f"p{indice}": valor for indice, valor in enumerate(params)}
    convertido = partes[0]
    for indice in range(len(params)):
        convertido += f":p{indice}" + partes[indice + 1]
    return convertido, bind


@st.cache_resource
def engine():
    return create_engine(st.secrets["supabase"]["url"], pool_pre_ping=True)


@st.cache_data(ttl=120, show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    convertido, bind = _sql_pg(sql, params)
    return pd.read_sql(text(convertido), engine(), params=bind)


def scalar(sql: str, params: tuple = ()):
    frame = query(sql, params)
    if frame.empty:
        return None
    return frame.iat[0, 0]


def options(sql: str) -> list[str]:
    frame = query(sql)
    values = []
    for raw in frame.iloc[:, 0].dropna().tolist():
        text = repair_text(str(raw)).strip()
        if text and text not in values:
            values.append(text)
    return values


def pintar_faixa(frame: pd.DataFrame, tinta: str, exceto: set[str] | None = None):
    pular = exceto or set()

    def cor(linha):
        return ["" if coluna in pular else tinta for coluna in linha.index]

    return frame.style.apply(cor, axis=1)


def pintar_nao_pagas(frame: pd.DataFrame, exceto: set[str] | None = None):
    pular = exceto or set()
    hoje = date.today()

    def cor(linha):
        status = "" if "quitado" not in linha.index or pd.isna(linha["quitado"]) else str(linha["quitado"]).strip().casefold()
        quando = data_iso(linha["dt_pagamento"]) if "dt_pagamento" in linha.index else None
        if status == "sim" and baixa_recente(quando, hoje):
            tinta = "background-color: #d7ebf8; color: #16324f"
        elif status != "sim":
            tinta = "background-color: #ffe4cc; color: #7c2d12"
        else:
            tinta = ""
        return ["" if coluna in pular else tinta for coluna in linha.index]

    return frame.style.apply(cor, axis=1)


def show_table(df: pd.DataFrame, key: str, legenda: str | None = None, destacar: bool = False) -> None:
    texto = legenda or f"{inteiro(len(df))} linha(s) neste resultado"
    st.caption(texto)
    if df.empty:
        st.info("Nenhum registro encontrado com esses filtros.")
        return
    visible = format_frame(df)
    tabela = pintar_nao_pagas(visible) if destacar and "quitado" in visible.columns else visible
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=560,
        column_config=column_config(list(visible.columns)),
    )
    st.download_button(
        "Baixar CSV deste resultado",
        data=visible.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{key}.csv",
        mime="text/csv",
        key=f"download_{key}",
    )


def obs_os_existe(termo: str, vinculo: str, condicao: str = "") -> tuple[str, list]:
    termos = termos_busca(termo)
    if not termos:
        return "", []
    partes = []
    valores = []
    for item in termos:
        partes.append("IFNULL(o.obs, '') LIKE ? ESCAPE '\\'")
        valores.append(like(item))
    filtro = f" AND {condicao}" if condicao else ""
    sql = (
        f"EXISTS (SELECT 1 FROM oficina_os o WHERE o.id_os = {vinculo}{filtro} AND ("
        + " OR ".join(partes)
        + "))"
    )
    return sql, valores


def text_clause(
    columns: list[str],
    text: str,
    params: list,
    extras: list[tuple[str, list]] | None = None,
) -> str:
    extras = [(sql, valores) for sql, valores in (extras or []) if sql]
    if not text.strip() and not extras:
        return ""
    parts = []
    if text.strip():
        token = like(text)
        for column in columns:
            parts.append(f"IFNULL(CAST({column} AS TEXT), '') LIKE ? ESCAPE '\\'")
            params.append(token)
    for sql, valores in extras:
        parts.append(sql)
        params.extend(valores)
    return " AND (" + " OR ".join(parts) + ")"


def date_clause(column: str, start, end, params: list) -> str:
    sql = ""
    if start is not None:
        sql += f" AND {column} >= ?"
        params.append(start.isoformat())
    if end is not None:
        sql += f" AND {column} <= ?"
        params.append(end.isoformat())
    return sql


def in_clause(column: str, selected: list[str], params: list) -> str:
    if not selected:
        return ""
    params.extend(selected)
    marks = ", ".join("?" for _ in selected)
    return f" AND {column} IN ({marks})"


def soltar_filtro_aberto() -> None:
    st.session_state.financeiro_aberto = False


def ir_financeiro_aberto() -> None:
    quitados = options(
        "SELECT DISTINCT quitado FROM oficina_financeiro WHERE quitado IS NOT NULL ORDER BY 1"
    )
    st.session_state.aba = ABA_FIN
    st.session_state.busca_fin = ""
    st.session_state.tipo_fin = ["Receita"]
    st.session_state.quitado_fin = [valor for valor in quitados if valor.casefold() != "sim"]
    st.session_state.pop("fin_de", None)
    st.session_state.pop("fin_ate", None)
    st.session_state.financeiro_aberto = True


def visao_geral() -> None:
    st.header(TITULO)
    if st.button("Pesquisar histórico", type="primary", key="abrir_historico"):
        st.session_state.historico_aberto = True
    if st.session_state.get("historico_aberto"):
        painel_historico()
        return
    ordens = int(scalar("SELECT COUNT(DISTINCT id_os) FROM oficina_os") or 0)
    itens = int(scalar("SELECT COUNT(*) FROM oficina_os") or 0)
    clientes = int(
        scalar(
            """
            SELECT COUNT(*) FROM (
                SELECT id_cliente AS cliente FROM oficina_os WHERE id_cliente IS NOT NULL
                UNION
                SELECT cliente FROM oficina_financeiro WHERE cliente IS NOT NULL
                UNION
                SELECT id_cliente FROM oficina_nfse WHERE id_cliente IS NOT NULL
            ) clientes
            """
        )
        or 0
    )
    contas = int(scalar("SELECT COUNT(*) FROM oficina_financeiro") or 0)
    notas = int(scalar("SELECT COUNT(*) FROM oficina_nfse") or 0)
    despesa = scalar("SELECT SUM(valor) FROM oficina_financeiro WHERE tipo = 'Despesa'")
    aberto = scalar(
        "SELECT SUM(valor - valor_pago) FROM oficina_financeiro WHERE " + ABERTO_SQL
    )
    qtd_aberto = int(scalar("SELECT COUNT(*) FROM oficina_financeiro WHERE " + ABERTO_SQL) or 0)
    autorizadas = int(scalar("SELECT COUNT(*) FROM oficina_nfse WHERE status_nf = 'Autorizada'") or 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ordens de serviço", inteiro(ordens), help="O.S. distintas")
    c2.metric("Itens de serviço", inteiro(itens))
    c3.metric("Clientes", inteiro(clientes), help="Clientes unificados entre OS, financeiro e NFS-e")
    c4.metric("NFS-e", inteiro(notas), help=f"{inteiro(autorizadas)} autorizadas")

    c5, c6 = st.columns([1, 2])
    c5.metric("Contas", inteiro(contas))
    c5.caption(f"Despesas lançadas: {brl(despesa)}")
    with c6:
        st.markdown(
            f"""
            <div style="background:#fff6ed;border:2px solid #c2410c;border-radius:14px;padding:18px 22px;">
              <div style="font-size:1.05rem;color:#9a3412;font-weight:700;">Em aberto (receita)</div>
              <div style="font-size:2.5rem;line-height:1.15;color:#7c2d12;font-weight:800;margin-top:4px;">{brl(aberto)}</div>
              <div style="color:#9a3412;margin-top:6px;">{inteiro(qtd_aberto)} contas de receita ainda não quitadas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Ver contas em aberto",
            type="primary",
            on_click=ir_financeiro_aberto,
            width="stretch",
        )

    left, right = st.columns(2)
    situacao = query(
        f"""
        SELECT {SITUACAO_SQL} AS situacao,
               COUNT(DISTINCT id_os) AS ordens
        FROM oficina_os
        GROUP BY 1
        ORDER BY ordens DESC
        """
    )
    status = query(
        """
        SELECT status_nf AS status, COUNT(*) AS notas
        FROM oficina_nfse
        GROUP BY status_nf
        ORDER BY notas DESC
        """
    )
    with left:
        st.subheader("OS por situação")
        if situacao.empty:
            st.write("Sem dados.")
        else:
            st.bar_chart(situacao.set_index("situacao")["ordens"], height=280, sort=False)
    with right:
        st.subheader("NFS-e por status")
        if status.empty:
            st.write("Sem dados.")
        else:
            st.bar_chart(status.set_index("status")["notas"], height=280)

    mensal_os = query(
        """
        SELECT substr(data_entrada, 1, 7) AS mes, COUNT(DISTINCT id_os) AS ordens
        FROM oficina_os
        WHERE data_entrada IS NOT NULL
        GROUP BY mes
        ORDER BY mes
        """
    )
    mensal_fin = query(
        """
        SELECT substr(data_lancamento, 1, 7) AS mes,
               SUM(CASE WHEN tipo = 'Receita' THEN valor ELSE 0 END) AS receitas,
               SUM(CASE WHEN tipo = 'Despesa' THEN valor ELSE 0 END) AS despesas
        FROM oficina_financeiro
        WHERE data_lancamento IS NOT NULL
        GROUP BY mes
        ORDER BY mes
        """
    )
    left, right = st.columns(2)
    with left:
        st.subheader("OS por mês de entrada")
        if not mensal_os.empty:
            st.line_chart(mensal_os.set_index("mes")["ordens"], height=280)
    with right:
        st.subheader("Lançamentos por mês")
        if not mensal_fin.empty:
            st.line_chart(mensal_fin.set_index("mes")[["receitas", "despesas"]], height=280)

    st.subheader("Maiores clientes por receita")
    top = query(
        """
        SELECT nome AS cliente,
               COUNT(*) AS contas,
               ROUND(SUM(valor), 2) AS valor,
               ROUND(SUM(valor_pago), 2) AS valor_pago
        FROM oficina_financeiro
        WHERE tipo = 'Receita' AND nome IS NOT NULL AND TRIM(nome) <> ''
        GROUP BY nome
        ORDER BY valor DESC
        LIMIT 15
        """
    )
    if not top.empty:
        st.dataframe(
            format_frame(top),
            width="stretch",
            hide_index=True,
            column_config={
                "cliente": "cliente",
                "contas": st.column_config.NumberColumn("contas", format="%d"),
                "valor": st.column_config.NumberColumn("valor", format="R$ %.2f"),
                "valor_pago": st.column_config.NumberColumn("valor pago", format="R$ %.2f"),
            },
        )

    importado = query(
        "SELECT arquivo, aba, registros, importado_em FROM oficina_importacao ORDER BY id"
    )
    if not importado.empty:
        with st.expander("Origem da importação"):
            st.dataframe(format_frame(importado), width="stretch", hide_index=True)


def aba_os() -> None:
    situacoes = options(
        f"""
        SELECT DISTINCT {SITUACAO_SQL}
        FROM oficina_os
        WHERE situacao IS NOT NULL
        ORDER BY 1
        """
    )
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    texto = f1.text_input(
        "Pesquisar",
        placeholder="Cliente, placa, serviço, mecânico, observação ou nº da OS",
        key="busca_os",
    )
    situacao = f2.multiselect("Situação", situacoes, key="sit_os")
    inicio = f3.date_input("Entrada de", value=None, key="os_de", format="DD/MM/YYYY")
    fim = f4.date_input("Entrada até", value=None, key="os_ate", format="DD/MM/YYYY")
    limite = st.slider("Máximo de O.S.", 10, 200, 40, 10, key="limite_os")

    params: list = []
    where = " WHERE 1=1"
    where += text_clause(
        [
            "id_os",
            "nome_cliente",
            "placa",
            "placa_veiculo",
            "modelo",
            "marca",
            "chassi",
            "cidade",
            "mecanico",
            "descricao",
            "obs",
            "nome_funcionario",
        ],
        texto,
        params,
    )
    if situacao:
        marks = ", ".join("?" for _ in situacao)
        where += f" AND {SITUACAO_SQL} IN ({marks})"
        params.extend(situacao)
    where += date_clause("data_entrada", inicio, fim, params)
    sql = f"""
        SELECT id_os,
               MAX(nome_cliente) AS nome_cliente,
               COALESCE(
                   NULLIF(TRIM(MAX(placa)), ''),
                   NULLIF(TRIM(MAX(placa_veiculo)), '')
               ) AS placa,
               NULLIF(
                   TRIM(COALESCE(MAX(marca), '') || ' ' || COALESCE(MAX(modelo), '')),
                   ''
               ) AS veiculo,
               MAX(data_entrada) AS data_entrada,
               MAX({SITUACAO_SQL}) AS situacao
        FROM oficina_os
        {where}
        GROUP BY id_os
        ORDER BY MAX(data_entrada) DESC, id_os DESC
        LIMIT ?
    """
    resumo = query(sql, tuple(params + [int(limite)]))
    resumo = resumo[OS_RESUMO_COLS]
    show_table(
        resumo.rename(columns=OS_RESUMO_NOMES),
        "oficina_os",
        f"{inteiro(len(resumo))} O.S. nesta lista, uma linha por ordem",
    )
    if resumo.empty:
        return

    ids = tuple(int(valor) for valor in resumo["id_os"].tolist())
    marcas = ", ".join("?" for _ in ids)
    detalhes = query(
        f"""
        SELECT id, id_os, obs, descricao, mecanico, quantidade, valor_unitario, valor_total
        FROM oficina_os
        WHERE id_os IN ({marcas})
        ORDER BY id_os, id
        """,
        ids,
    )
    st.subheader("Serviços de cada O.S.")
    st.caption("Abra a ordem para ver os itens e as observações.")
    for registro in resumo.itertuples(index=False):
        cliente = repair_text(registro.nome_cliente) if isinstance(registro.nome_cliente, str) else ""
        placa = repair_text(registro.placa) if isinstance(registro.placa, str) else ""
        titulo = f"OS {int(registro.id_os)} · {cliente or 'Sem cliente'} · {placa or 'sem placa'}"
        with st.expander(titulo):
            bloco = detalhes[detalhes["id_os"] == int(registro.id_os)].copy()
            observacoes: list[str] = []
            for texto_obs in bloco["obs"].dropna().map(repair_text):
                limpo = str(texto_obs).strip()
                if limpo and limpo not in observacoes:
                    observacoes.append(limpo)
            st.markdown("**Observações**")
            st.text_area(
                "Observações",
                value="\n\n".join(observacoes) if observacoes else "Sem observações.",
                height=140,
                disabled=True,
                label_visibility="collapsed",
                key=f"obs_os_{int(registro.id_os)}",
            )
            tem_item = (
                bloco["descricao"].notna()
                | bloco["mecanico"].notna()
                | bloco["quantidade"].notna()
                | bloco["valor_total"].notna()
            )
            itens = bloco.loc[tem_item, OS_DETALHE_COLS].rename(columns=OS_DETALHE_NOMES)
            if itens.empty:
                st.caption("Nenhum item ou serviço lançado nesta O.S.")
                continue
            st.dataframe(
                format_frame(itens),
                width="stretch",
                hide_index=True,
                column_config=column_config(list(itens.columns)),
            )


def texto_banco(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def data_banco(valor) -> str | None:
    if valor is None or pd.isna(valor) or valor == "":
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        return texto[:10] if texto else None
    if isinstance(valor, pd.Timestamp):
        return None if pd.isna(valor) else valor.date().isoformat()
    if hasattr(valor, "isoformat"):
        return valor.isoformat()[:10]
    return str(valor)[:10]


def valor_banco(valor) -> float:
    if valor is None or pd.isna(valor) or valor == "":
        return 0.0
    return round(float(valor), 2)


def data_iso(valor) -> date | None:
    if valor is None or valor is pd.NaT:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, pd.Timestamp):
        return valor.date()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() == "none":
        return None
    texto = texto[:10]
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(texto, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def pagamento_cobre(pago: float, devido: float) -> bool:
    return devido > 0 and pago + 0.004 >= devido


def baixa_recente(quando: date | None, hoje: date | None = None) -> bool:
    if quando is None:
        return False
    return (hoje or date.today()) - quando <= timedelta(days=DIAS_EDICAO_BAIXA)


def dias_em_atraso(vencimento, quitado, hoje: date | None = None) -> int | None:
    if texto_banco(quitado).casefold() == "sim":
        return None
    quando = data_iso(vencimento)
    if quando is None:
        return None
    dias = ((hoje or date.today()) - quando).days
    if dias <= 0:
        return None
    return dias


def serie_dias_vencidos(frame: pd.DataFrame) -> pd.Series:
    hoje = date.today()
    if frame.empty:
        return pd.Series(dtype="Int64")
    valores = [
        dias_em_atraso(vencimento, quitado, hoje)
        for vencimento, quitado in zip(frame["vencimento"], frame["quitado"], strict=True)
    ]
    return pd.Series(valores, index=frame.index, dtype="Int64")


def com_dias_vencidos(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "vencimento" not in frame.columns or "quitado" not in frame.columns:
        return frame
    saida = frame.copy()
    saida["dias_vencidos"] = serie_dias_vencidos(saida)
    colunas = [coluna for coluna in saida.columns if coluna != "dias_vencidos"]
    if "vencimento" in colunas:
        colunas.insert(colunas.index("vencimento") + 1, "dias_vencidos")
    else:
        colunas.append("dias_vencidos")
    return saida[colunas]


def regra_baixa(pago: float, devido: float, quitado: str, pagamento: date | None) -> tuple[str, date | None, bool]:
    if pagamento_cobre(pago, devido):
        return "Sim", pagamento or date.today(), False
    bloqueou = quitado.casefold() == "sim" or pagamento is not None
    return "Nao", None, bloqueou


def normalizar_baixas(editado: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    saida = editado.copy()
    bloqueadas: list[str] = []
    for indice, linha in saida.iterrows():
        pago = valor_banco(linha.valor_pago)
        devido = valor_banco(linha.valor)
        quitado, pagamento, bloqueou = regra_baixa(
            pago,
            devido,
            texto_banco(linha.quitado) or "Nao",
            data_iso(linha.dt_pagamento),
        )
        saida.at[indice, "quitado"] = quitado
        saida.at[indice, "dt_pagamento"] = pd.NaT if pagamento is None else pd.Timestamp(pagamento)
        saida.at[indice, "saldo"] = round(devido - pago, 2)
        if bloqueou:
            numero = numero_os(linha.os)
            bloqueadas.append(str(numero) if numero is not None else str(int(linha.id)))
    return saida, bloqueadas


def assinatura_baixa(frame: pd.DataFrame) -> tuple:
    linhas = []
    for linha in frame.itertuples(index=False):
        linhas.append(
            (
                int(linha.id),
                texto_banco(linha.quitado).casefold(),
                data_iso(linha.dt_pagamento),
                valor_banco(linha.valor_pago),
            )
        )
    return tuple(linhas)


def texto_km(valor) -> str:
    if valor is None:
        return "sem km"
    try:
        if pd.isna(valor):
            return "sem km"
    except TypeError:
        pass
    texto = str(valor).strip()
    if not texto or texto.lower() == "none":
        return "sem km"
    try:
        numero = float(texto)
    except ValueError:
        return f"{texto} km"
    if numero.is_integer():
        return f"{inteiro(numero)} km"
    return f"{numero:.1f}".replace(".", ",") + " km"


def gravar_baixas(editado: pd.DataFrame, original: pd.DataFrame) -> int:
    base = original.set_index("id")
    alteradas = 0
    with engine().begin() as conn:
        for linha in editado.itertuples(index=False):
            chave = int(linha.id)
            antes = base.loc[chave]
            pago = valor_banco(linha.valor_pago)
            quitado, quando, _bloqueou = regra_baixa(
                pago,
                valor_banco(linha.valor),
                texto_banco(linha.quitado) or "Nao",
                data_iso(linha.dt_pagamento),
            )
            pagamento = None if quando is None else quando.isoformat()
            obs = texto_banco(linha.obs_conta)
            if (
                texto_banco(antes["quitado"]).casefold() == quitado.casefold()
                and data_banco(antes["dt_pagamento"]) == pagamento
                and valor_banco(antes["valor_pago"]) == pago
                and texto_banco(antes["obs_conta"]) == obs
            ):
                continue
            conn.execute(
                text(
                    """
                    UPDATE oficina_financeiro
                    SET quitado = :quitado,
                        dt_pagamento = :pagamento,
                        valor_pago = :pago,
                        obs_conta = :obs
                    WHERE id = :id
                    """
                ),
                {
                    "quitado": quitado,
                    "pagamento": pagamento,
                    "pago": pago,
                    "obs": obs or None,
                    "id": chave,
                },
            )
            alteradas += 1
    return alteradas


def pedir_os(origem: str, chave: str) -> None:
    click = st.session_state.get(chave)
    if click is None:
        return
    try:
        rotulo = click.label
    except AttributeError:
        rotulo = click["label"]
    numero = numero_os(rotulo)
    if numero is None:
        return
    st.session_state.fin_os_perguntar = numero
    st.session_state.fin_os_aberta = None
    st.session_state.fin_origem = origem


def voltar_financeiro() -> None:
    st.session_state.fin_rolar = st.session_state.get("fin_origem") or "abertas"
    st.session_state.fin_os_perguntar = None
    st.session_state.fin_os_aberta = None


def dispensar_os() -> None:
    if st.session_state.get("fin_os_perguntar") or st.session_state.get("fin_os_aberta"):
        st.session_state.fin_rolar = st.session_state.get("fin_origem") or "abertas"
    st.session_state.fin_os_perguntar = None
    st.session_state.fin_os_aberta = None


def observacoes_os(bloco: pd.DataFrame) -> list[str]:
    textos: list[str] = []
    if bloco.empty or "obs" not in bloco.columns:
        return textos
    for texto in bloco["obs"].dropna().map(repair_text):
        limpo = str(texto).strip()
        if limpo and limpo not in textos:
            textos.append(limpo)
    return textos


def servicos_da_os(bloco: pd.DataFrame) -> pd.DataFrame:
    colunas = ["descricao", "mecanico", "quantidade", "valor_unitario", "valor_total"]
    if bloco.empty:
        return pd.DataFrame(columns=colunas)
    tem_item = (
        bloco["descricao"].notna()
        | bloco["mecanico"].notna()
        | bloco["quantidade"].notna()
        | bloco["valor_total"].notna()
    )
    return bloco.loc[tem_item, colunas]


def render_os(numero: int) -> None:
    existe = int(scalar("SELECT COUNT(*) FROM oficina_os WHERE id_os = ?", (numero,)) or 0)
    if not existe:
        st.warning(f"A OS {numero} não está no histórico de ordens.")
        return
    cab = query(
        f"""
        SELECT MAX(nome_cliente) AS nome_cliente,
               COALESCE(NULLIF(TRIM(MAX(placa)), ''), NULLIF(TRIM(MAX(placa_veiculo)), '')) AS placa,
               MAX(km) AS km,
               NULLIF(TRIM(COALESCE(MAX(marca), '') || ' ' || COALESCE(MAX(modelo), '')), '') AS veiculo,
               MAX(data_entrada) AS data_entrada,
               MAX(data_saida) AS data_saida,
               MAX({SITUACAO_SQL}) AS situacao
        FROM oficina_os
        WHERE id_os = ?
        """,
        (numero,),
    )
    linha = cab.iloc[0]
    st.table(
        {
            "Cliente": texto_limpo(linha.nome_cliente),
            "Placa": texto_limpo(linha.placa),
            "Km": texto_km(linha.km),
            "Veículo": texto_limpo(linha.veiculo),
            "Entrada": data_br(linha.data_entrada),
            "Saída": data_br(linha.data_saida) or "sem saída",
            "Situação": texto_limpo(linha.situacao),
        },
        border="horizontal",
    )
    bloco = query(
        """
        SELECT obs, descricao, mecanico, quantidade, valor_unitario, valor_total
        FROM oficina_os
        WHERE id_os = ?
        ORDER BY id
        """,
        (numero,),
    )
    observacoes = observacoes_os(bloco)
    st.markdown("**Observações**")
    st.text_area(
        "Observações",
        value="\n\n".join(observacoes) if observacoes else "Sem observações.",
        height=120,
        disabled=True,
        label_visibility="collapsed",
        key=f"obs_fin_{numero}",
    )
    itens = servicos_da_os(bloco).rename(columns=OS_DETALHE_NOMES)
    if itens.empty:
        st.caption("Nenhum item ou serviço lançado nesta O.S.")
        return
    st.dataframe(
        format_frame(itens),
        width="stretch",
        hide_index=True,
        column_config=column_config(list(itens.columns)),
        alt=f"Serviços da OS {numero}",
    )
    total = pd.to_numeric(bloco["valor_total"], errors="coerce").fillna(0).sum()
    st.caption(f"Total dos serviços: {brl(total)}")


@st.dialog("Ordem de serviço", width="large", on_dismiss=dispensar_os)
def dialogo_os() -> None:
    numero = numero_os(st.session_state.get("fin_os_perguntar"))
    if numero is None:
        return
    if st.session_state.get("fin_os_aberta") != numero:
        st.write(f"Deseja ver a OS {numero} completa?")
        confirmar, cancelar = st.columns(2)
        if cancelar.button("Não", width="stretch", key="nao_ver_os"):
            voltar_financeiro()
            st.rerun()
        if confirmar.button("Ver OS completa", type="primary", width="stretch", key="ver_os_completa"):
            st.session_state.fin_os_aberta = numero
            st.rerun(scope="fragment")
        return
    if st.button("Voltar ao financeiro", type="primary", key="voltar_fin_os"):
        voltar_financeiro()
        st.rerun()
    st.subheader(f"OS {numero}")
    render_os(numero)


def coluna_os(origem: str, chave: str):
    return st.column_config.ButtonColumn(
        "O.S.",
        type="primary",
        pinned=True,
        help="Clique para ver a OS completa",
        on_click=pedir_os,
        kwargs={"origem": origem, "chave": chave},
        key=chave,
    )


def ancora_fin(nome: str) -> None:
    st.html(f'<div id="fin-{nome}" style="scroll-margin-top:80px"></div>')


def limpar_pesquisa_fin() -> None:
    st.session_state.fin_termo = ""
    st.session_state.fin_termo_campo = ""


def pesquisa_financeiro() -> str:
    with st.form("pesquisa_fin", border=True):
        campo, acao = st.columns([4, 1], vertical_alignment="bottom")
        termo_digitado = campo.text_input(
            "Pesquisar por placa, nome do cliente, OS, mecânico ou observação",
            key="fin_termo_campo",
            placeholder="Placa, nome do cliente, OS, mecânico ou observação",
            persist_state="session",
        )
        pesquisou = acao.form_submit_button("Pesquisar", type="primary", width="stretch")
    if pesquisou:
        st.session_state.fin_termo = termo_digitado.strip()
    termo = st.session_state.get("fin_termo", "").strip()
    if termo:
        st.caption(f"Pesquisa ativa: {termo}")
        st.button("Limpar pesquisa", key="limpar_pesquisa_fin", on_click=limpar_pesquisa_fin)
    return termo


def tabela_contas(frame: pd.DataFrame, origem: str, chave: str) -> None:
    if frame.empty:
        st.info("Nenhuma conta encontrada com esses filtros.")
        return
    visivel = format_frame(com_dias_vencidos(frame))
    if "os" in visivel.columns:
        visivel["os"] = visivel["os"].map(
            lambda valor: "" if numero_os(valor) is None else str(numero_os(valor))
        )
    config = column_config(list(visivel.columns))
    if "os" in visivel.columns:
        config["os"] = coluna_os(origem, chave)
    tabela = pintar_nao_pagas(visivel, {"os"}) if "quitado" in visivel.columns else visivel
    st.caption("Clique no número da O.S. para abrir a ordem.")
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=560,
        column_config=config,
        alt="Contas do financeiro",
    )
    st.download_button(
        "Baixar CSV deste resultado",
        data=visivel.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"oficina_financeiro_{origem}.csv",
        mime="text/csv",
        key=f"download_fin_{origem}",
    )


def clausula_historico(termo: str, params: list) -> str:
    termos = termos_busca(termo)
    if not termos:
        return ""
    partes = []
    for campo in (
        "IFNULL(nome_cliente, '')",
        "IFNULL(placa, '')",
        "IFNULL(placa_veiculo, '')",
        "IFNULL(obs, '')",
    ):
        for item in termos:
            partes.append(f"{campo} LIKE ? ESCAPE '\\'")
            params.append(like(item))
    return " AND (" + " OR ".join(partes) + ")"


def consultar_historico(termo: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    params: list = []
    filtro = clausula_historico(termo, params)
    total = int(
        scalar(
            "SELECT COUNT(*) FROM (SELECT id_os FROM oficina_os WHERE 1=1"
            f"{filtro} GROUP BY id_os)",
            tuple(params),
        )
        or 0
    )
    cab = query(
        f"""
        SELECT id_os,
               MAX(nome_cliente) AS nome_cliente,
               COALESCE(NULLIF(TRIM(MAX(placa)), ''), NULLIF(TRIM(MAX(placa_veiculo)), '')) AS placa,
               MAX(km) AS km,
               NULLIF(TRIM(COALESCE(MAX(marca), '') || ' ' || COALESCE(MAX(modelo), '')), '') AS veiculo,
               MAX(data_entrada) AS data_entrada,
               MAX(data_saida) AS data_saida,
               MAX({SITUACAO_SQL}) AS situacao
        FROM oficina_os
        WHERE 1=1{filtro}
        GROUP BY id_os
        ORDER BY MAX(data_entrada) DESC, id_os DESC
        LIMIT 60
        """,
        tuple(params),
    )
    if cab.empty:
        return cab, cab, total
    ids = tuple(int(valor) for valor in cab["id_os"].tolist())
    marcas = ", ".join("?" for _ in ids)
    detalhes = query(
        f"""
        SELECT id, id_os, obs, descricao, mecanico, quantidade, valor_unitario, valor_total
        FROM oficina_os
        WHERE id_os IN ({marcas})
        ORDER BY id_os, id
        """,
        ids,
    )
    return cab, detalhes, total


def marcar_historico(ids: list[int], marcado: bool) -> None:
    for item in ids:
        st.session_state[f"hist_marca_{item}"] = marcado


def qtd_txt(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}".replace(".", ",")


def html_historico(cab: pd.DataFrame, detalhes: pd.DataFrame, termo: str) -> str:
    clientes = []
    for nome in cab["nome_cliente"].map(texto_limpo):
        if nome and nome not in clientes:
            clientes.append(nome)
    placas = []
    for placa in cab["placa"].map(texto_limpo):
        if placa and placa not in placas:
            placas.append(placa)
    blocos = []
    total_geral = 0.0
    for registro in cab.itertuples(index=False):
        numero = int(registro.id_os)
        bloco = detalhes[detalhes["id_os"] == numero] if not detalhes.empty else detalhes
        servicos = servicos_da_os(bloco)
        linhas = []
        total = 0.0
        for item in servicos.itertuples(index=False):
            valor = 0.0 if pd.isna(item.valor_total) else float(item.valor_total)
            total += valor
            linhas.append(
                "<tr>"
                f"<td>{html.escape(texto_limpo(item.descricao))}</td>"
                f"<td>{html.escape(texto_limpo(item.mecanico))}</td>"
                f"<td>{html.escape(qtd_txt(item.quantidade))}</td>"
                f"<td style='text-align:right'>{html.escape(brl(item.valor_unitario))}</td>"
                f"<td style='text-align:right'>{html.escape(brl(valor))}</td>"
                "</tr>"
            )
        total_geral += total
        observacoes = observacoes_os(bloco)
        obs_html = ""
        if observacoes:
            obs_html = "<p class='meta'><strong>Observações:</strong> " + html.escape(" | ".join(observacoes)) + "</p>"
        corpo = (
            "".join(linhas)
            if linhas
            else "<tr><td colspan='5'>Nenhum serviço lançado.</td></tr>"
        )
        blocos.append(
            f"<h2>OS {numero}</h2>"
            "<p class='meta'>"
            f"Cliente: {html.escape(texto_limpo(registro.nome_cliente) or 'não informado')}"
            f" · Placa: {html.escape(texto_limpo(registro.placa) or 'não informada')}"
            f" · Km: {html.escape(texto_km(registro.km))}"
            f" · Veículo: {html.escape(texto_limpo(registro.veiculo) or 'não informado')}"
            "</p>"
            "<p class='meta'>"
            f"Entrada: {html.escape(data_br(registro.data_entrada) or 'não informada')}"
            f" · Saída: {html.escape(data_br(registro.data_saida) or 'sem saída')}"
            f" · Situação: {html.escape(texto_limpo(registro.situacao) or 'não informada')}"
            "</p>"
            f"{obs_html}"
            "<table><thead><tr>"
            "<th>Serviço</th><th>Mecânico</th><th>Qtd.</th><th>Valor unitário</th><th>Total</th>"
            "</tr></thead><tbody>"
            f"{corpo}"
            f"<tr><td colspan='4' class='total'>Total da OS</td><td class='total'>{html.escape(brl(total))}</td></tr>"
            "</tbody></table>"
        )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Histórico — {html.escape(TITULO)}</title>
<style>
body {{ font-family: Arial, sans-serif; color: #1c2430; margin: 24px; }}
h1 {{ font-size: 20px; margin-bottom: 4px; }}
h2 {{ font-size: 16px; margin: 18px 0 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 4px; }}
th, td {{ border: 1px solid #d0d5dd; padding: 6px 8px; font-size: 12px; text-align: left; }}
th {{ background: #f4f6f8; }}
.total {{ text-align: right; font-weight: bold; }}
.meta {{ color: #475467; margin: 0 0 6px; }}
</style>
</head>
<body>
<h1>{html.escape(TITULO)}</h1>
<p class="meta">Histórico de ordens de serviço para o cliente · emitido em {date.today().strftime("%d/%m/%Y")}</p>
<p class="meta">Pesquisa: {html.escape(termo)} · Cliente: {html.escape(", ".join(clientes) or "não informado")} · Placa: {html.escape(", ".join(placas) or "não informada")}</p>
{"".join(blocos)}
<p class="total">Total geral das OS selecionadas: {html.escape(brl(total_geral))}</p>
</body>
</html>"""


def disparar_impressao(documento: str) -> None:
    payload = json.dumps(documento)
    st.html(
        "<script>"
        "const janela = window.open('', '_blank');"
        f"if (janela) {{ janela.document.open(); janela.document.write({payload}); janela.document.close(); janela.focus(); janela.print(); }}"
        "</script>",
        unsafe_allow_javascript=True,
    )


def painel_historico() -> None:
    st.subheader("Pesquisar histórico")
    if st.button("Fechar pesquisa", key="fechar_historico"):
        st.session_state.historico_aberto = False
        st.rerun()
    with st.form("pesquisa_historico", border=True):
        campo, acao = st.columns([4, 1], vertical_alignment="bottom")
        digitado = campo.text_input(
            "Placa, nome do cliente ou observação",
            key="historico_campo",
            placeholder="Placa, nome do cliente ou observação",
            persist_state="session",
        )
        enviou = acao.form_submit_button("Pesquisar", type="primary", width="stretch")
    if enviou:
        st.session_state.historico_termo = digitado.strip()
    termo = st.session_state.get("historico_termo", "").strip()
    if not termo:
        st.info("Digite a placa, o nome do cliente ou um trecho da observação e clique em Pesquisar.")
        return
    cab, detalhes, total = consultar_historico(termo)
    if cab.empty:
        st.warning("Nenhuma ordem de serviço encontrada para essa pesquisa.")
        return
    if total > len(cab):
        st.caption(f"Mostrando {inteiro(len(cab))} de {inteiro(total)} ordens. Refine a pesquisa para ver as demais.")
    else:
        st.caption(f"{inteiro(len(cab))} ordem(ns) de serviço. Marque as que devem sair na impressão.")
    ids = [int(valor) for valor in cab["id_os"].tolist()]
    marcar, limpar = st.columns(2)
    marcar.button("Marcar todas", key="hist_marcar", on_click=marcar_historico, args=(ids, True), width="stretch")
    limpar.button("Desmarcar", key="hist_limpar", on_click=marcar_historico, args=(ids, False), width="stretch")
    escolhidas = [item for item in ids if st.session_state.get(f"hist_marca_{item}")]
    documento = ""
    if escolhidas:
        selecionadas = cab[cab["id_os"].isin(escolhidas)]
        documento = html_historico(selecionadas, detalhes, termo)
        st.download_button(
            "Baixar relatório",
            data=documento.encode("utf-8"),
            file_name="historico-cliente.html",
            mime="text/html",
            key="hist_download",
        )
    imprimir = st.button(
        "Imprimir selecionadas",
        type="primary",
        key="hist_imprimir",
        disabled=not escolhidas,
    )
    if imprimir and documento:
        st.session_state.historico_imprimir = documento
    if not escolhidas:
        st.caption("Marque uma ou mais OS para imprimir o relatório do cliente.")
    for registro in cab.itertuples(index=False):
        numero = int(registro.id_os)
        bloco = detalhes[detalhes["id_os"] == numero] if not detalhes.empty else detalhes
        itens = servicos_da_os(bloco).rename(columns=OS_DETALHE_NOMES)
        with st.container(border=True):
            st.checkbox(
                f"Imprimir OS {numero}",
                key=f"hist_marca_{numero}",
                persist_state="session",
            )
            st.markdown(
                f"**OS {numero}** · {texto_limpo(registro.nome_cliente) or 'Sem cliente'} · "
                f"{texto_limpo(registro.placa) or 'sem placa'} · {texto_km(registro.km)}"
            )
            st.caption(
                f"Entrada {data_br(registro.data_entrada) or 'não informada'} · "
                f"Saída {data_br(registro.data_saida) or 'sem saída'} · "
                f"{texto_limpo(registro.veiculo) or 'veículo não informado'}"
            )
            observacoes = observacoes_os(bloco)
            if observacoes:
                st.caption("Observações: " + " | ".join(observacoes))
            if itens.empty:
                st.caption("Nenhum serviço lançado.")
                continue
            st.dataframe(
                format_frame(itens),
                width="stretch",
                hide_index=True,
                column_config=column_config(list(itens.columns)),
                alt=f"Serviços da OS {numero}",
            )
            total_os = pd.to_numeric(bloco["valor_total"], errors="coerce").fillna(0).sum()
            st.caption(f"Total da OS: {brl(total_os)}")
    pendente = st.session_state.pop("historico_imprimir", None)
    if isinstance(pendente, str) and pendente:
        disparar_impressao(pendente)


def config_baixas(origem: str, chave: str) -> dict:
    bloqueadas = [coluna for coluna in ABERTAS_COLS if coluna not in CAMPOS_BAIXA]
    config = {
        "id": None,
        "os": coluna_os(origem, chave),
        "nome": st.column_config.TextColumn("Cliente", disabled=True),
        "quitado": st.column_config.SelectboxColumn("Quitado", options=["Nao", "Sim"], required=True),
        "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY", disabled=True),
        "dias_vencidos": st.column_config.NumberColumn("Dias vencidos", format="%d", disabled=True),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", disabled=True),
        "valor_pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f", min_value=0, step=0.01),
        "saldo": st.column_config.NumberColumn("Saldo", format="R$ %.2f", disabled=True),
        "dt_pagamento": st.column_config.DateColumn("Dt pagamento", format="DD/MM/YYYY"),
        "obs_conta": st.column_config.TextColumn("Obs conta", width="large"),
        "forma_pagamento": st.column_config.TextColumn("Forma de pagamento", disabled=True),
        "parcela": st.column_config.NumberColumn("Parcela", format="%d", disabled=True),
        "descricao": st.column_config.TextColumn("Descrição", disabled=True, width="large"),
    }
    for coluna in bloqueadas:
        if coluna in config and isinstance(config[coluna], dict):
            config[coluna]["disabled"] = True
    return config


def preparar_editor(contas: pd.DataFrame) -> pd.DataFrame:
    editor = com_dias_vencidos(contas)[ABERTAS_COLS].copy()
    editor["quitado"] = editor["quitado"].map(
        lambda valor: "Sim" if texto_banco(valor).casefold() == "sim" else "Nao"
    )
    for coluna in ("nome", "obs_conta", "forma_pagamento", "descricao"):
        editor[coluna] = editor[coluna].map(lambda valor: "" if pd.isna(valor) else str(valor))
    editor["os"] = editor["os"].map(lambda valor: "" if numero_os(valor) is None else str(numero_os(valor)))
    editor["valor_pago"] = pd.to_numeric(editor["valor_pago"], errors="coerce").fillna(0)
    editor["valor"] = pd.to_numeric(editor["valor"], errors="coerce").fillna(0)
    editor["saldo"] = pd.to_numeric(editor["saldo"], errors="coerce").fillna(0)
    editor["dt_pagamento"] = pd.to_datetime(editor["dt_pagamento"], errors="coerce")
    editor["vencimento"] = pd.to_datetime(editor["vencimento"], errors="coerce")
    return editor


def mesmo_conjunto(rascunho, banco: pd.DataFrame) -> bool:
    if not isinstance(rascunho, pd.DataFrame) or "id" not in rascunho.columns:
        return False
    return set(rascunho["id"].astype(int)) == set(banco["id"].astype(int))


def editor_baixas(contas: pd.DataFrame, origem: str, chave: str, legenda: str) -> None:
    versao_chave = f"baixa_versao_{origem}"
    rascunho_chave = f"rascunho_{origem}"
    st.session_state.setdefault(versao_chave, 0)
    banco = preparar_editor(contas)
    rascunho = st.session_state.get(rascunho_chave)
    visivel = rascunho if mesmo_conjunto(rascunho, banco) else banco
    st.caption(legenda)
    alerta = st.session_state.pop(f"baixa_alerta_{origem}", None)
    if alerta:
        st.warning(alerta)
    alterado = st.data_editor(
        pintar_nao_pagas(visivel, {"os"}),
        width="stretch",
        hide_index=True,
        height=560 if origem == "abertas" else 360,
        num_rows="fixed",
        disabled=[coluna for coluna in ABERTAS_COLS if coluna not in CAMPOS_BAIXA],
        column_config=config_baixas(origem, chave),
        key=f"editor_{origem}_{st.session_state[versao_chave]}",
        alt="Contas com baixa editável",
    )
    ajustado, bloqueadas = normalizar_baixas(alterado)
    if assinatura_baixa(ajustado) != assinatura_baixa(alterado):
        st.session_state[rascunho_chave] = ajustado
        st.session_state[versao_chave] += 1
        if bloqueadas:
            lista = ", ".join(bloqueadas[:8])
            st.session_state[f"baixa_alerta_{origem}"] = (
                "Quitado e Dt pagamento só preenchem quando o valor pago é igual ou maior "
                f"que o valor da conta. Ajuste nas OS {lista}."
            )
        st.rerun()
    if st.button("Salvar baixas", type="primary", key=f"salvar_{origem}"):
        st.session_state.baixa_aviso = gravar_baixas(ajustado, banco)
        st.session_state[rascunho_chave] = None
        st.session_state[versao_chave] += 1
        st.cache_data.clear()
        st.rerun()


def aba_financeiro() -> None:
    rolar = st.session_state.pop("fin_rolar", None)
    termo = pesquisa_financeiro()
    params_abertas: list = []
    filtro_aberto = clausula_pesquisa_oficina(termo, params_abertas)
    abertas = query(
        f"""
        SELECT id, os, nome, quitado, vencimento, valor, valor_pago,
               ROUND(COALESCE(valor, 0) - COALESCE(valor_pago, 0), 2) AS saldo,
               dt_pagamento, obs_conta, forma_pagamento, parcela, descricao
        FROM oficina_financeiro
        WHERE {ABERTO_SQL}{filtro_aberto}
        ORDER BY CASE WHEN vencimento IS NULL OR TRIM(vencimento) = '' THEN 1 ELSE 0 END,
                 vencimento ASC,
                 os ASC,
                 id ASC
        """,
        tuple(params_abertas),
    )
    ancora_fin("abertas")
    st.subheader("Contas em aberto")
    aviso = st.session_state.pop("baixa_aviso", None)
    if aviso:
        st.success(f"{inteiro(aviso)} conta(s) atualizada(s).")
    elif aviso == 0:
        st.info("Nenhuma alteração para salvar.")
    c1, c2 = st.columns(2)
    c1.metric("Contas pendentes", inteiro(len(abertas)))
    c2.metric("Total em aberto", brl(abertas["saldo"].sum() if not abertas.empty else 0))
    if abertas.empty:
        st.info("Nenhuma conta de receita em aberto.")
    else:
        editor_baixas(
            abertas,
            "abertas",
            "fin_click_abertas",
            "Contas em aberto em laranja. Dias vencidos conta a partir do vencimento. "
            "Informe o valor pago: se ele for igual ou maior que o valor da conta, Quitado vira Sim "
            "e a data de hoje entra em Dt pagamento. A data continua editável. "
            "Com valor menor, Quitado e Dt pagamento não são preenchidos. "
            "O restante do painel não pode ser alterado. Clique no número da O.S. para abrir a ordem.",
        )

    ancora_fin("recentes")
    st.subheader("Baixas recentes")
    st.caption(
        f"Contas quitadas nos últimos {DIAS_EDICAO_BAIXA} dias ficam em azul e ainda podem ser corrigidas. "
        "Depois desse prazo a baixa fica bloqueada, como o restante do painel."
    )
    limite_recente = (date.today() - timedelta(days=DIAS_EDICAO_BAIXA)).isoformat()
    params_recentes = [limite_recente, *params_abertas]
    recentes = query(
        f"""
        SELECT id, os, nome, quitado, vencimento, valor, valor_pago,
               ROUND(COALESCE(valor, 0) - COALESCE(valor_pago, 0), 2) AS saldo,
               dt_pagamento, obs_conta, forma_pagamento, parcela, descricao
        FROM oficina_financeiro
        WHERE tipo = 'Receita'
          AND lower(IFNULL(quitado, '')) = 'sim'
          AND substr(IFNULL(dt_pagamento, ''), 1, 10) >= ?
          {filtro_aberto}
        ORDER BY dt_pagamento DESC, id DESC
        """,
        tuple(params_recentes),
    )
    if recentes.empty:
        st.info(f"Nenhuma baixa nos últimos {DIAS_EDICAO_BAIXA} dias.")
    else:
        r1, r2 = st.columns(2)
        r1.metric("Baixas no prazo", inteiro(len(recentes)))
        r2.metric("Valor dessas baixas", brl(recentes["valor_pago"].sum()))
        editor_baixas(
            recentes,
            "recentes",
            "fin_click_recentes",
            "Ajuste Valor pago, Quitado, Dt pagamento ou Obs conta se a baixa precisar de correção.",
        )

    ancora_fin("todas")
    st.subheader("Todas as contas")
    st.caption(
        f"Contas recebidas nos últimos {DIAS_EDICAO_BAIXA} dias ficam no topo das recebidas, "
        "da baixa mais nova para a mais antiga. Depois desse prazo elas seguem a ordem de vencimento."
    )
    tipos = options("SELECT DISTINCT tipo FROM oficina_financeiro WHERE tipo IS NOT NULL ORDER BY 1")
    quitados = options("SELECT DISTINCT quitado FROM oficina_financeiro WHERE quitado IS NOT NULL ORDER BY 1")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    texto = f1.text_input(
        "Pesquisar",
        placeholder="OS, cliente, descrição, documento ou observação",
        key="busca_fin",
        persist_state="session",
    )
    tipo = f2.multiselect(
        "Tipo", tipos, key="tipo_fin", on_change=soltar_filtro_aberto, persist_state="session"
    )
    quitado = f3.multiselect(
        "Quitado", quitados, key="quitado_fin", on_change=soltar_filtro_aberto, persist_state="session"
    )
    limite = f4.slider("Máximo de linhas", 50, 5000, 500, 50, key="limite_fin", persist_state="session")
    d1, d2 = st.columns(2)
    inicio = d1.date_input(
        "Vencimento de", value=None, key="fin_de", format="DD/MM/YYYY", persist_state="session"
    )
    fim = d2.date_input(
        "Vencimento até", value=None, key="fin_ate", format="DD/MM/YYYY", persist_state="session"
    )

    params: list = []
    where = " WHERE 1=1"
    where += text_clause(
        ["os", "nome", "descricao", "documento", "forma_pagamento", "departamento"],
        texto,
        params,
        [obs_os_existe(texto, "oficina_financeiro.os")],
    )
    where += clausula_pesquisa_oficina(termo, params)
    if st.session_state.get("financeiro_aberto"):
        where += " AND " + ABERTO_SQL
    else:
        where += in_clause("tipo", tipo, params)
        where += in_clause("quitado", quitado, params)
    where += date_clause("vencimento", inicio, fim, params)
    totais = query(
        f"SELECT COUNT(*) AS n, SUM(valor) AS valor, SUM(valor_pago) AS pago, SUM(valor - valor_pago) AS aberto FROM oficina_financeiro{where}",
        tuple(params),
    )
    cols = ", ".join(FIN_COLS)
    recebida_recente = (
        "tipo = 'Receita' AND lower(IFNULL(quitado, '')) = 'sim' "
        "AND substr(IFNULL(dt_pagamento, ''), 1, 10) >= ?"
    )
    sql = (
        f"SELECT {cols} FROM oficina_financeiro{where} "
        f"ORDER BY CASE WHEN {ABERTO_SQL} THEN 0 ELSE 1 END, "
        f"CASE WHEN {recebida_recente} THEN 0 ELSE 1 END, "
        f"CASE WHEN {recebida_recente} THEN dt_pagamento END DESC, "
        "CASE WHEN vencimento IS NULL OR TRIM(vencimento) = '' THEN 1 ELSE 0 END, "
        "vencimento ASC, id ASC LIMIT ?"
    )
    frame = query(sql, tuple([*params, limite_recente, limite_recente, int(limite)]))
    m1, m2, m3 = st.columns(3)
    m1.metric("Linhas no filtro", inteiro(totais.iat[0, 0] or 0))
    m2.metric("Valor filtrado", brl(totais.iat[0, 1]))
    m3.metric("Saldo em aberto", brl(totais.iat[0, 3]))
    tabela_contas(frame, "todas", "fin_click_todas")
    if st.session_state.get("fin_os_perguntar"):
        dialogo_os()
    if rolar in {"abertas", "recentes", "todas"}:
        st.html(
            "<script>"
            f"var alvo=document.getElementById('fin-{rolar}');"
            "if(alvo){alvo.scrollIntoView({block:'start'});}"
            "</script>",
            unsafe_allow_javascript=True,
        )


CONTAS_CLIENTE_SQL = """
SELECT
    f.id,
    f.os,
    f.parcela,
    f.descricao,
    f.vencimento,
    f.quitado,
    ROUND(COALESCE(f.valor, 0), 2) AS valor,
    ROUND(COALESCE(f.valor_pago, 0), 2) AS valor_pago,
    ROUND(COALESCE(f.valor, 0) - COALESCE(f.valor_pago, 0), 2) AS saldo,
    COALESCE(
        NULLIF(TRIM(f.nome), ''),
        NULLIF(TRIM(o.nome_cliente), ''),
        NULLIF(TRIM(o.placa), ''),
        'Sem identificação'
    ) AS cliente,
    COALESCE(NULLIF(TRIM(o.placa), ''), '') AS placa,
    CASE
        WHEN lower(IFNULL(f.quitado, '')) <> 'sim'
         AND TRIM(IFNULL(f.vencimento, '')) <> ''
         AND substr(f.vencimento, 1, 10) < ?
        THEN 1 ELSE 0
    END AS vencida,
    CASE
        WHEN lower(IFNULL(f.quitado, '')) <> 'sim' THEN 1 ELSE 0
    END AS aberta
FROM oficina_financeiro f
LEFT JOIN (
    SELECT id_os,
           MAX(nome_cliente) AS nome_cliente,
           COALESCE(
               NULLIF(TRIM(MAX(placa)), ''),
               NULLIF(TRIM(MAX(placa_veiculo)), '')
           ) AS placa
    FROM oficina_os
    GROUP BY id_os
) o ON o.id_os = f.os
WHERE f.tipo = 'Receita'
"""
VERMELHO = "background-color: #f8d0d0; color: #7f1d1d"
AZUL = "background-color: #d7ebf8; color: #16324f"


def contas_clientes(hoje: str) -> pd.DataFrame:
    frame = query(CONTAS_CLIENTE_SQL, (hoje,))
    if frame.empty:
        frame["chave"] = []
        return frame
    frame["cliente"] = frame["cliente"].map(lambda valor: texto_limpo(valor) or "Sem identificação")
    frame["placa"] = frame["placa"].map(texto_limpo)
    frame["chave"] = frame["cliente"].str.casefold()
    return frame


def nome_do_grupo(valores: pd.Series) -> str:
    validos = valores.map(lambda valor: texto_limpo(valor))
    validos = validos[validos != ""]
    if validos.empty:
        return "Sem identificação"
    return str(validos.mode().iloc[0])


def chaves_da_busca(base: pd.DataFrame, termo: str) -> set[str] | None:
    texto = termo.strip().casefold()
    if not texto or base.empty:
        return None
    cliente = base["cliente"].fillna("").str.casefold()
    placa = base["placa"].fillna("").str.casefold()
    mask = cliente.str.contains(texto, regex=False) | placa.str.contains(texto, regex=False)
    return set(base.loc[mask, "chave"])


def listas_clientes(base: pd.DataFrame, busca: set[str] | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if base.empty:
        vazio = pd.DataFrame(columns=["chave", "cliente", "contas", "ordens", "divida", "a_vencer"])
        return vazio, vazio
    vencidas = base[base["vencida"] == 1]
    if busca is not None:
        vencidas = vencidas[vencidas["chave"].isin(busca)]
    if vencidas.empty:
        inad = pd.DataFrame(columns=["chave", "cliente", "contas", "ordens", "divida"])
    else:
        inad = (
            vencidas.groupby("chave", as_index=False)
            .agg(
                cliente=("cliente", nome_do_grupo),
                contas=("id", "count"),
                ordens=("os", "nunique"),
                divida=("saldo", "sum"),
            )
            .sort_values(["divida", "cliente"], ascending=[False, True])
            .reset_index(drop=True)
        )
        inad["divida"] = inad["divida"].round(2)
    chaves_vermelhas = set(base.loc[base["vencida"] == 1, "chave"])
    azuis = base[~base["chave"].isin(chaves_vermelhas)]
    if busca is not None:
        azuis = azuis[azuis["chave"].isin(busca)]
    if azuis.empty:
        adim = pd.DataFrame(columns=["chave", "cliente", "a_vencer"])
    else:
        a_vencer = (
            base[(base["aberta"] == 1) & (base["vencida"] == 0)]
            .groupby("chave")["saldo"]
            .sum()
        )
        adim = (
            azuis.groupby("chave", as_index=False)
            .agg(cliente=("cliente", nome_do_grupo))
            .sort_values("cliente")
            .reset_index(drop=True)
        )
        adim["a_vencer"] = adim["chave"].map(a_vencer).fillna(0).round(2)
    return inad, adim


def abrir_divida() -> None:
    click = st.session_state.get("cli_click_divida")
    if click is None:
        return
    ordem = list(st.session_state.get("cli_ordem") or [])
    rotulos = list(st.session_state.get("cli_rotulos") or [])
    nomes = list(st.session_state.get("cli_nomes") or [])
    try:
        rotulo = click.label
        indice = click.row
    except AttributeError:
        rotulo = click["label"]
        indice = click["row"]
    escolhido = None
    if isinstance(rotulo, str) and rotulos.count(rotulo) == 1:
        escolhido = rotulos.index(rotulo)
    elif isinstance(indice, int) and 0 <= indice < len(ordem):
        escolhido = indice
    if escolhido is None:
        return
    st.session_state.cli_cliente = ordem[escolhido]
    st.session_state.cli_nome = nomes[escolhido] if escolhido < len(nomes) else ordem[escolhido]
    st.session_state.cli_os = None
    st.session_state.cli_os_aberta = None


def abrir_os_cliente() -> None:
    click = st.session_state.get("cli_click_os")
    if click is None:
        return
    try:
        rotulo = click.label
    except AttributeError:
        rotulo = click["label"]
    numero = numero_os(rotulo)
    if numero is None:
        return
    st.session_state.cli_os = numero
    st.session_state.cli_os_aberta = None


def fechar_cliente() -> None:
    st.session_state.cli_cliente = None
    st.session_state.cli_nome = None
    st.session_state.cli_os = None
    st.session_state.cli_os_aberta = None


def dividas_do_cliente(base: pd.DataFrame, chave: str) -> pd.DataFrame:
    linhas = base[(base["chave"] == chave) & (base["vencida"] == 1)].copy()
    if linhas.empty:
        return linhas
    linhas["dias"] = [
        dias_em_atraso(vencimento, quitado)
        for vencimento, quitado in zip(linhas["vencimento"], linhas["quitado"], strict=True)
    ]
    linhas = linhas.sort_values(["vencimento", "os", "parcela"], kind="mergesort")
    linhas["os"] = linhas["os"].map(lambda valor: "" if numero_os(valor) is None else str(numero_os(valor)))
    linhas["vencimento"] = linhas["vencimento"].map(data_br)
    return linhas.reset_index(drop=True)


@st.dialog("Dívidas do cliente", width="large", on_dismiss=fechar_cliente)
def dialogo_dividas() -> None:
    base = contas_clientes(date.today().isoformat())
    chave = st.session_state.get("cli_cliente")
    if not chave:
        return
    nome = st.session_state.get("cli_nome") or chave
    numero = numero_os(st.session_state.get("cli_os"))
    if numero is not None and st.session_state.get("cli_os_aberta") == numero:
        if st.button("Voltar às dívidas", type="primary", key="voltar_dividas"):
            st.session_state.cli_os = None
            st.session_state.cli_os_aberta = None
            st.rerun(scope="fragment")
        st.subheader(f"OS {numero}")
        render_os(numero)
        return
    if numero is not None:
        st.write(f"Deseja ver a OS {numero} completa?")
        confirmar, cancelar = st.columns(2)
        if cancelar.button("Não", width="stretch", key="nao_ver_os_cli"):
            st.session_state.cli_os = None
            st.rerun(scope="fragment")
        if confirmar.button("Ver OS completa", type="primary", width="stretch", key="ver_os_cli"):
            st.session_state.cli_os_aberta = numero
            st.rerun(scope="fragment")
        return
    linhas = dividas_do_cliente(base, chave)
    st.subheader(nome)
    if linhas.empty:
        st.success("Este cliente não tem dívida vencida. Ele está na lista de adimplentes.")
        return
    st.caption(f"Dívida vencida: {brl(linhas['saldo'].sum())}. Clique no número da O.S. para abrir a ordem completa.")
    visivel = linhas[["os", "placa", "vencimento", "dias", "parcela", "valor", "valor_pago", "saldo", "descricao"]].copy()
    config = {
        "os": st.column_config.ButtonColumn(
            "O.S.",
            type="primary",
            pinned=True,
            help="Clique para ver a OS completa",
            on_click=abrir_os_cliente,
            key="cli_click_os",
        ),
        "placa": st.column_config.TextColumn("Placa"),
        "vencimento": st.column_config.TextColumn("Vencimento"),
        "dias": st.column_config.NumberColumn("Dias vencidos"),
        "parcela": st.column_config.TextColumn("Parcela"),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        "valor_pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f"),
        "saldo": st.column_config.NumberColumn("Saldo", format="R$ %.2f"),
        "descricao": st.column_config.TextColumn("Descrição"),
    }
    st.dataframe(
        visivel,
        width="stretch",
        hide_index=True,
        height=360,
        column_config=config,
        alt=f"Dívidas de {nome}",
    )


def aba_clientes() -> None:
    hoje = date.today().isoformat()
    base = contas_clientes(hoje)
    termo = st.text_input(
        "Pesquisar cliente",
        placeholder="Nome do cliente ou placa",
        key="busca_cli",
        persist_state="session",
    )
    busca = chaves_da_busca(base, termo)
    inad, adim = listas_clientes(base, busca)
    c1, c2, c3 = st.columns(3)
    c1.metric("Inadimplentes", inteiro(len(inad)))
    c2.metric("Dívida vencida", brl(inad["divida"].sum() if not inad.empty else 0))
    c3.metric("Adimplentes", inteiro(len(adim)))
    st.caption(
        "A lista vermelha reúne quem tem conta de receita vencida e não quitada. "
        "Ao quitar essa conta no Financeiro, o cliente sai da lista vermelha e passa para a lista azul. "
        "Quando a conta não tem nome, o cliente aparece pela placa."
    )

    st.subheader("Inadimplentes")
    if inad.empty:
        st.info("Nenhum cliente inadimplente com esses filtros.")
        st.session_state.cli_ordem = []
        st.session_state.cli_rotulos = []
        st.session_state.cli_nomes = []
    else:
        grade = inad[["cliente", "contas", "ordens", "divida"]].copy()
        rotulos = [brl(valor) for valor in inad["divida"]]
        grade["divida"] = rotulos
        st.session_state.cli_ordem = inad["chave"].tolist()
        st.session_state.cli_rotulos = rotulos
        st.session_state.cli_nomes = inad["cliente"].tolist()
        config = {
            "cliente": st.column_config.TextColumn("Cliente"),
            "contas": st.column_config.NumberColumn("Contas", format="%d"),
            "ordens": st.column_config.NumberColumn("O.S.", format="%d"),
            "divida": st.column_config.ButtonColumn(
                "Dívida",
                type="primary",
                alignment="right",
                help="Clique para ver as O.S. desta dívida",
                on_click=abrir_divida,
                key="cli_click_divida",
            ),
        }
        st.dataframe(
            pintar_faixa(grade, VERMELHO, {"divida"}),
            width="stretch",
            hide_index=True,
            height=480,
            column_config=config,
            alt="Clientes inadimplentes",
        )

    st.subheader("Adimplentes")
    st.caption("Clientes sem conta vencida em aberto. A coluna A vencer mostra saldo que ainda não venceu.")
    if adim.empty:
        st.info("Nenhum cliente adimplente com esses filtros.")
    else:
        grade = adim[["cliente", "a_vencer"]].copy()
        config = {
            "cliente": st.column_config.TextColumn("Cliente"),
            "a_vencer": st.column_config.NumberColumn("A vencer", format="R$ %.2f"),
        }
        st.dataframe(
            pintar_faixa(grade, AZUL),
            width="stretch",
            hide_index=True,
            height=480,
            column_config=config,
            alt="Clientes adimplentes",
        )
    if st.session_state.get("cli_cliente"):
        dialogo_dividas()


def aba_nfse() -> None:
    status = options("SELECT DISTINCT status_nf FROM oficina_nfse WHERE status_nf IS NOT NULL ORDER BY 1")
    f1, f2, f3 = st.columns([2, 1, 1])
    texto = f1.text_input(
        "Pesquisar",
        placeholder="Número, cliente, placa, OS, motivo ou observação",
        key="busca_nf",
    )
    escolhidos = f2.multiselect("Status", status, key="status_nf")
    limite = f3.slider("Máximo de linhas", 50, 2000, 500, 50, key="limite_nf")
    d1, d2 = st.columns(2)
    inicio = d1.date_input("Cadastro de", value=None, key="nf_de", format="DD/MM/YYYY")
    fim = d2.date_input("Cadastro até", value=None, key="nf_ate", format="DD/MM/YYYY")

    params: list = []
    where = " WHERE 1=1"
    where += text_clause(
        [
            "n.numero_nf",
            "n.id_nf",
            "n.nome_cliente",
            "v.nome_os",
            "v.placa",
            "n.ref_id",
            "n.ref_nf",
            "n.motivo_nf",
            "n.status_nf",
        ],
        texto,
        params,
        [obs_os_existe(texto, "n.ref_id", "lower(n.ref_nf) = 'os'")],
    )
    where += in_clause("n.status_nf", escolhidos, params)
    where += date_clause("substr(n.data_cadastro, 1, 10)", inicio, fim, params)
    cols = ", ".join(f"n.{coluna}" if coluna != "placa" else "v.placa" for coluna in NF_COLS)
    sql = f"""
        SELECT {cols}
        FROM oficina_nfse n
        LEFT JOIN (
            SELECT id_os, MAX(placa) AS placa, MAX(nome_cliente) AS nome_os
            FROM oficina_os
            GROUP BY id_os
        ) v ON lower(n.ref_nf) = 'os' AND v.id_os = n.ref_id
        {where}
        ORDER BY n.data_cadastro DESC, n.id DESC
        LIMIT ?
    """
    show_table(query(sql, tuple(params + [int(limite)])), "oficina_nfse")


def barra_rolagem_superior() -> None:
    st.html(
        """
<style>
.barra-superior { overflow-x: auto; overflow-y: hidden; height: 14px; margin: 0 0 4px; }
.barra-superior::-webkit-scrollbar { height: 12px; }
.barra-superior::-webkit-scrollbar-thumb { background: #0c6b4d; border-radius: 8px; }
.barra-superior::-webkit-scrollbar-track { background: #e5f0ea; }
</style>
<script>
(function () {
  if (window.__barraSuperior) window.__barraSuperior.disconnect();
  function candidato(el) {
    if (!el || el.classList.contains("barra-superior") || el.closest(".barra-superior")) return false;
    const estilo = getComputedStyle(el);
    const eixo = estilo.overflowX;
    return (eixo === "auto" || eixo === "scroll") && el.scrollWidth > el.clientWidth + 24 && el.clientWidth > 80;
  }
  function instalar() {
    const todos = [...document.querySelectorAll("div")].filter(candidato);
    todos.filter(el => !todos.some(outro => outro !== el && el.contains(outro))).forEach(el => {
      const existente = el.previousElementSibling;
      if (el.dataset.barraSuperior === "1" && existente && existente.classList.contains("barra-superior")) {
        existente.firstElementChild.style.width = el.scrollWidth + "px";
        return;
      }
      el.dataset.barraSuperior = "1";
      const barra = document.createElement("div");
      barra.className = "barra-superior";
      const interno = document.createElement("div");
      interno.style.height = "1px";
      interno.style.width = el.scrollWidth + "px";
      barra.appendChild(interno);
      el.parentElement.insertBefore(barra, el);
      let sincronizando = false;
      barra.addEventListener("scroll", () => {
        if (sincronizando) return;
        sincronizando = true;
        el.scrollLeft = barra.scrollLeft;
        sincronizando = false;
      });
      el.addEventListener("scroll", () => {
        if (sincronizando) return;
        sincronizando = true;
        barra.scrollLeft = el.scrollLeft;
        sincronizando = false;
      });
    });
  }
  instalar();
  setTimeout(instalar, 500);
  setTimeout(instalar, 1400);
  window.__barraSuperior = new MutationObserver(() => instalar());
  window.__barraSuperior.observe(document.body, {childList: true, subtree: true});
})();
</script>
        """,
        unsafe_allow_javascript=True,
    )


def main() -> None:
    st.set_page_config(page_title=TITULO, page_icon=":wrench:", layout="wide")
    st.title(TITULO)
    st.caption("Histórico no Supabase")
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        st.error(f"Não foi possível conectar ao Supabase. {exc}")
        st.stop()
    if "aba" not in st.session_state:
        st.session_state.aba = ABA_GERAL
    if "financeiro_aberto" not in st.session_state:
        st.session_state.financeiro_aberto = False
    st.session_state.setdefault("fin_termo", "")
    st.session_state.setdefault("fin_os_perguntar", None)
    st.session_state.setdefault("fin_os_aberta", None)
    st.session_state.setdefault("fin_origem", "abertas")
    st.session_state.setdefault("historico_aberto", False)
    st.session_state.setdefault("historico_termo", "")
    st.session_state.setdefault("cli_cliente", None)
    st.session_state.setdefault("cli_nome", None)
    st.session_state.setdefault("cli_os", None)
    st.session_state.setdefault("cli_os_aberta", None)

    with st.sidebar:
        st.header(TITULO)
        st.write("Histórico da Oficina Integrada. As baixas das contas em aberto são gravadas neste banco.")
        if st.button("Atualizar dados", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        periodo = query("SELECT MIN(data_entrada), MAX(data_entrada) FROM oficina_os")
        if not periodo.empty and periodo.iat[0, 0]:
            st.caption(f"Entradas de {periodo.iat[0, 0]} a {periodo.iat[0, 1]}")

    aba = st.segmented_control(
        "Seções",
        ABAS,
        key="aba",
        required=True,
        label_visibility="collapsed",
        width="stretch",
    )
    if aba == ABA_OS:
        aba_os()
    elif aba == ABA_FIN:
        aba_financeiro()
    elif aba == ABA_CLI:
        aba_clientes()
    elif aba == ABA_NF:
        aba_nfse()
    else:
        visao_geral()
    barra_rolagem_superior()


main()
