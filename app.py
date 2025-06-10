import unicodedata
import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import io
import re

st.set_page_config(page_title="Receitas por Produto", page_icon="dollar")

st.subheader("", divider=True)

st.title("💲Receita Mensal por Produto")

uploaded_files = st.file_uploader(
    "Adicione o(s) arquivo(s) para leitura e geração do Excel referente aos totais consolidados.",
    type=["pdf"],
    accept_multiple_files=True,
)

st.subheader("", divider=True)

descricao_padrao = {
    "TARIFA MANUTENCAO": "TARIFA DE MANUTENCAO",
    "TARIFA MANUTENÇÃO": "TARIFA DE MANUTENCAO",
    "TARIFA DE MANUTENÇÃO": "TARIFA DE MANUTENCAO",
    "TARIFA SEGUNDA VIA DE CARTAO": "TARIFA SEGUNDA VIA DE CARTAO",
    "TARIFA  SEGUNDA VIA DE CARTÃO": "TARIFA SEGUNDA VIA DE CARTAO",

    "SEGUNDA VIA DE CARTAO": "TARIFA SEGUNDA VIA DE CARTAO",
    "SEGUNDA VIA DE CARTÃO": "TARIFA SEGUNDA VIA DE CARTAO",

    "DESCONTO NA RENEGOCIACAO DE DIVIDA": "DESCONTO NA RENEGOCIACAO DE DIVIDA",
    "DESCONTO NA RENEGOCIAÇÃO DE DÍVIDA": "DESCONTO NA RENEGOCIACAO DE DIVIDA",
    "DESCONTO NO VALOR PRINCIPAL DA FATURA": "DESCONTO NO VALOR PRINCIPAL DA FATURA",
    "ESTORNO JUROS POR ATRASO": "ESTORNO JUROS POR ATRASO",
    "JUROS POR ATRASO": "JUROS POR ATRASO",
    "MULTA POR ATRASO": "MULTA POR ATRASO",
    "ENCARGOS FINANCIAMENTO": "ENCARGOS FINANCIAMENTO",
    "LANCAMENTO DE ACRESCIMO DE ACORDO": "LANCAMENTO DE ACRESCIMO DE ACORDO",
    "TOTAL GERAL": "TOTAL GERAL",
}

def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto).strip().upper()
    return descricao_padrao.get(texto, texto) 

dados_gerais = []

if uploaded_files:
    for arquivo in uploaded_files:
        leitor = PdfReader(arquivo)
        texto = leitor.pages[0].extract_text()

        
        linhas = [
            linha for linha in texto.split('\n')
            if not re.search(r'Página \d+ de|[0-3]?\d/\d{2}/\d{4}|[0-2]?\d:\d{2}:\d{2}', linha)
        ]

    
        produto = "Desconhecido"
        for linha in linhas:
            if "Produto:" in linha:
                match = re.search(r'Produto:\s*(.+)', linha)
                if match:
                    produto = match.group(1).strip()

        dados = {"Produto": produto}

        for linha in linhas:
            match = re.match(r"(.+?)\s+(-?[\d\.,]+)$", linha.strip())
            if match:
                descricao_raw = match.group(1)
                descricao = normalizar(descricao_raw)
                valor = match.group(2).replace(".", "").replace(",", ".")
                try:
                    valor_float = float(valor)
                    dados[descricao] = valor_float
                except:
                    pass

        dados_gerais.append(dados)

    df = pd.DataFrame(dados_gerais)
    df = df.fillna(0)  

    df["JUROS"] = (
        df.get("JUROS POR ATRASO", 0)
        + df.get("MULTA POR ATRASO", 0)
        + df.get("ENCARGOS FINANCIAMENTO", 0)
    )

    df["DESCONTOS"] = (
        df.get("DESCONTO NA RENEGOCIACAO DE DIVIDA", 0)
        + df.get("DESCONTO NO VALOR PRINCIPAL DA FATURA", 0)
        + df.get("ESTORNO JUROS POR ATRASO", 0)

        + df.get("ESTORNO DE MULTA POR ATRASO", 0)
    )

    df = df.drop(columns=[
        "JUROS POR ATRASO",
        "MULTA POR ATRASO",
        "ENCARGOS FINANCIAMENTO",
        "DESCONTO NA RENEGOCIACAO DE DIVIDA",
        "DESCONTO NO VALOR PRINCIPAL DA FATURA",
        "ESTORNO JUROS POR ATRASO",

        "ESTORNO DE MULTA POR ATRASO"
    ], errors="ignore")

    cols = df.columns.tolist()
    if "Produto" in cols and "JUROS" in cols:
        cols.insert(cols.index("Produto") + 1, cols.pop(cols.index("JUROS")))  
    if "DESCONTOS" in cols:
        cols.append(cols.pop(cols.index("DESCONTOS")))  
    df = df[cols]

    total_row = df.iloc[:, 1:].sum(numeric_only=True)
    total_row["Produto"] = "TOTAL GERAL"

    cols = df.columns.tolist()


    if "Produto" in cols and "JUROS" in cols:
        cols.insert(cols.index("Produto") + 1, cols.pop(cols.index("JUROS")))


    if "DESCONTOS" in cols:
        cols.append(cols.pop(cols.index("DESCONTOS")))


    for nome_total in ["TOTAL GERAL", "TOTAL GERAL:"]:
        if nome_total in cols:
            cols.append(cols.pop(cols.index(nome_total)))

    df = df[cols]


    total_row_df = pd.DataFrame([total_row])

    df_sem_total = df[df["Produto"] != "TOTAL GERAL"]

    df_ordenado = df_sem_total.sort_values(by="Produto", ignore_index=True)

    df_final = pd.concat([df_ordenado, total_row_df], ignore_index=True)


    st.dataframe(df_final)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Resumo')

    st.subheader("", divider=True)

    st.download_button(
        label="📥 Baixar Excel",
        data=output.getvalue(),
        file_name="resumo_receitas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

