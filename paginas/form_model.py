# Arquivo: form_model.py
# Data: 21/02/2025 - Hora: 14:30
# CursorAI - claude 3.5 sonnet 
# Adaptação para o uso de Discos SSD e a pasta Data para o banco de dados
# Rotina de coleta de logs de acesso ao sistema

import sqlite3
import streamlit as st
import pandas as pd
import re

from config import DB_PATH
from paginas.monitor import registrar_acesso  # Ajustado para incluir o caminho completo

MAX_COLUMNS = 5  # Número máximo de colunas no layout

def date_to_days(date_str):
    """
    Converte uma data no formato dd/mm/aaaa para número de dias desde 01/01/1900
    """
    try:
        if not date_str:
            return 0
            
        dia, mes, ano = map(int, date_str.split('/'))
        
        # Validação básica da data
        if not (1900 <= ano <= 2100 and 1 <= mes <= 12 and 1 <= dia <= 31):
            return 0
            
        # Cálculo dos dias
        # Anos completos desde 1900
        days = (ano - 1900) * 365
        
        # Adiciona dias dos anos bissextos
        leap_years = sum(1 for y in range(1900, ano) if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0))
        days += leap_years
        
        # Dias dos meses completos no ano atual
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0):
            days_in_month[2] = 29
            
        days += sum(days_in_month[1:mes])
        
        # Adiciona dias do mês atual
        days += dia - 1
        
        return days
    except Exception as e:
        st.error(f"Erro na conversão de data: {str(e)}")
        return 0

def get_element_value(cursor, name_element, element=None):
    """Busca o valor de um elemento na tabela forms_tab."""
    cursor.execute("""
        SELECT value_element 
        FROM forms_tab 
        WHERE name_element = ? AND user_id = ?
    """, (name_element, st.session_state.user_id))
    result = cursor.fetchone()
    if result and result[0] is not None:
        return float(result[0])  # Valor já está como REAL no banco
    return 0.0

def calculate_formula(formula, values, cursor):
    """
    Calcula o resultado de uma fórmula com suporte a operações matemáticas e datas.
    """
    try:
        # Se a fórmula for um número direto
        if isinstance(formula, (int, float)):
            return float(formula)
        
        # Se for string numérica
        if isinstance(formula, str):
            formula = formula.replace(',', '.')
            if formula.replace('.','',1).isdigit():
                return float(formula)
        
        # Processa referências de diferentes abas
        processed_formula = str(formula)
        
        # Verifica se é uma fórmula de data (mantém lógica existente)
        if re.match(r'^\s*[A-Z][0-9]+\s*-\s*[A-Z][0-9]+\s*$', processed_formula):
            # Extrai as duas referências
            refs = re.findall(r'[A-Z][0-9]+', processed_formula)
            if len(refs) == 2:
                # Inverte a ordem das referências para garantir data_final - data_inicial
                data_final = refs[0]  # B2
                data_inicial = refs[1]  # A2
                
                # Busca as datas no banco
                cursor.execute("""
                    SELECT str_element 
                    FROM forms_tab 
                    WHERE name_element = ? AND user_id = ?
                """, (data_final, st.session_state.user_id))
                result = cursor.fetchone()
                data_final_str = result[0] if result and result[0] else None
                
                cursor.execute("""
                    SELECT str_element 
                    FROM forms_tab 
                    WHERE name_element = ? AND user_id = ?
                """, (data_inicial, st.session_state.user_id))
                result = cursor.fetchone()
                data_inicial_str = result[0] if result and result[0] else None
                
                # Converte as datas para dias
                dias_final = date_to_days(data_final_str)
                dias_inicial = date_to_days(data_inicial_str)
                
                # Calcula a diferença em dias
                diff_dias = dias_final - dias_inicial
                
                # Converte para meses (usando média mais precisa de dias por mês)
                meses = diff_dias / 30.44
                
                return max(0, meses)  # Garante que não retorne valor negativo
        
        # Processa referências na fórmula
        cell_refs = re.findall(r'(?:Insumos!)?[A-Z]{1,2}[0-9]+', processed_formula)
        
        for ref in cell_refs:
            float_value = get_element_value(
                cursor, 
                ref, 
                st.session_state.user_id if not ref.startswith('Insumos!') else None
            )
            processed_formula = re.sub(r'\b' + re.escape(ref) + r'\b', str(float_value), processed_formula)
        
        # Substitui vírgulas por pontos antes do eval
        processed_formula = processed_formula.replace(',', '.')
        result = eval(processed_formula)
        return float(result)
        
    except Exception as e:
        st.error(f"Erro no cálculo da fórmula: {str(e)}")
        return 0.0

def process_conditional_element(cursor, element):
    """
    Processa elemento do tipo 'condicao' seguindo a lógica especificada.
    """
    try:
        name = element[0]
        math_ref = element[2]
        select_pairs = element[5]
        
        cursor.execute("""
            SELECT str_element 
            FROM forms_tab 
            WHERE name_element = ? AND user_id = ?
        """, (math_ref, st.session_state.user_id))
        
        ref_result = cursor.fetchone()
        if not ref_result or not ref_result[0]:
            return 0.0
            
        selected_value = ref_result[0].strip()
        pairs = [pair.strip() for pair in select_pairs.split('|')]
        
        for pair in pairs:
            condition, target = pair.split(':')
            condition = condition.strip()
            target = target.strip()
            
            if condition == selected_value:
                cursor.execute("""
                    SELECT math_element 
                    FROM forms_insumos 
                    WHERE name_element = ?
                """, (target,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    try:
                        math_value = result[0]
                        if '/' in math_value:
                            num, den = map(float, math_value.split('/'))
                            final_value = num / den
                        else:
                            final_value = float(math_value)
                        
                        # Atualiza o banco com valor REAL
                        cursor.execute("""
                            UPDATE forms_tab 
                            SET value_element = ? 
                            WHERE name_element = ? AND user_id = ?
                        """, (final_value, name, st.session_state.user_id))
                        
                        return final_value
                        
                    except ValueError:
                        return 0.0
                    
        return 0.0
        
    except Exception as e:
        st.error(f"Erro ao processar condição: {str(e)}")
        return 0.0

def titulo(cursor, element):
    """
    Exibe títulos formatados na interface com base nos valores do banco de dados.
    """
    try:
        name, msg, col, row, str_value = element[0], element[3], element[7], element[8], element[6]
        type_elem = element[1]  # type_element
        
        # Verifica se a coluna é válida
        if col > 6:
            st.error(f"Posição de coluna inválida para o título {name}: {col}. Deve ser entre 1 e 6.")
            return
        
        # Se for do tipo 'titulo', usa o str_element do próprio registro
        if type_elem == 'titulo':
            if str_value:
                formatted_msg = f"{str_value.replace('✅ Operação concluída com sucesso!', msg)}"
                st.markdown(formatted_msg, unsafe_allow_html=True)
                return
        
        # Para os demais casos
        if str_value and not "Operação concluída" in str_value:
            st.markdown(str_value, unsafe_allow_html=True)
            st.markdown(msg, unsafe_allow_html=True)
        else:
            st.markdown(msg, unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Erro ao processar título: {str(e)}")

def new_user(cursor, user_id):
    """
    Inicializa registros para um novo usuário copiando dados do user_id 0.
    Mantém a seção original dos registros ao copiar.
    """
    try:
        # Verifica se já existem registros para o usuário
        cursor.execute("""
            SELECT COUNT(*) FROM forms_tab WHERE user_id = ?
        """, (user_id,))
        
        if cursor.fetchone()[0] > 0:
            return  # Usuário já tem registros
            
        # Copia registros do user_id 0 mantendo a seção original
        cursor.execute("""
            INSERT INTO forms_tab (
                name_element, type_element, math_element, msg_element,
                value_element, select_element, str_element, e_col, e_row,
                section, user_id
            )
            SELECT 
                name_element, type_element, math_element, msg_element,
                value_element, select_element, str_element, e_col, e_row,
                section, ? as user_id
            FROM forms_tab 
            WHERE user_id = 0
        """, (user_id,))
        
        st.success(f"Registros iniciais criados para o usuário {user_id}")
        
    except Exception as e:
        st.error(f"Erro ao criar registros para novo usuário: {str(e)}")
        raise

def process_forms_tab(section='cafe'):
    """
    Processa registros da tabela forms_tab e exibe em layout de grade.
    
    Args:
        section (str): Seção a ser exibida ('cafe', 'moagem' ou 'embalagem')
    """
    conn = None
    try:
        # Inicializa flag de log no session_state se não existir
        log_key = f"log_registered_{section}"
        if log_key not in st.session_state:
            st.session_state[log_key] = False
            
        # 1. Verifica se há um usuário logado
        if 'user_id' not in st.session_state:
            st.error("Usuário não está logado!")
            return
            
        # 2. Armazena user_id em variável
        user_id = st.session_state.user_id
        
        # Títulos com estilo baseados na seção
        titles = {
            'cafe': "## Página de Entrada de Dados - Tipo do Café",
            'moagem': "## Página de Entrada de Dados - Moagem e Torrefação",
            'embalagem': "## Página de Entrada de Dados - Embalagem"
        }
        st.markdown(titles.get(section, "## Página de Entrada de Dados"))
        
        # Inicializa session_state
        if 'form_values' not in st.session_state:
            st.session_state.form_values = {}
        
        # Conexão com o banco
        conn = sqlite3.connect(DB_PATH)  # Atualizado para usar DB_PATH
        cursor = conn.cursor()

        # 3. Garante que existam dados para o usuário
        new_user(cursor, user_id)
        conn.commit()

        # 4. Busca dados específicos do usuário logado e da seção atual
        cursor.execute("""
            SELECT name_element, type_element, math_element, msg_element,
                   value_element, select_element, str_element, e_col, e_row
            FROM forms_tab
            WHERE user_id = ? AND section = ?
            ORDER BY e_row, e_col
        """, (user_id, section))
        elements = cursor.fetchall()

        # Verifica se existem elementos para esta seção
        if not elements:
            st.warning(f"Nenhum elemento encontrado para a seção {section}")
            return

        # Agrupa elementos por linha
        rows = {}
        for element in elements:
            e_row = element[8]
            if e_row not in rows:
                rows[e_row] = []
            rows[e_row].append(element)

        # Processa cada linha
        for row_num in sorted(rows.keys()):
            row_elements = rows[row_num]
            
            # Processa elementos ocultos primeiro
            for element in row_elements:
                if element[1].endswith('H'):
                    name = element[0]
                    type_elem = element[1]
                    math_elem = element[2]
                    
                    if type_elem == 'formulaH':
                        result = calculate_formula(math_elem, st.session_state.form_values, cursor)
                        cursor.execute("""
                            UPDATE forms_tab 
                            SET value_element = ? 
                            WHERE name_element = ? AND user_id = ?
                        """, (result, name, st.session_state.user_id))
                        conn.commit()
                    elif type_elem == 'condicaoH':
                        result = process_conditional_element(cursor, element)
                        cursor.execute("""
                            UPDATE forms_tab 
                            SET value_element = ? 
                            WHERE name_element = ? AND user_id = ?
                        """, (result, name, st.session_state.user_id))
                        conn.commit()
                    elif type_elem == 'call_insumosH':
                        result = call_insumos(cursor, element)
                        cursor.execute("""
                            UPDATE forms_tab 
                            SET value_element = ? 
                            WHERE name_element = ? AND user_id = ?
                        """, (result, name, st.session_state.user_id))
                        conn.commit()
            
            # Verifica se há elementos visíveis na linha para criar o layout
            visible_elements = [e for e in row_elements if not e[1].endswith('H')]
            if not visible_elements:
                continue
                
            # Verifica se é uma linha de espaçamento
            if any(element[1] == 'pula_linha' for element in visible_elements):
                st.markdown("<br>", unsafe_allow_html=True)
                continue
            
            # Layout com colunas apenas para elementos visíveis
            cols = st.columns(MAX_COLUMNS)
            
            for element in visible_elements:
                name = element[0]
                type_elem = element[1]
                math_elem = element[2]
                msg = element[3]
                value = element[4]
                select_options = element[5]
                str_value = element[6]
                e_col = element[7] - 1  # Ajusta para índice 0-4
                
                # Verifica se a coluna está dentro do limite
                if e_col >= MAX_COLUMNS:
                    continue  # Pula silenciosamente elementos fora do limite

                with cols[e_col]:
                    try:
                        # Processa elementos do tipo título
                        if type_elem == 'titulo':
                            titulo(cursor, element)
                            continue

                        # Processa elementos ocultos
                        if type_elem.endswith('H'):
                            if type_elem == 'formulaH':
                                result = calculate_formula(math_elem, st.session_state.form_values, cursor)
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET value_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (result, name, st.session_state.user_id))
                                conn.commit()
                            elif type_elem == 'condicaoH':
                                result = process_conditional_element(cursor, element)
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET value_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (result, name, st.session_state.user_id))
                                conn.commit()
                            elif type_elem == 'call_insumosH':
                                result = call_insumos(cursor, element)
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET value_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (result, name, st.session_state.user_id))
                                conn.commit()
                            continue

                        # Processamento normal para elementos visíveis
                        if type_elem == 'selectbox':
                            options = [opt.strip() for opt in select_options.split('|')]
                            selected = st.selectbox(
                                msg,
                                options=options,
                                key=f"select_{name}_{row_num}_{e_col}",
                                index=options.index(str_value) if str_value in options else 0
                            )
                            
                            if selected != str_value:
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET str_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (selected, name, st.session_state.user_id))
                                conn.commit()
                                st.rerun()
                            
                            st.session_state.form_values[name] = 0.0

                        elif type_elem == 'call_insumos':
                            try:
                                result = call_insumos(cursor, element)
                                conn.commit()
                                
                                # Configurações de estilo para métricas
                                FONT_SIZES = {
                                    'small': '12px',
                                    'medium': '16px',
                                    'large': '20px',
                                    'xlarge': '24px'
                                }
                                
                                msg_parts = msg.split('|')
                                display_msg = msg_parts[0].strip()
                                font_size = 'medium'
                                
                                if len(msg_parts) > 1:
                                    for param in msg_parts[1:]:
                                        if param.startswith('size:'):
                                            requested_size = param.split(':')[1].strip()
                                            if requested_size in FONT_SIZES:
                                                font_size = requested_size

                                st.markdown(f"""
                                    <div style='text-align: left;'>
                                        <p style='font-size: {FONT_SIZES[font_size]}; margin-bottom: 0;'>{display_msg}</p>
                                        <p style='font-size: {FONT_SIZES[font_size]}; font-weight: bold;'>{result:.2f}</p>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                            except Exception as e:
                                st.error(f"Erro ao processar call_insumos: {str(e)}")

                        elif type_elem == 'input':
                            try:
                                # Converte o valor REAL do banco para exibição no formato BR
                                if value is not None:
                                    current_value = f"{float(value):.2f}".replace('.', ',')
                                else:
                                    current_value = "0,00"
                                
                                input_value = st.text_input(
                                    msg,
                                    value=current_value,
                                    key=f"input_{name}_{row_num}_{e_col}"
                                )
                                
                                try:
                                    # Remove pontos de milhar e converte vírgula para ponto
                                    cleaned_input = input_value.strip().replace('.', '').replace(',', '.')
                                    numeric_value = float(cleaned_input)
                                    
                                    # Compara valores como float
                                    if abs(numeric_value - float(value or 0)) > 1e-10:
                                        # Registra log apenas uma vez por seção
                                        if not st.session_state[log_key]:
                                            registrar_acesso(
                                                st.session_state.user_id,
                                                f"forms_{section}",
                                                f"Alteração em formulário de {section}"
                                            )
                                            st.session_state[log_key] = True
                                            
                                        cursor.execute("""
                                            UPDATE forms_tab 
                                            SET value_element = ? 
                                            WHERE name_element = ? AND user_id = ?
                                        """, (numeric_value, name, st.session_state.user_id))
                                        conn.commit()
                                        st.rerun()
                                    
                                    st.session_state.form_values[name] = numeric_value
                                    
                                except ValueError:
                                    st.error(f"Por favor, insira apenas números em {msg}")
                                    st.session_state.form_values[name] = float(value or 0)
                            
                            except Exception as e:
                                st.error(f"Erro ao processar input: {str(e)}")

                        elif type_elem == 'formula':
                            try:
                                # Configurações de estilo para métricas
                                FONT_SIZES = {
                                    'small': '12px',
                                    'medium': '16px',
                                    'large': '20px',
                                    'xlarge': '24px'
                                }
                                
                                msg_parts = msg.split('|')
                                display_msg = msg_parts[0].strip()
                                font_size = 'medium'
                                
                                if len(msg_parts) > 1:
                                    for param in msg_parts[1:]:
                                        if param.startswith('size:'):
                                            requested_size = param.split(':')[1].strip()
                                            if requested_size in FONT_SIZES:
                                                font_size = requested_size

                                result = calculate_formula(math_elem, st.session_state.form_values, cursor)
                                
                                # Atualiza o banco com valor REAL
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET value_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (result, name, st.session_state.user_id))
                                conn.commit()
                                
                                # Ajusta casas decimais baseado no valor
                                if abs(result) < 1 and result != 0:
                                    result_br = f"{result:.6f}".replace('.', ',')
                                else:
                                    result_br = f"{result:.2f}".replace('.', ',')
                                
                                st.markdown(f"""
                                    <div style='text-align: left;'>
                                        <p style='font-size: {FONT_SIZES[font_size]}; margin-bottom: 0;'>{display_msg}</p>
                                        <p style='font-size: {FONT_SIZES[font_size]}; font-weight: bold;'>{result_br}</p>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )

                            except Exception as e:
                                st.error(f"Erro ao processar fórmula: {str(e)}")

                        elif type_elem == 'condicao':
                            try:
                                # Configurações de estilo para métricas
                                FONT_SIZES = {
                                    'small': '12px',    # Fonte pequena
                                    'medium': '16px',   # Fonte média (padrão)
                                    'large': '20px',    # Fonte grande
                                    'xlarge': '24px'    # Fonte extra grande
                                }
                                
                                # Extrai o tamanho da fonte do msg_element (se existir)
                                # Formato esperado: "texto|size:small" ou apenas "texto"
                                msg_parts = msg.split('|')
                                display_msg = msg_parts[0].strip()
                                font_size = 'medium'  # Tamanho padrão
                                
                                # Processa parâmetros adicionais
                                if len(msg_parts) > 1:
                                    for param in msg_parts[1:]:
                                        if param.startswith('size:'):
                                            requested_size = param.split(':')[1].strip()
                                            if requested_size in FONT_SIZES:
                                                font_size = requested_size

                                # Processa o elemento condicional
                                result = process_conditional_element(cursor, element)
                                
                                # Converte resultado para formato BR antes de salvar
                                result_br = f"{result:.2f}".replace('.', ',')
                                
                                # Aplica estilo customizado usando HTML/CSS
                                st.markdown(f"""
                                    <div style='text-align: center;'>
                                        <p style='font-size: {FONT_SIZES[font_size]}; margin-bottom: 0;'>{display_msg}</p>
                                        <p style='font-size: {FONT_SIZES[font_size]}; font-weight: bold;'>{result_br}</p>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )

                            except Exception as e:
                                st.error(f"Erro ao processar condição: {str(e)}")

                        elif type_elem == 'input_data':
                            # Pega o valor atual do str_element
                            current_value = str_value if str_value else ''
                            
                            # Campo de entrada para data
                            input_value = st.text_input(
                                msg,
                                value=current_value,
                                key=f"input_data_{name}_{row_num}_{e_col}"
                            )
                            
                            # Validação do formato da data
                            if input_value:
                                # Regex para validar formato dd/mm/aaaa
                                date_pattern = r'^\d{2}/\d{2}/\d{4}$'
                                if not re.match(date_pattern, input_value):
                                    st.error(f"Por favor, insira a data no formato dd/mm/aaaa em {msg}")
                                else:
                                    # Validação adicional dos valores da data
                                    try:
                                        dia, mes, ano = map(int, input_value.split('/'))
                                        # Verifica se é uma data válida
                                        if (mes < 1 or mes > 12 or dia < 1 or dia > 31 or
                                            ano < 1900 or ano > 2100 or
                                            (mes in [4, 6, 9, 11] and dia > 30) or
                                            (mes == 2 and dia > 29)):
                                            st.error(f"Data inválida em {msg}")
                                        else:
                                            # Atualiza o banco apenas se o valor mudou
                                            if input_value != current_value:
                                                cursor.execute("""
                                                    UPDATE forms_tab 
                                                    SET str_element = ? 
                                                    WHERE name_element = ? AND user_id = ?
                                                """, (input_value, name, st.session_state.user_id))
                                                conn.commit()
                                                st.rerun()
                                    except ValueError:
                                        st.error(f"Data inválida em {msg}")
                            
                            # Mantém o value_element como 0 já que não é usado para datas
                            st.session_state.form_values[name] = '0.0'

                        elif type_elem == 'formula_data':
                            try:
                                # Configurações de estilo para métricas
                                FONT_SIZES = {
                                    'small': '12px',    # Fonte pequena
                                    'medium': '16px',   # Fonte média (padrão)
                                    'large': '20px',    # Fonte grande
                                    'xlarge': '24px'    # Fonte extra grande
                                }
                                
                                # Extrai o tamanho da fonte do msg_element (se existir)
                                msg_parts = msg.split('|')
                                display_msg = msg_parts[0].strip()
                                font_size = 'medium'  # Tamanho padrão
                                
                                # Processa parâmetros adicionais
                                if len(msg_parts) > 1:
                                    for param in msg_parts[1:]:
                                        if param.startswith('size:'):
                                            requested_size = param.split(':')[1].strip()
                                            if requested_size in FONT_SIZES:
                                                font_size = requested_size

                                # Calcula o resultado da fórmula de data
                                result = calculate_formula(math_elem, st.session_state.form_values, cursor)
                                
                                # Converte resultado para formato BR antes de salvar
                                result_br = f"{result:.0f}".replace('.', ',')
                                
                                # Atualiza o value_element no banco
                                cursor.execute("""
                                    UPDATE forms_tab 
                                    SET value_element = ? 
                                    WHERE name_element = ? AND user_id = ?
                                """, (result_br, name, st.session_state.user_id))
                                conn.commit()
                                
                                # Aplica estilo customizado usando HTML/CSS
                                st.markdown(f"""
                                    <div style='text-align: left;'>
                                        <p style='font-size: {FONT_SIZES[font_size]}; margin-bottom: 0;'>{display_msg}</p>
                                        <p style='font-size: {FONT_SIZES[font_size]}; font-weight: bold;'>{result_br}</p>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )

                            except Exception as e:
                                st.error(f"Erro ao processar fórmula de data: {str(e)}")

                    except Exception as e:
                        st.error(f"Erro ao processar {name}: {str(e)}")

        # Separador
        st.divider()

    except Exception as e:
        st.error(f"Erro ao processar formulário: {str(e)}")
    finally:
        if conn:
            conn.close()

def call_insumos(cursor, element):
    """
    Busca valor de referência na tabela forms_insumos e atualiza value_element.
    
    Args:
        cursor: Cursor do banco de dados SQLite
        element: Tupla contendo os dados do elemento (name, type, math, msg, value, select, str, col, row)
    
    Returns:
        float: Valor numérico encontrado ou 0.0 em caso de erro
    """
    try:
        name = element[0]  # name_element da forms_tab
        str_value = element[6]  # str_element da forms_tab (ex: 'InsumosI15')
        
        # Verifica se há uma referência válida
        if not str_value:
            return 0.0
            
        # Busca o math_element na forms_insumos onde name_element = str_value da forms_tab
        cursor.execute("""
            SELECT math_element 
            FROM forms_insumos 
            WHERE name_element = ?
        """, (str_value.strip(),))
        
        result = cursor.fetchone()
        if not result:
            st.warning(f"Referência '{str_value}' não encontrada em forms_insumos")
            return 0.0
            
        try:
            math_value = result[0]
            if not math_value:
                return 0.0
                
            # Processa o valor do math_element
            if '/' in math_value:  # Se for uma fração
                num, den = map(lambda x: float(x.replace(',', '.')), math_value.split('/'))
                if den == 0:
                    st.error(f"Divisão por zero encontrada em '{math_value}'")
                    return 0.0
                final_value = num / den
            else:
                final_value = float(math_value.replace(',', '.'))
            
            # Converte para formato BR antes de salvar
            final_value_br = f"{final_value:.2f}".replace('.', ',')
            
            cursor.execute("""
                UPDATE forms_tab 
                SET value_element = ?
                WHERE name_element = ? AND user_id = ?
            """, (final_value_br, name, st.session_state.user_id))
            
            return final_value  # Retorna float para cálculos
            
        except ValueError as e:
            st.error(f"Valor inválido '{result[0]}' para a referência '{str_value}': {str(e)}")
            return 0.0
            
    except sqlite3.Error as e:
        st.error(f"Erro no banco de dados: {str(e)}")
        return 0.0
    except Exception as e:
        st.error(f"Erro inesperado ao processar referência: {str(e)}")
        return 0.0
