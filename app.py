import traceback
import streamlit as st

try:
    # --- O SEU CÓDIGO ORIGINAL COMEÇA AQUI ---
    import hashlib
    import html
    import json
    import secrets
    import unicodedata
    import uuid
    from datetime import date, datetime, timedelta
    from pathlib import Path
    from urllib.parse import urlsplit
    import pandas as pd
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    # (Pode colar o resto do seu código original logo abaixo disto)

except Exception as e:
    st.error("⚠️ ERRO CRÍTICO NO ARRANQUE DO APLICATIVO:")
    st.code(traceback.format_exc())
    st.stop()

TITULO = "Auto Peças & Mecânica Aliança"
CNPJ_NUMERO = "29027383000173"
ENDERECO_EMPRESA = "Rua Carajás, Qd. 54, Lt. 01, S/N, Centro"
TELEFONE_NUMERO = "6136122894"
MULTA_MORATORIA = 0.02
JUROS_MORA_MES = 0.01
LOGO = Path(__file__).resolve().parent / "logo_alianca.jpg"


def mostrar_logo(largura: int = 180) -> None:
    st.image(LOGO, width=largura, alt="Logo Auto Peças e Mecânica Aliança")


def estilo_login() -> None:
    st.html(
        """
        <style>
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stBottom"] {
          background: #021524;
        }
        [data-testid="stHeader"] { background: #021524; }
        [data-testid="stDecoration"] { display: none; }
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3 {
          color: #f7fbff;
          text-align: center;
        }
        [data-testid="stMain"] [data-testid="stCaptionContainer"],
        [data-testid="stMain"] [data-testid="stCaptionContainer"] p {
          color: #d5e4ee;
          text-align: center;
        }
        [data-testid="stMain"] [data-testid="stImage"] {
          display: flex;
          justify-content: center;
        }
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMain"] label {
          color: #f7fbff;
        }
        [data-testid="stMain"] input {
          background: #f4f8fb;
          color: #021524;
          border: 1px solid #7ad7f0;
          caret-color: #021524;
        }
        [data-testid="stMain"] [data-testid="stForm"] {
          border-color: #1d4d66;
        }
        </style>
        """
    )

ABA_GERAL = "Visão geral"
ABA_OS = "Ordens de Serviço"
ABA_FIN = "Financeiro"
ABA_CLI = "Clientes"
ABA_NF = "Notas Fiscais (NFS-e)"
ABA_USUARIOS = "Usuários"
ABA_LOG = "Log"
ABAS = [ABA_GERAL, ABA_OS, ABA_FIN, ABA_CLI, ABA_NF]
ABA_RECEBER = "Contas a receber"
ABA_PAGAR = "Contas a pagar"
CHAVES_MENU = {
    ABA_GERAL: "nav_visao",
    ABA_OS: "nav_os",
    ABA_FIN: "nav_financeiro",
    ABA_CLI: "nav_clientes",
    ABA_NF: "nav_notas",
    ABA_USUARIOS: "nav_usuarios",
    ABA_LOG: "nav_log",
    ABA_RECEBER: "nav_receber",
    ABA_PAGAR: "nav_pagar",
}

OS_RESUMO_COLS = [
    "id_os",
    "nome_cliente",
    "placa",
    "veiculo",
    "km",
    "data_entrada",
    "situacao",
]
OS_RESUMO_NOMES = {
    "id_os": "Número da O.S.",
    "nome_cliente": "Cliente",
    "placa": "Placa",
    "veiculo": "Veículo",
    "km": "Km",
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
    "importado_em",
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


_ACENTOS = "áàâãäåéèêëíìîïóòôõöúùûüýÿçñ"
_SEM_ACENTO = "aaaaaaeeeeiiiiooooouuuuyycn"


def sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFD", str(texto).casefold())
    sem_marca = "".join(caractere for caractere in base if unicodedata.category(caractere) != "Mn")
    return sem_marca.translate(str.maketrans(_ACENTOS, _SEM_ACENTO))


def like(text: str) -> str:
    escaped = sem_acento(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def comparar_busca(expressao: str) -> str:
    return (
        "translate(lower(COALESCE(CAST("
        + expressao
        + " AS TEXT), '')), '"
        + _ACENTOS
        + "', '"
        + _SEM_ACENTO
        + "') LIKE ? ESCAPE '\\'"
    )


def contem_termo(serie: pd.Series, termo: str) -> pd.Series:
    alvo = sem_acento(termo.strip())
    if not alvo:
        return pd.Series(False, index=serie.index)
    return serie.fillna("").astype(str).map(sem_acento).str.contains(alvo, regex=False)


def termos_busca(texto: str) -> list[str]:
    bruto = sem_acento(texto.strip())
    if not bruto:
        return []
    limpo = "".join(caractere for caractere in bruto if caractere.isalnum())
    termos = [bruto]
    if limpo and limpo != bruto:
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
    for campo in ("os", "nome"):
        for item in termos:
            partes.append(comparar_busca(campo))
            params.append(like(item))
    existe = []
    for campo in (
        "o.id_os",
        "o.nome_cliente",
        "o.placa",
        "o.placa_veiculo",
        "o.mecanico",
        "o.obs",
    ):
        for item in termos:
            existe.append(comparar_busca(campo))
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


def _supabase_url() -> str:
    if "SUPABASE_URL" in st.secrets:
        url = str(st.secrets["SUPABASE_URL"])
    else:
        url = str(st.secrets["supabase"]["url"])
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@st.cache_resource
def engine():
    try:
        eng = create_engine(_supabase_url(), pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as e:
        print(f"ERRO CRITICO SUPABASE: {e}")
        raise e


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
        partes.append(comparar_busca("o.obs"))
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
    termos = termos_busca(text)
    if not termos and not extras:
        return ""
    parts = []
    for item in termos:
        token = like(item)
        for column in columns:
            parts.append(comparar_busca(column))
            params.append(token)
    for sql, valores in extras:
        parts.append(sql)
        params.extend(valores)
    if not parts:
        return ""
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


def texto_lembrete_baixa() -> str:
    aviso = f"NENHUMA BAIXA NOS ÚLTIMOS {DIAS_EDICAO_BAIXA} DIAS."
    ultima = scalar(
        """
        SELECT MAX(substr(IFNULL(dt_pagamento, ''), 1, 10))
        FROM oficina_financeiro
        WHERE tipo = 'Receita'
          AND lower(IFNULL(quitado, '')) = 'sim'
          AND substr(IFNULL(dt_pagamento, ''), 1, 10) <> ''
        """
    )
    if not ultima:
        return aviso
    quando = pd.to_datetime(str(ultima)[:10], errors="coerce")
    if pd.isna(quando):
        return aviso
    dias = (date.today() - quando.date()).days
    if dias >= DIAS_EDICAO_BAIXA:
        return aviso
    if dias <= 0:
        return "Última baixa hoje."
    if dias == 1:
        return "Última baixa a 1 dia."
    return f"Última baixa a {dias} dias."


def mostrar_lembrete_baixa() -> None:
    texto = html.escape(texto_lembrete_baixa())
    st.markdown(
        "<p style='text-align:center;font-weight:700;font-size:1.05rem;margin:0.15rem 0 0.7rem'>"
        f"{texto}</p>",
        unsafe_allow_html=True,
    )


def visao_geral() -> None:
    mostrar_lembrete_baixa()
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
              <div style="font-size:0.95rem;color:#9a3412;font-weight:700;">Em aberto (receita)</div>
              <div style="font-size:2rem;line-height:1.15;color:#7c2d12;font-weight:800;margin-top:4px;">{brl(aberto)}</div>
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
               MAX(km) AS km,
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
    resumo["km"] = resumo["km"].map(texto_km)
    visivel = format_frame(resumo).rename(columns=OS_RESUMO_NOMES)
    visivel["Número da O.S."] = visivel["Número da O.S."].map(
        lambda valor: "" if numero_os(valor) is None else str(numero_os(valor))
    )
    st.caption(f"{inteiro(len(visivel))} O.S. nesta lista, uma linha por ordem")
    if visivel.empty:
        st.info("Nenhum registro encontrado com esses filtros.")
    else:
        st.caption("Clique no número da O.S. para abrir a ordem completa.")
        config = column_config(list(visivel.columns))
        config["Número da O.S."] = st.column_config.ButtonColumn(
            "Número da O.S.",
            type="primary",
            pinned=True,
            help="Clique para ver a OS completa",
            on_click=pedir_os,
            kwargs={"origem": "ordens", "chave": "os_click_lista"},
            key="os_click_lista",
        )
        st.dataframe(
            visivel,
            width="stretch",
            hide_index=True,
            height=560,
            column_config=config,
            alt="Lista de ordens de serviço",
        )
        st.download_button(
            "Baixar CSV deste resultado",
            data=visivel.to_csv(index=False).encode("utf-8-sig"),
            file_name="oficina_os.csv",
            mime="text/csv",
            key="download_oficina_os",
        )
    if resumo.empty:
        if st.session_state.get("fin_os_perguntar") and st.session_state.get("fin_origem") == "ordens":
            dialogo_os()
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
        titulo = (
            f"OS {int(registro.id_os)} · {cliente or 'Sem cliente'} · "
            f"{placa or 'sem placa'} · {registro.km}"
        )
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
            itens.insert(0, "Km", registro.km)
            st.dataframe(
                format_frame(itens),
                width="stretch",
                hide_index=True,
                column_config=column_config(list(itens.columns)),
                alt=f"Serviços da OS {int(registro.id_os)}",
            )
    if st.session_state.get("fin_os_perguntar") and st.session_state.get("fin_origem") == "ordens":
        dialogo_os()


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


def _resumo_log(valor: str, limite: int = 80) -> str:
    texto = valor.strip()
    if not texto:
        return "vazio"
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "…"


def _sim_nao(valor: str) -> str:
    return "Sim" if valor.casefold() == "sim" else "Não"


def _descricao_baixa(linha, antes, quitado: str, pagamento: str | None, pago: float, obs: str) -> str:
    os_num = texto_banco(getattr(linha, "os", "")) or "sem número"
    cliente = texto_banco(getattr(linha, "nome", "")) or "sem cliente"
    partes: list[str] = []
    antes_pago = valor_banco(antes["valor_pago"])
    if antes_pago != pago:
        partes.append(f"valor pago de {brl(antes_pago)} para {brl(pago)}")
    antes_quitado = texto_banco(antes["quitado"]) or "Nao"
    if antes_quitado.casefold() != quitado.casefold():
        partes.append(f"quitado de {_sim_nao(antes_quitado)} para {_sim_nao(quitado)}")
    antes_data = data_banco(antes["dt_pagamento"])
    if antes_data != pagamento:
        partes.append(
            f"data de pagamento de {data_br(antes_data) or 'vazia'} para {data_br(pagamento) or 'vazia'}"
        )
    antes_obs = texto_banco(antes["obs_conta"])
    if antes_obs != obs:
        partes.append(f"observação de {_resumo_log(antes_obs)} para {_resumo_log(obs)}")
    mudancas = "; ".join(partes) if partes else "dados da baixa"
    return f"OS {os_num}, {cliente}, conta {int(linha.id)}: {mudancas}."


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
            registrar_log(
                "Baixa",
                _descricao_baixa(linha, antes, quitado, pagamento, pago, obs),
                conn=conn,
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
    rotulo_voltar = (
        "Voltar à lista" if st.session_state.get("fin_origem") == "ordens" else "Voltar ao financeiro"
    )
    if st.button(rotulo_voltar, type="primary", key="voltar_fin_os"):
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
    for campo in ("nome_cliente", "placa", "placa_veiculo", "obs"):
        for item in termos:
            partes.append(comparar_busca(campo))
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


def documento_empresa(numero: str) -> str:
    digitos = "".join(caractere for caractere in numero if caractere.isdigit())
    if len(digitos) != 14:
        return numero
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def telefone_empresa(numero: str) -> str:
    digitos = "".join(caractere for caractere in numero if caractere.isdigit())
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    return numero


def _grupo_extenso(numero: int) -> str:
    unidades = (
        "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
        "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete",
        "dezoito", "dezenove",
    )
    dezenas = ("", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa")
    centenas = (
        "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
        "seiscentos", "setecentos", "oitocentos", "novecentos",
    )
    if numero == 100:
        return "cem"
    centena, resto = divmod(numero, 100)
    partes: list[str] = []
    if centena:
        partes.append(centenas[centena])
    if resto:
        if resto < 20:
            partes.append(unidades[resto])
        else:
            dezena, unidade = divmod(resto, 10)
            partes.append(dezenas[dezena] + (f" e {unidades[unidade]}" if unidade else ""))
    return " e ".join(partes)


def _inteiro_extenso(numero: int) -> str:
    if numero == 0:
        return "zero"
    escalas = ((10**9, "bilhão", "bilhões"), (10**6, "milhão", "milhões"), (10**3, "mil", "mil"))
    partes: list[str] = []
    resto = numero
    for tamanho, singular, plural in escalas:
        quantidade, resto = divmod(resto, tamanho)
        if not quantidade:
            continue
        if tamanho == 1000 and quantidade == 1:
            partes.append("mil")
        else:
            nome = singular if quantidade == 1 else plural
            partes.append(f"{_grupo_extenso(quantidade)} {nome}")
    if resto:
        partes.append(_grupo_extenso(resto))
    return " e ".join(partes)


def reais_por_extenso(valor: float) -> str:
    centavos_totais = int(round(abs(float(valor)) * 100))
    reais, centavos = divmod(centavos_totais, 100)

    def moeda(quantidade: int, singular: str, plural: str) -> str:
        if quantidade <= 0:
            return ""
        return f"{_inteiro_extenso(quantidade)} {singular if quantidade == 1 else plural}"

    texto_reais = moeda(reais, "real", "reais")
    texto_centavos = moeda(centavos, "centavo", "centavos")
    if texto_reais and texto_centavos:
        return f"{texto_reais} e {texto_centavos}"
    return texto_reais or texto_centavos or "zero real"


def encargos_legais(saldo: float, dias: int | None) -> tuple[float, float]:
    if saldo <= 0 or not dias or dias <= 0:
        return 0.0, 0.0
    multa = round(saldo * MULTA_MORATORIA, 2)
    juros = round(saldo * JUROS_MORA_MES * (dias / 30), 2)
    return juros, multa


def separar_obs_encargos(obs: str) -> tuple[str, float | None, float | None]:
    marca = "[[encargos "
    if marca not in obs:
        return obs.strip(), None, None
    limpo, _, resto = obs.partition(marca)
    miolo = resto.split("]]", 1)[0]
    juros = multa = None
    for parte in miolo.split():
        if "=" not in parte:
            continue
        chave, texto = parte.split("=", 1)
        try:
            numero = round(float(texto), 2)
        except ValueError:
            continue
        if chave == "juros":
            juros = numero
        elif chave == "multa":
            multa = numero
    return limpo.strip(), juros, multa


def obs_com_encargos(obs: str, juros: float, multa: float, gravar_marca: bool) -> str | None:
    limpo, _, _ = separar_obs_encargos(obs)
    if gravar_marca:
        limpo = f"{limpo}\n[[encargos juros={juros:.2f} multa={multa:.2f}]]".strip()
    return limpo or None


def garantir_encargos() -> bool:
    if "fin_tem_encargos" in st.session_state:
        return bool(st.session_state.fin_tem_encargos)
    try:
        with engine().begin() as conn:
            conn.execute(text("ALTER TABLE oficina_financeiro ADD COLUMN IF NOT EXISTS juros double precision"))
            conn.execute(text("ALTER TABLE oficina_financeiro ADD COLUMN IF NOT EXISTS multa double precision"))
        st.session_state.fin_tem_encargos = True
    except Exception:
        st.session_state.fin_tem_encargos = False
    return bool(st.session_state.fin_tem_encargos)


def buscar_conta(conta_id: int) -> pd.Series | None:
    extra = ", juros, multa" if garantir_encargos() else ""
    frame = query(
        f"""
        SELECT id, os, nome, quitado, vencimento, valor, valor_pago, dt_pagamento,
               obs_conta, forma_pagamento, parcela, descricao, desconto,
               data_lancamento, emissao, departamento, documento, conta, tipo
               {extra}
        FROM oficina_financeiro
        WHERE id = ?
        """,
        (int(conta_id),),
    )
    if frame.empty:
        return None
    return frame.iloc[0]


def _encargos_salvos(linha: pd.Series) -> tuple[float, float, bool]:
    if "juros" in linha.index and (pd.notna(linha["juros"]) or pd.notna(linha["multa"])):
        return valor_banco(linha["juros"]), valor_banco(linha["multa"]), True
    _, juros, multa = separar_obs_encargos(texto_banco(linha["obs_conta"]))
    if juros is None and multa is None:
        return 0.0, 0.0, False
    return valor_banco(juros), valor_banco(multa), True


def abrir_os_da_conta(numero: int, origem: str) -> None:
    st.session_state.fin_baixa_id = None
    st.session_state.fin_os_perguntar = int(numero)
    st.session_state.fin_os_aberta = None
    st.session_state.fin_origem = origem


def abrir_baixa(conta_id: int, reabrir: bool = False) -> None:
    st.session_state.fin_os_perguntar = None
    st.session_state.fin_os_aberta = None
    st.session_state.fin_baixa_id = int(conta_id)
    st.session_state.fin_baixa_reabrir = bool(reabrir)
    st.session_state.fin_baixa_init = None


def fechar_baixa() -> None:
    st.session_state.fin_baixa_id = None
    st.session_state.fin_baixa_reabrir = False


def _sync_data_pagamento(conta_id: int) -> None:
    pago = valor_banco(st.session_state.get(f"bx_pago_{conta_id}"))
    if pago > 0 and st.session_state.get(f"bx_data_{conta_id}") is None:
        st.session_state[f"bx_data_{conta_id}"] = date.today()


def _recalcular_encargos(conta_id: int, saldo: float, dias: int | None) -> None:
    juros, multa = encargos_legais(saldo, dias)
    st.session_state[f"bx_juros_{conta_id}"] = juros
    st.session_state[f"bx_multa_{conta_id}"] = multa


def valor_divida_exibida(valor, pago, juros=0, multa=0) -> float:
    principal = valor_banco(valor)
    recebido = valor_banco(pago)
    acrescimo = valor_banco(juros) + valor_banco(multa)
    if acrescimo > 0:
        return round(max(0.0, principal + acrescimo - recebido), 2)
    return round(max(0.0, principal - recebido), 2)


def gravar_conta_baixa(
    conta_id: int,
    *,
    pago: float,
    juros: float,
    multa: float,
    quando: date | None,
    obs: str,
    quitar: bool,
) -> None:
    tem_colunas = garantir_encargos()
    pagamento = None if quando is None else quando.isoformat()
    quitado = "Sim" if quitar else "Nao"
    obs_banco = obs_com_encargos(obs, juros, multa, gravar_marca=not tem_colunas)
    with engine().begin() as conn:
        colunas = "valor_pago, quitado, dt_pagamento, obs_conta, os, nome"
        if tem_colunas:
            colunas += ", juros, multa"
        antes = conn.execute(
            text(f"SELECT {colunas} FROM oficina_financeiro WHERE id = :id"),
            {"id": int(conta_id)},
        ).mappings().first()
        if antes is None:
            return
        campos = """
            quitado = :quitado,
            dt_pagamento = :pagamento,
            valor_pago = :pago,
            obs_conta = :obs
        """
        params = {
            "quitado": quitado,
            "pagamento": pagamento,
            "pago": round(pago, 2),
            "obs": obs_banco,
            "id": int(conta_id),
        }
        if tem_colunas:
            campos += ", juros = :juros, multa = :multa"
            params["juros"] = round(juros, 2)
            params["multa"] = round(multa, 2)
        conn.execute(
            text(f"UPDATE oficina_financeiro SET {campos} WHERE id = :id"),
            params,
        )
        os_num = texto_banco(antes["os"]) or "sem número"
        cliente = texto_banco(antes["nome"]) or "sem cliente"
        situacao = "quitada" if quitar else "parcial"
        registrar_log(
            "Baixa",
            (
                f"OS {os_num}, {cliente}, conta {int(conta_id)}: baixa {situacao}, "
                f"valor pago {brl(pago)}, juros {brl(juros)}, multa {brl(multa)}, "
                f"pagamento em {data_br(pagamento) or 'sem data'}."
            ),
            conn=conn,
        )


def _estilo_documento() -> str:
    return """
    body { font-family: Georgia, "Times New Roman", serif; color: #1c2430; margin: 28px; }
    header { border-bottom: 2px solid #145c45; padding-bottom: 12px; margin-bottom: 18px; }
    h1 { font-family: Arial, sans-serif; font-size: 20px; margin: 0; letter-spacing: 0.04em; }
    h2 { font-family: Arial, sans-serif; font-size: 16px; margin: 4px 0 0; color: #145c45; }
    .empresa { margin: 4px 0 0; font-family: Arial, sans-serif; font-size: 12px; color: #3d4a42; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    th, td { border: 1px solid #c5d7ce; padding: 7px 8px; font-size: 13px; text-align: left; vertical-align: top; }
    th { width: 34%; background: #f4fbf7; font-family: Arial, sans-serif; }
    .texto { font-size: 14px; line-height: 1.45; text-align: justify; }
    .carimbo { margin-top: 16px; font-family: Arial, sans-serif; font-weight: 700; color: #145c45; }
    .assinatura { margin-top: 56px; width: 280px; border-top: 1px solid #1c2430; padding-top: 6px;
                  font-family: Arial, sans-serif; font-size: 12px; }
    """


def _cabecalho_documento(titulo_doc: str) -> str:
    cnpj = html.escape(documento_empresa(CNPJ_NUMERO))
    endereco = html.escape(ENDERECO_EMPRESA)
    telefone = html.escape(telefone_empresa(TELEFONE_NUMERO))
    nome = html.escape(TITULO.upper())
    return f"""
    <header>
      <h1>{nome}</h1>
      <p class="empresa">CNPJ {cnpj}<br>{endereco}<br>Telefone {telefone}</p>
      <h2>{html.escape(titulo_doc)}</h2>
    </header>
    """


def _linha_doc(rotulo: str, valor: str) -> str:
    return f"<tr><th>{html.escape(rotulo)}</th><td>{html.escape(valor or '—')}</td></tr>"


def html_recibo(dados: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Recibo — {html.escape(TITULO)}</title>
<style>{_estilo_documento()}</style>
</head>
<body>
{_cabecalho_documento("RECIBO DE QUITAÇÃO")}
<p class="texto">
Recebemos de <strong>{html.escape(dados["cliente"])}</strong> a importância de
<strong>{html.escape(dados["valor_pago"])}</strong>
({html.escape(dados["extenso"])}),
referente a {html.escape(dados["descricao"])}, OS nº {html.escape(dados["os"])},
dando plena, rasa e irrevogável quitação do débito abaixo.
</p>
<table>
{_linha_doc("Recibo nº", dados["numero"])}
{_linha_doc("Cliente", dados["cliente"])}
{_linha_doc("Nº OS", dados["os"])}
{_linha_doc("Descrição", dados["descricao"])}
{_linha_doc("Parcela", dados["parcela"])}
{_linha_doc("Vencimento", dados["vencimento"])}
{_linha_doc("Valor da dívida", dados["divida"])}
{_linha_doc("Juros", dados["juros"])}
{_linha_doc("Multa", dados["multa"])}
{_linha_doc("Valor pago", dados["valor_pago"])}
{_linha_doc("Data do pagamento", dados["pagamento"])}
{_linha_doc("Obs", dados["obs"])}
</table>
<p class="carimbo">QUITADO</p>
<p class="texto">{html.escape(ENDERECO_EMPRESA)}, {html.escape(dados["pagamento"])}.</p>
<div class="assinatura">{html.escape(TITULO)}<br>CNPJ {html.escape(documento_empresa(CNPJ_NUMERO))}</div>
</body>
</html>"""


def html_promissoria(dados: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Nota promissória — {html.escape(TITULO)}</title>
<style>{_estilo_documento()}</style>
</head>
<body>
{_cabecalho_documento("NOTA PROMISSÓRIA")}
<table>
{_linha_doc("Nº", dados["numero"])}
{_linha_doc("Valor", dados["valor"])}
{_linha_doc("Vencimento", dados["vencimento"])}
{_linha_doc("Nº OS", dados["os"])}
{_linha_doc("Praça de pagamento", ENDERECO_EMPRESA)}
</table>
<p class="texto">
Pagarei até {html.escape(dados["vencimento"])}, por esta única via de nota promissória, a
<strong>{html.escape(TITULO.upper())}</strong>, CNPJ {html.escape(documento_empresa(CNPJ_NUMERO))},
ou à sua ordem, a quantia de <strong>{html.escape(dados["valor"])}</strong>
({html.escape(dados["extenso"])}), em moeda corrente nacional, referente a
{html.escape(dados["descricao"])}, OS nº {html.escape(dados["os"])}.
</p>
<p class="texto">Pagável em {html.escape(ENDERECO_EMPRESA)}.</p>
<table>
{_linha_doc("Emitente", dados["cliente"])}
{_linha_doc("CPF/CNPJ do emitente", "")}
{_linha_doc("Data de emissão", dados["emissao"])}
{_linha_doc("Obs", dados["obs"])}
</table>
<div class="assinatura">Assinatura do emitente<br>{html.escape(dados["cliente"])}</div>
</body>
</html>"""


def _dados_documento(linha: pd.Series, juros: float, multa: float, pago: float, quando: date | None, obs: str) -> dict:
    cliente = texto_limpo(linha["nome"]) or "Cliente não informado"
    numero_ordem = numero_os(linha["os"])
    vencimento = data_br(linha["vencimento"]) or "não informado"
    return {
        "numero": str(int(linha["id"])),
        "cliente": cliente,
        "os": str(numero_ordem) if numero_ordem is not None else "—",
        "descricao": texto_limpo(linha["descricao"]) or "Serviços e peças",
        "parcela": texto_limpo(linha["parcela"]) or "—",
        "vencimento": vencimento,
        "vencimento_extenso": f"No vencimento de {vencimento}" if data_br(linha["vencimento"]) else "À vista",
        "divida": brl(valor_banco(linha["valor"])),
        "juros": brl(juros),
        "multa": brl(multa),
        "valor": brl(round(valor_banco(linha["valor"]) + juros + multa, 2)),
        "valor_pago": brl(pago),
        "extenso": reais_por_extenso(pago if pago else valor_banco(linha["valor"]) + juros + multa),
        "pagamento": data_br(quando) or "—",
        "emissao": date.today().strftime("%d/%m/%Y"),
        "obs": obs.strip() or "—",
    }


def _ficha_conta(linha: pd.Series, dias: int | None) -> None:
    numero = numero_os(linha["os"])
    pares = [
        ("Cliente", texto_limpo(linha["nome"]) or "—"),
        ("Nº OS", str(numero) if numero is not None else "—"),
        ("Descrição", texto_limpo(linha["descricao"]) or "—"),
        ("Parcela", texto_limpo(linha["parcela"]) or "—"),
        ("Vencimento", data_br(linha["vencimento"]) or "—"),
        ("Dias vencidos", str(dias) if dias else "—"),
        ("Valor original", brl(linha["valor"])),
        ("Já pago", brl(linha["valor_pago"])),
        ("Forma de pagamento", texto_limpo(linha["forma_pagamento"]) or "—"),
        ("Documento", texto_limpo(linha["documento"]) or "—"),
        ("Departamento", texto_limpo(linha["departamento"]) or "—"),
        ("Conta", texto_limpo(linha["conta"]) or "—"),
        ("Emissão", data_br(linha["emissao"]) or "—"),
        ("Lançamento", data_br(linha["data_lancamento"]) or "—"),
        ("Desconto", brl(linha["desconto"])),
    ]
    linhas = "".join(_linha_doc(rotulo, valor) for rotulo, valor in pares)
    st.html(
        "<style>.ficha-baixa th,.ficha-baixa td{border:1px solid #d5e4ee;padding:6px 8px;font-size:14px;text-align:left}"
        ".ficha-baixa{width:100%;border-collapse:collapse}.ficha-baixa th{width:34%;background:#f4f8fb}</style>"
        f"<table class='ficha-baixa'>{linhas}</table>"
    )


def _preparar_form_baixa(conta_id: int, linha: pd.Series, reabrir: bool) -> None:
    if st.session_state.get("fin_baixa_init") == conta_id:
        return
    juros, multa, tem_salvo = _encargos_salvos(linha)
    dias = dias_em_atraso(linha["vencimento"], "Nao" if reabrir else linha["quitado"])
    saldo = round(max(0.0, valor_banco(linha["valor"]) - valor_banco(linha["valor_pago"])), 2)
    if not tem_salvo:
        juros, multa = encargos_legais(valor_banco(linha["valor"]) if reabrir else saldo, dias)
    obs, _, _ = separar_obs_encargos(texto_banco(linha["obs_conta"]))
    st.session_state[f"bx_juros_{conta_id}"] = float(juros)
    st.session_state[f"bx_multa_{conta_id}"] = float(multa)
    st.session_state[f"bx_obs_{conta_id}"] = obs
    st.session_state[f"bx_pago_{conta_id}"] = float(valor_banco(linha["valor_pago"]) if reabrir else 0.0)
    st.session_state[f"bx_data_{conta_id}"] = data_iso(linha["dt_pagamento"]) if reabrir else None
    st.session_state.fin_baixa_init = conta_id


def _totais_baixa(linha: pd.Series, conta_id: int, reabrir: bool) -> tuple[float, float, float, float]:
    juros = valor_banco(st.session_state.get(f"bx_juros_{conta_id}"))
    multa = valor_banco(st.session_state.get(f"bx_multa_{conta_id}"))
    pago_campo = valor_banco(st.session_state.get(f"bx_pago_{conta_id}"))
    ja_pago = valor_banco(linha["valor_pago"])
    pago_total = pago_campo if reabrir else round(ja_pago + pago_campo, 2)
    devido = round(valor_banco(linha["valor"]) + juros + multa, 2)
    return juros, multa, pago_total, devido


def _salvar_form_baixa(linha: pd.Series, conta_id: int, reabrir: bool, quitar: bool) -> None:
    juros, multa, pago_total, devido = _totais_baixa(linha, conta_id, reabrir)
    pago_campo = valor_banco(st.session_state.get(f"bx_pago_{conta_id}"))
    quando = data_iso(st.session_state.get(f"bx_data_{conta_id}"))
    if quitar and pago_total + 0.004 < devido:
        st.error("A baixa só é concluída quando o valor pago é igual ou maior que a dívida com juros e multa.")
        return
    if not quitar and pago_total + 0.004 >= devido:
        st.error("A baixa parcial fica para um valor menor que o total para quitação.")
        return
    if not quitar and not reabrir and pago_campo <= 0:
        st.error("Informe o valor pago nesta baixa parcial.")
        return
    if pago_total > 0 and quando is None:
        st.error("Informe a data do pagamento.")
        return
    obs = texto_banco(st.session_state.get(f"bx_obs_{conta_id}"))
    gravar_conta_baixa(
        conta_id,
        pago=pago_total,
        juros=juros,
        multa=multa,
        quando=quando,
        obs=obs,
        quitar=quitar,
    )
    st.session_state.baixa_aviso = 1
    st.session_state.baixa_aviso_texto = (
        "Baixa registrada. A conta foi quitada." if quitar else "Baixa parcial registrada. A conta continua em aberto."
    )
    fechar_baixa()
    st.cache_data.clear()
    st.rerun()


@st.dialog("Baixa da conta", width="large", on_dismiss=fechar_baixa)
def dialogo_baixa() -> None:
    conta_id = st.session_state.get("fin_baixa_id")
    if not conta_id:
        return
    linha = buscar_conta(int(conta_id))
    if linha is None:
        st.warning("Esta conta não está mais no financeiro.")
        return
    reabrir = bool(st.session_state.get("fin_baixa_reabrir"))
    _preparar_form_baixa(int(conta_id), linha, reabrir)
    if reabrir:
        st.subheader("Reabrir baixa")
    dias = dias_em_atraso(linha["vencimento"], "Nao")
    _ficha_conta(linha, dias)
    saldo = round(max(0.0, valor_banco(linha["valor"]) - valor_banco(linha["valor_pago"])), 2)
    base_legal = valor_banco(linha["valor"]) if reabrir else saldo
    juros_lei, multa_lei = encargos_legais(base_legal, dias)
    st.caption(
        "Multa de 2% sobre o saldo vencido, uma vez (Código de Defesa do Consumidor, art. 52, § 1º). "
        "Juros de mora de 1% ao mês, proporcionais aos dias (mês de 30 dias), teto usual da relação de consumo "
        "quando não há índice contratado. Os valores sugeridos podem ser alterados antes de salvar. "
        f"Sugestão para {dias or 0} dia(s): juros {brl(juros_lei)} e multa {brl(multa_lei)}."
    )
    j1, j2, j3 = st.columns([1, 1, 1], vertical_alignment="bottom")
    j1.number_input("Juros", min_value=0.0, step=0.01, format="%.2f", key=f"bx_juros_{conta_id}")
    j2.number_input("Multa", min_value=0.0, step=0.01, format="%.2f", key=f"bx_multa_{conta_id}")
    j3.button(
        "Recalcular pela lei",
        key=f"bx_recalc_{conta_id}",
        on_click=_recalcular_encargos,
        args=(int(conta_id), base_legal, dias),
        width="stretch",
    )
    rotulo_pago = "Valor pago" if reabrir else "Valor pago nesta baixa"
    p1, p2 = st.columns(2)
    p1.number_input(
        rotulo_pago,
        min_value=0.0,
        step=0.01,
        format="%.2f",
        key=f"bx_pago_{conta_id}",
        on_change=_sync_data_pagamento,
        args=(int(conta_id),),
    )
    p2.date_input(
        "Data do pagamento",
        format="DD/MM/YYYY",
        key=f"bx_data_{conta_id}",
    )
    st.text_area("Obs", key=f"bx_obs_{conta_id}", height=80)
    juros, multa, pago_total, devido = _totais_baixa(linha, int(conta_id), reabrir)
    restante = round(max(0.0, devido - pago_total), 2)
    r1, r2, r3 = st.columns(3)
    r1.metric("Total para quitação", brl(devido))
    r2.metric("Valor pago acumulado", brl(pago_total))
    r3.metric("Valor restante", brl(restante))
    pode_quitar = pago_total + 0.004 >= devido and pago_total > 0
    pode_parcial = pago_total + 0.004 < devido and (
        valor_banco(st.session_state.get(f"bx_pago_{conta_id}")) > 0 or reabrir
    )
    b1, b2 = st.columns(2)
    if b1.button("Salvar baixa", type="primary", width="stretch", key=f"bx_salvar_{conta_id}", disabled=not pode_quitar):
        _salvar_form_baixa(linha, int(conta_id), reabrir, True)
    if b2.button("Salvar baixa parcial", width="stretch", key=f"bx_parcial_{conta_id}", disabled=not pode_parcial):
        _salvar_form_baixa(linha, int(conta_id), reabrir, False)
    if not pode_quitar:
        st.caption("A baixa integral só fica disponível quando o valor pago é igual ou maior que o total para quitação.")
    quando = data_iso(st.session_state.get(f"bx_data_{conta_id}"))
    obs = texto_banco(st.session_state.get(f"bx_obs_{conta_id}"))
    dados = _dados_documento(linha, juros, multa, pago_total, quando, obs)
    dados_nota = dict(dados)
    valor_nota = restante if restante > 0 else devido
    dados_nota["valor"] = brl(valor_nota)
    dados_nota["extenso"] = reais_por_extenso(valor_nota)
    i1, i2 = st.columns(2)
    if i1.button("Imprimir recibo quitado", width="stretch", key=f"bx_recibo_{conta_id}", disabled=not pode_quitar):
        disparar_impressao(html_recibo(dados))
    if i2.button("Imprimir nota promissória", width="stretch", key=f"bx_nota_{conta_id}"):
        disparar_impressao(html_promissoria(dados_nota))


def _celula_dias(dias: int | None) -> None:
    if not dias:
        st.write("—")
        return
    st.html(
        f"<div style='font-size:18px;font-weight:700;line-height:1.2;color:#9a3412'>{int(dias)}</div>"
    )


def listar_contas_abertas(contas: pd.DataFrame) -> None:
    cab = st.columns([1.05, 3.3, 1.35, 1.25, 1.45, 1.15], vertical_alignment="center")
    for coluna, titulo in zip(cab, ("Nº OS", "Descrição", "Vencimento", "Dias vencidos", "Valor da dívida", ""), strict=True):
        if titulo:
            coluna.markdown(f"**{titulo}**")
    for registro in contas.itertuples(index=False):
        conta_id = int(registro.id)
        numero = numero_os(registro.os)
        dias = dias_em_atraso(registro.vencimento, registro.quitado)
        divida = valor_divida_exibida(registro.valor, registro.valor_pago, getattr(registro, "juros", 0), getattr(registro, "multa", 0))
        with st.container(border=True):
            cols = st.columns([1.05, 3.3, 1.35, 1.25, 1.45, 1.15], vertical_alignment="center")
            if numero is None:
                cols[0].write("—")
            else:
                cols[0].button(
                    str(numero),
                    key=f"os_abertas_{conta_id}",
                    on_click=abrir_os_da_conta,
                    args=(numero, "abertas"),
                )
            cols[1].write(texto_limpo(registro.descricao) or "—")
            cols[2].write(data_br(registro.vencimento) or "—")
            with cols[3]:
                _celula_dias(dias)
            cols[4].write(brl(divida))
            cols[5].button(
                "Baixar",
                type="primary",
                key=f"baixar_{conta_id}",
                on_click=abrir_baixa,
                args=(conta_id, False),
                width="stretch",
            )


def listar_baixas_recentes(contas: pd.DataFrame) -> None:
    cab = st.columns([1.05, 3.3, 1.45, 1.45, 1.35], vertical_alignment="center")
    for coluna, titulo in zip(cab, ("Nº OS", "Descrição", "Pagamento", "Valor pago", ""), strict=True):
        if titulo:
            coluna.markdown(f"**{titulo}**")
    for registro in contas.itertuples(index=False):
        conta_id = int(registro.id)
        numero = numero_os(registro.os)
        with st.container(border=True):
            cols = st.columns([1.05, 3.3, 1.45, 1.45, 1.35], vertical_alignment="center")
            if numero is None:
                cols[0].write("—")
            else:
                cols[0].button(
                    str(numero),
                    key=f"os_recentes_{conta_id}",
                    on_click=abrir_os_da_conta,
                    args=(numero, "recentes"),
                )
            cols[1].write(texto_limpo(registro.descricao) or "—")
            cols[2].write(data_br(registro.dt_pagamento) or "—")
            cols[3].write(brl(registro.valor_pago))
            cols[4].button(
                "Reabrir baixa",
                type="primary",
                key=f"reabrir_{conta_id}",
                on_click=abrir_baixa,
                args=(conta_id, True),
                width="stretch",
            )


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
    tem_encargos = garantir_encargos()
    cols_encargos = (
        ", COALESCE(juros, 0) AS juros, COALESCE(multa, 0) AS multa" if tem_encargos else ""
    )
    params_abertas: list = []
    filtro_aberto = clausula_pesquisa_oficina(termo, params_abertas)
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
    mostrar_lembrete_baixa()
    abertas = query(
        f"""
        SELECT id, os, nome, quitado, vencimento, valor, valor_pago,
               ROUND(COALESCE(valor, 0) - COALESCE(valor_pago, 0), 2) AS saldo,
               dt_pagamento, obs_conta, forma_pagamento, parcela, descricao
               {cols_encargos}
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
    aviso_texto = st.session_state.pop("baixa_aviso_texto", None)
    if aviso:
        st.success(aviso_texto or f"{inteiro(aviso)} conta(s) atualizada(s).")
    elif aviso == 0:
        st.info("Nenhuma alteração para salvar.")
    total_aberto = 0.0
    if not abertas.empty:
        total_aberto = round(
            sum(
                valor_divida_exibida(
                    registro.valor,
                    registro.valor_pago,
                    getattr(registro, "juros", 0),
                    getattr(registro, "multa", 0),
                )
                for registro in abertas.itertuples(index=False)
            ),
            2,
        )
    c1, c2 = st.columns(2)
    c1.metric("Contas pendentes", inteiro(len(abertas)))
    c2.metric("Total em aberto", brl(total_aberto))
    if abertas.empty:
        st.info("Nenhuma conta de receita em aberto.")
    else:
        st.caption(
            "A descrição fica na segunda coluna. Dias vencidos aparecem em negrito. "
            "Baixar abre a conta no centro da tela para o pagamento, juros, multa, obs e impressão."
        )
        listar_contas_abertas(abertas)

    ancora_fin("recentes")
    st.subheader("Baixas recentes")
    st.caption(
        f"Contas quitadas nos últimos {DIAS_EDICAO_BAIXA} dias. "
        "Reabrir baixa abre a mesma tela da conta para os ajustes."
    )
    if recentes.empty:
        mostrar_lembrete_baixa()
    else:
        r1, r2 = st.columns(2)
        r1.metric("Baixas no prazo", inteiro(len(recentes)))
        r2.metric("Valor dessas baixas", brl(recentes["valor_pago"].sum()))
        listar_baixas_recentes(recentes)

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
    if st.session_state.get("fin_baixa_id"):
        dialogo_baixa()
    elif st.session_state.get("fin_os_perguntar") and st.session_state.get("fin_origem") != "ordens":
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
    if not termo.strip() or base.empty:
        return None
    mask = contem_termo(base["cliente"], termo) | contem_termo(base["placa"], termo)
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


def _hash_senha(senha: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 120_000)
    return salt.hex(), digest.hex()


def _senha_confere(senha: str, salt_hex: str, hash_hex: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), 120_000)
    return secrets.compare_digest(digest.hex(), hash_hex)


def _erro_login(login: str) -> str | None:
    login = login.strip()
    if len(login) < 3:
        return "O login precisa ter pelo menos 3 caracteres."
    if any(caractere.isspace() for caractere in login):
        return "O login não pode conter espaços."
    return None


def _erro_senha(senha: str) -> str | None:
    if len(senha) < 6:
        return "A senha precisa ter pelo menos 6 caracteres."
    return None


def garantir_usuarios() -> None:
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS painel_usuario (
                    id bigserial PRIMARY KEY,
                    nome text NOT NULL,
                    login text NOT NULL,
                    senha_salt text NOT NULL,
                    senha_hash text NOT NULL,
                    administrador boolean NOT NULL DEFAULT false,
                    ativo boolean NOT NULL DEFAULT true,
                    criado_em timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS painel_usuario_login_lower
                ON painel_usuario (lower(login))
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE painel_usuario
                ADD COLUMN IF NOT EXISTS trocar_senha boolean NOT NULL DEFAULT false
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS painel_log (
                    id bigserial PRIMARY KEY,
                    quando timestamptz NOT NULL DEFAULT now(),
                    usuario_id bigint,
                    usuario_nome text,
                    usuario_login text,
                    acao text NOT NULL,
                    detalhe text NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS painel_log_quando
                ON painel_log (quando DESC)
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE painel_log
                ADD COLUMN IF NOT EXISTS origem text
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE painel_log
                ADD COLUMN IF NOT EXISTS modulo text
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS painel_presenca (
                    sessao text PRIMARY KEY,
                    usuario_id bigint NOT NULL,
                    visto_em timestamptz NOT NULL DEFAULT now(),
                    conectado boolean NOT NULL DEFAULT true
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS painel_presenca_usuario
                ON painel_presenca (usuario_id)
                """
            )
        )


def _host_local(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return True
    partes = host.split(".")
    if len(partes) == 4 and all(parte.isdigit() for parte in partes):
        primeiro, segundo = int(partes[0]), int(partes[1])
        if primeiro == 10 or (primeiro == 192 and segundo == 168):
            return True
        if primeiro == 172 and 16 <= segundo <= 31:
            return True
    return False


MODULO_OS = "OS - Oficina Integrada"
MODULO_PV = "PV - Next"
ROTULOS_MODULO = {"os": MODULO_OS, "pv": MODULO_PV}


def origem_acesso() -> str:
    url = st.context.url or ""
    host = (urlsplit(url).hostname or "").lower() if url else ""
    if not host:
        bruto = ""
        try:
            bruto = st.context.headers.get("host") or ""
        except Exception:
            bruto = ""
        host = bruto.split(":")[0].strip().lower()
    if _host_local(host):
        return "Local"
    if not host:
        return "Não informado"
    return "Público"


def texto_link_acesso() -> str:
    origem = origem_acesso()
    if origem == "Local":
        return "pelo link local"
    if origem == "Público":
        return "pelo link público"
    return "por um link não identificado"


def registrar_log(
    acao: str,
    detalhe: str,
    *,
    usuario: dict | None = None,
    login_informado: str | None = None,
    modulo: str | None = None,
    conn=None,
) -> None:
    if usuario is None and login_informado is None:
        usuario = st.session_state.get("usuario")
    usuario = usuario or {}
    usuario_id = usuario.get("id")
    params = {
        "usuario_id": int(usuario_id) if usuario_id is not None else None,
        "usuario_nome": (usuario.get("nome") or login_informado or "").strip() or None,
        "usuario_login": (usuario.get("login") or login_informado or "").strip() or None,
        "acao": acao,
        "detalhe": detalhe,
        "origem": origem_acesso(),
        "modulo": modulo if modulo is not None else ROTULOS_MODULO.get(st.session_state.get("modulo") or ""),
    }
    sql = text(
        """
        INSERT INTO painel_log
            (usuario_id, usuario_nome, usuario_login, acao, detalhe, origem, modulo)
        VALUES
            (:usuario_id, :usuario_nome, :usuario_login, :acao, :detalhe, :origem, :modulo)
        """
    )
    if conn is not None:
        conn.execute(sql, params)
        return
    with engine().begin() as proprio:
        proprio.execute(sql, params)


def listar_log(limite: int = 400) -> pd.DataFrame:
    colunas = ["quando", "usuario", "login", "acao", "modulo", "origem", "detalhe"]
    with engine().connect() as conn:
        linhas = conn.execute(
            text(
                """
                SELECT quando AT TIME ZONE 'America/Sao_Paulo' AS quando,
                       COALESCE(usuario_nome, '') AS usuario,
                       COALESCE(usuario_login, '') AS login,
                       acao,
                       COALESCE(NULLIF(modulo, ''), '—') AS modulo,
                       COALESCE(NULLIF(origem, ''), 'Não informado') AS origem,
                       detalhe
                FROM painel_log
                ORDER BY id DESC
                LIMIT :limite
                """
            ),
            {"limite": int(limite)},
        ).mappings().all()
    frame = pd.DataFrame(linhas, columns=colunas)
    if not frame.empty:
        frame["quando"] = pd.to_datetime(frame["quando"])
    return frame


SEGUNDOS_ONLINE = 120


def id_sessao() -> str:
    sessao = st.session_state.get("sessao_id")
    if not sessao:
        sessao = uuid.uuid4().hex
        st.session_state.sessao_id = sessao
    return str(sessao)


def marcar_presenca(usuario_id: int) -> None:
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO painel_presenca (sessao, usuario_id, visto_em, conectado)
                VALUES (:sessao, :usuario_id, now(), true)
                ON CONFLICT (sessao) DO UPDATE
                SET usuario_id = EXCLUDED.usuario_id,
                    visto_em = now(),
                    conectado = true
                """
            ),
            {"sessao": id_sessao(), "usuario_id": int(usuario_id)},
        )


def desconectar_sessao() -> None:
    sessao = st.session_state.get("sessao_id")
    if not sessao:
        return
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE painel_presenca
                SET conectado = false,
                    visto_em = now()
                WHERE sessao = :sessao
                """
            ),
            {"sessao": sessao},
        )


def listar_presenca() -> pd.DataFrame:
    colunas = ["usuario", "login", "situacao", "ultimo_acesso"]
    with engine().connect() as conn:
        linhas = conn.execute(
            text(
                """
                SELECT u.nome AS usuario,
                       u.login,
                       CASE
                           WHEN NOT u.ativo THEN 'Inativo'
                           WHEN COALESCE(p.online, false) THEN 'Conectado'
                           ELSE 'Desconectado'
                       END AS situacao,
                       p.ultimo_acesso
                FROM painel_usuario u
                LEFT JOIN LATERAL (
                    SELECT bool_or(
                               conectado
                               AND visto_em > now() - make_interval(secs => :segundos)
                           ) AS online,
                           MAX(visto_em) AT TIME ZONE 'America/Sao_Paulo' AS ultimo_acesso
                    FROM painel_presenca
                    WHERE usuario_id = u.id
                ) p ON true
                ORDER BY
                    CASE
                        WHEN NOT u.ativo THEN 2
                        WHEN COALESCE(p.online, false) THEN 0
                        ELSE 1
                    END,
                    u.nome,
                    u.login
                """
            ),
            {"segundos": SEGUNDOS_ONLINE},
        ).mappings().all()
    frame = pd.DataFrame(linhas, columns=colunas)
    if not frame.empty:
        frame["ultimo_acesso"] = pd.to_datetime(frame["ultimo_acesso"])
    return frame


@st.fragment(run_every="45s")
def pulso_presenca() -> None:
    usuario = st.session_state.get("usuario")
    if not usuario or not usuario.get("id"):
        return
    agora = datetime.now().timestamp()
    if st.session_state.get("pulso_em", 0) + 25 > agora:
        return
    try:
        marcar_presenca(int(usuario["id"]))
    except Exception:
        return
    st.session_state.pulso_em = agora


@st.fragment(run_every="30s")
def mostrar_presenca() -> None:
    quadro = listar_presenca()
    st.subheader("Conexões")
    if quadro.empty:
        st.info("Nenhum usuário cadastrado.")
        return
    conectados = int((quadro["situacao"] == "Conectado").sum())
    st.caption(
        f"{inteiro(conectados)} conectado(s). "
        "A pessoa fica conectada com o painel aberto e desconectada ao sair, "
        "ou cerca de 2 minutos depois de fechar a tela."
    )
    tabela = quadro.rename(
        columns={
            "usuario": "Usuário",
            "login": "Login",
            "situacao": "Situação",
            "ultimo_acesso": "Último acesso",
        }
    )
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Último acesso": st.column_config.DatetimeColumn(
                "Último acesso",
                format="DD/MM/YYYY HH:mm",
            ),
        },
        alt="Usuários conectados e último acesso",
    )


def encerrar_sessao() -> None:
    usuario = st.session_state.get("usuario")
    if usuario:
        registrar_log("Saída", f"Saiu do painel {texto_link_acesso()}.", usuario=usuario)
    desconectar_sessao()
    st.session_state.pop("usuario", None)
    st.session_state.pop("modulo", None)
    st.rerun()


def contar_usuarios() -> int:
    with engine().connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM painel_usuario")).scalar()
    return int(total or 0)


def autenticar(login: str, senha: str) -> tuple[dict | None, str | None]:
    with engine().connect() as conn:
        linha = conn.execute(
            text(
                """
                SELECT id, nome, login, senha_salt, senha_hash, administrador, ativo, trocar_senha
                FROM painel_usuario
                WHERE lower(login) = lower(:login)
                """
            ),
            {"login": login.strip()},
        ).mappings().first()
    if linha is None or not _senha_confere(senha, linha["senha_salt"], linha["senha_hash"]):
        return None, "Login ou senha incorretos."
    if not linha["ativo"]:
        return None, "Este usuário está desativado."
    return {
        "id": int(linha["id"]),
        "nome": linha["nome"],
        "login": linha["login"],
        "administrador": bool(linha["administrador"]),
        "trocar_senha": bool(linha["trocar_senha"]),
    }, None


def usuario_sessao(usuario_id: int) -> dict | None:
    with engine().connect() as conn:
        linha = conn.execute(
            text(
                """
                SELECT id, nome, login, administrador, ativo, trocar_senha
                FROM painel_usuario
                WHERE id = :id
                """
            ),
            {"id": usuario_id},
        ).mappings().first()
    if linha is None or not linha["ativo"]:
        return None
    return {
        "id": int(linha["id"]),
        "nome": linha["nome"],
        "login": linha["login"],
        "administrador": bool(linha["administrador"]),
        "trocar_senha": bool(linha["trocar_senha"]),
    }


def criar_usuario(
    nome: str,
    login: str,
    senha: str,
    administrador: bool,
    exigir_troca: bool = True,
) -> str | None:
    nome = nome.strip()
    login = login.strip()
    if not nome:
        return "Informe o nome."
    erro = _erro_login(login) or _erro_senha(senha)
    if erro:
        return erro
    salt, digest = _hash_senha(senha)
    try:
        with engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO painel_usuario
                        (nome, login, senha_salt, senha_hash, administrador, trocar_senha)
                    VALUES
                        (:nome, :login, :salt, :digest, :administrador, :trocar_senha)
                    """
                ),
                {
                    "nome": nome,
                    "login": login,
                    "salt": salt,
                    "digest": digest,
                    "administrador": administrador,
                    "trocar_senha": exigir_troca,
                },
            )
    except IntegrityError:
        return "Já existe um usuário com esse login."
    return None


def listar_usuarios() -> pd.DataFrame:
    with engine().connect() as conn:
        linhas = conn.execute(
            text(
                """
                SELECT id, nome, login, administrador, ativo, trocar_senha
                FROM painel_usuario
                ORDER BY nome, login
                """
            )
        ).mappings().all()
    return pd.DataFrame(
        linhas,
        columns=["id", "nome", "login", "administrador", "ativo", "trocar_senha"],
    )


def admins_ativos(exceto_id: int | None = None) -> int:
    sql = "SELECT COUNT(*) FROM painel_usuario WHERE administrador AND ativo"
    params: dict = {}
    if exceto_id is not None:
        sql += " AND id <> :id"
        params["id"] = exceto_id
    with engine().connect() as conn:
        total = conn.execute(text(sql), params).scalar()
    return int(total or 0)


def definir_ativo(usuario_id: int, ativo: bool) -> str | None:
    if not ativo and admins_ativos(exceto_id=usuario_id) == 0:
        return "É preciso manter pelo menos um administrador ativo."
    with engine().begin() as conn:
        conn.execute(
            text("UPDATE painel_usuario SET ativo = :ativo WHERE id = :id"),
            {"ativo": ativo, "id": usuario_id},
        )
    return None


def definir_senha(usuario_id: int, senha: str, exigir_troca: bool) -> str | None:
    erro = _erro_senha(senha)
    if erro:
        return erro
    salt, digest = _hash_senha(senha)
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE painel_usuario
                SET senha_salt = :salt, senha_hash = :digest, trocar_senha = :trocar_senha
                WHERE id = :id
                """
            ),
            {"salt": salt, "digest": digest, "trocar_senha": exigir_troca, "id": usuario_id},
        )
    return None


def senha_confere_id(usuario_id: int, senha: str) -> bool:
    with engine().connect() as conn:
        linha = conn.execute(
            text("SELECT senha_salt, senha_hash FROM painel_usuario WHERE id = :id"),
            {"id": usuario_id},
        ).mappings().first()
    if linha is None:
        return False
    return _senha_confere(senha, linha["senha_salt"], linha["senha_hash"])


def tela_acesso() -> None:
    estilo_login()
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        with st.container(horizontal_alignment="center", key="logo_acesso"):
            mostrar_logo(220)
        st.title(TITULO)
        if contar_usuarios() == 0:
            st.subheader("Criar o administrador")
            st.caption("Esta conta cadastra as outras pessoas do painel.")
            with st.form("primeiro_admin"):
                nome = st.text_input("Nome")
                login = st.text_input("Login")
                senha = st.text_input("Senha", type="password")
                confirma = st.text_input("Confirmar senha", type="password")
                criar = st.form_submit_button("Criar administrador", type="primary", width="stretch")
            if criar:
                if senha != confirma:
                    st.error("As senhas não são iguais.")
                    return
                erro = criar_usuario(nome, login, senha, True, exigir_troca=False)
                if erro:
                    st.error(erro)
                    return
                usuario, erro_login = autenticar(login, senha)
                if usuario is None:
                    st.error(erro_login or "Não foi possível entrar com a conta criada.")
                    return
                registrar_log(
                    "Cadastro de usuário",
                    "Criou a primeira conta de administrador.",
                    usuario=usuario,
                )
                registrar_log("Acesso", f"Entrou no painel {texto_link_acesso()}.", usuario=usuario)
                st.session_state.usuario = usuario
                st.rerun()
            return
        st.subheader("Entrar")
        with st.form("login"):
            login = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if entrar:
            usuario, erro = autenticar(login, senha)
            if erro or usuario is None:
                motivo = erro or "Login ou senha incorretos."
                registrar_log(
                    "Acesso",
                    f"Tentativa de acesso recusada {texto_link_acesso()}: {motivo}",
                    login_informado=login.strip(),
                )
                st.error(motivo)
                return
            registrar_log("Acesso", f"Entrou no painel {texto_link_acesso()}.", usuario=usuario)
            st.session_state.usuario = usuario
            st.rerun()


def tela_trocar_senha() -> None:
    estilo_login()
    usuario = st.session_state.usuario
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        with st.container(horizontal_alignment="center", key="logo_troca"):
            mostrar_logo(220)
        st.title(TITULO)
        st.subheader("Troque sua senha")
        st.caption("A senha recebida serve só para entrar a primeira vez.")
        with st.form("troca_obrigatoria"):
            atual = st.text_input("Senha atual", type="password")
            nova = st.text_input("Nova senha", type="password")
            confirma = st.text_input("Confirmar nova senha", type="password")
            salvar = st.form_submit_button("Salvar nova senha", type="primary", width="stretch")
        if st.button("Sair", key="sair_troca", width="stretch"):
            encerrar_sessao()
        if not salvar:
            return
        if not senha_confere_id(int(usuario["id"]), atual):
            st.error("A senha atual está incorreta.")
            return
        if nova != confirma:
            st.error("As senhas novas não são iguais.")
            return
        if nova == atual:
            st.error("Escolha uma senha diferente da que você recebeu.")
            return
        erro = definir_senha(int(usuario["id"]), nova, exigir_troca=False)
        if erro:
            st.error(erro)
            return
        registrar_log(
            "Senha",
            "Trocou a senha temporária do primeiro acesso.",
            usuario=usuario,
        )
        st.session_state.usuario = usuario_sessao(int(usuario["id"]))
        st.rerun()


def aba_usuarios() -> None:
    if not st.session_state.usuario["administrador"]:
        st.session_state.aba = ABA_GERAL
        st.rerun()
    st.subheader("Usuários")
    with st.container(border=True):
        st.markdown("Novo usuário")
        st.caption("A senha cadastrada vale só para o primeiro acesso. A pessoa terá que trocá-la ao entrar.")
        with st.form("novo_usuario", clear_on_submit=True):
            nome = st.text_input("Nome", key="novo_nome")
            login = st.text_input("Login", key="novo_login")
            senha = st.text_input("Senha", type="password", key="novo_senha")
            administrador = st.checkbox("Administrador", key="novo_admin")
            cadastrar = st.form_submit_button("Cadastrar", type="primary")
        if cadastrar:
            erro = criar_usuario(nome, login, senha, administrador)
            if erro:
                st.error(erro)
            else:
                papel = "administrador" if administrador else "usuário"
                registrar_log(
                    "Cadastro de usuário",
                    f"Cadastrou {nome.strip()} (login {login.strip()}) como {papel}.",
                )
                st.success(f"{nome.strip()} foi cadastrado.")
    lista = listar_usuarios()
    visivel = lista.drop(columns=["id"]).rename(
        columns={
            "nome": "Nome",
            "login": "Login",
            "administrador": "Administrador",
            "ativo": "Ativo",
            "trocar_senha": "Troca pendente",
        }
    )
    st.dataframe(visivel, hide_index=True, width="stretch", alt="Usuários cadastrados no painel")
    escolhido = st.selectbox(
        "Alterar usuário",
        lista["id"].tolist(),
        format_func=lambda usuario_id: lista.loc[lista["id"] == usuario_id, "nome"].iloc[0]
        + " ("
        + lista.loc[lista["id"] == usuario_id, "login"].iloc[0]
        + ")",
    )
    linha = lista.loc[lista["id"] == escolhido].iloc[0]
    eu = int(st.session_state.usuario["id"])
    if int(linha["id"]) == eu:
        st.caption("Esta é a sua conta.")
    else:
        rotulo = "Desativar" if bool(linha["ativo"]) else "Reativar"
        if st.button(rotulo, key="alternar_usuario"):
            erro = definir_ativo(int(linha["id"]), not bool(linha["ativo"]))
            if erro:
                st.error(erro)
            else:
                verbo = "Reativou" if not bool(linha["ativo"]) else "Desativou"
                registrar_log(
                    "Usuário",
                    f"{verbo} {linha['nome']} (login {linha['login']}).",
                )
                st.rerun()
    with st.form(f"trocar_senha_{int(linha['id'])}"):
        st.caption("Se a pessoa esqueceu a senha, defina outra. No próximo acesso ela terá que trocá-la.")
        nova = st.text_input("Nova senha", type="password")
        salvar = st.form_submit_button("Redefinir senha")
    if salvar:
        propria = int(linha["id"]) == eu
        erro = definir_senha(int(linha["id"]), nova, exigir_troca=not propria)
        if erro:
            st.error(erro)
        elif propria:
            registrar_log("Senha", "Trocou a própria senha.")
            st.session_state.usuario = usuario_sessao(eu)
            st.success("Senha atualizada.")
        else:
            registrar_log(
                "Senha",
                f"Redefiniu a senha de {linha['nome']} (login {linha['login']}). "
                "A troca ficou pendente para o próximo acesso.",
            )
            st.success("Senha redefinida. No próximo acesso a pessoa precisará trocá-la.")


def aba_log() -> None:
    if not st.session_state.usuario["administrador"]:
        st.session_state.aba = ABA_GERAL
        st.rerun()
    st.subheader("Log")
    mostrar_presenca()
    st.caption(
        "Acessos e alterações do painel, do mais recente para o mais antigo. "
        "O registro começa a partir de agora."
    )
    registros = listar_log()
    if registros.empty:
        st.info("Nenhum acesso ou alteração registrado ainda.")
        return
    acoes = sorted(registros["acao"].dropna().unique().tolist())
    busca, filtro = st.columns([2, 1])
    texto = busca.text_input(
        "Pesquisar",
        placeholder="Usuário, login ou alteração",
        key="busca_log",
    )
    escolhidas = filtro.multiselect("Ação", acoes, key="acao_log")
    visivel = registros
    if escolhidas:
        visivel = visivel[visivel["acao"].isin(escolhidas)]
    termo = texto.strip()
    if termo:
        mascara = pd.Series(False, index=visivel.index)
        for coluna in ("usuario", "login", "acao", "modulo", "origem", "detalhe"):
            mascara = mascara | contem_termo(visivel[coluna], termo)
        visivel = visivel[mascara]
    if visivel.empty:
        st.info("Nenhum registro com esse filtro.")
        return
    st.caption(f"{inteiro(len(visivel))} registro(s).")
    tabela = visivel.rename(
        columns={
            "quando": "Quando",
            "usuario": "Usuário",
            "login": "Login",
            "acao": "Ação",
            "modulo": "Módulo",
            "origem": "Origem",
            "detalhe": "Detalhe",
        }
    )
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Quando": st.column_config.DatetimeColumn("Quando", format="DD/MM/YYYY HH:mm"),
            "Detalhe": st.column_config.TextColumn("Detalhe", width="large"),
        },
        alt="Acessos e alterações do painel",
    )


def esconder_gerenciar() -> None:
    st.html(
        """
        <style>
        [data-testid="stToolbar"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"] { display: none !important; }
        </style>
        <script>
        (function () {
          if (window.__esconderGerenciar) window.__esconderGerenciar.disconnect();
          const texto = /^\\s*[<‹]?\\s*(gerenciar aplicativo|manage app)\\s*$/i;
          function documentos() {
            const lista = [document];
            try {
              if (window.parent && window.parent.document && window.parent.document !== document) {
                lista.push(window.parent.document);
              }
            } catch (erro) {}
            return lista;
          }
          function esconder() {
            documentos().forEach((doc) => {
              doc.querySelectorAll("button, a, div, span").forEach((el) => {
                const conteudo = (el.innerText || "").trim();
                if (!texto.test(conteudo)) return;
                const alvo = el.closest("button, a") || el;
                alvo.style.setProperty("display", "none", "important");
                if (alvo.parentElement && (alvo.parentElement.innerText || "").trim().length < 40) {
                  alvo.parentElement.style.setProperty("display", "none", "important");
                }
              });
            });
          }
          esconder();
          setTimeout(esconder, 400);
          setTimeout(esconder, 1500);
          window.__esconderGerenciar = new MutationObserver(esconder);
          window.__esconderGerenciar.observe(document.body, {childList: true, subtree: true, characterData: true});
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def tela_modulos() -> None:
    st.html(
        """
        <style>
        .st-key-capa_loja h1 {
          text-align: center;
          color: #0c6b4d;
          font-weight: 700;
        }
        .st-key-menu_modulos,
        .st-key-menu_modulos [data-testid="stHorizontalBlock"] {
          width: 100%;
          justify-content: center !important;
        }
        .st-key-menu_modulos button {
          background-color: #0c6b4d !important;
          color: #f4fbf7 !important;
          border: 1px solid #084a36 !important;
          border-radius: 999px !important;
          box-shadow: 0 8px 18px rgba(12, 107, 77, 0.34) !important;
          font-weight: 700 !important;
          min-width: 16rem;
          height: auto !important;
          line-height: 1.25;
          text-align: center !important;
          padding: 0.75rem 1.4rem !important;
        }
        .st-key-menu_modulos button p {
          width: 100%;
          margin: 0;
          text-align: center !important;
        }
        .st-key-menu_modulos button:hover {
          background-color: #14845f !important;
        }
        </style>
        <script>
        (function () {
          const raiz = document.documentElement;
          raiz.lang = "pt-BR";
          raiz.setAttribute("translate", "no");
          const travar = () => {
            document.querySelectorAll("button, h1, p, label").forEach((el) => {
              el.setAttribute("translate", "no");
            });
          };
          travar();
          if (window.__travarTexto) window.__travarTexto.disconnect();
          window.__travarTexto = new MutationObserver(travar);
          window.__travarTexto.observe(document.body, {childList: true, subtree: true});
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
    with st.container(key="capa_loja", horizontal_alignment="center"):
        mostrar_logo(200)
        st.title(TITULO)
    with st.container(
        key="menu_modulos",
        horizontal=True,
        horizontal_alignment="center",
        gap="medium",
    ):
        if st.button(f"{MODULO_OS}  \nSERVIÇOS", key="mod_os", type="primary", wrap=True):
            st.session_state.modulo = "os"
            registrar_log("Acesso", f"Acessou o módulo {MODULO_OS}.")
            st.rerun()
        if st.button(f"{MODULO_PV}  \nPEÇAS", key="mod_pv", type="primary", wrap=True):
            st.session_state.modulo = "pv"
            registrar_log("Acesso", f"Acessou o módulo {MODULO_PV}.", modulo=MODULO_PV)
            st.rerun()
    if st.button("Sair", key="sair_modulos"):
        encerrar_sessao()


PASTA_PLANILHAS_NEXT = Path(
    r"C:\Users\apema\OneDrive\Aliança\Documentos\OFICINA INTEGRADA\NEXT - planilhas"
)
_XML_PLANILHA = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _celula_planilha(referencia: str) -> tuple[int, int]:
    coluna = ""
    linha = ""
    for caractere in referencia:
        if caractere.isalpha():
            coluna += caractere
        else:
            linha += caractere
    numero = 0
    for caractere in coluna:
        numero = numero * 26 + ord(caractere.upper()) - 64
    return numero, int(linha or 0)


def ler_primeira_aba(conteudo: bytes) -> list[list[str]]:
    import xml.etree.ElementTree as ET
    from io import BytesIO
    from zipfile import ZipFile

    with ZipFile(BytesIO(conteudo)) as arquivo:
        compartilhadas: list[str] = []
        if "xl/sharedStrings.xml" in arquivo.namelist():
            raiz = ET.fromstring(arquivo.read("xl/sharedStrings.xml"))
            for item in raiz.findall(f"{_XML_PLANILHA}si"):
                compartilhadas.append(
                    "".join(texto.text or "" for texto in item.iter(f"{_XML_PLANILHA}t"))
                )
        relacoes = ET.fromstring(arquivo.read("xl/_rels/workbook.xml.rels"))
        destino = {
            relacao.attrib["Id"]: relacao.attrib["Target"]
            for relacao in relacoes
        }
        livro = ET.fromstring(arquivo.read("xl/workbook.xml"))
        folha = livro.find(f"{_XML_PLANILHA}sheets/{_XML_PLANILHA}sheet")
        if folha is None:
            return []
        alvo = destino[folha.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
        if not alvo.startswith("xl/"):
            alvo = "xl/" + alvo.lstrip("/")
        raiz = ET.fromstring(arquivo.read(alvo))
    grade: dict[int, dict[int, str]] = {}
    for celula in raiz.iter(f"{_XML_PLANILHA}c"):
        coluna, linha = _celula_planilha(celula.attrib.get("r", ""))
        if linha <= 0:
            continue
        tipo = celula.attrib.get("t")
        valor = celula.find(f"{_XML_PLANILHA}v")
        if tipo == "s" and valor is not None and valor.text:
            texto = compartilhadas[int(valor.text)]
        elif tipo == "inlineStr":
            texto = "".join(item.text or "" for item in celula.iter(f"{_XML_PLANILHA}t"))
        else:
            texto = valor.text if valor is not None and valor.text else ""
        grade.setdefault(linha, {})[coluna] = texto
    linhas: list[list[str]] = []
    for indice in range(1, max(grade, default=0) + 1):
        colunas = grade.get(indice, {})
        if not colunas:
            linhas.append([])
            continue
        ultima = max(colunas)
        linhas.append([colunas.get(numero, "") for numero in range(1, ultima + 1)])
    return linhas


def _numero_planilha(valor: str) -> float:
    texto = (valor or "").strip()
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return round(float(texto), 2)


def _data_planilha(valor: str) -> date | None:
    texto = (valor or "").strip()
    if not texto:
        return None
    try:
        serial = float(texto)
    except ValueError:
        return data_iso(texto)
    if serial < 20000 or serial > 80000:
        return None
    return date(1899, 12, 30) + timedelta(days=int(serial))


def tipo_planilha_next(linhas: list[list[str]], nome_arquivo: str = "") -> str | None:
    texto = " ".join(" ".join(linha) for linha in linhas[:8]).casefold()
    arquivo = nome_arquivo.casefold()
    if "contas a pagar" in texto or "pagar" in arquivo:
        return "pagar"
    if "contas a receber" in texto or "receber" in arquivo:
        return "receber"
    return None


def lancamentos_da_planilha(linhas: list[list[str]]) -> list[dict]:
    cabecalho = -1
    for indice, linha in enumerate(linhas):
        if linha and linha[0].strip().casefold() == "código":
            cabecalho = indice
            break
    if cabecalho < 0:
        return []
    registros: list[dict] = []
    for linha in linhas[cabecalho + 1 :]:
        if not linha or not linha[0].strip():
            continue
        while len(linha) < 8:
            linha.append("")
        codigo = linha[0].strip()
        if not codigo.isdigit():
            continue
        registros.append(
            {
                "codigo": codigo,
                "duplicata": linha[1].strip() or None,
                "vencimento": _data_planilha(linha[2]),
                "nome": linha[3].strip() or None,
                "historico": linha[4].strip() or None,
                "data_pagamento": _data_planilha(linha[5]),
                "valor_baixa": _numero_planilha(linha[6]),
                "valor_liquido": _numero_planilha(linha[7]),
            }
        )
    return registros


def garantir_next() -> None:
    if st.session_state.get("next_schema_ok"):
        return
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS next_lancamento (
                    id bigserial PRIMARY KEY,
                    tipo text NOT NULL,
                    codigo text,
                    duplicata text,
                    vencimento date,
                    nome text,
                    historico text,
                    data_pagamento date,
                    valor_baixa double precision,
                    valor_liquido double precision,
                    origem_arquivo text,
                    importado_em timestamptz NOT NULL DEFAULT now(),
                    quitado text NOT NULL DEFAULT 'Nao',
                    valor_pago double precision NOT NULL DEFAULT 0,
                    obs_conta text,
                    juros double precision,
                    multa double precision
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS next_lancamento_tipo_vencimento
                ON next_lancamento (tipo, vencimento)
                """
            )
        )
        for coluna, tipo_coluna in (
            ("quitado", "text NOT NULL DEFAULT 'Nao'"),
            ("valor_pago", "double precision NOT NULL DEFAULT 0"),
            ("obs_conta", "text"),
            ("juros", "double precision"),
            ("multa", "double precision"),
        ):
            conn.execute(
                text(f"ALTER TABLE next_lancamento ADD COLUMN IF NOT EXISTS {coluna} {tipo_coluna}")
            )
    st.session_state.next_schema_ok = True


def gravar_lancamentos_next(tipo: str, registros: list[dict], origem: str) -> int:
    garantir_next()
    with engine().begin() as conn:
        anteriores = conn.execute(
            text(
                """
                SELECT codigo, duplicata, vencimento, quitado, valor_pago,
                       data_pagamento, obs_conta, juros, multa
                FROM next_lancamento
                WHERE tipo = :tipo
                """
            ),
            {"tipo": tipo},
        ).mappings().all()
        guardados = []
        for antigo in anteriores:
            pago = float(antigo["valor_pago"] or 0)
            quitado = str(antigo["quitado"] or "").strip().casefold()
            observacao = str(antigo["obs_conta"] or "").strip()
            if quitado == "sim" or pago > 0 or observacao or antigo["juros"] or antigo["multa"]:
                guardados.append(dict(antigo))
        conn.execute(text("DELETE FROM next_lancamento WHERE tipo = :tipo"), {"tipo": tipo})
        if registros:
            conn.execute(
                text(
                    """
                    INSERT INTO next_lancamento (
                        tipo, codigo, duplicata, vencimento, nome, historico,
                        data_pagamento, valor_baixa, valor_liquido, origem_arquivo
                    ) VALUES (
                        :tipo, :codigo, :duplicata, :vencimento, :nome, :historico,
                        :data_pagamento, :valor_baixa, :valor_liquido, :origem
                    )
                    """
                ),
                [{**registro, "tipo": tipo, "origem": origem} for registro in registros],
            )
        for antigo in guardados:
            conn.execute(
                text(
                    """
                    UPDATE next_lancamento
                    SET quitado = :quitado,
                        valor_pago = :valor_pago,
                        data_pagamento = :data_pagamento,
                        obs_conta = :obs_conta,
                        juros = :juros,
                        multa = :multa
                    WHERE tipo = :tipo
                      AND codigo = :codigo
                      AND COALESCE(duplicata, '') = COALESCE(:duplicata, '')
                      AND vencimento IS NOT DISTINCT FROM :vencimento
                    """
                ),
                {**antigo, "tipo": tipo},
            )
        registrar_log(
            "Importação",
            f"Subiu {len(registros)} lançamentos de contas a {tipo} a partir de {origem}.",
            modulo=MODULO_PV,
            conn=conn,
        )
    st.cache_data.clear()
    return len(registros)


def importar_arquivo_next(conteudo: bytes, nome: str) -> tuple[str, int]:
    linhas = ler_primeira_aba(conteudo)
    tipo = tipo_planilha_next(linhas, nome)
    if tipo is None:
        raise ValueError("A planilha precisa ser de contas a pagar ou de contas a receber.")
    registros = lancamentos_da_planilha(linhas)
    if not registros:
        raise ValueError("Nenhum lançamento encontrado nessa planilha.")
    return tipo, gravar_lancamentos_next(tipo, registros, nome)


def arquivos_pasta_next() -> list[tuple[str, Path]]:
    if not PASTA_PLANILHAS_NEXT.is_dir():
        return []
    encontrados: list[tuple[str, Path]] = []
    for arquivo in sorted(PASTA_PLANILHAS_NEXT.glob("*.xlsx")):
        tipo = tipo_planilha_next([], arquivo.name)
        if tipo:
            encontrados.append((tipo, arquivo))
    return encontrados


def subir_pasta_next() -> list[str]:
    avisos: list[str] = []
    for tipo, arquivo in arquivos_pasta_next():
        quantidade = importar_arquivo_next(arquivo.read_bytes(), arquivo.name)[1]
        nome = "Contas a pagar" if tipo == "pagar" else "Contas a receber"
        avisos.append(f"{nome}: {inteiro(quantidade)} lançamentos de {arquivo.name}.")
    return avisos


def lancamentos_next(tipo: str) -> pd.DataFrame:
    garantir_next()
    return query(
        """
        SELECT codigo, duplicata, vencimento, nome, historico,
               data_pagamento, valor_baixa, valor_liquido, importado_em
        FROM next_lancamento
        WHERE tipo = ?
        ORDER BY CASE WHEN vencimento IS NULL THEN 1 ELSE 0 END, vencimento, codigo
        """,
        (tipo,),
    )


def cabecalho_modulo() -> None:
    logo, titulo, sair = st.columns([1, 4, 1], vertical_alignment="center")
    with logo:
        mostrar_logo(92)
    with titulo:
        st.title(TITULO)
    with sair:
        if st.button("Menu", width="stretch", key="voltar_menu"):
            st.session_state.modulo = None
            st.rerun()
        if st.button("Sair", width="stretch", key="sair_topo"):
            encerrar_sessao()


def lateral_modulo(usuario: dict, texto: str, legenda: str | None = None) -> None:
    with st.sidebar:
        mostrar_logo(150)
        st.header(TITULO)
        st.write(usuario["nome"])
        if usuario["administrador"]:
            st.caption("Administrador")
        st.write(texto)
        if st.button("Sair", width="stretch", key="sair_menu"):
            encerrar_sessao()
        if st.button("Atualizar dados", width="stretch", key="atualizar_dados"):
            st.cache_data.clear()
            st.rerun()
        if legenda:
            st.caption(legenda)


def clausula_pesquisa_next(termo: str, params: list) -> str:
    termos = termos_busca(termo)
    if not termos:
        return ""
    partes = []
    for campo in ("codigo", "duplicata", "nome", "historico", "obs_conta"):
        for item in termos:
            partes.append(comparar_busca(campo))
            params.append(like(item))
    return " AND (" + " OR ".join(partes) + ")"


def limpar_pesquisa_next(tipo: str) -> None:
    st.session_state[f"next_termo_{tipo}"] = ""
    st.session_state[f"next_termo_campo_{tipo}"] = ""


def pesquisa_next(tipo: str) -> str:
    with st.form(f"pesquisa_next_{tipo}", border=True):
        campo, acao = st.columns([4, 1], vertical_alignment="bottom")
        termo_digitado = campo.text_input(
            "Pesquisar por código, duplicata, nome ou histórico",
            key=f"next_termo_campo_{tipo}",
            placeholder="Código, duplicata, nome ou histórico",
            persist_state="session",
        )
        pesquisou = acao.form_submit_button("Pesquisar", type="primary", width="stretch")
    if pesquisou:
        st.session_state[f"next_termo_{tipo}"] = str(termo_digitado or "").strip()
    termo = str(st.session_state.get(f"next_termo_{tipo}", "")).strip()
    if termo:
        st.caption(f"Pesquisa ativa: {termo}")
        st.button(
            "Limpar pesquisa",
            key=f"limpar_pesquisa_next_{tipo}",
            on_click=limpar_pesquisa_next,
            args=(tipo,),
        )
    return termo


def texto_lembrete_next() -> str:
    aviso = f"NENHUMA BAIXA NOS ÚLTIMOS {DIAS_EDICAO_BAIXA} DIAS."
    ultima = scalar(
        """
        SELECT MAX(substr(CAST(data_pagamento AS TEXT), 1, 10))
        FROM next_lancamento
        WHERE lower(IFNULL(quitado, '')) = 'sim'
          AND substr(CAST(data_pagamento AS TEXT), 1, 10) <> ''
        """
    )
    if not ultima:
        return aviso
    quando = pd.to_datetime(str(ultima)[:10], errors="coerce")
    if pd.isna(quando):
        return aviso
    dias = (date.today() - quando.date()).days
    if dias >= DIAS_EDICAO_BAIXA:
        return aviso
    if dias <= 0:
        return "Última baixa hoje."
    if dias == 1:
        return "Última baixa a 1 dia."
    return f"Última baixa a {dias} dias."


def mostrar_lembrete_next() -> None:
    texto = html.escape(texto_lembrete_next())
    st.markdown(
        "<p style='text-align:center;font-weight:700;font-size:1.05rem;margin:0.15rem 0 0.7rem'>"
        f"{texto}</p>",
        unsafe_allow_html=True,
    )


def _baixa_pela_linha(chave_ids: str, chave_click: str, reabrir: bool) -> None:
    click = st.session_state.get(chave_click)
    ids = list(st.session_state.get(chave_ids) or [])
    if click is None:
        return
    try:
        indice = click.row
    except AttributeError:
        indice = click["row"]
    if isinstance(indice, int) and 0 <= indice < len(ids):
        abrir_baixa_next(int(ids[indice]), reabrir)


def click_baixar_vencidas() -> None:
    _baixa_pela_linha("nx_ids_vencidas", "nx_click_baixar_vencidas", False)


def click_baixar_avencer() -> None:
    _baixa_pela_linha("nx_ids_avencer", "nx_click_baixar_avencer", False)


def click_baixar_notas() -> None:
    _baixa_pela_linha("nx_ids_notas", "nx_click_baixar_notas", False)
    fechar_notas_cliente()


def click_reabrir_next() -> None:
    _baixa_pela_linha("nx_ids_recentes", "nx_click_reabrir", True)


def titulo_central(texto: str) -> None:
    st.markdown(
        "<h3 style='text-align:center;margin:0.15rem 0 0.45rem'>"
        f"{html.escape(texto)}</h3>",
        unsafe_allow_html=True,
    )


def nome_lista_next(tipo: str, vencida: bool) -> str:
    if tipo == "pagar":
        return "Contas a pagar vencidas" if vencida else "Contas a pagar a vencer"
    return "Contas a receber vencidas" if vencida else "Contas a vencer não vencidas"


def _contas_com_divida(contas: pd.DataFrame) -> pd.DataFrame:
    if contas.empty:
        return contas
    trabalho = contas.copy()
    if "cliente" not in trabalho.columns:
        trabalho["cliente"] = trabalho.get("descricao", "")
    trabalho["cliente"] = trabalho["cliente"].map(lambda valor: texto_limpo(valor) or "Sem identificação")
    trabalho["chave"] = trabalho["cliente"].map(sem_acento)
    vencimento = pd.to_datetime(trabalho["vencimento"], errors="coerce")
    trabalho["eh_vencida"] = vencimento.notna() & (vencimento < pd.Timestamp(date.today()))
    juros = trabalho["juros"] if "juros" in trabalho.columns else pd.Series(0, index=trabalho.index)
    multa = trabalho["multa"] if "multa" in trabalho.columns else pd.Series(0, index=trabalho.index)
    trabalho["divida"] = [
        valor_divida_exibida(valor, pago, juro, multa_valor)
        for valor, pago, juro, multa_valor in zip(
            trabalho["valor"], trabalho["valor_pago"], juros, multa, strict=True
        )
    ]
    return trabalho


def abrir_notas_cliente() -> None:
    click = st.session_state.get("nx_cli_click")
    if click is None:
        return
    ordem = list(st.session_state.get("nx_cli_ordem") or [])
    rotulos = list(st.session_state.get("nx_cli_rotulos") or [])
    nomes = list(st.session_state.get("nx_cli_nomes") or [])
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
    st.session_state.nx_cli_cliente = ordem[escolhido]
    st.session_state.nx_cli_nome = nomes[escolhido] if escolhido < len(nomes) else ordem[escolhido]


def fechar_notas_cliente() -> None:
    st.session_state.nx_cli_cliente = None
    st.session_state.nx_cli_nome = None


@st.dialog("Notas em aberto", width="large", on_dismiss=fechar_notas_cliente)
def dialogo_notas_cliente() -> None:
    chave = st.session_state.get("nx_cli_cliente")
    base = st.session_state.get("nx_notas_base")
    if not chave or base is None or getattr(base, "empty", True):
        return
    nome = st.session_state.get("nx_cli_nome") or chave
    linhas = base[base["chave"] == chave].copy()
    st.subheader(nome)
    if linhas.empty:
        st.info("Este cliente não tem notas em aberto.")
        return
    vencido = float(linhas.loc[linhas["eh_vencida"], "divida"].sum())
    a_vencer = float(linhas.loc[~linhas["eh_vencida"], "divida"].sum())
    st.caption(
        f"{inteiro(len(linhas))} notas em aberto. "
        f"Vencidas: {brl(vencido)}. A vencer: {brl(a_vencer)}."
    )
    st.session_state.nx_ids_notas = [int(valor) for valor in linhas["id"].tolist()]
    visivel = pd.DataFrame(
        {
            "Código": linhas["codigo"].map(lambda valor: texto_limpo(valor) or "—"),
            "Descrição": linhas["descricao"].map(lambda valor: texto_limpo(valor) or "—")
            if "descricao" in linhas.columns
            else "—",
            "Vencimento": linhas["vencimento"].map(lambda valor: data_br(valor) or "—"),
            "Situação": ["Vencida" if flag else "A vencer" for flag in linhas["eh_vencida"]],
            "Valor": linhas["divida"],
            "Baixar": ["Baixar"] * len(linhas),
        }
    )
    st.dataframe(
        visivel,
        width="stretch",
        hide_index=True,
        height=min(420, max(160, 48 + len(visivel) * 35)),
        column_config={
            "Código": st.column_config.TextColumn("Código", width="small"),
            "Descrição": st.column_config.TextColumn("Descrição", width="medium"),
            "Vencimento": st.column_config.TextColumn("Vencimento", width="small"),
            "Situação": st.column_config.TextColumn("Situação", width="small"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", width="small"),
            "Baixar": st.column_config.ButtonColumn(
                "Baixar",
                type="primary",
                width="small",
                on_click=click_baixar_notas,
                key="nx_click_baixar_notas",
            ),
        },
        alt=f"Notas em aberto de {nome}",
    )


def mostrar_totais_cliente(contas: pd.DataFrame) -> None:
    trabalho = _contas_com_divida(contas)
    st.session_state.nx_notas_base = trabalho
    if trabalho.empty:
        st.info("Nenhuma conta em aberto para esse cliente.")
        return
    trabalho = trabalho.copy()
    trabalho["vencido"] = trabalho["divida"].where(trabalho["eh_vencida"], 0.0)
    trabalho["a_vencer"] = trabalho["divida"].where(~trabalho["eh_vencida"], 0.0)
    resumo = (
        trabalho.groupby("chave", as_index=False)
        .agg(
            cliente=("cliente", nome_do_grupo),
            vencido=("vencido", "sum"),
            a_vencer=("a_vencer", "sum"),
            notas=("id", "count"),
        )
        .sort_values(["vencido", "a_vencer", "cliente"], ascending=[False, False, True])
    )
    t1, t2 = st.columns(2)
    t1.metric("Valor vencido", brl(resumo["vencido"].sum()))
    t2.metric("Valor a vencer", brl(resumo["a_vencer"].sum()))
    grade = resumo[["cliente", "vencido", "a_vencer"]].copy()
    rotulos = [f"{int(qtd)} notas" for qtd in resumo["notas"]]
    grade["notas"] = rotulos
    st.session_state.nx_cli_ordem = resumo["chave"].tolist()
    st.session_state.nx_cli_rotulos = rotulos
    st.session_state.nx_cli_nomes = resumo["cliente"].tolist()

    def cor_cliente(linha):
        tinta = VERMELHO if valor_banco(linha["vencido"]) > 0 else AZUL
        return ["" if coluna == "notas" else tinta for coluna in linha.index]

    st.dataframe(
        grade.style.apply(cor_cliente, axis=1),
        width="stretch",
        hide_index=True,
        height=min(420, max(160, 48 + len(grade) * 35)),
        column_config={
            "cliente": st.column_config.TextColumn("Cliente", width="medium"),
            "vencido": st.column_config.NumberColumn("Vencidas", format="R$ %.2f", width="small"),
            "a_vencer": st.column_config.NumberColumn("A vencer", format="R$ %.2f", width="small"),
            "notas": st.column_config.ButtonColumn(
                "Notas em aberto",
                type="primary",
                width="small",
                help="Quantidade de notas em aberto e o valor de cada uma",
                on_click=abrir_notas_cliente,
                key="nx_cli_click",
            ),
        },
        alt="Totais do cliente em contas vencidas e a vencer",
    )
    if st.session_state.get("nx_cli_cliente"):
        dialogo_notas_cliente()


def listar_next_abertas(
    contas: pd.DataFrame,
    *,
    chave_ids: str,
    chave_click: str,
    ao_clicar,
    alt: str,
    vermelho: bool = False,
) -> None:
    st.session_state[chave_ids] = [int(valor) for valor in contas["id"].tolist()]
    visivel = pd.DataFrame(
        {
            "Código": contas["codigo"].map(lambda valor: texto_limpo(valor) or "—"),
            "Descrição": contas["descricao"].map(lambda valor: texto_limpo(valor) or "—"),
            "Vencimento": contas["vencimento"].map(lambda valor: data_br(valor) or "—"),
            "Dias vencidos": [
                dias_em_atraso(vencimento, quitado)
                for vencimento, quitado in zip(contas["vencimento"], contas["quitado"], strict=True)
            ],
            "Valor da dívida": [
                valor_divida_exibida(valor, pago, juros, multa)
                for valor, pago, juros, multa in zip(
                    contas["valor"],
                    contas["valor_pago"],
                    contas["juros"] if "juros" in contas.columns else [0] * len(contas),
                    contas["multa"] if "multa" in contas.columns else [0] * len(contas),
                    strict=True,
                )
            ],
            "Baixar": ["Baixar"] * len(contas),
        }
    )
    tabela = pintar_faixa(visivel, VERMELHO, {"Baixar"}) if vermelho else visivel
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=min(480, max(160, 48 + len(contas) * 35)),
        column_config={
            "Código": st.column_config.TextColumn("Código", width="small"),
            "Descrição": st.column_config.TextColumn("Descrição", width="medium"),
            "Vencimento": st.column_config.TextColumn("Vencimento", width="small"),
            "Dias vencidos": st.column_config.NumberColumn("Dias vencidos", format="%d", width="small"),
            "Valor da dívida": st.column_config.NumberColumn("Valor da dívida", format="R$ %.2f", width="small"),
            "Baixar": st.column_config.ButtonColumn(
                "Baixar",
                type="primary",
                width="small",
                on_click=ao_clicar,
                key=chave_click,
            ),
        },
        alt=alt,
    )


def listar_next_recentes(contas: pd.DataFrame) -> None:
    st.session_state.nx_ids_recentes = [int(valor) for valor in contas["id"].tolist()]
    visivel = pd.DataFrame(
        {
            "Código": contas["codigo"].map(lambda valor: texto_limpo(valor) or "—"),
            "Descrição": contas["descricao"].map(lambda valor: texto_limpo(valor) or "—"),
            "Pagamento": contas["dt_pagamento"].map(lambda valor: data_br(valor) or "—"),
            "Valor pago": pd.to_numeric(contas["valor_pago"], errors="coerce"),
            "Reabrir baixa": ["Reabrir baixa"] * len(contas),
        }
    )
    st.dataframe(
        visivel,
        width="stretch",
        hide_index=True,
        height=420,
        column_config={
            "Código": st.column_config.TextColumn("Código"),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
            "Pagamento": st.column_config.TextColumn("Pagamento"),
            "Valor pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f"),
            "Reabrir baixa": st.column_config.ButtonColumn(
                "Reabrir baixa",
                type="primary",
                width="medium",
                on_click=click_reabrir_next,
                key="nx_click_reabrir",
            ),
        },
        alt="Baixas recentes do Next",
    )


def abrir_baixa_next(conta_id: int, reabrir: bool = False) -> None:
    st.session_state.next_baixa_id = int(conta_id)
    st.session_state.next_baixa_reabrir = bool(reabrir)
    st.session_state.next_baixa_init = None


def fechar_baixa_next() -> None:
    st.session_state.next_baixa_id = None
    st.session_state.next_baixa_reabrir = False


def buscar_next(conta_id: int) -> pd.Series | None:
    frame = query(
        """
        SELECT id,
               codigo AS os,
               codigo,
               COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), '')) AS nome,
               quitado,
               vencimento,
               valor_liquido AS valor,
               COALESCE(valor_pago, 0) AS valor_pago,
               data_pagamento AS dt_pagamento,
               obs_conta,
               duplicata AS parcela,
               COALESCE(NULLIF(TRIM(historico), ''), NULLIF(TRIM(nome), '')) AS descricao,
               tipo,
               juros,
               multa
        FROM next_lancamento
        WHERE id = ?
        """,
        (int(conta_id),),
    )
    if frame.empty:
        return None
    return frame.iloc[0]


def _sync_data_next(conta_id: int) -> None:
    pago = valor_banco(st.session_state.get(f"nx_pago_{conta_id}"))
    if pago > 0 and st.session_state.get(f"nx_data_{conta_id}") is None:
        st.session_state[f"nx_data_{conta_id}"] = date.today()


def _conta_a_pagar(linha: pd.Series) -> bool:
    return str(linha.get("tipo", "")).strip().casefold() == "pagar"


def _recalcular_next(conta_id: int, saldo: float, dias: int | None, aplicar_juros: bool = True) -> None:
    juros, multa = encargos_legais(saldo, dias)
    st.session_state[f"nx_juros_{conta_id}"] = juros if aplicar_juros else 0.0
    st.session_state[f"nx_multa_{conta_id}"] = multa


def _preparar_baixa_next(conta_id: int, linha: pd.Series, reabrir: bool) -> None:
    if st.session_state.get("next_baixa_init") == conta_id:
        return
    juros, multa, tem_salvo = _encargos_salvos(linha)
    dias = dias_em_atraso(linha["vencimento"], "Nao" if reabrir else linha["quitado"])
    saldo = round(max(0.0, valor_banco(linha["valor"]) - valor_banco(linha["valor_pago"])), 2)
    if not tem_salvo:
        juros, multa = encargos_legais(valor_banco(linha["valor"]) if reabrir else saldo, dias)
    if _conta_a_pagar(linha):
        juros = 0.0
    obs, _, _ = separar_obs_encargos(texto_banco(linha["obs_conta"]))
    st.session_state[f"nx_juros_{conta_id}"] = float(juros)
    st.session_state[f"nx_multa_{conta_id}"] = float(multa)
    st.session_state[f"nx_obs_{conta_id}"] = obs
    st.session_state[f"nx_pago_{conta_id}"] = float(valor_banco(linha["valor_pago"]) if reabrir else 0.0)
    st.session_state[f"nx_data_{conta_id}"] = data_iso(linha["dt_pagamento"]) if reabrir else None
    st.session_state.next_baixa_init = conta_id


def _totais_next(linha: pd.Series, conta_id: int, reabrir: bool) -> tuple[float, float, float, float]:
    juros = 0.0 if _conta_a_pagar(linha) else valor_banco(st.session_state.get(f"nx_juros_{conta_id}"))
    multa = valor_banco(st.session_state.get(f"nx_multa_{conta_id}"))
    pago_campo = valor_banco(st.session_state.get(f"nx_pago_{conta_id}"))
    ja_pago = valor_banco(linha["valor_pago"])
    pago_total = pago_campo if reabrir else round(ja_pago + pago_campo, 2)
    devido = round(valor_banco(linha["valor"]) + juros + multa, 2)
    return juros, multa, pago_total, devido


def gravar_next_baixa(
    conta_id: int,
    *,
    pago: float,
    juros: float,
    multa: float,
    quando: date | None,
    obs: str,
    quitar: bool,
) -> None:
    pagamento = None if quando is None else quando.isoformat()
    quitado = "Sim" if quitar else "Nao"
    with engine().begin() as conn:
        antes = conn.execute(
            text(
                """
                SELECT codigo, nome, historico
                FROM next_lancamento
                WHERE id = :id
                """
            ),
            {"id": int(conta_id)},
        ).mappings().first()
        if antes is None:
            return
        conn.execute(
            text(
                """
                UPDATE next_lancamento
                SET quitado = :quitado,
                    data_pagamento = :pagamento,
                    valor_pago = :pago,
                    obs_conta = :obs,
                    juros = :juros,
                    multa = :multa
                WHERE id = :id
                """
            ),
            {
                "quitado": quitado,
                "pagamento": pagamento,
                "pago": round(pago, 2),
                "obs": obs,
                "juros": round(juros, 2),
                "multa": round(multa, 2),
                "id": int(conta_id),
            },
        )
        codigo = texto_banco(antes["codigo"]) or "sem código"
        cliente = texto_banco(antes["nome"]) or texto_banco(antes["historico"]) or "sem nome"
        situacao = "quitada" if quitar else "parcial"
        registrar_log(
            "Baixa",
            (
                f"Código {codigo}, {cliente}, lançamento {int(conta_id)}: baixa {situacao}, "
                f"valor pago {brl(pago)}, juros {brl(juros)}, multa {brl(multa)}, "
                f"pagamento em {data_br(pagamento) or 'sem data'}."
            ),
            modulo=MODULO_PV,
            conn=conn,
        )


def _salvar_baixa_next(linha: pd.Series, conta_id: int, reabrir: bool, quitar: bool) -> None:
    juros, multa, pago_total, devido = _totais_next(linha, conta_id, reabrir)
    pago_campo = valor_banco(st.session_state.get(f"nx_pago_{conta_id}"))
    quando = data_iso(st.session_state.get(f"nx_data_{conta_id}"))
    if quitar and pago_total + 0.004 < devido:
        complemento = "multa" if _conta_a_pagar(linha) else "juros e multa"
        st.error(f"A baixa só é concluída quando o valor pago é igual ou maior que a dívida com {complemento}.")
        return
    if not quitar and pago_total + 0.004 >= devido:
        st.error("A baixa parcial fica para um valor menor que o total para quitação.")
        return
    if not quitar and not reabrir and pago_campo <= 0:
        st.error("Informe o valor pago nesta baixa parcial.")
        return
    if pago_total > 0 and quando is None:
        st.error("Informe a data do pagamento.")
        return
    obs = texto_banco(st.session_state.get(f"nx_obs_{conta_id}"))
    gravar_next_baixa(
        conta_id,
        pago=pago_total,
        juros=juros,
        multa=multa,
        quando=quando,
        obs=obs,
        quitar=quitar,
    )
    st.session_state.next_baixa_aviso = 1
    st.session_state.next_baixa_aviso_texto = (
        "Baixa registrada. A conta foi quitada." if quitar else "Baixa parcial registrada. A conta continua em aberto."
    )
    fechar_baixa_next()
    st.cache_data.clear()
    st.rerun()


def _ficha_next(linha: pd.Series, dias: int | None) -> None:
    pares = [
        ("Cliente", texto_limpo(linha["nome"]) or "—"),
        ("Código", texto_limpo(linha["codigo"]) or "—"),
        ("Descrição", texto_limpo(linha["descricao"]) or "—"),
        ("Parcela", texto_limpo(linha["parcela"]) or "—"),
        ("Vencimento", data_br(linha["vencimento"]) or "—"),
        ("Dias vencidos", str(dias) if dias else "—"),
        ("Valor original", brl(linha["valor"])),
        ("Já pago", brl(linha["valor_pago"])),
    ]
    linhas = "".join(_linha_doc(rotulo, valor) for rotulo, valor in pares)
    st.html(
        "<style>.ficha-baixa th,.ficha-baixa td{border:1px solid #d5e4ee;padding:6px 8px;font-size:14px;text-align:left}"
        ".ficha-baixa{width:100%;border-collapse:collapse}.ficha-baixa th{width:34%;background:#f4f8fb}</style>"
        f"<table class='ficha-baixa'>{linhas}</table>"
    )


@st.dialog("Baixa da conta", width="large", on_dismiss=fechar_baixa_next)
def dialogo_baixa_next() -> None:
    conta_id = st.session_state.get("next_baixa_id")
    if not conta_id:
        return
    linha = buscar_next(int(conta_id))
    if linha is None:
        st.warning("Esta conta não está mais no Next.")
        return
    reabrir = bool(st.session_state.get("next_baixa_reabrir"))
    _preparar_baixa_next(int(conta_id), linha, reabrir)
    if reabrir:
        st.subheader("Reabrir baixa")
    dias = dias_em_atraso(linha["vencimento"], "Nao")
    _ficha_next(linha, dias)
    saldo = round(max(0.0, valor_banco(linha["valor"]) - valor_banco(linha["valor_pago"])), 2)
    base_legal = valor_banco(linha["valor"]) if reabrir else saldo
    pagar = _conta_a_pagar(linha)
    juros_lei, multa_lei = encargos_legais(base_legal, dias)
    if pagar:
        st.caption(
            "Contas a pagar não recebem juros. A multa sugerida pode ser alterada antes de salvar. "
            f"Sugestão para {dias or 0} dia(s): multa {brl(multa_lei)}."
        )
        j1, j2 = st.columns([1, 1], vertical_alignment="bottom")
        j1.number_input("Multa", min_value=0.0, step=0.01, format="%.2f", key=f"nx_multa_{conta_id}")
        j2.button(
            "Recalcular pela lei",
            key=f"nx_recalc_{conta_id}",
            on_click=_recalcular_next,
            args=(int(conta_id), base_legal, dias, False),
            width="stretch",
        )
    else:
        st.caption(
            "Multa de 2% sobre o saldo vencido, uma vez (Código de Defesa do Consumidor, art. 52, § 1º). "
            "Juros de mora de 1% ao mês, proporcionais aos dias (mês de 30 dias), teto usual da relação de consumo "
            "quando não há índice contratado. Os valores sugeridos podem ser alterados antes de salvar. "
            f"Sugestão para {dias or 0} dia(s): juros {brl(juros_lei)} e multa {brl(multa_lei)}."
        )
        j1, j2, j3 = st.columns([1, 1, 1], vertical_alignment="bottom")
        j1.number_input("Juros", min_value=0.0, step=0.01, format="%.2f", key=f"nx_juros_{conta_id}")
        j2.number_input("Multa", min_value=0.0, step=0.01, format="%.2f", key=f"nx_multa_{conta_id}")
        j3.button(
            "Recalcular pela lei",
            key=f"nx_recalc_{conta_id}",
            on_click=_recalcular_next,
            args=(int(conta_id), base_legal, dias, True),
            width="stretch",
        )
    rotulo_pago = "Valor pago" if reabrir else "Valor pago nesta baixa"
    p1, p2 = st.columns(2)
    p1.number_input(
        rotulo_pago,
        min_value=0.0,
        step=0.01,
        format="%.2f",
        key=f"nx_pago_{conta_id}",
        on_change=_sync_data_next,
        args=(int(conta_id),),
    )
    p2.date_input("Data do pagamento", format="DD/MM/YYYY", key=f"nx_data_{conta_id}")
    st.text_area("Obs", key=f"nx_obs_{conta_id}", height=80)
    juros, multa, pago_total, devido = _totais_next(linha, int(conta_id), reabrir)
    restante = round(max(0.0, devido - pago_total), 2)
    r1, r2, r3 = st.columns(3)
    r1.metric("Total para quitação", brl(devido))
    r2.metric("Valor pago acumulado", brl(pago_total))
    r3.metric("Valor restante", brl(restante))
    pode_quitar = pago_total + 0.004 >= devido and pago_total > 0
    pode_parcial = pago_total + 0.004 < devido and (
        valor_banco(st.session_state.get(f"nx_pago_{conta_id}")) > 0 or reabrir
    )
    b1, b2 = st.columns(2)
    if b1.button("Salvar baixa", type="primary", width="stretch", key=f"nx_salvar_{conta_id}", disabled=not pode_quitar):
        _salvar_baixa_next(linha, int(conta_id), reabrir, True)
    if b2.button("Salvar baixa parcial", width="stretch", key=f"nx_parcial_{conta_id}", disabled=not pode_parcial):
        _salvar_baixa_next(linha, int(conta_id), reabrir, False)
    if not pode_quitar:
        st.caption("A baixa integral só fica disponível quando o valor pago é igual ou maior que o total para quitação.")
    quando = data_iso(st.session_state.get(f"nx_data_{conta_id}"))
    obs = texto_banco(st.session_state.get(f"nx_obs_{conta_id}"))
    dados = _dados_documento(linha, juros, multa, pago_total, quando, obs)
    dados_nota = dict(dados)
    valor_nota = restante if restante > 0 else devido
    dados_nota["valor"] = brl(valor_nota)
    dados_nota["extenso"] = reais_por_extenso(valor_nota)
    i1, i2 = st.columns(2)
    if i1.button("Imprimir recibo quitado", width="stretch", key=f"nx_recibo_{conta_id}", disabled=not pode_quitar):
        disparar_impressao(html_recibo(dados))
    if i2.button("Imprimir nota promissória", width="stretch", key=f"nx_nota_{conta_id}"):
        disparar_impressao(html_promissoria(dados_nota))


def tabela_next(frame: pd.DataFrame, tipo: str) -> None:
    if frame.empty:
        st.info("Nenhuma conta encontrada com esses filtros.")
        return
    visivel = format_frame(com_dias_vencidos(frame))
    config = column_config(list(visivel.columns))
    tabela = pintar_nao_pagas(visivel) if "quitado" in visivel.columns else visivel
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=560,
        column_config=config,
        alt="Contas do Next",
    )
    st.download_button(
        "Baixar CSV deste resultado",
        data=visivel.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"next_{tipo}.csv",
        mime="text/csv",
        key=f"download_next_{tipo}",
    )


def botoes_financeiro_next() -> str:
    st.session_state.setdefault("next_fin_lista", "receber")
    ativa = st.session_state.next_fin_lista
    if ativa not in {"receber", "pagar"}:
        ativa = "receber"
        st.session_state.next_fin_lista = ativa
    marca = "btn_next_receber" if ativa == "receber" else "btn_next_pagar"
    st.html(
        f"""
        <style>
        .st-key-menu_next_fin,
        .st-key-menu_next_fin [data-testid="stHorizontalBlock"] {{
          width: 100%;
          justify-content: center !important;
        }}
        .st-key-menu_next_fin button {{
          background-color: #0c6b4d !important;
          color: #f4fbf7 !important;
          border: 1px solid #084a36 !important;
          border-radius: 999px !important;
          box-shadow: 0 8px 18px rgba(12, 107, 77, 0.34) !important;
          font-weight: 600 !important;
          padding: 0.45rem 0.95rem !important;
        }}
        .st-key-menu_next_fin button:hover {{
          background-color: #14845f !important;
        }}
        .st-key-menu_next_fin .st-key-{marca} button,
        .st-key-menu_next_fin .st-key-{marca} button:hover {{
          background-color: #c4a35a !important;
          color: #1a2e28 !important;
          border-color: #a8883e !important;
          box-shadow: 0 10px 22px rgba(196, 163, 90, 0.45) !important;
        }}
        </style>
        """
    )
    with st.container(
        key="menu_next_fin",
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
        gap="small",
    ):
        if st.button("Contas a receber", key="btn_next_receber", type="primary"):
            if ativa != "receber":
                st.session_state.next_fin_lista = "receber"
                st.rerun()
        if st.button("Contas a pagar", key="btn_next_pagar", type="primary"):
            if ativa != "pagar":
                st.session_state.next_fin_lista = "pagar"
                st.rerun()
    return ativa


def painel_contas_next() -> None:
    tipo = botoes_financeiro_next()
    termo = pesquisa_next("fin")
    params_busca: list = []
    filtro = clausula_pesquisa_next(termo, params_busca)
    limite_recente = (date.today() - timedelta(days=DIAS_EDICAO_BAIXA)).isoformat()
    descricao_sql = "COALESCE(NULLIF(TRIM(historico), ''), NULLIF(TRIM(nome), ''))"
    recentes = query(
        f"""
        SELECT id, codigo, {descricao_sql} AS descricao, vencimento,
               valor_liquido AS valor, COALESCE(valor_pago, 0) AS valor_pago,
               data_pagamento AS dt_pagamento, quitado
        FROM next_lancamento
        WHERE tipo = ?
          AND lower(IFNULL(quitado, '')) = 'sim'
          AND substr(CAST(data_pagamento AS TEXT), 1, 10) >= ?
          {filtro}
        ORDER BY data_pagamento DESC, id DESC
        """,
        tuple([tipo, limite_recente, *params_busca]),
    )
    mostrar_lembrete_next()
    abertas = query(
        f"""
        SELECT id, codigo, {descricao_sql} AS descricao,
               COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), ''), 'Sem identificação') AS cliente,
               vencimento,
               valor_liquido AS valor, COALESCE(valor_pago, 0) AS valor_pago,
               juros, multa, quitado
        FROM next_lancamento
        WHERE tipo = ?
          AND lower(IFNULL(quitado, '')) <> 'sim'
          {filtro}
        ORDER BY CASE WHEN vencimento IS NULL THEN 1 ELSE 0 END, vencimento, codigo
        """,
        tuple([tipo, *params_busca]),
    )
    vencimento = pd.to_datetime(abertas["vencimento"], errors="coerce") if not abertas.empty else pd.Series(dtype="datetime64[ns]")
    vencidas_mask = vencimento.notna() & (vencimento < pd.Timestamp(date.today()))
    vencidas = abertas.loc[vencidas_mask] if not abertas.empty else abertas
    a_vencer = abertas.loc[~vencidas_mask] if not abertas.empty else abertas
    if tipo == "pagar":
        if not vencidas.empty:
            vencidas = vencidas.copy()
            vencidas["juros"] = 0
        if not a_vencer.empty:
            a_vencer = a_vencer.copy()
            a_vencer["juros"] = 0

    def total_lista(contas: pd.DataFrame) -> float:
        if contas.empty:
            return 0.0
        return round(
            sum(
                valor_divida_exibida(
                    registro.valor,
                    registro.valor_pago,
                    getattr(registro, "juros", 0),
                    getattr(registro, "multa", 0),
                )
                for registro in contas.itertuples(index=False)
            ),
            2,
        )

    aviso = st.session_state.pop("next_baixa_aviso", None)
    aviso_texto = st.session_state.pop("next_baixa_aviso_texto", None)
    if aviso:
        st.success(aviso_texto or f"{inteiro(aviso)} conta(s) atualizada(s).")
    elif aviso == 0:
        st.info("Nenhuma alteração para salvar.")

    if tipo == "receber":
        st.caption("Na busca, o valor do cliente fica separado em contas vencidas e contas a vencer.")
        mostrar_totais_cliente(abertas)

    coluna_vencidas, coluna_avencer = st.columns(2, gap="medium")
    with coluna_vencidas:
        st.html('<div id="next-vencidas" style="scroll-margin-top:80px"></div>')
        titulo_central(nome_lista_next(tipo, True))
        v1, v2 = st.columns(2)
        v1.metric("Quantidade", inteiro(len(vencidas)))
        v2.metric("Valor", brl(total_lista(vencidas)))
        if vencidas.empty:
            st.info("Nenhuma conta vencida.")
        else:
            st.caption("Estas contas já passaram do vencimento e ainda não foram quitadas.")
            listar_next_abertas(
                vencidas,
                chave_ids="nx_ids_vencidas",
                chave_click="nx_click_baixar_vencidas",
                ao_clicar=click_baixar_vencidas,
                alt="Contas vencidas do Next",
                vermelho=True,
            )
    with coluna_avencer:
        st.html('<div id="next-avencer" style="scroll-margin-top:80px"></div>')
        titulo_central(nome_lista_next(tipo, False))
        a1, a2 = st.columns(2)
        a1.metric("Quantidade", inteiro(len(a_vencer)))
        a2.metric("Valor", brl(total_lista(a_vencer)))
        if a_vencer.empty:
            st.info("Nenhuma conta em aberto por vencer.")
        else:
            st.caption("No dia seguinte ao vencimento, se não forem quitadas, passam para a lista vermelha.")
            listar_next_abertas(
                a_vencer,
                chave_ids="nx_ids_avencer",
                chave_click="nx_click_baixar_avencer",
                ao_clicar=click_baixar_avencer,
                alt="Contas a vencer do Next",
            )

    st.html('<div id="next-recentes" style="scroll-margin-top:80px"></div>')
    st.subheader("Baixas recentes")
    st.caption(
        f"Contas quitadas nos últimos {DIAS_EDICAO_BAIXA} dias. "
        "Reabrir baixa abre a mesma tela da conta para os ajustes."
    )
    if recentes.empty:
        mostrar_lembrete_next()
    else:
        r1, r2 = st.columns(2)
        r1.metric("Baixas no prazo", inteiro(len(recentes)))
        r2.metric("Valor dessas baixas", brl(recentes["valor_pago"].sum()))
        listar_next_recentes(recentes)

    st.html('<div id="next-todas" style="scroll-margin-top:80px"></div>')
    st.subheader("Todas as contas")
    st.caption(
        f"Contas recebidas nos últimos {DIAS_EDICAO_BAIXA} dias ficam no topo das recebidas, "
        "da baixa mais nova para a mais antiga. Depois desse prazo elas seguem a ordem de vencimento."
    )
    quadro_quitado = query(
        """
        SELECT DISTINCT quitado
        FROM next_lancamento
        WHERE quitado IS NOT NULL AND TRIM(quitado) <> ''
        ORDER BY 1
        """
    )
    quitados = [str(valor) for valor in quadro_quitado.iloc[:, 0].tolist()] if not quadro_quitado.empty else ["Nao", "Sim"]
    f1, f2, f3 = st.columns([2, 1, 1])
    texto = f1.text_input(
        "Pesquisar",
        placeholder="Código, nome, histórico, duplicata ou observação",
        key="busca_next_fin",
        persist_state="session",
    )
    quitado = f2.multiselect(
        "Quitado",
        quitados,
        key="quitado_next_fin",
        persist_state="session",
    )
    limite = f3.slider(
        "Máximo de linhas",
        50,
        5000,
        500,
        50,
        key="limite_next_fin",
        persist_state="session",
    )
    d1, d2 = st.columns(2)
    inicio = d1.date_input(
        "Vencimento de",
        value=None,
        key="next_de_fin",
        format="DD/MM/YYYY",
        persist_state="session",
    )
    fim = d2.date_input(
        "Vencimento até",
        value=None,
        key="next_ate_fin",
        format="DD/MM/YYYY",
        persist_state="session",
    )
    params: list = [tipo]
    where = " WHERE tipo = ?"
    where += clausula_pesquisa_next(termo, params)
    where += text_clause(["codigo", "nome", "historico", "duplicata", "obs_conta"], texto, params)
    where += in_clause("quitado", quitado, params)
    where += date_clause("vencimento", inicio, fim, params)
    totais = query(
        f"""
        SELECT COUNT(*) AS n, SUM(valor_liquido) AS valor, SUM(valor_pago) AS pago,
               SUM(valor_liquido - COALESCE(valor_pago, 0)) AS aberto
        FROM next_lancamento{where}
        """,
        tuple(params),
    )
    recebida = (
        "lower(IFNULL(quitado, '')) = 'sim' "
        "AND substr(IFNULL(CAST(data_pagamento AS TEXT), ''), 1, 10) >= ?"
    )
    frame = query(
        f"""
        SELECT codigo, {descricao_sql} AS descricao, duplicata, vencimento, quitado,
               valor_liquido AS valor, COALESCE(valor_pago, 0) AS valor_pago,
               data_pagamento AS dt_pagamento
        FROM next_lancamento{where}
        ORDER BY CASE WHEN lower(IFNULL(quitado, '')) <> 'sim' THEN 0 ELSE 1 END,
                 CASE WHEN {recebida} THEN 0 ELSE 1 END,
                 CASE WHEN {recebida} THEN data_pagamento END DESC,
                 CASE WHEN vencimento IS NULL THEN 1 ELSE 0 END,
                 vencimento, codigo
        LIMIT ?
        """,
        tuple([*params, limite_recente, limite_recente, int(limite)]),
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Linhas no filtro", inteiro(totais.iat[0, 0] or 0))
    m2.metric("Valor filtrado", brl(totais.iat[0, 1]))
    m3.metric("Saldo em aberto", brl(totais.iat[0, 3]))
    tabela_next(frame, "fin")
    if st.session_state.get("next_baixa_id"):
        dialogo_baixa_next()


def ir_contas_receber() -> None:
    st.session_state.aba_pv = ABA_FIN
    st.session_state.next_fin_lista = "receber"
    st.session_state.quitado_next_fin = ["Nao"]
    st.session_state.busca_next_fin = ""


def origem_next() -> None:
    origem = query(
        """
        SELECT origem_arquivo AS arquivo,
               CASE tipo WHEN 'pagar' THEN 'Despesa' ELSE 'Receita' END AS aba,
               COUNT(*) AS registros,
               MAX(importado_em) AS importado_em
        FROM next_lancamento
        GROUP BY origem_arquivo, tipo
        ORDER BY origem_arquivo
        """
    )
    if origem.empty:
        return
    with st.expander("Origem da importação"):
        st.dataframe(format_frame(origem), width="stretch", hide_index=True)


def visao_next() -> None:
    mostrar_lembrete_next()
    resumo = query(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE tipo = 'receber' AND lower(COALESCE(quitado, '')) <> 'sim'
            ) AS receber_n,
            COUNT(*) FILTER (
                WHERE tipo = 'pagar' AND lower(COALESCE(quitado, '')) <> 'sim'
            ) AS pagar_n,
            COUNT(DISTINCT NULLIF(TRIM(COALESCE(nome, historico)), '')) FILTER (
                WHERE tipo = 'receber'
            ) AS clientes,
            COUNT(*) AS contas,
            SUM(valor_liquido - COALESCE(valor_pago, 0)) FILTER (
                WHERE tipo = 'receber' AND lower(COALESCE(quitado, '')) <> 'sim'
            ) AS aberto
        FROM next_lancamento
        """
    )
    receber_n = int(resumo.iat[0, 0] or 0) if not resumo.empty else 0
    pagar_n = int(resumo.iat[0, 1] or 0) if not resumo.empty else 0
    clientes = int(resumo.iat[0, 2] or 0) if not resumo.empty else 0
    contas = int(resumo.iat[0, 3] or 0) if not resumo.empty else 0
    aberto = resumo.iat[0, 4] if not resumo.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contas a receber", inteiro(receber_n))
    c2.metric("Contas a pagar", inteiro(pagar_n))
    c3.metric("Clientes", inteiro(clientes))
    c4.metric("Lançamentos", inteiro(contas))
    c5, c6 = st.columns([1, 2])
    c5.metric("Contas", inteiro(contas))
    with c6:
        st.markdown(
            f"""
            <div style="background:#fff6ed;border:2px solid #c2410c;border-radius:14px;padding:18px 22px;">
              <div style="font-size:0.95rem;color:#9a3412;font-weight:700;">Em aberto (receita)</div>
              <div style="font-size:2rem;line-height:1.15;color:#7c2d12;font-weight:800;margin-top:4px;">{brl(aberto)}</div>
              <div style="color:#9a3412;margin-top:6px;">{inteiro(receber_n)} contas de receita ainda não quitadas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("Ver contas em aberto", type="primary", on_click=ir_contas_receber, width="stretch")
    por_tipo = query(
        """
        SELECT CASE tipo WHEN 'pagar' THEN 'Despesa' ELSE 'Receita' END AS tipo,
               COUNT(*) AS contas
        FROM next_lancamento
        GROUP BY tipo
        ORDER BY tipo
        """
    )
    mensal = query(
        """
        SELECT substr(CAST(vencimento AS TEXT), 1, 7) AS mes,
               SUM(CASE WHEN tipo = 'receber' THEN valor_liquido ELSE 0 END) AS receitas,
               SUM(CASE WHEN tipo = 'pagar' THEN valor_liquido ELSE 0 END) AS despesas
        FROM next_lancamento
        WHERE vencimento IS NOT NULL
        GROUP BY mes
        ORDER BY mes
        """
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Contas por tipo")
        if por_tipo.empty:
            st.write("Sem dados.")
        else:
            st.bar_chart(por_tipo.set_index("tipo")["contas"], height=280, sort=False)
    with right:
        st.subheader("Lançamentos por mês")
        if mensal.empty:
            st.write("Sem dados.")
        else:
            st.line_chart(mensal.set_index("mes")[["receitas", "despesas"]], height=280)
    st.subheader("Maiores clientes por receita")
    top = query(
        """
        SELECT COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), '')) AS cliente,
               COUNT(*) AS contas,
               ROUND(SUM(valor_liquido), 2) AS valor,
               ROUND(SUM(COALESCE(valor_pago, 0)), 2) AS valor_pago
        FROM next_lancamento
        WHERE tipo = 'receber'
        GROUP BY COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), ''))
        HAVING COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), '')) IS NOT NULL
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
    origem_next()


def contas_next_clientes() -> pd.DataFrame:
    frame = query(
        """
        SELECT id,
               COALESCE(NULLIF(TRIM(nome), ''), NULLIF(TRIM(historico), ''), 'Sem identificação') AS cliente,
               codigo,
               duplicata AS parcela,
               COALESCE(NULLIF(TRIM(historico), ''), NULLIF(TRIM(nome), '')) AS descricao,
               vencimento,
               quitado,
               ROUND(COALESCE(valor_liquido, 0), 2) AS valor,
               ROUND(COALESCE(valor_pago, 0), 2) AS valor_pago,
               COALESCE(juros, 0) AS juros,
               COALESCE(multa, 0) AS multa,
               ROUND(COALESCE(valor_liquido, 0) - COALESCE(valor_pago, 0), 2) AS saldo
        FROM next_lancamento
        WHERE tipo = 'receber'
        """
    )
    if frame.empty:
        return frame
    frame["cliente"] = frame["cliente"].map(lambda valor: texto_limpo(valor) or "Sem identificação")
    frame["chave"] = frame["cliente"].str.casefold()
    vencimento = pd.to_datetime(frame["vencimento"], errors="coerce")
    aberta = frame["quitado"].fillna("").astype(str).str.casefold().ne("sim")
    frame["vencida"] = (aberta & vencimento.notna() & (vencimento < pd.Timestamp(date.today()))).astype(int)
    return frame


def abrir_divida_next() -> None:
    click = st.session_state.get("nx_cli_click")
    if click is None:
        return
    ordem = list(st.session_state.get("nx_cli_ordem") or [])
    rotulos = list(st.session_state.get("nx_cli_rotulos") or [])
    nomes = list(st.session_state.get("nx_cli_nomes") or [])
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
    st.session_state.nx_cli_cliente = ordem[escolhido]
    st.session_state.nx_cli_nome = nomes[escolhido] if escolhido < len(nomes) else ordem[escolhido]


def fechar_cliente_next() -> None:
    st.session_state.nx_cli_cliente = None
    st.session_state.nx_cli_nome = None


@st.dialog("Dívidas do cliente", width="large", on_dismiss=fechar_cliente_next)
def dialogo_dividas_next() -> None:
    base = contas_next_clientes()
    chave = st.session_state.get("nx_cli_cliente")
    if not chave:
        return
    nome = st.session_state.get("nx_cli_nome") or chave
    linhas = base[(base["chave"] == chave) & (base["vencida"] == 1)].copy()
    st.subheader(nome)
    if linhas.empty:
        st.success("Este cliente não tem dívida vencida. Ele está na lista de adimplentes.")
        return
    linhas["dias"] = [
        dias_em_atraso(vencimento, quitado)
        for vencimento, quitado in zip(linhas["vencimento"], linhas["quitado"], strict=True)
    ]
    linhas["vencimento"] = linhas["vencimento"].map(data_br)
    st.caption(f"Dívida vencida: {brl(linhas['saldo'].sum())}.")
    visivel = linhas[["codigo", "descricao", "vencimento", "dias", "parcela", "valor", "valor_pago", "saldo"]]
    st.dataframe(
        visivel,
        width="stretch",
        hide_index=True,
        height=360,
        column_config={
            "codigo": st.column_config.TextColumn("Código"),
            "descricao": st.column_config.TextColumn("Descrição"),
            "vencimento": st.column_config.TextColumn("Vencimento"),
            "dias": st.column_config.NumberColumn("Dias vencidos"),
            "parcela": st.column_config.TextColumn("Parcela"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "valor_pago": st.column_config.NumberColumn("Valor pago", format="R$ %.2f"),
            "saldo": st.column_config.NumberColumn("Saldo", format="R$ %.2f"),
        },
        alt=f"Dívidas de {nome}",
    )


def clientes_next() -> None:
    base = contas_next_clientes()
    termo = st.text_input(
        "Pesquisar cliente",
        placeholder="Nome do cliente",
        key="busca_cli_next",
        persist_state="session",
    )
    if termo.strip() and not base.empty:
        base = base[contem_termo(base["cliente"], termo)]
    if not base.empty:
        base = base[base["quitado"].fillna("").astype(str).str.casefold().ne("sim")]
    st.caption("O valor do cliente fica separado em contas vencidas e contas a vencer. O botão abre as notas em aberto.")
    mostrar_totais_cliente(base)
    if st.session_state.get("next_baixa_id"):
        dialogo_baixa_next()


def tela_pv() -> None:
    usuario = st.session_state.usuario
    garantir_next()
    cabecalho_modulo()
    periodo = query("SELECT MIN(vencimento), MAX(vencimento) FROM next_lancamento")
    legenda = None
    if not periodo.empty and periodo.iat[0, 0]:
        legenda = f"Vencimentos de {data_br(periodo.iat[0, 0])} a {data_br(periodo.iat[0, 1])}"
    lateral_modulo(
        usuario,
        "Histórico do Next. As baixas das contas em aberto são gravadas neste banco.",
        legenda,
    )
    abas = [ABA_GERAL, ABA_FIN, ABA_CLI]
    if usuario["administrador"]:
        abas.append(ABA_USUARIOS)
        abas.append(ABA_LOG)
    menu_principal(abas, "aba_pv")
    aba = st.session_state.get("aba_pv")
    if aba == ABA_FIN:
        painel_contas_next()
    elif aba == ABA_CLI:
        clientes_next()
    elif aba == ABA_USUARIOS:
        aba_usuarios()
    elif aba == ABA_LOG:
        aba_log()
    else:
        visao_next()
    barra_rolagem_superior()




def menu_principal(abas: list[str], chave: str = "aba") -> None:
    ativa = st.session_state.get(chave)
    if ativa not in abas:
        ativa = abas[0]
        st.session_state[chave] = ativa
    chave_ativa = CHAVES_MENU[ativa]
    st.html(
        f"""
        <style>
        [data-testid="stMain"] h1 {{
          text-align: center;
          margin-bottom: 0.15rem;
        }}
        .st-key-menu_navegacao,
        .st-key-menu_navegacao [data-testid="stHorizontalBlock"] {{
          width: 100%;
          justify-content: center !important;
        }}
        .st-key-menu_navegacao {{
          position: sticky;
          top: 0.45rem;
          z-index: 999;
          padding: 0.15rem 0 0.55rem;
        }}
        .st-key-menu_navegacao button {{
          background-color: #0c6b4d !important;
          color: #f4fbf7 !important;
          border: 1px solid #084a36 !important;
          border-radius: 999px !important;
          box-shadow: 0 8px 18px rgba(12, 107, 77, 0.34) !important;
          font-weight: 600 !important;
          padding: 0.45rem 0.95rem !important;
        }}
        .st-key-menu_navegacao button:hover {{
          background-color: #14845f !important;
          transform: translateY(-2px);
        }}
        .st-key-menu_navegacao .st-key-{chave_ativa} button,
        .st-key-menu_navegacao .st-key-{chave_ativa} button:hover {{
          background-color: #c4a35a !important;
          color: #1a2e28 !important;
          border-color: #a8883e !important;
          box-shadow: 0 10px 22px rgba(196, 163, 90, 0.45) !important;
        }}
        </style>
        """
    )
    with st.container(
        key="menu_navegacao",
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
        gap="small",
    ):
        for nome in abas:
            if st.button(nome, key=CHAVES_MENU[nome], type="primary"):
                if nome != ativa:
                    st.session_state[chave] = nome
                    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=TITULO,
        page_icon=str(LOGO),
        layout="wide",
    )
    esconder_gerenciar()
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        garantir_usuarios()
    except Exception as exc:
        st.title(TITULO)
        st.error(f"Não foi possível conectar ao Supabase. {exc}")
        st.stop()
    if "usuario" in st.session_state:
        agora = datetime.now().timestamp()
        if st.session_state.get("usuario_verificado_em", 0) + 30 <= agora:
            usuario = usuario_sessao(int(st.session_state.usuario["id"]))
            st.session_state.usuario_verificado_em = agora
            if usuario is None:
                desconectar_sessao()
                st.session_state.pop("usuario", None)
            else:
                st.session_state.usuario = usuario
    if "usuario" not in st.session_state:
        tela_acesso()
        return
    pulso_presenca()
    if st.session_state.usuario.get("trocar_senha"):
        tela_trocar_senha()
        return
    usuario = st.session_state.usuario
    modulo = st.session_state.get("modulo")
    if modulo == "pv":
        tela_pv()
        return
    if modulo != "os":
        tela_modulos()
        return
    cabecalho_modulo()
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

    periodo = query("SELECT MIN(data_entrada), MAX(data_entrada) FROM oficina_os")
    legenda = None
    if not periodo.empty and periodo.iat[0, 0]:
        legenda = f"Entradas de {periodo.iat[0, 0]} a {periodo.iat[0, 1]}"
    lateral_modulo(
        usuario,
        "Histórico da Oficina Integrada. As baixas das contas em aberto são gravadas neste banco.",
        legenda,
    )

    abas = list(ABAS)
    if usuario["administrador"]:
        abas.append(ABA_USUARIOS)
        abas.append(ABA_LOG)
    if st.session_state.get("aba") not in abas:
        st.session_state.aba = ABA_GERAL
    menu_principal(abas)
    aba = st.session_state.aba
    if aba == ABA_OS:
        aba_os()
    elif aba == ABA_FIN:
        aba_financeiro()
    elif aba == ABA_CLI:
        aba_clientes()
    elif aba == ABA_NF:
        aba_nfse()
    elif aba == ABA_USUARIOS:
        aba_usuarios()
    elif aba == ABA_LOG:
        aba_log()
    else:
        visao_geral()
    barra_rolagem_superior()


main()
