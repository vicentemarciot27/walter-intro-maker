import streamlit as st
import pandas as pd
import json
import time
from workflow import run_fund_selection_workflow, load_data
import subprocess
from get_record_id import get_record_id_from_name
from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
from langchain.output_parsers.structured import StructuredOutputParser

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
        "surviving_percentage": 1,
        "gdoc_id": "1AkNbFeXe5dvuzBVhFQUDfPh7B51YmjhasSGRUW4mMm0",
        "use_docs": True
    }

if 'results' not in st.session_state:
    st.session_state.results = None

if 'inputs' not in st.session_state:
    st.session_state.inputs = None

if 'progress' not in st.session_state:
    st.session_state.progress = None

if 'company_data' not in st.session_state:
    st.session_state.company_data = {
        "company": "",
        "description_company": "",
        "description_person": "",
        "industry": "",
        "round_size": 10,
        "round_type": "Series A",
        "round_commitment": 2,
        "leader_or_follower": "leader",
        "fund_closeness": "Close",
        "fund_quality": "High",
        "observations": "",
    }

# Definir a estrutura de saída para o LLM
class CompanyInfo(TypedDict):
    """
    Informações estruturadas sobre uma empresa.
    """
    description_company: str
    description_person: Optional[str]
    industry: str
    observations: str

# Função para extrair informações da empresa usando LLM
def extract_company_info(company_record):

    print(f"Company record: {company_record}")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Configurar LLM para retornar saída estruturada
    llm = llm.with_structured_output(CompanyInfo)
    
    prompt = f"""
    Baseado nas informações da empresa a seguir, extraia dados para preencher um formulário.
    
    Informações da empresa:
    {company_record}
    
    Por favor, forneça as seguintes informações (se disponíveis):
    1. Uma descrição completa da empresa (description_company)
    2. A indústria/setor de atuação (industry) - forneça múltiplos setores separados por vírgulas
    3. Informações sobre a rodada de investimento:
       - Tamanho aproximado em milhões de USD (round_size)
       - Tipo de rodada (round_type) por exemplo: Seed, Series A, etc.
    4. Descrição do representante ou CEO (description_person)
    5. Any other relevant information (observations). Try to include things like the company's website, employee count, list appearances... any information.
    
    Se alguma informação não estiver disponível, coloque ["NOT FOUND"]
    """
    
    # O LLM já retornará diretamente a estrutura definida em CompanyInfo
    try:
        company_data = llm.invoke(prompt)

        print(f"Company data: {company_data}")
                
        # Garantir que campos numéricos sejam do tipo correto
        if "round_size" in company_data and company_data["round_size"]:
            try:
                company_data["round_size"] = float(company_data["round_size"])
            except (ValueError, TypeError):
                company_data["round_size"] = 10  # valor padrão
                
        return company_data
    except Exception as e:
        st.error(f"Erro ao processar dados da empresa: {str(e)}")
        return {
            "description_company": "",
            "description_person": "",
            "industry": "",
            "observations": f"Erro ao processar: {str(e)}"
        }

with tab1:
    # Campo para buscar empresa por nome
    company_name = st.text_input("Buscar empresa por nome", value=st.session_state.company_data["company"])
    
    if st.button("Buscar informações"):
        try:
            with st.spinner("Buscando informações da empresa..."):
                # Obter informações da empresa usando a função get_record_id_from_name
                company_record = get_record_id_from_name(company_name, "companies")
                
                # Extrair informações relevantes usando LLM
                company_info = extract_company_info(company_record)
                
                # Atualizar o estado da sessão com as informações obtidas
                st.session_state.company_data.update({
                    "company": company_name,
                    **company_info
                })
                
                st.success(f"Informações de {company_name} encontradas e preenchidas!")
        except Exception as e:
            st.error(f"Erro ao buscar informações: {str(e)}")

    # Formulário para dados da empresa
    with st.form("company_form"):
        st.subheader("Company Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company = st.text_input("Company Name", value=st.session_state.company_data["company"])
            description_company = st.text_area(
                "Company Description", 
                value=st.session_state.company_data["description_company"]
            )
            description_person = st.text_area(
                "Representative Description", 
                value=st.session_state.company_data["description_person"]
            )
            industry = st.text_input(
                "Industry", 
                value=st.session_state.company_data["industry"]
            )
        
        with col2:
            round_size = st.number_input("Round Size (in millions of USD)", value=st.session_state.company_data["round_size"], help="Tamanho da rodada em milhões de USD")
            round_type = st.text_input("Funding Type", value=st.session_state.company_data["round_type"])
            round_commitment = st.number_input("Round Commitment (in millions of USD)", value=st.session_state.company_data["round_commitment"], help="Tamanho da rodada em milhões de USD")
            leader_or_follower = st.selectbox(
                "Position in Round",
                options=["leader", "follower", "both"],
                index=["leader", "follower", "both"].index(st.session_state.company_data["leader_or_follower"])
            )
            fund_closeness = st.selectbox(
                "Fund Proximity",
                options=["Close", "Distant", "Irrelevant"],
                index=["Close", "Distant", "Irrelevant"].index(st.session_state.company_data["fund_closeness"])
            )

            fund_quality = st.selectbox(
                "Fund Quality",
                options=["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(st.session_state.company_data["fund_quality"])
            )
            
        observations = st.text_area(
            "Additional Observations", 
            value=st.session_state.company_data["observations"]
        )
        
        submitted = st.form_submit_button("Get introduceable funds")
        
        if submitted:
            # Atualizar os dados da empresa no estado da sessão
            st.session_state.company_data = {
                "company": company,
                "description_company": description_company,
                "description_person": description_person,
                "industry": industry,
                "round_size": round_size,
                "round_type": round_type,
                "round_commitment": round_commitment,
                "leader_or_follower": leader_or_follower,
                "fund_closeness": fund_closeness,
                "fund_quality": fund_quality,
                "observations": observations
            }
            
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
                "fund_quality": fund_quality,
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
