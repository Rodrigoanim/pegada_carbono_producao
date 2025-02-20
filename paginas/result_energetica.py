# Arquivo: result_energetica.py
# Data: 16/02/2025 20:00
# Pagina de Análise Energética - Torrefação

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

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
    Cria registros iniciais para um novo usuário na tabela forms_energetica,
    copiando os dados do template (user_id = 0)
    """
    try:
        # Verifica se já existem registros para o usuário
        cursor.execute("""
            SELECT COUNT(*) FROM forms_energetica 
            WHERE user_id = ?
        """, (user_id,))
        
        if cursor.fetchone()[0] == 0:
            # Copia dados do template (user_id = 0) para o novo usuário
            cursor.execute("""
                INSERT INTO forms_energetica (
                    user_id, name_element, type_element, math_element,
                    msg_element, value_element, select_element, str_element,
                    e_col, e_row, section
                )
                SELECT 
                    ?, name_element, type_element, math_element,
                    msg_element, value_element, select_element, str_element,
                    e_col, e_row, section
                FROM forms_energetica
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
            cursor.execute("""
                SELECT value_element 
                FROM forms_tab 
                WHERE name_element = ? 
                AND user_id = ?
                ORDER BY ID_element DESC
                LIMIT 1
            """, (str_value, user_id))
            
            result = cursor.fetchone()
            
            if result:
                value = result[0]
                
                cursor.execute("""
                    UPDATE forms_energetica 
                    SET value_element = ? 
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
    Cria um gráfico de barras verticais com dados da tabela forms_energetica.
    
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
                FROM forms_energetica 
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
                FROM forms_energetica 
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
    Cria uma tabela estilizada com dados da tabela forms_energetica.
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
                FROM forms_energetica 
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
            color: #4A4A4A;
            margin-top: 4px;
            margin-bottom: 25px;
            font-family: sans-serif;
            font-weight: 500;
        '>Análise Energética - Torrefação</h2>
    """, unsafe_allow_html=True)

def show_results():
    """
    Função principal para exibir a página de resultados com layout em duas colunas
    """
    try:
        if 'user_id' not in st.session_state:
            st.error("Usuário não está logado!")
            return
            
        user_id = st.session_state.user_id
        
        # Adiciona o subtítulo no início da página
        subtitulo()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Garante que existam dados para o usuário
        new_user(cursor, user_id)
        
        # Buscar todos os elementos ordenados por row e col
        cursor.execute("""
            SELECT name_element, type_element, math_element, msg_element,
                   value_element, select_element, str_element, e_col, e_row,
                   section, user_id
            FROM forms_energetica
            WHERE (type_element = 'titulo' OR type_element = 'pula linha' 
                  OR type_element = 'call_dados' OR type_element = 'grafico'
                  OR type_element = 'tabela' OR type_element = 'grafico_ae'
                  OR type_element = 'tabela_ae')
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
                            elif element[1] == 'grafico_ae':
                                grafico_ae(cursor, element)
                            elif element[1] == 'tabela_ae':
                                tabela_ae(cursor, element)
                    
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
                            elif element[1] == 'grafico_ae':
                                grafico_ae(cursor, element)
                            elif element[1] == 'tabela_ae':
                                tabela_ae(cursor, element)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Erro ao carregar resultados: {str(e)}")

def grafico_ae(cursor, element):
    """
    Cria um gráfico de barras agrupadas para análise energética com 3 conjuntos de dados.
    
    Args:
        cursor: Conexão com o banco de dados
        element: Tupla com os dados do elemento tipo 'grafico_ae'
        
    Configurações do elemento:
        type_element: 'grafico_ae'
        msg_element: título do gráfico
        math_element: número de colunas por conjunto
        select_element: grupos de type_names separados por | (ex: 'N1,N2,N3,N4|M1,M2,M3,M4|T1,T2,T3,T4')
        str_element: rótulos separados por | (ex: 'Demanda elétrica|Demanda térmica|Total')
    """
    try:
        type_elem = element[1]   # type_element
        msg = element[3]         # msg_element
        select = element[5]      # select_element
        rotulos = element[6]     # str_element
        user_id = element[10]    # user_id
        
        if type_elem != 'grafico_ae':
            return
            
        # Validações iniciais
        if not select or not rotulos:
            st.error("Configuração incompleta do gráfico: select ou rótulos vazios")
            return
            
        # Separa os grupos de dados e rótulos
        grupos_dados = [grupo.split(',') for grupo in select.split('|')]
        categorias = rotulos.split('|')
        
        # Define as séries de dados (Simulação, Menor valor setorial, etc.)
        series = ['Simulação da Empresa', 'Menor valor setorial', 'Média setorial', 'Maior valor setorial']
        
        # Dicionário para armazenar os valores
        dados = {serie: [] for serie in series}
        
        # Busca os valores para cada grupo
        for grupo in grupos_dados:
            for i, type_name in enumerate(grupo):
                cursor.execute("""
                    SELECT value_element 
                    FROM forms_energetica 
                    WHERE name_element = ? 
                    AND user_id = ?
                    ORDER BY ID_element DESC
                    LIMIT 1
                """, (type_name.strip(), user_id))
                
                result = cursor.fetchone()
                valor = result[0] if result and result[0] is not None else 0.0
                dados[series[i]].append(valor)
        
        # Criar DataFrame para o plotly
        df_data = []
        cores = ['#B2D3C2', '#D7A9A9', '#B0E0E6', '#C4A484']  # Novas cores personalizadas
        
        for i, serie in enumerate(series):
            for j, categoria in enumerate(categorias):
                df_data.append({
                    'Categoria': categoria,
                    'Valor': dados[serie][j],
                    'Série': serie
                })
        
        df = pd.DataFrame(df_data)
        
        # Criar o gráfico usando plotly express
        fig = px.bar(
            df,
            x='Categoria',
            y='Valor',
            color='Série',
            barmode='group',
            text=df['Valor'].apply(lambda x: format_br_number(x)),
            title=None,
            color_discrete_sequence=cores  # Aplicando as novas cores
        )
        
        # Configurar o layout
        fig.update_layout(
            xaxis_title=None,
            yaxis_title="MJ/1000kg de café",
            height=500,
            width=None,
            legend_title=None,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(
                tickfont=dict(size=14),
                title_font=dict(size=16)
            ),
            yaxis=dict(
                tickfont=dict(size=14),
                title_font=dict(size=16),
                tickformat=",.",
                separatethousands=True
            ),
            margin=dict(t=60, b=100)  # Aumenta margem inferior para legenda
        )
        
        # Configurar o texto nas barras
        fig.update_traces(
            textposition='auto',
            textfont=dict(size=12)
        )
        
        # Adicionar o título
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
        
        # Exibir o gráfico
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    except Exception as e:
        st.error(f"Erro ao criar gráfico AE: {str(e)}")

def tabela_ae(cursor, element):
    """
    Cria uma tabela estilizada para análise energética com 3 conjuntos de dados.
    Busca os cabeçalhos da tabela do registro tabela_ae.
    """
    try:
        type_elem = element[1]   # type_element
        msg = element[3]         # msg_element
        select = element[5]      # select_element
        str_value = element[6]   # str_element (cabeçalhos da tabela)
        user_id = element[10]    # user_id
        
        if type_elem != 'tabela_ae':
            return
            
        # Validações iniciais
        if not select or not str_value:
            st.error("Configuração incompleta da tabela: select ou str_element vazios")
            return
            
        # Separa os grupos de dados
        grupos_dados = [grupo.split(',') for grupo in select.split('|')]
        
        # Usa os cabeçalhos definidos no str_element do próprio elemento tabela_ae
        categorias = str_value.split('|')
        
        # Define as séries de dados
        series = ['Simulação da Empresa', 'Menor valor setorial', 'Média setorial', 'Maior valor setorial']
        
        # Lista para armazenar os valores
        dados = []
        
        # Busca os valores para cada grupo
        for grupo in grupos_dados:
            valores_grupo = []
            for type_name in grupo:
                cursor.execute("""
                    SELECT value_element 
                    FROM forms_energetica 
                    WHERE name_element = ? 
                    AND user_id = ?
                    ORDER BY ID_element DESC
                    LIMIT 1
                """, (type_name.strip(), user_id))
                
                result = cursor.fetchone()
                valor = format_br_number(result[0]) if result and result[0] is not None else '0,00'
                valores_grupo.append(valor)
            dados.append(valores_grupo)

        # Criar três colunas, usando a do meio para a tabela
        col1, col2, col3 = st.columns([1, 8, 1])
        
        with col2:
            # Título da tabela
            st.markdown(f"<h4 style='text-align: left; margin-top: 20px; margin-bottom: 10px;'>{msg}</h4>", unsafe_allow_html=True)
            
            # Criar DataFrame com os cabeçalhos dinâmicos
            df_dict = {'Indicadores': series}
            for i, categoria in enumerate(categorias):
                df_dict[categoria] = [dados[i][j] for j in range(4)]
            
            df = pd.DataFrame(df_dict)
            
            # Aplicar estilo ao DataFrame
            styled_df = df.style.set_properties(**{
                'background-color': 'white',
                'border': '1px solid #dee2e6',
                'text-align': 'right',
                'padding': '10px 12px',
                'font-size': '14px'
            }).set_properties(subset=['Indicadores'], **{
                'text-align': 'left'
            }).set_table_styles([
                {'selector': 'thead',
                 'props': [('background-color', '#e8f5e9'),  # Cabeçalho verde claro
                          ('font-weight', 'bold'),
                          ('border-bottom', '2px solid #dee2e6'),
                          ('font-size', '18px')]},
                {'selector': 'tbody tr',
                 'props': [('background-color', 'white')]},  # Todas as linhas brancas
                {'selector': 'td',
                 'props': [('border-bottom', '1px solid #dee2e6')]},
            ]).hide(axis='index')  # Remove a coluna de índice
            
            # Exibir a tabela estilizada
            st.table(styled_df)
            
            # Espaçamento após a tabela
            st.markdown("<br>", unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erro ao criar tabela AE: {str(e)}")

if __name__ == "__main__":
    show_results()

