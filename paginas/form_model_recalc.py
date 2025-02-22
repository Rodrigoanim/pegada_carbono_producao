# Arquivo: form_model_recalc.py
# Data: 21/02/2025 - Hora: 19h01
# CursorAI - claude 3.5 sonnet 
# Rotina de recalculo de fórmulas

import sqlite3
import re
import os
import sys

# Adiciona o diretório pai ao path do Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH
import streamlit as st

def verificar_dados_usuario(cursor, user_id):
    """Verifica/copia dados do template (user_id=0) para novo usuário"""
    try:
        cursor.execute("SELECT COUNT(*) FROM forms_tab WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO forms_tab (
                    name_element, type_element, math_element, msg_element, 
                    value_element, select_element, str_element, e_col, e_row, 
                    user_id, section
                )
                SELECT 
                    name_element, type_element, math_element, msg_element, 
                    CAST(
                        CASE 
                            WHEN type_element = 'formula' THEN 0.0
                            ELSE COALESCE(value_element, 0.0)
                        END AS REAL
                    ) as value_element,
                    select_element, str_element, e_col, e_row, 
                    ?, section
                FROM forms_tab 
                WHERE user_id = 0
            """, (user_id,))
            cursor.connection.commit()
            return True
        return False
    except Exception:
        return False

def calculate_formula(cursor, name, user_id):
    """Calcula o valor de uma fórmula"""
    try:
        cursor.execute("""
            SELECT math_element 
            FROM forms_tab 
            WHERE name_element = ? AND user_id = ?
            ORDER BY ID_element DESC LIMIT 1
        """, (name, user_id))
        
        formula = cursor.fetchone()
        if not formula or not formula[0]:
            return 0.0
            
        math_expr = str(formula[0]).replace(',', '.')
        refs = re.findall(r'[A-Z]+[0-9]+|[A-Z]+[A-Z]+[0-9]+', math_expr)
        
        for ref in refs:
            cursor.execute("""
                SELECT COALESCE(value_element, 0) 
                FROM forms_tab 
                WHERE name_element = ? AND user_id = ?
                ORDER BY ID_element DESC LIMIT 1
            """, (ref, user_id))
            
            value = cursor.fetchone()
            math_expr = math_expr.replace(ref, str(value[0] if value else 0))
        
        return float(eval(math_expr))
            
    except Exception as e:
        print(f"Erro ao calcular {name}: {str(e)}")
        return 0.0

def atualizar_formulas(cursor, user_id):
    """
    Atualiza todas as fórmulas em ordem específica para um determinado usuário
    """
    try:
        # Busca todas as fórmulas no banco
        cursor.execute("""
            SELECT name_element, type_element, math_element
            FROM forms_tab 
            WHERE user_id = ? 
            AND (type_element = 'formula' OR type_element = 'formulaH')
            ORDER BY ID_element
        """, (user_id,))
        
        formulas = cursor.fetchall()
        
        for formula in formulas:
            name_element, type_element, math_element = formula
            result = calculate_formula(cursor, name_element, user_id)
            
            cursor.execute("""
                UPDATE forms_tab 
                SET value_element = CAST(? AS REAL)
                WHERE name_element = ? 
                AND user_id = ?
            """, (result, name_element, user_id))
            
        cursor.connection.commit()
        return True
        
    except Exception as e:
        print(f"Erro ao atualizar fórmulas: {str(e)}")
        return False
