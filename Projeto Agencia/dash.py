import streamlit as st
import pandas as pd

st.set_page_config(layout='wide')

# 1. Carrega o arquivo
# O arquivo tem aspas no início e fim de cada linha, então usamos quotechar
df_raw = pd.read_csv('JANEIRO.csv', quotechar='"')

# 2. Lógica para separar a coluna única em várias colunas
# Como os dados são separados por múltiplos espaços, usamos regex '\s{2,}'
# Isso significa: "dividir onde houver 2 ou mais espaços"
df = df_raw.iloc[:, 0].str.split(r'\s{2,}', expand=True)

# 3. Definir os nomes das colunas baseados no cabeçalho
df.columns = ['Id', 'Nome', 'Produto', 'Status', 'Total', 'Taxa', 'Liquido']

st.title("Relatório de Janeiro")

# 4. EXIBIR OS DADOS (O que estava faltando)
st.subheader("Visualização da Tabela")
st.dataframe(df, use_container_width=True)

# Exemplo de como acessar uma coluna específica agora que estão separadas
if 'Total' in df.columns:
    st.write("Coluna de Totais capturada com sucesso!")