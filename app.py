import streamlit as st
import sqlite3
import os
from datetime import date
from PIL import Image
import extra_streamlit_components as stx

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Casa de Família",
    page_icon="🏡",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. GESTÃO DA BASE DE DADOS (SQLite)
# -----------------------------------------------------------------------------
def inicializar_bd():
    """Garante que a base de dados e as tabelas essenciais existem."""
    conexao = sqlite3.connect("casa_familia.db")
    cursor = conexao.cursor()
    
    # Tabela de Utilizadores (Palavra-passe em texto simples)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilizadores (
            username TEXT PRIMARY KEY,
            nome_exibicao TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Tabela de Compras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quem_pediu TEXT NOT NULL
        )
    ''')
    
    # Tabela de Marcações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marcacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_inicio DATE NOT NULL,
            data_fim DATE NOT NULL
        )
    ''')
    
    # Tabela de Manutenção
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manutencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarefa TEXT NOT NULL,
            urgencia TEXT NOT NULL,
            quem_registou TEXT NOT NULL
        )
    ''')
    
    # Tabela de Fotos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ficheiro TEXT NOT NULL,
            descricao TEXT,
            quem_enviou TEXT NOT NULL
        )
    ''')
    
    # Criar contas iniciais se a tabela estiver completamente vazia
    cursor.execute("SELECT COUNT(*) FROM utilizadores")
    if cursor.fetchone()[0] == 0:
        utilizadores_iniciais = [
            ("ana", "Ana", "familia123"),
            ("carlos", "Carlos", "familia123"),
            ("maria", "Maria", "familia123"),
            ("joao", "João", "familia123"),
            ("avos", "Avós", "familia123")
        ]
        cursor.executemany(
            "INSERT INTO utilizadores (username, nome_exibicao, password) VALUES (?, ?, ?)",
            utilizadores_iniciais
        )
    
    conexao.commit()
    conexao.close()

# Executa a verificação/inicialização da BD
inicializar_bd()

# Criar pasta para guardar fotos se não existir
if not os.path.exists("fotos"):
    os.makedirs("fotos")

# -----------------------------------------------------------------------------
# 3. GESTÃO DE SESSÃO (Cookies + Session State)
# -----------------------------------------------------------------------------
cookie_manager = stx.CookieManager()

# Tenta ler o utilizador a partir do cookie salvo no navegador
cookie_user = cookie_manager.get(cookie="casa_familia_user")

# Sincroniza o cookie com a memória de sessão do Streamlit (st.session_state)
if "utilizador_logado" not in st.session_state:
    st.session_state.utilizador_logado = cookie_user
elif cookie_user and not st.session_state.utilizador_logado:
    st.session_state.utilizador_logado = cookie_user

# -----------------------------------------------------------------------------
# 4. ECRÃ DE LOGIN (Quando nenhum utilizador está autenticado)
# -----------------------------------------------------------------------------
if not st.session_state.utilizador_logado:
    st.title("🏡 Casa de Família - Iniciar Sessão")
    st.write("Seleciona o teu nome e introduz a tua palavra-passe.")
    
    # Obter lista de utilizadores da BD
    conn = sqlite3.connect("casa_familia.db")
    c = conn.cursor()
    c.execute("SELECT username, nome_exibicao FROM utilizadores")
    contas = c.fetchall()
    conn.close()
    
    opcoes_contas = {nome_ex: user for user, nome_ex in contas}
    
    escolha_nome = st.selectbox("Quem és tu?", list(opcoes_contas.keys()))
    password_inserida = st.text_input("Palavra-passe:", type="password")
    
    if st.button("Iniciar Sessão", type="primary"):
        username_selecionado = opcoes_contas[escolha_nome]
        
        # Consultar palavra-passe na base de dados
        conn = sqlite3.connect("casa_familia.db")
        c = conn.cursor()
        c.execute("SELECT password FROM utilizadores WHERE username = ?", (username_selecionado,))
        resultado = c.fetchone()
        conn.close()
        
        # Comparar texto ignorando espaços acidentais nas extremidades (.strip())
        if resultado and password_inserida.strip() == str(resultado[0]).strip():
            # 1. Guardar na memória imediata do Streamlit
            st.session_state.utilizador_logado = username_selecionado
            
            # 2. Guardar no cookie do navegador para acessos futuros
            cookie_manager.set("casa_familia_user", username_selecionado, key="set_user", expires_at=date(2030, 1, 1))
            
            st.success(f"Bem-vindo(a), {escolha_nome}!")
            st.rerun()
        else:
            st.error("Palavra-passe incorreta. Verifica o texto introduzido.")

# -----------------------------------------------------------------------------
# 5. PAINEL PRINCIPAL (Acessível após login com sucesso)
# -----------------------------------------------------------------------------
else:
    username_ativo = st.session_state.utilizador_logado
    
    # Obter o nome de exibição do utilizador atual
    conn = sqlite3.connect("casa_familia.db")
    c = conn.cursor()
    c.execute("SELECT nome_exibicao FROM utilizadores WHERE username = ?", (username_ativo,))
    utilizador_atual_row = c.fetchone()
    conn.close()
    
    utilizador_atual = utilizador_atual_row[0] if utilizador_atual_row else username_ativo

    st.title("🏡 A Nossa Casa de Família")
    st.write(f"Olá, **{utilizador_atual}**! 👋")

    # Separadores do Menu
    aba_cal, aba_comp, aba_manut, aba_galeria, aba_conta = st.tabs([
        "📅 Calendário", 
        "🛒 Compras", 
        "🛠️ Manutenção", 
        "📸 Galeria",
        "⚙️ Minha Conta"
    ])

    # =========================================================================
    # ABA 1: CALENDÁRIO DE ESTADIAS
    # =========================================================================
    with aba_cal:
        st.header("📅 Marcações de Estadias")
        col1, col2 = st.columns(2)
        with col1:
            dt_chegada = st.date_input("Data de Chegada", value=date.today())
        with col2:
            dt_saida = st.date_input("Data de Saída", value=date.today())
            
        if st.button("Guardar Estadia", type="primary"):
            if dt_saida >= dt_chegada:
                conn = sqlite3.connect("casa_familia.db")
                c = conn.cursor()
                c.execute("INSERT INTO marcacoes (nome, data_inicio, data_fim) VALUES (?, ?, ?)",
                          (utilizador_atual, dt_chegada, dt_saida))
                conn.commit()
                conn.close()
                st.success("Estadia guardada com sucesso!")
                st.rerun()
            else:
                st.error("A data de saída deve ser igual ou posterior à data de chegada.")

        st.divider()
        st.subheader("📋 Próximas Estadias Agendadas")
        conn = sqlite3.connect("casa_familia.db")
        c = conn.cursor()
        c.execute("SELECT nome, data_inicio, data_fim FROM marcacoes ORDER BY data_inicio ASC")
        agendamentos = c.fetchall()
        conn.close()
        
        if agendamentos:
            for nome, inicio, fim in agendamentos:
                st.write(f"🟢 **{nome}**: de `{inicio}` até `{fim}`")
        else:
            st.caption("Ainda não há estadias agendadas.")

    # =========================================================================
    # ABA 2: LISTA DE COMPRAS
    # =========================================================================
    with aba_comp:
        st.header("🛒 Lista de Compras")
        novo_item = st.text_input("O que é preciso comprar?")
        if st.button("Adicionar à Lista"):
            if novo_item.strip():
                conn = sqlite3.connect("casa_familia.db")
                c = conn.cursor()
                c.execute("INSERT INTO compras (item, quem_pediu) VALUES (?, ?)", (novo_item, utilizador_atual))
                conn.commit()
                conn.close()
                st.success(f"'{novo_item}' adicionado!")
                st.rerun()

        st.divider()
        st.subheader("🛍️ Itens em Falta")
        conn = sqlite3.connect("casa_familia.db")
        c = conn.cursor()
        c.execute("SELECT id, item, quem_pediu FROM compras")
        itens = c.fetchall()
        conn.close()
        
        if itens:
            for id_item, item, quem in itens:
                col_texto, col_botao = st.columns([3, 1])
                with col_texto:
                    st.write(f"• **{item}** *(pedido por {quem})*")
                with col_botao:
                    if st.button("Comprado", key=f"comp_{id_item}"):
                        conn = sqlite3.connect("casa_familia.db")
                        c = conn.cursor()
                        c.execute("DELETE FROM compras WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        st.rerun()
        else:
            st.caption("A lista de compras está vazia!")

    # =========================================================================
    # ABA 3: MANUTENÇÃO
    # =========================================================================
    with aba_manut:
        st.header("🛠️ Manutenção da Casa")
        tarefa = st.text_input("Descrição do problema:")
        urgencia = st.selectbox("Nível de Urgência:", ["Baixa", "Média", "Alta"])
        
        if st.button("Registar Manutenção"):
            if tarefa.strip():
                conn = sqlite3.connect("casa_familia.db")
                c = conn.cursor()
                c.execute("INSERT INTO manutencao (tarefa, urgencia, quem_registou) VALUES (?, ?, ?)",
                          (tarefa, urgencia, utilizador_atual))
                conn.commit()
                conn.close()
                st.success("Tarefa registada!")
                st.rerun()

        st.divider()
        st.subheader("🔧 Tarefas Pendentes")
        conn = sqlite3.connect("casa_familia.db")
        c = conn.cursor()
        c.execute("SELECT id, tarefa, urgencia, quem_registou FROM manutencao")
        tarefas = c.fetchall()
        conn.close()
        
        if tarefas:
            for id_tar, tar, urg, quem in tarefas:
                col_txt, col_btn = st.columns([3, 1])
                with col_txt:
                    emoji = "🔴" if urg == "Alta" else ("🟡" if urg == "Média" else "🟢")
                    st.write(f"{emoji} **{tar}** | Urgência: {urg} *(por {quem})*")
                with col_btn:
                    if st.button("Resolvido", key=f"man_{id_tar}"):
                        conn = sqlite3.connect("casa_familia.db")
                        c = conn.cursor()
                        c.execute("DELETE FROM manutencao WHERE id = ?", (id_tar,))
                        conn.commit()
                        conn.close()
                        st.rerun()
        else:
            st.caption("Não há tarefas pendentes.")

    # =========================================================================
    # ABA 4: GALERIA DE FOTOS
    # =========================================================================
    with aba_galeria:
        st.header("📸 Galeria de Fotografias")
        ficheiro_imagem = st.file_uploader("Escolhe uma foto:", type=["jpg", "jpeg", "png"])
        legenda = st.text_input("Legenda:")
        
        if st.button("Enviar Foto"):
            if ficheiro_imagem is not None:
                caminho_foto = os.path.join("fotos", ficheiro_imagem.name)
                imagem = Image.open(ficheiro_imagem)
                imagem.save(caminho_foto, optimize=True, quality=85)
                
                conn = sqlite3.connect("casa_familia.db")
                c = conn.cursor()
                c.execute("INSERT INTO fotos (ficheiro, descricao, quem_enviou) VALUES (?, ?, ?)",
                          (caminho_foto, legenda, utilizador_atual))
                conn.commit()
                conn.close()
                st.success("Fotografia partilhada!")
                st.rerun()

        st.divider()
        st.subheader("🖼️ Álbum da Família")
        conn = sqlite3.connect("casa_familia.db")
        c = conn.cursor()
        c.execute("SELECT ficheiro, descricao, quem_enviou FROM fotos ORDER BY id DESC")
        lista_fotos = c.fetchall()
        conn.close()
        
        if lista_fotos:
            cols = st.columns(2)
            idx = 0
            for caminho, desc, quem in lista_fotos:
                if os.path.exists(caminho):
                    with cols[idx % 2]:
                        st.image(caminho, use_container_width=True)
                        st.caption(f"**{desc}** (por {quem})")
                    idx += 1
        else:
            st.caption("Ainda não foram partilhadas fotos.")

    # =========================================================================
    # ABA 5: A MINHA CONTA
    # =========================================================================
    with aba_conta:
        st.header("⚙️ A Minha Conta")
        st.write(f"Sessão iniciada como: **{utilizador_atual}**")
        
        st.subheader("🔐 Alterar a minha Palavra-passe")
        pass_atual = st.text_input("Palavra-passe Atual:", type="password", key="pass_act")
        nova_pass = st.text_input("Nova Palavra-passe:", type="password", key="pass_new")
        
        if st.button("Guardar Alteração"):
            conn = sqlite3.connect("casa_familia.db")
            c = conn.cursor()
            c.execute("SELECT password FROM utilizadores WHERE username = ?", (username_ativo,))
            pass_db = c.fetchone()[0]
            
            if pass_atual.strip() == str(pass_db).strip():
                c.execute("UPDATE utilizadores SET password = ? WHERE username = ?", (nova_pass.strip(), username_ativo))
                conn.commit()
                conn.close()
                st.success("Palavra-passe alterada com sucesso!")
            else:
                conn.close()
                st.error("A palavra-passe atual inserida está incorreta.")

        st.divider()
        st.subheader("🚪 Terminar Sessão")
        if st.button("Sair da Conta"):
            st.session_state.utilizador_logado = None
            cookie_manager.delete("casa_familia_user", key="del_user")
            st.rerun()