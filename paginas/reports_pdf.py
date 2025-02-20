# Arquivo: reports.py
# Data: 18/01/2025

import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import date
from io import BytesIO
import tempfile

def load_indicator_data(user_id):
    """Carrega os dados das tabelas Etapa_1, Etapa_2 e Etapa_3."""
    conn = sqlite3.connect("calcpc.db")
    cursor = conn.cursor()

    # Etapa 1
    cursor.execute("""
        SELECT COALESCE(SUM(Etp1_energia_insumo1 + Etp1_energia_insumo2 + Etp1_energia_insumo3), 0) AS energia,
               COALESCE(SUM(Etp1_agua_insumo1 + Etp1_agua_insumo2 + Etp1_agua_insumo3), 0) AS agua,
               COALESCE(SUM(Etp1_insumo1 + Etp1_insumo2 + Etp1_insumo3 + Etp1_residuo1 + Etp1_residuo2 + Etp1_residuo3), 0) AS co2
        FROM Etapa_1 WHERE ID_User = ?
    """, (user_id,))
    etapa1 = cursor.fetchone()

    # Etapa 2
    cursor.execute("""
        SELECT COALESCE(SUM(Etp2_energia_insumo1 + Etp2_energia_insumo2 + Etp2_energia_insumo3), 0) AS energia,
               COALESCE(SUM(Etp2_agua_insumo1 + Etp2_agua_insumo2 + Etp2_agua_insumo3), 0) AS agua,
               COALESCE(SUM(Etp2_insumo1 + Etp2_insumo2 + Etp2_insumo3 + Etp2_residuo1 + Etp2_residuo2 + Etp2_residuo3), 0) AS co2
        FROM Etapa_2 WHERE ID_User = ?
    """, (user_id,))
    etapa2 = cursor.fetchone()

    # Etapa 3
    cursor.execute("""
        SELECT COALESCE(SUM(Etp3_energia_insumo1 + Etp3_energia_insumo2 + Etp3_energia_insumo3), 0) AS energia,
               COALESCE(SUM(Etp3_agua_insumo1 + Etp3_agua_insumo2 + Etp3_agua_insumo3), 0) AS agua,
               COALESCE(SUM(Etp3_insumo1 + Etp3_insumo2 + Etp3_insumo3 + Etp3_residuo1 + Etp3_residuo2 + Etp3_residuo3), 0) AS co2
        FROM Etapa_3 WHERE ID_User = ?
    """, (user_id,))
    etapa3 = cursor.fetchone()

    conn.close()

    return {
        "Etapa 1": etapa1,
        "Etapa 2": etapa2,
        "Etapa 3": etapa3
    }

def plot_indicator(stage, data):
    """Gera um gráfico de barras para os indicadores de uma etapa."""
    labels = ["Energia", "Água", "CO2"]
    plt.figure(figsize=(5, 3))
    plt.bar(labels, data, color=["blue", "green", "red"])
    plt.title(f"Indicadores - {stage}")
    plt.ylabel("Valores")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def generate_pdf(user_id, indicadores, user_name, company_name):
    """Gera um PDF consolidando os gráficos e dados."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Cabeçalho do relatório
    pdf.cell(200, 10, txt="Relatório de Indicadores - Pegada de Carbono", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Usuário: {user_name}", ln=True)
    pdf.cell(200, 10, txt=f"Empresa: {company_name}", ln=True)
    pdf.cell(200, 10, txt=f"Data: {date.today().strftime('%d/%m/%Y')}", ln=True)

    for stage, data in indicadores.items():
        pdf.add_page()
        pdf.cell(200, 10, txt=f"{stage}", ln=True)

        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, "Indicador", 1)
        pdf.cell(60, 10, "Valor", 1)
        pdf.ln()

        labels = ["Energia", "Água", "CO2"]
        for label, value in zip(labels, data):
            pdf.cell(60, 10, label, 1)
            pdf.cell(60, 10, str(value), 1)
            pdf.ln()

        buf = plot_indicator(stage, data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(buf.read())
            temp_file.flush()
            pdf.image(temp_file.name, x=None, y=None, w=100)

    buf = BytesIO()
    pdf.output(buf, "F")
    buf.seek(0)
    return buf

def app():
    """Exibe a página de relatórios."""
    if "user_profile" not in st.session_state or st.session_state["user_profile"] not in ["Usuario", "Adm"]:
        st.error("Você não tem permissão para acessar esta página.")
        return

    st.title("Relatórios - Indicadores de Pegada de Carbono")

    user_id = st.session_state.get("user_id", 0)
    indicadores = load_indicator_data(user_id)

    conn = sqlite3.connect("calcpc.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nome_usuario, empresa FROM Usuarios WHERE ID_User = ?", (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    user_name, company_name = user_info if user_info else ("Usuário", "Empresa")

    for stage, data in indicadores.items():
        st.subheader(stage)
        df = pd.DataFrame({"Indicador": ["Energia", "Água", "CO2"], "Valor": data})
        st.table(df)

        buf = plot_indicator(stage, data)
        st.image(buf, caption=f"Gráfico - {stage}")
        buf.close()

    if st.button("Gerar PDF"):
        pdf_buf = generate_pdf(user_id, indicadores, user_name, company_name)
        st.download_button(
            label="Baixar Relatório em PDF",
            data=pdf_buf,
            file_name="relatorio_indicadores.pdf",
            mime="application/pdf"
        )
