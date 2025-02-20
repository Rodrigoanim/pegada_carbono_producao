# Arquivo: crude.py
# Data: 16/02/2025  16:45
# IDE Cursor - claude 3.5 sonnet
# Campos editáveis / forms_setorial_sea

import streamlit as st
import pandas as pd
import sqlite3

# Nome do banco de dados
DB_NAME = "calcpc.db"

def format_br_number(value):
    """Formata um número para o padrão brasileiro."""
    try:
        if pd.isna(value) or value == '':
            return ''
        return f"{float(str(value).replace(',', '.')):.2f}".replace('.', ',')
    except:
        return ''

def get_table_analysis(cursor, table_name):
    """Analisa a estrutura e dados da tabela."""
    # Análise da estrutura
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    
    # Contagem de registros
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    record_count = cursor.fetchone()[0]
    
    # Data da última atualização (assumindo que existe uma coluna 'data' ou similar)
    try:
        cursor.execute(f"SELECT MAX(data) FROM {table_name}")
        last_update = cursor.fetchone()[0]
    except:
        last_update = "N/A"
    
    # Maior user_id
    try:
        cursor.execute(f"SELECT MAX(user_id) FROM {table_name}")
        max_user_id = cursor.fetchone()[0]
    except:
        max_user_id = "N/A"
    
    return {
        "columns": columns_info,
        "record_count": record_count,
        "last_update": last_update,
        "max_user_id": max_user_id
    }

def show_crud():
    """Exibe registros administrativos em formato de tabela."""
    st.title("Lista de Registros ADM")
    
    if st.button("Atualizar Dados"):
        st.rerun()
    
    # Atualiza a lista de tabelas para incluir a tabela de usuários
    tables = ["", "usuarios", "forms_tab", "forms_insumos", "forms_resultados", 
              "forms_result_sea", "forms_setorial", "forms_setorial_sea", "forms_energetica"]
    
    selected_table = st.selectbox("Selecione a tabela", tables, key="table_selector")
    
    if selected_table:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # Verifica se é a tabela de usuários para tratamento especial da senha
            is_user_table = selected_table == "usuarios"
            
            # Análise da tabela
            analysis = get_table_analysis(cursor, selected_table)
            
            # Exibe informações da tabela em um expander
            with st.expander("Informações da Tabela", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Registros", analysis["record_count"])
                with col2:
                    st.metric("Última Atualização", analysis["last_update"])
                with col3:
                    st.metric("Maior User ID", analysis["max_user_id"])
                
                # Exibe estrutura da tabela
                st.write("### Estrutura da Tabela")
                structure_df = pd.DataFrame(
                    analysis["columns"],
                    columns=["cid", "name", "type", "notnull", "dflt_value", "pk"]
                )
                st.dataframe(
                    structure_df[["name", "type", "notnull", "pk"]],
                    hide_index=True,
                    use_container_width=True
                )
            
            # Busca dados
            cursor.execute(f"SELECT * FROM {selected_table}")
            data = cursor.fetchall()
            
            # Busca nomes das colunas e tipos
            cursor.execute(f"PRAGMA table_info({selected_table})")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]
            
            # Cria DataFrame
            df = pd.DataFrame(data, columns=columns)
            
            # Configura o tipo de cada coluna baseado no tipo do SQLite
            column_config = {}
            for col_info in columns_info:
                col_name = col_info[1]
                col_type = col_info[2].upper()
                
                # Configuração especial para a tabela de usuários
                if is_user_table:
                    if col_name == "perfil":
                        column_config[col_name] = st.column_config.SelectboxColumn(
                            "perfil",
                            width="medium",
                            required=True,
                            options=["adm", "usuario", "Gestor"]
                        )
                    elif col_name == "email":
                        column_config[col_name] = st.column_config.TextColumn(
                            "email",
                            width="medium",
                            required=True
                        )
                    else:
                        if 'INTEGER' in col_type:
                            column_config[col_name] = st.column_config.NumberColumn(
                                col_name,
                                width="medium",
                                required=True,
                            )
                        else:
                            column_config[col_name] = st.column_config.TextColumn(
                                col_name,
                                width="medium",
                                required=True
                            )
                else:
                    # Configuração padrão para outras tabelas
                    if 'INTEGER' in col_type:
                        column_config[col_name] = st.column_config.NumberColumn(
                            col_name,
                            width="medium",
                            required=True,
                        )
                    elif 'REAL' in col_type:
                        column_config[col_name] = st.column_config.NumberColumn(
                            col_name,
                            width="medium",
                            required=True,
                        )
                    else:
                        column_config[col_name] = st.column_config.TextColumn(
                            col_name,
                            width="medium",
                            required=True
                        )
            
            # Converte para formato editável
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                hide_index=False,
                key=f"editor_{selected_table}"
            )
            
            # Botão para salvar alterações
            if st.button("Salvar Alterações"):
                try:
                    # Detecta mudanças
                    if not edited_df.equals(df):
                        # Atualiza o banco de dados
                        for index, row in edited_df.iterrows():
                            update_query = f"""
                            UPDATE {selected_table}
                            SET {', '.join(f'{col} = ?' for col in columns)}
                            WHERE rowid = {index + 1}
                            """
                            cursor.execute(update_query, tuple(row))
                        
                        conn.commit()
                        st.success("Alterações salvas com sucesso!")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao salvar alterações: {str(e)}")
            
            # Botão de download - convertendo ponto para vírgula na coluna value
            if not df.empty:
                export_df = edited_df.copy()
                
                # Procura pela coluna que contém 'value' no nome
                value_columns = [col for col in export_df.columns if 'value' in col.lower()]
                
                # Converte os números para string e substitui ponto por vírgula
                for value_col in value_columns:
                    export_df[value_col] = export_df[value_col].apply(lambda x: str(x).replace('.', ',') if pd.notnull(x) else '')
                
                # Desativa a formatação automática do pandas para números
                txt_data = export_df.to_csv(sep='\t', index=False, encoding='cp1252', float_format=None)
                st.download_button(
                    label="Download TXT",
                    data=txt_data.encode('cp1252'),
                    file_name=f"{selected_table}.txt",
                    mime="text/plain"
                )
        
        except Exception as e:
            st.error(f"Erro ao processar dados: {str(e)}")
        
        finally:
            conn.close()

# Remover ou comentar a função app() se não estiver sendo usada
# def app():
#     """Função principal que será chamada pelo main.py"""
#     show_admin_records()
