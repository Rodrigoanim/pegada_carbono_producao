# Arquivo: resultados.py
# Data: 17/02/2025 19:00
# Pagina de resultados - Dashboard

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from datetime import date
from io import BytesIO
import tempfile
import matplotlib.pyplot as plt

# Nome do banco de dados
DB_NAME = "calcpc.db"

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

def subtitulo():
    """
    Exibe um subtítulo centralizado com estilo personalizado
    """
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

def generate_pdf_report(cursor, user_id):
    """
    Gera um relatório PDF com os dados e gráficos dos resultados em layout de duas colunas.
    Agrupa elementos pelo e_row para manter tabela e gráfico juntos.
    """
    try:
        # Buscar informações do usuário
        cursor.execute("""
            SELECT nome, empresa FROM usuarios WHERE id = ?
        """, (user_id,))
        user_data = cursor.fetchone()
        user_name = user_data[0] if user_data else "Usuário"
        company_name = user_data[1] if user_data else "Empresa"

        # Inicializar PDF em modo paisagem
        pdf = FPDF(orientation='L')
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 14)  # Fonte em negrito para o título

        # Cabeçalho do relatório
        pdf.cell(280, 10, txt="Simulador da Pegada de Carbono do Café Torrado", ln=True, align="L")
        
        # Adiciona o subtítulo
        pdf.set_font("Helvetica", 'B', 12)  # Fonte um pouco menor para o subtítulo
        pdf.cell(280, 10, txt="Resultados das Simulações da Empresa", ln=True, align="L")
        
        # Informações do usuário
        pdf.set_font("Helvetica", size=12)  # Volta para a fonte normal
        pdf.cell(280, 10, txt=f"Usuário: {user_name} | Empresa: {company_name}", ln=True, align="L")
        pdf.cell(280, 10, txt=f"Data: {date.today().strftime('%d/%m/%Y')}", ln=True, align="L")

        # Buscar dados ordenados por e_row
        cursor.execute("""
            SELECT name_element, type_element, msg_element, value_element, 
                   select_element, str_element, section, e_col, e_row
            FROM forms_resultados
            WHERE type_element IN ('tabela', 'grafico')
            AND user_id = ?
            ORDER BY e_row, e_col
        """, (user_id,))
        
        elements = cursor.fetchall()

        # Agrupar elementos por e_row
        rows = {}
        for elem in elements:
            e_row = elem[8]  # e_row
            if e_row not in rows:
                rows[e_row] = []
            rows[e_row].append(elem)

        # Processar cada linha
        for e_row, row_elements in rows.items():
            if len(row_elements) >= 2:
                tabela = next((e for e in row_elements if e[1] == 'tabela'), None)
                grafico = next((e for e in row_elements if e[1] == 'grafico'), None)

                if tabela and grafico:
                    # Adicionar título da seção
                    pdf.set_font("Helvetica", 'B', 14)
                    pdf.cell(280, 10, txt=tabela[2], ln=True, align="C")  # msg_element da tabela
                    pdf.set_font("Helvetica", size=10)

                    # Configurar posições iniciais
                    y_start = pdf.get_y() + 10
                    x_table = 10
                    x_graph = 150

                    # Processar tabela (lado esquerdo)
                    pdf.set_xy(x_table, y_start)
                    select_values = tabela[4].split('|')
                    labels = tabela[5].split('|')
                    
                    # Cabeçalho da tabela
                    pdf.cell(70, 10, "Descrição", 1)
                    pdf.cell(60, 10, "Valor", 1)
                    pdf.ln()

                    # Dados da tabela
                    for type_name, label in zip(select_values, labels):
                        pdf.set_x(x_table)
                        cursor.execute("""
                            SELECT value_element 
                            FROM forms_resultados 
                            WHERE name_element = ? AND user_id = ?
                            ORDER BY ID_element DESC LIMIT 1
                        """, (type_name.strip(), user_id))
                        
                        result = cursor.fetchone()
                        value = format_br_number(result[0]) if result and result[0] is not None else '0,00'
                        
                        pdf.cell(70, 10, label, 1)
                        pdf.cell(60, 10, value, 1)
                        pdf.ln()

                    # Processar gráfico (lado direito)
                    select_values = grafico[4].split('|')
                    labels = grafico[5].split('|')
                    valores = []
                    cores = grafico[6].split('|') if grafico[6] else ['#1f77b4'] * len(labels)  # Usa section para cores

                    for type_name in select_values:
                        cursor.execute("""
                            SELECT value_element 
                            FROM forms_resultados 
                            WHERE name_element = ? AND user_id = ?
                            ORDER BY ID_element DESC LIMIT 1
                        """, (type_name.strip(), user_id))
                        
                        result = cursor.fetchone()
                        valor = float(result[0]) if result and result[0] is not None else 0.0
                        valores.append(valor)

                    # Gerar gráfico com cores da coluna section
                    plt.figure(figsize=(8, 8))
                    plt.bar(labels, valores, color=cores)
                    plt.title(grafico[2])
                    plt.xticks(rotation=45)
                    plt.tight_layout()

                    # Salvar gráfico temporariamente
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
                        plt.close()
                        pdf.image(temp_file.name, x=x_graph, y=y_start, w=120)

                    # Adicionar nova página para a próxima seção
                    pdf.add_page()

        # Retornar PDF como bytes
        return pdf.output(dest='S').encode('latin-1')

    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None

def show_results():
    """
    Função principal para exibir a página de resultados com layout em duas colunas
    """
    try:
        if 'user_id' not in st.session_state:
            st.error("Usuário não está logado!")
            return
            
        user_id = st.session_state.user_id
        
        # Adiciona o subtítulo antes do conteúdo principal
        subtitulo()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Adicionar botão para gerar PDF
        if st.button("Gerar Relatório PDF"):
            pdf_content = generate_pdf_report(cursor, user_id)
            if pdf_content:
                st.download_button(
                    label="Baixar Relatório PDF",
                    data=pdf_content,
                    file_name=f"relatorio_resultados_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

        # Garante que existam dados para o usuário
        new_user(cursor, user_id)
        
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
                            if element[1] == 'titulo':
                                titulo(cursor, element)
                            elif element[1] == 'pula linha':
                                pula_linha(cursor, element)
                            elif element[1] == 'call_dados':
                                call_dados(cursor, element)
                            elif element[1] == 'grafico':
                                grafico_barra(cursor, element)
                            elif element[1] == 'tabela':
                                tabela_dados(cursor, element)
                    
                    # Elementos da coluna 2 (e_col > 3)
                    else:
                        with col2:
                            if element[1] == 'titulo':
                                titulo(cursor, element)
                            elif element[1] == 'pula linha':
                                pula_linha(cursor, element)
                            elif element[1] == 'call_dados':
                                call_dados(cursor, element)
                            elif element[1] == 'grafico':
                                grafico_barra(cursor, element)
                            elif element[1] == 'tabela':
                                tabela_dados(cursor, element)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Erro ao carregar resultados: {str(e)}")

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

if __name__ == "__main__":
    show_results()

