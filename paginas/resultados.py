# Arquivo: resultados.py
# Data: 19/02/2025 09:25
# Pagina de resultados - Dashboard
# Adaptação para o uso de Discos SSD e a pasta Data para o banco de dados

# type: ignore
# pylance: disable=reportMissingModuleSource

try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        KeepTogether
    )
except ImportError as e:
    print(f"Erro ao importar ReportLab: {e}")

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date
import io
import tempfile
import matplotlib.pyplot as plt
import traceback
from paginas.monitor import registrar_acesso
from paginas.form_model_recalc import verificar_dados_usuario, calculate_formula, atualizar_formulas
import time

from config import DB_PATH  # Adicione esta importação

def format_br_number(value):
    """
    Formata um número para o padrão brasileiro (vírgula como separador decimal)
    Usa 5 casas decimais para valores < 1 e 2 casas decimais para valores >= 1
    """
    try:
        if value is None:
            return "0,00"
        
        float_value = float(value)
        if abs(float_value) < 1 and float_value != 0:
            return f"{float_value:.5f}".replace('.', ',')
        else:
            return f"{float_value:.2f}".replace('.', ',')
    except:
        return "0,00"

def titulo(cursor, element):
    """
    Exibe títulos formatados na interface com base nos valores do banco de dados.
    """
    try:
        name = element[0]        # name_element
        type_elem = element[1]   # type_element
        msg = element[3]         # msg_element
        value = element[4]       # value_element (já é REAL do SQLite)
        str_value = element[6]   # str_element
        col = element[7]         # e_col
        row = element[8]         # e_row
        
        # Verifica se a coluna é válida
        if col > 6:
            st.error(f"Posição de coluna inválida para o título {name}: {col}. Deve ser entre 1 e 6.")
            return
        
        # Se for do tipo 'titulo', usa o str_element do próprio registro
        if type_elem == 'titulo':
            if str_value:
                # Se houver um valor numérico para exibir
                if value is not None:
                    # Formata o valor para o padrão brasileiro
                    value_br = format_br_number(value)
                    # Substitui {value} no str_value pelo valor formatado
                    str_value = str_value.replace('{value}', value_br)
                st.markdown(str_value, unsafe_allow_html=True)
            else:
                st.markdown(msg, unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Erro ao processar título: {str(e)}")

def pula_linha(cursor, element):
    """
    Adiciona uma linha em branco na interface quando o type_element é 'pula linha'
    """
    try:
        type_elem = element[1]  # type_element
        
        if type_elem == 'pula linha':
            st.markdown("<br>", unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Erro ao processar pula linha: {str(e)}")

def new_user(cursor, user_id):
    """
    Cria registros iniciais para um novo usuário na tabela forms_resultados,
    copiando os dados do template (user_id = 0)
    """
    try:
        # Verifica se já existem registros para o usuário
        cursor.execute("""
            SELECT COUNT(*) FROM forms_resultados 
            WHERE user_id = ?
        """, (user_id,))
        
        if cursor.fetchone()[0] == 0:
            # Copia dados do template (user_id = 0) para o novo usuário
            # value_element já é REAL, então não precisa de conversão
            cursor.execute("""
                INSERT INTO forms_resultados (
                    user_id, name_element, type_element, math_element,
                    msg_element, value_element, select_element, str_element,
                    e_col, e_row, section
                )
                SELECT 
                    ?, name_element, type_element, math_element,
                    msg_element, value_element, select_element, str_element,
                    e_col, e_row, section
                FROM forms_resultados
                WHERE user_id = 0
            """, (user_id,))
            
            cursor.connection.commit()
            st.success("Dados iniciais criados com sucesso!")
            
    except Exception as e:
        st.error(f"Erro ao criar dados do usuário: {str(e)}")

def call_dados(cursor, element):
    """
    Busca dados na tabela forms_tab e atualiza o value_element do registro atual.
    Mantém consistência usando o mesmo user_id.
    """
    try:
        name = element[0]        # name_element
        type_elem = element[1]   # type_element
        str_value = element[6]   # str_element
        user_id = element[10]    # user_id
        
        if type_elem == 'call_dados':
            # Busca o valor com CAST para garantir precisão decimal
            cursor.execute("""
                SELECT CAST(value_element AS DECIMAL(20, 8))
                FROM forms_tab 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (str_value, user_id))
            
            result = cursor.fetchone()
            
            if result:
                value = float(result[0]) if result[0] is not None else 0.0
                
                # Atualiza usando CAST para manter a precisão
                cursor.execute("""
                    UPDATE forms_resultados 
                    SET value_element = CAST(? AS DECIMAL(20, 8))
                    WHERE name_element = ? 
                    AND user_id = ?
                """, (value, name, user_id))
                
                cursor.connection.commit()
            else:
                st.warning(f"Valor não encontrado na tabela forms_tab para {str_value} (user_id: {user_id})")
                
    except Exception as e:
        st.error(f"Erro ao processar call_dados: {str(e)}")

def grafico_barra(cursor, element):
    """
    Cria um gráfico de barras verticais com dados da tabela forms_resultados.
    
    Args:
        cursor: Conexão com o banco de dados
        element: Tupla com os dados do elemento tipo 'grafico'
        
    Configurações do elemento:
        type_element: 'grafico'
        msg_element: título do gráfico
        math_element: número de colunas do gráfico
        select_element: type_names separados por | (ex: 'N24|N25|N26')
        str_element: rótulos separados por | (ex: 'Energia|Água|GEE')
        
    Nota: Largura do gráfico fixada em 90% da coluna para melhor visualização
    """
    try:
        type_elem = element[1]   # type_element
        msg = element[3]         # msg_element
        select = element[5]      # select_element
        rotulos = element[6]     # str_element
        user_id = element[10]    # user_id
        
        if type_elem != 'grafico':
            return
            
        # Validações iniciais
        if not select or not rotulos:
            st.error("Configuração incompleta do gráfico: select ou rótulos vazios")
            return
            
        # Separa os type_names e rótulos
        type_names = select.split('|')
        labels = rotulos.split('|')
        
        # Lista para armazenar os valores e cores
        valores = []
        cores = []
        
        # Busca os valores e cores para cada type_name
        for type_name in type_names:
            # Primeiro busca o valor
            cursor.execute("""
                SELECT value_element 
                FROM forms_resultados 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (type_name.strip(), user_id))
            
            result = cursor.fetchone()
            valor = result[0] if result and result[0] is not None else 0.0
            
            # Depois busca a cor no registro do gráfico atual
            cursor.execute("""
                SELECT section 
                FROM forms_resultados 
                WHERE type_element = 'grafico'
                AND select_element LIKE ?
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (f"%{type_name}%", user_id))
            
            color_result = cursor.fetchone()
            cor = color_result[0] if color_result and color_result[0] else '#1f77b4'
            
            valores.append(valor)
            cores.append(cor)
        
        # Criar o gráfico usando plotly express com cores personalizadas
        fig = px.bar(
            x=labels,
            y=valores,
            text=[format_br_number(v) for v in valores],
            title=None,
            color_discrete_sequence=cores
        )
        
        # Configura o layout
        fig.update_layout(
            xaxis_title="Etapas",
            yaxis_title="Valores",
            showlegend=False,
            height=400,
            width=None,
            xaxis=dict(
                tickfont=dict(size=14),
                title_font=dict(size=16)
            ),
            yaxis=dict(
                tickfont=dict(size=14),
                title_font=dict(size=16),
                tickformat=",.",
                separatethousands=True
            )
        )
        
        # Configura o texto nas barras
        fig.update_traces(
            textposition='auto',
            textfont=dict(size=16)
        )
        
        # Adiciona o título personalizado antes do gráfico
        st.markdown(f"""
            <h3 style='
                text-align: center;
                font-size: 24px;
                font-weight: 600;
                color: #000000;
                margin-top: 20px;
                margin-bottom: 30px;
                padding: 10px;
                font-family: sans-serif;
                letter-spacing: 0.5px;
                border-bottom: 2px solid #e8f5e9;
            '>{msg}</h3>
        """, unsafe_allow_html=True)
        
        # Exibe o gráfico
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    except Exception as e:
        st.error(f"Erro ao criar gráfico: {str(e)}")

def tabela_dados(cursor, element):
    """
    Cria uma tabela estilizada com dados da tabela forms_resultados.
    Tabela transposta (vertical) com valores em vez de nomes.
    
    Args:
        cursor: Conexão com o banco de dados
        element: Tupla com os dados do elemento tipo 'tabela'
        
    Configurações do elemento:
        type_element: 'tabela'
        msg_element: título da tabela
        math_element: número de colunas da tabela
        select_element: type_names separados por | (ex: 'N24|N25|N26')
        str_element: rótulos separados por | (ex: 'Energia|Água|GEE')
        
    Nota: 
        - Layout usando três colunas do Streamlit para centralização
        - Proporção de colunas: [1, 8, 1] (10% vazio, 80% tabela, 10% vazio)
        - Valores formatados no padrão brasileiro
        - Tabela transposta (vertical) para melhor leitura
        - Coluna 'Valor' com largura aumentada em 25%
    """
    try:
        # Extrai informações do elemento
        type_elem = element[1]   # type_element
        msg = element[3]         # msg_element (título da tabela)
        select = element[5]      # select_element (type_names separados por |)
        rotulos = element[6]     # str_element (rótulos separados por |)
        user_id = element[10]    # user_id
        
        if type_elem != 'tabela':
            return
            
        # Validações iniciais
        if not select or not rotulos:
            st.error("Configuração incompleta da tabela: select ou rótulos vazios")
            return
            
        # Separa os type_names e rótulos
        type_names = select.split('|')
        rotulos = rotulos.split('|')
        
        # Valida se quantidade de rótulos corresponde aos type_names
        if len(type_names) != len(rotulos):
            st.error("Número de rótulos diferente do número de valores")
            return
            
        # Lista para armazenar os valores
        valores = []
        
        # Busca os valores para cada type_name
        for type_name in type_names:
            cursor.execute("""
                SELECT value_element 
                FROM forms_resultados 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (type_name.strip(), user_id))
            
            result = cursor.fetchone()
            valor = format_br_number(result[0]) if result and result[0] is not None else '0,00'
            valores.append(valor)
        
        # Criar DataFrame com os dados
        df = pd.DataFrame({
            'Descrição': rotulos,
            'Valor': valores
        })
        
        # Criar três colunas, usando a do meio para a tabela
        col1, col2, col3 = st.columns([1, 8, 1])
        
        with col2:
            # Espaçamento fixo definido no código
            spacing = 20  # valor em pixels ajustado conforme solicitado
            
            # Adiciona quebras de linha antes do título
            num_breaks = spacing // 20
            for _ in range(num_breaks):
                st.markdown("<br>", unsafe_allow_html=True)
            
            # Exibe o título da tabela a esquerda
            st.markdown(f"<h4 style='text-align: left;'>{msg}</h4>", unsafe_allow_html=True)
            
            # Criar HTML da tabela com estilos inline
            html_table = f"""
            <div style='font-size: 20px; width: 80%;'>
                <table style='width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 10px; overflow: hidden; box-shadow: 0 0 8px rgba(0,0,0,0.1);'>
                    <thead>
                        <tr>
                            <th style='text-align: left; padding: 10px; background-color: #e8f5e9; border-bottom: 2px solid #dee2e6;'>Descrição</th>
                            <th style='text-align: right; padding: 10px; background-color: #e8f5e9; border-bottom: 2px solid #dee2e6;'>Valor</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"<tr><td style='padding: 8px 10px; border-bottom: 1px solid #dee2e6;'>{row['Descrição']}</td><td style='text-align: right; padding: 8px 10px; border-bottom: 1px solid #dee2e6;'>{row['Valor']}</td></tr>" for _, row in df.iterrows())}
                    </tbody>
                </table>
            </div>
            """
            
            # Exibe a tabela HTML
            st.markdown(html_table, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erro ao criar tabela: {str(e)}")

def gerar_dados_tabela(cursor, elemento):
    """Função auxiliar para gerar dados da tabela"""
    try:
        msg = elemento[3]         # msg_element
        select = elemento[5]      # select_element
        rotulos = elemento[6]     # str_element
        user_id = elemento[10]    # user_id
        
        if not select or not rotulos:
            st.error("Configuração incompleta da tabela: select ou rótulos vazios")
            return None
            
        # Separa os type_names e rótulos
        type_names = str(select).split('|')
        labels = str(rotulos).split('|')
        valores = []
        
        # Busca os valores para cada type_name
        for type_name in type_names:
            cursor.execute("""
                SELECT value_element 
                FROM forms_resultados 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (type_name.strip(), user_id))
            
            result = cursor.fetchone()
            valor = format_br_number(result[0]) if result and result[0] is not None else '0,00'
            valores.append(valor)
        
        # Retornar dados formatados para a tabela
        return {
            'title': msg if msg else "Tabela de Dados",
            'data': [['Descrição', 'Valor']] + list(zip(labels, valores))
        }
        
    except Exception as e:
        st.error(f"Erro ao gerar dados da tabela: {str(e)}")
        return None

def gerar_dados_grafico(cursor, elemento):
    """Função auxiliar para gerar gráfico como imagem para o PDF"""
    try:
        msg = elemento[3]         # msg_element
        select = elemento[5]      # select_element
        rotulos = elemento[6]     # str_element
        user_id = elemento[10]    # user_id
        cor = elemento[9]         # section (cor do gráfico)
        
        if not select or not rotulos:
            st.error("Configuração incompleta do gráfico: select ou rótulos vazios")
            return None
            
        type_names = str(select).split('|')
        labels = str(rotulos).split('|')
        valores = []
        cores = [cor] * len(type_names)  # Usar a mesma cor para todas as barras
        
        for type_name in type_names:
            cursor.execute("""
                SELECT value_element 
                FROM forms_resultados 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (type_name.strip(), user_id))
            
            result = cursor.fetchone()
            valor = float(result[0]) if result and result[0] is not None else 0.0
            valores.append(valor)
        
        # Criar gráfico usando plotly
        fig = px.bar(
            x=labels,
            y=valores,
            text=[format_br_number(v) for v in valores],
            title=None,
            color_discrete_sequence=cores
        )
        
        # Configurar layout
        fig.update_layout(
            showlegend=False,
            height=400,
            width=800,
            margin=dict(t=30, b=50),
            xaxis=dict(title=None),
            yaxis=dict(title=None)
        )
        
        # Configurar texto nas barras
        fig.update_traces(textposition='auto')
        
        # Converter para imagem
        img_bytes = fig.to_image(format="png")
        
        return {
            'title': msg,
            'image': Image(io.BytesIO(img_bytes), width=400, height=300)
        }
        
    except Exception as e:
        st.error(f"Erro ao gerar gráfico: {str(e)}")
        st.write("Debug: Stack trace completo:", traceback.format_exc())
        return None

def subtitulo():
    try:
        col1, col2 = st.columns([8, 2])
        with col1:
            st.markdown("""
                <h2 style='
                    text-align: Left;
                    font-size: 36px;
                    color: #000000;
                    margin-top: 10px;
                    margin-bottom: 30px;
                    font-family: sans-serif;
                    font-weight: 500;
                '>Resultado das Simulações da Empresa</h2>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("Gerar PDF", type="primary"):
                try:
                    # Criar um placeholder para as mensagens
                    msg_placeholder = st.empty()
                    msg_placeholder.info("Gerando PDF... Por favor, aguarde.")
                    
                    # 2. Registra geração do PDF
                    registrar_acesso(
                        st.session_state.user_id,
                        "resultados",
                        "Geração PDF na simulação Resultados"
                    )
                    
                    # Configuração inicial do PDF com orientação paisagem
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(
                        buffer,
                        pagesize=landscape(A4),
                        rightMargin=36,
                        leftMargin=36,
                        topMargin=36,
                        bottomMargin=36
                    )
                    
                    elements = []
                    styles = getSampleStyleSheet()
                    title_style = ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Heading1'],
                        fontSize=24,
                        spaceAfter=30,
                        alignment=1  # 1 = centralizado
                    )
                    
                    subtitle_style = ParagraphStyle(
                        'CustomSubtitle',
                        parent=styles['Heading2'],
                        fontSize=18,
                        spaceAfter=20,
                        alignment=1  # 1 = centralizado
                    )
                    
                    # Título principal centralizado
                    elements.append(Paragraph("Resultado das Simulações da Empresa", title_style))
                    elements.append(Spacer(1, 20))
                    
                    # Usar a mesma lógica da tela
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    # Buscar elementos ordenados por row e col (mesma query da tela)
                    cursor.execute("""
                        SELECT name_element, type_element, math_element, msg_element,
                               value_element, select_element, str_element, e_col, e_row,
                               section, user_id
                        FROM forms_resultados
                        WHERE (type_element = 'titulo' OR type_element = 'pula linha' 
                              OR type_element = 'call_dados' OR type_element = 'grafico'
                              OR type_element = 'tabela')
                        AND user_id = ?
                        ORDER BY e_row, e_col
                    """, (st.session_state.user_id,))
                    
                    elements_data = cursor.fetchall()
                    
                    # Agrupar elementos por e_row (mesma lógica da tela)
                    row_elements = {}
                    for element in elements_data:
                        e_row = element[8]
                        if e_row not in row_elements:
                            row_elements[e_row] = []
                        row_elements[e_row].append(element)
                    
                    # Processar elementos por linha
                    for e_row in sorted(row_elements.keys()):
                        row_data = row_elements[e_row]
                        
                        # Separar elementos da linha por coluna
                        col1_elements = [e for e in row_data if e[7] <= 3]  # e_col <= 3
                        col2_elements = [e for e in row_data if e[7] > 3]   # e_col > 3
                        
                        # Para cada par de elementos (tabela e gráfico)
                        tabela = next((e for e in col1_elements if e[1] == 'tabela'), None)
                        grafico = next((e for e in col2_elements if e[1] == 'grafico'), None)
                        
                        if tabela and grafico:
                            dados_tabela = gerar_dados_tabela(cursor, tabela)
                            dados_grafico = gerar_dados_grafico(cursor, grafico)
                            
                            if dados_tabela and dados_grafico:
                                # Criar grupo de elementos que devem ficar juntos
                                section_elements = []
                                
                                # Título da seção (usando msg_element da tabela)
                                section_elements.append(Paragraph(tabela[3], subtitle_style))  # tabela[3] é o msg_element
                                section_elements.append(Spacer(1, 10))
                                
                                # Criar tabela de dados
                                t_dados = Table(
                                    dados_tabela['data'],
                                    colWidths=[200, 100]
                                )
                                t_dados.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                                ]))
                                
                                # Ajustar tamanho do gráfico
                                dados_grafico['image']._width = 400
                                dados_grafico['image']._height = 300
                                
                                # Layout em duas colunas
                                layout_data = [[t_dados, dados_grafico['image']]]
                                layout = Table(
                                    layout_data,
                                    colWidths=[300, 450],
                                    style=[
                                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                        ('LEFTPADDING', (0, 0), (-1, -1), 15),
                                        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                                    ]
                                )
                                
                                section_elements.append(layout)
                                section_elements.append(Spacer(1, 30))
                                
                                # Adicionar todos os elementos da seção juntos
                                elements.append(KeepTogether(section_elements))
                    
                    conn.close()
                    
                    # Gerar PDF
                    doc.build(elements)
                    
                    # Preparar download
                    pdf_data = buffer.getvalue()
                    buffer.close()
                    
                    # Ao finalizar, limpar a mensagem de "Gerando..." e mostrar o botão de download
                    msg_placeholder.empty()  # Limpa a mensagem anterior
                    with msg_placeholder.container():
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_data,
                            file_name="resultados.pdf",
                            mime="application/pdf"
                        )
                        st.success("PDF gerado com sucesso!")
                    
                except Exception as e:
                    msg_placeholder.error(f"Erro ao gerar PDF: {str(e)}")
                    st.write("Debug: Stack trace completo:", traceback.format_exc())
                    
    except Exception as e:
        st.error(f"Erro ao gerar interface: {str(e)}")

def show_results():
    """
    Função principal para exibir a página de resultados
    """
    conn = None
    try:
        if 'user_id' not in st.session_state:
            st.error("Usuário não está logado!")
            return
            
        user_id = st.session_state.user_id
        
        # Estabelece conexão com retry
        for _ in range(3):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=20)
                cursor = conn.cursor()
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    time.sleep(1)
                    continue
                raise e
        else:
            st.error("Não foi possível conectar ao banco de dados. Tente novamente.")
            return

        # 1. Verifica se usuário tem dados em forms_tab
        verificar_dados_usuario(cursor, user_id)
        
        # 2. Atualiza todas as fórmulas e verifica o resultado
        if not atualizar_formulas(cursor, user_id):
            st.error("Erro ao atualizar fórmulas!")
            return

        # 3. Verifica/inicializa dados em forms_resultados
        new_user(cursor, user_id)
        conn.commit()
        
        # 4. Registra acesso à página
        registrar_acesso(
            user_id,
            "resultados",
            "Acesso na simulação Resultados"
        )

        # Adiciona o subtítulo antes do conteúdo principal
        subtitulo()
        
        # Configuração para esconder elementos durante a impressão e controlar quebra de página
        hide_streamlit_style = """
            <style>
                @media print {
                    [data-testid="stSidebar"] {
                        display: none !important;
                    }
                    .stApp {
                        margin: 0;
                        padding: 0;
                    }
                    #MainMenu {
                        display: none !important;
                    }
                    .page-break {
                        page-break-before: always !important;
                    }
                }
            </style>
        """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)
        
        # Buscar todos os elementos ordenados por row e col
        cursor.execute("""
            SELECT name_element, type_element, math_element, msg_element,
                   value_element, select_element, str_element, e_col, e_row,
                   section, user_id
            FROM forms_resultados
            WHERE (type_element = 'titulo' OR type_element = 'pula linha' 
                  OR type_element = 'call_dados' OR type_element = 'grafico'
                  OR type_element = 'tabela')
            AND user_id = ?
            ORDER BY e_row, e_col
        """, (user_id,))
        
        elements = cursor.fetchall()
        
        # Contador para gráficos
        grafico_count = 0
        
        # Agrupar elementos por e_row
        row_elements = {}
        for element in elements:
            e_row = element[8]  # e_row do elemento
            if e_row not in row_elements:
                row_elements[e_row] = []
            row_elements[e_row].append(element)
        
        # Processar elementos por linha
        for e_row in sorted(row_elements.keys()):
            # Criar container para cada linha
            with st.container():
                col1, col2 = st.columns(2)
                
                # Processar elementos desta linha
                for element in row_elements[e_row]:
                    e_col = element[7]  # e_col do elemento
                    
                    # Elementos da coluna 1 (e_col <= 3)
                    if e_col <= 3:
                        with col1:
                            if element[1] == 'grafico':
                                grafico_count += 1
                                grafico_barra(cursor, element)
                                if grafico_count == 2:
                                    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
                            else:
                                if element[1] == 'titulo':
                                    titulo(cursor, element)
                                elif element[1] == 'pula linha':
                                    pula_linha(cursor, element)
                                elif element[1] == 'call_dados':
                                    call_dados(cursor, element)
                                elif element[1] == 'tabela':
                                    tabela_dados(cursor, element)
                    
                    # Elementos da coluna 2 (e_col > 3)
                    else:
                        with col2:
                            if element[1] == 'grafico':
                                grafico_count += 1
                                grafico_barra(cursor, element)
                                if grafico_count == 2:
                                    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
                            else:
                                if element[1] == 'titulo':
                                    titulo(cursor, element)
                                elif element[1] == 'pula linha':
                                    pula_linha(cursor, element)
                                elif element[1] == 'call_dados':
                                    call_dados(cursor, element)
                                elif element[1] == 'tabela':
                                    tabela_dados(cursor, element)
        
    except Exception as e:
        print(f"ERRO em show_results: {str(e)}")
        st.error(f"Erro ao carregar resultados: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    show_results()

