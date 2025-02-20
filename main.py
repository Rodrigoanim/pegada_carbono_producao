# Arquivo: main.py
# Data: 17/02/2025 - Hora: 17h19
# IDE Cursor - claude 3.5 sonnet
# comando: streamlit run main.py

import streamlit as st
import sqlite3
from paginas.form_model import process_forms_tab
from datetime import datetime
import time

# Configuração da página - deve ser a primeira chamada do Streamlit
st.set_page_config(
    page_title="Simulador da Pegada de Carbono do Café Torrado",
    layout="wide"
)

def authenticate_user():
    """Autentica o usuário e verifica seu perfil no banco de dados."""
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
            <h1 style='text-align: center;'>Simulador da Pegada de<br>Carbono do Café Torrado</h1>
            <p style='text-align: center; font-size: 20px;'>Faça login para acessar o sistema</p>
        """, unsafe_allow_html=True)
        
        # Login na sidebar
        st.sidebar.title("Login - ver. fev_17_01a")
        email = st.sidebar.text_input("E-mail")
        password = st.sidebar.text_input("Senha", type="password")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            login_button = st.button("Entrar")
        
        if login_button:
            conn = sqlite3.connect("calcpc.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, perfil, nome FROM usuarios WHERE email = ? AND senha = ?
            """, (email, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state["logged_in"] = True
                st.session_state["user_profile"] = user[2]
                st.session_state["user_id"] = user[1]
                st.session_state["user_name"] = user[3]
                st.sidebar.success(f"Login bem-sucedido! Bem-vindo, {user[3]}.")
                st.rerun()
            else:
                st.sidebar.error("E-mail ou senha inválidos.")

    return st.session_state.get("logged_in", False), st.session_state.get("user_profile", None)

def show_welcome():
    """Exibe a tela de boas-vindas com informações do usuário"""
    st.title("Bem-vindo ao Sistema!")
    
    # Buscar dados do usuário
    conn = sqlite3.connect("calcpc.db")
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
                <h3 style="color: #2c3e50; font-size: 20px;">Seus Dados</h3>
                <div style="color: #34495e; font-size: 16px;">
                    <p>ID: {st.session_state.get('user_id')}</p>
                    <p>Nome: {st.session_state.get('user_name')}</p>
                    <p>E-mail: {user_info[0]}</p>
                    <p>Empresa: {empresa}</p>
                    <p>Perfil: {st.session_state.get('user_profile')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 2: Atividades (simplificada)
    with col2:
        st.markdown(f"""
            <div style="background-color: #e8f8ef; padding: 20px; border-radius: 8px;">
                <h3 style="color: #2c3e50; font-size: 20px;">Suas Atividades</h3>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Data Atual: {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 3: Módulos
    with col3:
        modulos_html = """
            <div style="background-color: #fff8e8; padding: 20px; border-radius: 8px;">
                <h3 style="color: #2c3e50; font-size: 20px;">Módulos Disponíveis</h3>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Formulário - Tipo do Café</p>
                    <p>Formulário - Moagem e Torrefação</p>
                    <p>Formulário - Embalagem</p>
                    <p>Resultados / Gráficos</p>
                    <p>Resultados SEA - Sem Etapa Agrícola</p>
                    <p>Comparação Setorial</p>
                    <p>Comparação Setorial SEA - Sem Etapa Agrícola</p>
                    <p>Análise Energética - Torrefação</p>
                </div>
            </div>
        """
        
        st.markdown(modulos_html, unsafe_allow_html=True)

def main():
    """Gerencia a navegação entre as páginas do sistema."""
    logged_in, user_profile = authenticate_user()

    if not logged_in:
        st.stop()
    
    # Armazenar página anterior para comparação
    if "previous_page" not in st.session_state:
        st.session_state["previous_page"] = None
    
    # Titulo da página
    st.title("Simulador da Pegada de Carbono do Café Torrado")

    # Adicionar informação do usuário logado
    st.sidebar.markdown(f"""
        **Usuário:** {st.session_state.get('user_name')}  
        **ID:** {st.session_state.get('user_id')}  
        **Perfil:** {st.session_state.get('user_profile')}
    """)

    if st.sidebar.button("Logout"):
        for key in ['logged_in', 'user_profile', 'user_id', 'user_name']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.title("Menu de Navegação")
    
    # Adicionando "Comparação Setorial" ao menu de opções
    menu_options = ["Bem-vindo", "Form - Tipo do Café", "Form - Moagem e Torrefação", 
                   "Form - Embalagem", "Resultados", "Resultados SEA", "Comparação Setorial",
                   "Comparação Setorial SEA", "Análise Energética - Torrefação"]
    
    if user_profile and user_profile.lower() == "adm":
        menu_options.append("Administração")
    
    section = st.sidebar.radio(
        "Selecione a página:",
        menu_options,
        key="menu_selection"
    )

    # Verificar se houve mudança de página
    if st.session_state.get("previous_page") != section:
        save_current_form_data()
        st.session_state["previous_page"] = section

    # Mapeamento das opções do menu para os valores da coluna section
    section_map = {
        "Form - Tipo do Café": "cafe",
        "Form - Moagem e Torrefação": "moagem",
        "Form - Embalagem": "embalagem",
        "Resultados": "resultados",
        "Administração": "crud"
    }
    
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
    elif section == "Administração":
        from paginas.crude import show_crud
        show_crud()

def save_current_form_data():
    """Salva os dados do formulário atual quando houver mudança de página"""
    if "form_data" in st.session_state:
        with st.spinner('Salvando dados...'):
            conn = sqlite3.connect("calcpc.db")
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

if __name__ == "__main__":
    main()
