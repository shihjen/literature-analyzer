# import dependencies
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go 
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import streamlit as st
from Bio import Entrez
from dotenv import load_dotenv


load_dotenv()
email = os.getenv('email')


def search(query):
    Entrez.email = email
    handle = Entrez.esearch(db='pubmed',sort='relevance',retmax='250000',retmode='xml',term=query)
    results = Entrez.read(handle)
    return results

def get_studies_list(keyword):
    studies = search(keyword)
    studiesIdList = studies['IdList']
    return studiesIdList

def fetch_details(id_list):
    ids = ','.join(id_list)
    Entrez.email = email
    handle = Entrez.efetch(db='pubmed',retmode='xml',id=ids)
    results = Entrez.read(handle)
    return results

def get_literature_summary(studiesIdList):
    chunk_size = 10000
    
    title_list= []
    abstract_list=[]
    journal_list = []
    pmid_list = []
    language_list =[]
    pubdate_year_list = []
    pubdate_month_list = []
    publisher_list = []

    for chunk_i in range(0, len(studiesIdList), chunk_size):
        chunk = studiesIdList[chunk_i:chunk_i + chunk_size]
        papers = fetch_details(chunk)
        for i, paper in enumerate (papers['PubmedArticle']):
            title_list.append(paper['MedlineCitation']['Article']['ArticleTitle'])
            try:
                abstract_list.append(paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0])
            except:
                abstract_list.append('No Data')
            try:
                journal_list.append(paper['MedlineCitation']['Article']['Journal']['Title'])
            except:
                journal_list.append('No Data')
            try:
                pmid_list.append(paper['MedlineCitation']['PMID'])
            except:
                pmid_list.append('No Data')
            try:
                publisher_list.append(paper['MedlineCitation']['MedlineJournalInfo']['Country'])
            except: 
                publisher_list.append('No Data')
            try:
                language_list.append(paper['MedlineCitation']['Article']['Language'][0])
            except:
                language_list.append('No Data')
            try:
                pubdate_year_list.append(paper['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']['Year'])
            except:
                pubdate_year_list.append('No Data')
            try:
                pubdate_month_list.append(paper['MedlineCitation']['Article']['Journal']['JournalIssue']['PubDate']['Month'])
            except:
                pubdate_month_list.append('No Data')
                
            df = pd.DataFrame(list(zip(title_list, abstract_list, journal_list, pmid_list, publisher_list, language_list, pubdate_year_list, pubdate_month_list)),
                            columns=['Title', 'Abstract', 'Journal', 'PMID', 'Publisher', 'Language', 'Year', 'Month'])
    return df

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')


# Streamlit page configuration
st.set_page_config(
    page_title='Literature Analyzer',
    page_icon=':bar_chart:',
    layout='wide',
    initial_sidebar_state='expanded'
)


# Streamlit UI - sidebar
st.sidebar.title('Keyword Search')
keyword = st.sidebar.text_input('Enter the keyword for searching')

# Refresh button to clear session state
if st.sidebar.button('Refresh'):
    st.session_state.clear()

# Streamlit UI - body
st.title('Literature :blue[Analyzer] :chart_with_upwards_trend:')
st.write('''
The Literature Analyzer app is designed to assist researcher to perform a quick analysis on scientific literature data from PubMed. 
By entering a keyword related to a research topic, users can quickly retrieve and visualize extensive publication data, helping them gain insights into trends, popular journals, publication languages, and geographic distribution of research work. 
Additionally, the app allows users to download the retrieved data in a CSV file for further analysis.
''')

if keyword:
    if 'data' not in st.session_state:
        with st.spinner('Fetching data...'):
            st.session_state.studiesIdList = get_studies_list(keyword)
            st.session_state.data = get_literature_summary(st.session_state.studiesIdList)

    csv = convert_df(st.session_state.data)
    st.sidebar.download_button(
    label='Download data as CSV',
    data=csv,
    file_name=f'{keyword}_pubmed_literature.csv',
    mime='text/csv')

    combined_abstract = ' '.join(st.session_state.data['Abstract'])
    
    year = st.session_state.data['Year'].value_counts().sort_index()
    top_year = st.session_state.data['Year'].value_counts().sort_values(ascending=False)
        
    journal = st.session_state.data['Journal'].value_counts().sort_values(ascending=False)
    top_journal = journal[:20].reset_index()
    top_journal.columns = ['Journal', 'Count']

    language = st.session_state.data['Language'].value_counts().sort_values()

    publisher = st.session_state.data['Publisher'].value_counts()
    publisher_df = pd.DataFrame([publisher.index, publisher.values]).T
    publisher_df.columns=['Country','Count']

    # plot 1 -- line chart
    nticks = len(year.index)
    container = st.container(border=True)
    container.markdown('### :date: Number of Publications Over the Years')
    container.metric('Most publications in Year', str(top_year.index[0]), int(top_year.values[0]))
    fig = px.line(x=year.index, y=year.values, title='Number of Publications Over the Years')
    fig.update_layout(xaxis_title='Year', yaxis_title='Number of Publications', height=600)
    fig.update_xaxes(nticks=nticks)
    container.plotly_chart(fig, theme='streamlit', use_container_width=True)

    # plot 2 -- treemap
    container2 = st.container(border=True)
    container2.markdown('### :blue_book: Publication by Journal')
    #container1.metric('Most publications in Journal', str(top_journal.index[0]), int(top_journal.values[0]))
    fig2 = px.treemap(top_journal, path=['Journal'], values='Count', title='Top 20 Publication Journal')
    fig2.update_layout(height=800)
    container2.plotly_chart(fig2, theme='streamlit', use_container_width=True)

    # plot 3 -- bar chart
    container3 = st.container(border=True)
    container3.markdown('### :speech_balloon: Number of Publications by Language')
    fig3 = px.bar(language, x=language.index.str.upper(), y=language.values, text=language.values)
    fig3.update_layout(xaxis_title='Language', yaxis_title='Number of Publications', xaxis=dict(tickangle=0), height=500)
    fig3.update_traces(texttemplate='%{text}', textposition='outside')
    container3.plotly_chart(fig3, theme='streamlit', use_container_width=True)

    # plot 4 -- map
    container4 = st.container(border=True)
    container4.markdown(f'### :earth_asia: Worldwide Journal Publishers for Research on :blue[{(keyword).upper()}]')

    fig4 = go.Figure(go.Choropleth(
    locations=publisher_df['Country'],  
    locationmode='country names',
    z=publisher_df['Count'],  
    text=publisher_df['Country'],  
    colorscale='blues',  
    reversescale=False,  
    marker_line_color='darkgray',  
    marker_line_width=0.5,  
    colorbar_title='Count'))

    fig4.update_layout(width=1000,height=600,
        geo=dict(
            showcoastlines=True,  # show coastlines on the map
            projection_type='equirectangular'  # projection type for the map
        )
    )
    container4.plotly_chart(fig4, theme='streamlit', use_container_width=True)

    # plot 5 -- wordcloud
    container5 = st.container(border=True)
    container5.markdown('### :pencil2: Most Frequent Words in Abstract')
    wordcloud = WordCloud(width = 1000, height = 500,
                          background_color = 'black',
                          colormap = 'plasma',
                          max_words = 200,
                          max_font_size = 100,
                          min_font_size = 10).generate(combined_abstract)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')  
    container5.pyplot(plt)

    # data table
    container6 = st.container(border=True)
    container6.markdown('### :arrow_double_down: Extracted Data')
    container6.dataframe(st.session_state.data)
    container6.download_button(
        label='Download Table',
        data=csv,
        file_name=f'{keyword}_pubmed_literature.csv',
        mime='text/csv'
    )


