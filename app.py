import streamlit as st
import pandas as pd
import json
import time
from workflow import run_fund_selection_workflow, load_data
import subprocess
# Configuração da página
st.set_page_config(
    page_title="Walter Intro Maker",
    page_icon="🤖",
    layout="wide"
)

# Título principal
st.title("Walter Intro Maker")
st.subheader("Intros to Funds Matcher")

# Criando abas
tab1, tab2 = st.tabs(["Company Information", "Parameters"])

# Inicializar estado da sessão para parâmetros e resultados
if 'parameters' not in st.session_state:
    st.session_state.parameters = {
        "batch_size": 10,
        "surviving_percentage": 0.5,
        "gdoc_id": "1AkNbFeXe5dvuzBVhFQUDfPh7B51YmjhasSGRUW4mMm0",
    }

if 'results' not in st.session_state:
    st.session_state.results = None

if 'inputs' not in st.session_state:
    st.session_state.inputs = None

if 'progress' not in st.session_state:
    st.session_state.progress = None

with tab1:
    # Formulário para dados da empresa
    with st.form("company_form"):
        st.subheader("Company Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company = st.text_input("Company Name", value="Brendi")
            description_company = st.text_area(
                "Company Description", 
                value="Brendi is a company that creates AI agents to sell food in Brazilian restaurants via delivery. They are going to be the next ifood"
            )
            description_person = st.text_area(
                "Representative Description", 
                value="Daniel is the CEO of Brendi. he studied at ITA, is very young and energetic"
            )
            industry = st.text_input(
                "Industry", 
                value="AI Solutions, Food Delivery, Restaurant Management, AI Agents, Embedded Finance"
            )
        
        with col2:
            round_size = st.number_input("Round Size (in millions of USD)", value=10, help="Tamanho da rodada em milhões de USD")
            round_type = st.text_input("Funding Type", value="Series A")
            round_commitment = st.number_input("Round Commitment (in millions of USD)", value=2, help="Tamanho da rodada em milhões de USD")
            leader_or_follower = st.selectbox(
                "Position in Round",
                options=["leader", "follower", "both"],
                index=0
            )
            fund_closeness = st.selectbox(
                "Fund Proximity",
                options=["Close", "Distant", "Irrelevant"],
                index=0
            )
            
        observations = st.text_area(
            "Additional Observations", 
            value="We are sure this deal is very hot, so we want the top funds with us in this one, but they have to fit"
        )
        
        submitted = st.form_submit_button("Generate Introduction")
        
        if submitted:
            # Criar o dicionário de inputs
            st.session_state.inputs = {
                "company": company,
                "description_company": description_company,
                "description_person": description_person,
                "round": {"size": round_size, "Funding": round_type},
                "round_commitment": round_commitment,
                "leader_or_follower": leader_or_follower,
                "industry": industry,
                "fund_closeness": fund_closeness,
                "observations": observations
            }
            
            # Iniciar processamento em segundo plano e mudar para a aba de resultados
            st.session_state.progress = "starting"
            st.rerun()

with tab2:
    st.subheader("Generation Parameters")
    
    # Formulário para parâmetros
    with st.form("parameters_form"):
        batch_size = st.slider("Batch Size", 1, 50, st.session_state.parameters["batch_size"])
        surviving_percentage = st.slider("Survival Percentage", 0.1, 1.0, st.session_state.parameters["surviving_percentage"], 0.1)
        
        # Adicionar campo para ID do Google Doc
        gdoc_id = st.text_input("ID do Google Doc", 
                               value=st.session_state.parameters.get("gdoc_id", "1AkNbFeXe5dvuzBVhFQUDfPh7B51YmjhasSGRUW4mMm0"),
                               help="ID do documento do Google que contém informações adicionais")
        
        params_submitted = st.form_submit_button("Save Parameters")

        use_docs = st.checkbox("Use Google Docs", value=st.session_state.parameters.get("use_docs", False))
        
        if params_submitted:
            st.session_state.parameters = {
                "batch_size": batch_size,
                "surviving_percentage": surviving_percentage,
                "gdoc_id": gdoc_id,  # Adicionar o ID do Google Doc aos parâmetros
                "use_docs": use_docs
            }
            
            st.success("Parâmetros salvos com sucesso!")

st.subheader("Analysis Results")

# Verificar se o processamento deve começar
if st.session_state.progress == "starting" and st.session_state.inputs:
    # Container para exibir progresso
    progress_container = st.empty()
    status_container = st.empty()
    
    # Mostrar processo de execução
    try:
        # Run the script file
        result = subprocess.Popen(['bash', 'run.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()

        # Display the terminal output
        st.text('\n'.join(stdout.decode().split('\n')[1:][:-1]))
        progress_container.progress(0)
        status_container.info("Starting processing...")
        
        # Carregar dados
        status_container.info("Loading data...")
        progress_container.progress(10)
        
        # Verificar se há ID do Google Doc
        if st.session_state.parameters.get("gdoc_id"):
            status_container.info(f"Loading Google Doc content: {st.session_state.parameters['gdoc_id']}...")
            progress_container.progress(20)
        
        # Processar seleção de fundos
        status_container.info("Analyzing compatible funds...")
        progress_container.progress(30)
        
        # Chamar a função do workflow
        results = run_fund_selection_workflow(
            st.session_state.inputs, 
            st.session_state.parameters
        )
        
        progress_container.progress(100)
        status_container.success("Processing completed!")
        
        # Armazenar resultados
        st.session_state.results = results
        st.session_state.progress = "completed"
        
        # Recarregar para exibir resultados completos
        st.rerun()
        
    except Exception as e:
        status_container.error(f"Error during processing: {str(e)}")
        st.session_state.progress = None

# Exibir resultados se disponíveis
if st.session_state.results:
    # Exibir tabela com os melhores fundos
    st.subheader("Selected Funds")
    
    # Criar DataFrame para exibição
    fund_data = []
    for fund in st.session_state.results["top_funds"]:
        fund_data.append({
            "Fund Name": fund.fund_name,
            "Score": round(fund.score, 0),
            "Reason": fund.reason
        })
    
    result_df = pd.DataFrame(fund_data)
    st.dataframe(result_df)
    
    # Botão para baixar resultados como CSV
    csv = result_df.to_csv(index=False)
    st.download_button(
        label="Download Results (CSV)",
        data=csv,
        file_name="selected_funds.csv",
        mime="text/csv"
    )

elif st.session_state.progress is None:
    st.info("Fill in the company information and click 'Generate Introduction' to analyze compatible funds.")

# Rodapé
st.markdown("---")
st.markdown("Developed by Norte Ventures")
