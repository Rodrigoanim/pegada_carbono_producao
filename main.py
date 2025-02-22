# Arquivo: main.py
# Data: 21/02/2025 - Hora: 10H30
# IDE Cursor - claude 3.5 sonnet
# comando: streamlit run main.py
# novo programa: monitor.py - Dashboard de monitoramento de uso

import streamlit as st
import sqlite3
from paginas.form_model import process_forms_tab
from datetime import datetime, timedelta
import time
import sys
from config import DB_PATH, DATA_DIR  # Atualize a importação
import os
from paginas.monitor import registrar_acesso  # Adicione esta importação no topo do arquivo

# Adicione esta linha logo no início do arquivo, após os imports
# os.environ['RENDER'] = 'true'

# Configuração da página - deve ser a primeira chamada do Streamlit
st.set_page_config(
    page_title="Simulador da Pegada de Carbono do Café Torrado",
    layout="wide",
    menu_items={
        'About': """
        ### Sobre o Sistema - Simulador da Pegada de Carbono do Café Torrado
        
        Versão: 1.0.0 Beta
        
        Este sistema foi desenvolvido para simular a pegada de carbono 
        do processo de produção do café torrado.
        
        © 2025 Todos os direitos reservados. ABIC - Associação Brasileira de Indústrias de Café.
        """,
        'Get Help': None,
        'Report a bug': None
    }
)

def authenticate_user():
    """Autentica o usuário e verifica seu perfil no banco de dados."""
    # Verifica se o banco existe
    if not DB_PATH.exists():
        st.error(f"Banco de dados não encontrado em {DB_PATH}")
        return False, None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = None

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    if not st.session_state["logged_in"]:
        # Criar uma coluna centralizada
        col1, col2, col3 = st.columns([1, 20, 1])
        
        with col2:
            # Imagem de capa usando pegada.jpg da raiz
            st.image("pegada.jpg", use_container_width=True)
            
        st.markdown("""
            <p style='text-align: center; font-size: 40px;font-weight: bold;'>Simulador da Pegada de Carbono do Café Torrado</p>
            <p style='text-align: center; font-size: 20px;'>Faça login para acessar o sistema</p>
        """, unsafe_allow_html=True)
        
        # Login na sidebar
        st.sidebar.title("Login - versão Logs.2")
        email = st.sidebar.text_input("E-mail", key="email")
        password = st.sidebar.text_input("Senha", type="password", key="password", on_change=lambda: st.session_state.update({"enter_pressed": True}) if "password" in st.session_state else None)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            login_button = st.button("Entrar") or st.session_state.get("enter_pressed", False)
            if "enter_pressed" in st.session_state:
                st.session_state.enter_pressed = False
        
        if login_button:
            cursor.execute("""
                SELECT id, user_id, perfil, nome FROM usuarios WHERE email = ? AND senha = ?
            """, (email, password))
            user = cursor.fetchone()

            if user:
                st.session_state["logged_in"] = True
                st.session_state["user_profile"] = user[2]
                st.session_state["user_id"] = user[1]
                st.session_state["user_name"] = user[3]
                
                # Registrar o acesso bem-sucedido
                registrar_acesso(
                    user_id=user[1],
                    programa="main.py",
                    acao="login"
                )
                
                st.sidebar.success(f"Login bem-sucedido! Bem-vindo, {user[3]}.")
                st.rerun()
            else:
                st.sidebar.error("E-mail ou senha inválidos.")

    return st.session_state.get("logged_in", False), st.session_state.get("user_profile", None)

def get_timezone_offset():
    """
    Determina se é necessário aplicar offset de timezone baseado no ambiente
    """
    is_production = os.getenv('RENDER') is not None
    
    if is_production:
        # Se estiver no Render, ajusta 3 horas para trás
        return datetime.now() - timedelta(hours=3)
    return datetime.now()  # Se local, usa hora atual

def show_welcome():
    """Exibe a tela de boas-vindas com informações do usuário"""
    st.markdown("""
                <p style='text-align: left; font-size: 40px;'>Bem-vindo ao sistema!</p>
    """, unsafe_allow_html=True)
    
    # Buscar dados do usuário
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email, empresa 
        FROM usuarios 
        WHERE user_id = ?
    """, (st.session_state.get('user_id'),))
    user_info = cursor.fetchone()
    
    # Removemos a consulta de contagem de formulários
    conn.close()
    
    empresa = user_info[1] if user_info[1] is not None else "Não informada"
    
    # Layout em colunas usando st.columns
    col1, col2, col3 = st.columns(3)
    
    # Coluna 1: Dados do Usuário
    with col1:
        st.markdown(f"""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Seus Dados</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>ID: {st.session_state.get('user_id')}</p>
                    <p>Nome: {st.session_state.get('user_name')}</p>
                    <p>E-mail: {user_info[0]}</p>
                    <p>Empresa: {empresa}</p>
                    <p>Perfil: {st.session_state.get('user_profile')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 2: Atividades (atualizada com hora)
    with col2:
        current_time = get_timezone_offset()
        ambiente = "Produção" if os.getenv('RENDER') else "Local"
        
        st.markdown(f"""
            <div style="background-color: #e8f8ef; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Suas Atividades</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Data Atual: {current_time.strftime('%d/%m/%Y')}</p>
                    <p>Hora Atual: {current_time.strftime('%H:%M:%S')}</p>
                    <p>Ambiente: {ambiente}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 3: Módulos
    with col3:
        modulos_html = """
            <div style="background-color: #fff8e8; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Módulos Disponíveis</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Inputs - Tipo do Café</p>
                    <p>Inputs - Moagem e Torrefação</p>
                    <p>Inputs - Embalagem</p>
                    <p>Simulações - Resultados</p>
                    <p>Simulações - Resultados SEA - Sem Etapa Agrícola</p>
                    <p>Simulações - Comparação Setorial</p>
                    <p>Simulações - Comparação Setorial SEA - Sem Etapa Agrícola</p>
                    <p>Simulações - Análise Energética - Torrefação</p>
                </div>
            </div>
        """
        
        st.markdown(modulos_html, unsafe_allow_html=True)

def main():
    """Gerencia a navegação entre as páginas do sistema."""
    # Verifica se o diretório data existe
    if not DATA_DIR.exists():
        st.error(f"Pasta '{DATA_DIR}' não encontrada. O programa não pode continuar.")
        st.stop()
        
    # Verifica se o banco existe
    if not DB_PATH.exists():
        st.error(f"Banco de dados '{DB_PATH}' não encontrado. O programa não pode continuar.")
        st.stop()
        
    logged_in, user_profile = authenticate_user()
    
    if not logged_in:
        st.stop()
    
    # Armazenar página anterior para comparação
    if "previous_page" not in st.session_state:
        st.session_state["previous_page"] = None
    
    # Titulo da página
    st.markdown("<p style='text-align: left; font-size: 44px;font-weight: bold;'>Simulador da Pegada de Carbono do Café Torrado</p>", 
                unsafe_allow_html=True)

    # Adicionar informação do usuário logado
    st.sidebar.markdown(f"""
        **Usuário:** {st.session_state.get('user_name')}  
        **ID:** {st.session_state.get('user_id')}  
        **Perfil:** {st.session_state.get('user_profile')}
    """)

    if st.sidebar.button("Logout"):
        # Registrar o logout antes de limpar a sessão
        if "user_id" in st.session_state:
            registrar_acesso(
                user_id=st.session_state["user_id"],
                programa="main.py",
                acao="logout"
            )
        
        for key in ['logged_in', 'user_profile', 'user_id', 'user_name']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.title("Menu de Navegação")
    
    # Criando grupos de menu
    menu_groups = {
        "Principal": ["Bem-vindo"],
        "Formulários Inputs": [
            "Form - Tipo do Café",
            "Form - Moagem e Torrefação", 
            "Form - Embalagem"
        ],
        "Simulações": [
            "Resultados",
            "Resultados SEA",
            "Comparação Setorial",
            "Comparação Setorial SEA",
            "Análise Energética - Torrefação"
        ],
        "Administração": []  # Será preenchido condicionalmente
    }
    
    # Adicionar opções administrativas baseado no perfil
    if user_profile and user_profile.lower() in ["adm", "master"]:
        menu_groups["Administração"].append("Monitor de Uso")
    if user_profile and user_profile.lower() == "master":
        menu_groups["Administração"].append("Info Tabelas (CRUD)")
    if user_profile and user_profile.lower() == "master":
        menu_groups["Administração"].append("Diagnóstico")
    
    # Se não houver opções de administração, remover o grupo
    if not menu_groups["Administração"]:
        menu_groups.pop("Administração")
    
    # Criar seletor de grupo
    selected_group = st.sidebar.selectbox(
        "Selecione o módulo:",
        options=list(menu_groups.keys()),
        key="group_selection"
    )
    
    # Criar seletor de página dentro do grupo
    section = st.sidebar.radio(
        "Selecione a página:",
        menu_groups[selected_group],
        key="menu_selection"
    )

    # Atualizar o mapeamento para incluir o novo nome do CRUD
    section_map = {
        "Form - Tipo do Café": "cafe",
        "Form - Moagem e Torrefação": "moagem",
        "Form - Embalagem": "embalagem",
        "Resultados": "resultados",
        "Info Tabelas (CRUD)": "crud"
    }
    
    # Verificar se houve mudança de página
    if st.session_state.get("previous_page") != section:
        save_current_form_data()
        st.session_state["previous_page"] = section

    # Processa a seção selecionada
    if section == "Bem-vindo":
        show_welcome()
    elif section in ["Form - Tipo do Café", "Form - Moagem e Torrefação", "Form - Embalagem"]:
        process_forms_tab(section_map[section])
    elif section == "Resultados":
        from paginas.resultados import show_results
        show_results()
    elif section == "Resultados SEA":
        from paginas.result_sea import show_results
        show_results()
    elif section == "Comparação Setorial":
        from paginas.result_setorial import show_results
        show_results()
    elif section == "Comparação Setorial SEA":
        from paginas.result_setorial_sea import show_results
        show_results()
    elif section == "Análise Energética - Torrefação":
        from paginas.result_energetica import show_results
        show_results()
    elif section == "Info Tabelas (CRUD)":
        from paginas.crude import show_crud
        show_crud()
    elif section == "Monitor de Uso":
        from paginas.monitor import main as show_monitor
        show_monitor()
    elif section == "Diagnóstico":
        from paginas.diagnostico import show_diagnostics
        show_diagnostics()

def save_current_form_data():
    """Salva os dados do formulário atual quando houver mudança de página"""
    if "form_data" in st.session_state:
        with st.spinner('Salvando dados...'):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Criar tabelas se não existirem
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS form_cafe (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    data_input TIMESTAMP,
                    tipo_cafe TEXT,
                    quantidade FLOAT,
                    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS form_moagem (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    data_input TIMESTAMP,
                    tipo_moagem TEXT,
                    temperatura FLOAT,
                    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS form_embalagem (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    data_input TIMESTAMP,
                    tipo_embalagem TEXT,
                    peso FLOAT,
                    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
                )
            """)
            
            previous_page = st.session_state.get("previous_page", "")
            
            if "Form - Tipo do Café" in previous_page:
                tipo_cafe = st.session_state.get("form_data", {}).get("tipo_cafe")
                quantidade = st.session_state.get("form_data", {}).get("quantidade")
                
                if tipo_cafe and quantidade is not None:  # Verifica se os dados existem
                    cursor.execute("""
                        INSERT OR REPLACE INTO form_cafe 
                        (user_id, data_input, tipo_cafe, quantidade)
                        VALUES (?, datetime('now'), ?, ?)
                    """, (
                        st.session_state["user_id"],
                        tipo_cafe,
                        quantidade
                    ))
            
            elif "Form - Moagem e Torrefação" in previous_page:
                cursor.execute("""
                    INSERT OR REPLACE INTO form_moagem 
                    (user_id, data_input, tipo_moagem, temperatura)
                    VALUES (?, datetime('now'), ?, ?)
                """, (
                    st.session_state["user_id"],
                    st.session_state.get("form_data", {}).get("tipo_moagem"),
                    st.session_state.get("form_data", {}).get("temperatura")
                ))
            
            elif "Form - Embalagem" in previous_page:
                cursor.execute("""
                    INSERT OR REPLACE INTO form_embalagem 
                    (user_id, data_input, tipo_embalagem, peso)
                    VALUES (?, datetime('now'), ?, ?)
                """, (
                    st.session_state["user_id"],
                    st.session_state.get("form_data", {}).get("tipo_embalagem"),
                    st.session_state.get("form_data", {}).get("peso")
                ))
            
            conn.commit()
            conn.close()
            # Limpar os dados do formulário após salvar
            st.session_state["form_data"] = {}
            time.sleep(0.5)  # Pequeno delay para feedback visual
        st.success('Dados salvos com sucesso!')

def login():
    """Função de login do usuário"""
    # Mova estas variáveis para dentro da função
    email = st.text_input("E-mail", key="email")
    senha = st.text_input("Senha", type="password", key="password")
    
    if st.form_submit_button("Login"):
        try:
            # Use a conexão do DB_PATH em vez de criar_conexao
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
            usuario = cursor.fetchone()
            
            if usuario:
                st.session_state.autenticado = True
                st.session_state.user_id = usuario[0]
                st.session_state.nome = usuario[1]
                st.session_state.email = usuario[2]
                st.session_state.admin = usuario[4]
                
                # Registra o acesso bem-sucedido
                registrar_acesso(
                    user_id=usuario[0],
                    programa="main.py",
                    acao="login"
                )
                
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos")
                
            conn.close()
            
        except Exception as e:
            st.error(f"Erro ao realizar login: {str(e)}")
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    main()
