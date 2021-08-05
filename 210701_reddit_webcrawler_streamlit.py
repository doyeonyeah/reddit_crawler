import streamlit as st

from dy_crawler.config import *
# from dy_crawler.utils import *

# Basic
import pandas as pd
import numpy as np

# Crawler
import requests
session = requests.Session()
session.verify = False # Disable SSL
import praw # Reddit
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import Select
# from bs4 import BeautifulSoup

# Time
import time
from datetime import datetime

# Processing
import re

# Visualization
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# Etc
import warnings
warnings.filterwarnings("ignore")



###### INFO
st.title('Reddit Webcrawler :spider:')
st.warning(
 """
 **Ver. 210805_1.1**   
 This is the Streamlit version of the Reddit crawler.  
 You can download crawled Reddit posts and comments data in various Excel formats.
 
 **Config**  
 Subreddits, Search Keywords, Filter Words: Multiple inputs allowed  
 Filename: Name of the final Excel file  
 Search In: Choose between 3. (OR option)
 """
)



###### PRAW Session
session = requests.Session()
session.verify = False    # Disable SSL
reddit = praw.Reddit(client_id=reddit_id,
                     client_secret=reddit_secret,
                     user_agent=reddit_agent,
                     username=reddit_username,
                     password=reddit_password,
                     requestor_kwargs={'session': session})



###### Config Inputs

topic = st.sidebar.text_input('Select Subreddits:', "all")
topic = '+'.join([x.strip() for x in topic.split(',')])
if topic=="":
    topic="all"

search_keywords = st.sidebar.text_input('Search Keywords:', "LG Energy Solution battery, LG Chem battery")
search_keywords = [x.strip() for x in search_keywords.split(',')]

sort_type = st.sidebar.selectbox('Sort Type:', ['new', 'relevance', 'hot', 'top'])

import dateutil.relativedelta
start_date = st.sidebar.date_input('Start Date:', datetime.today().date()-dateutil.relativedelta.relativedelta(months=1)).strftime("%Y-%m-%d")
end_date = st.sidebar.date_input('End Date:', datetime.today().date()).strftime("%Y-%m-%d")

save_id = st.sidebar.text_input('Filename:','lg_battery')


filter_keywords = st.sidebar.text_input('Filter Words:','LG')
filter_keywords = [x.strip() for x in filter_keywords.split(',')]
if filter_keywords=="":
    filter_keywords=None


search_in = st.sidebar.multiselect('Search In:', ['comment_text', 'title', 'text'], default=["comment_text"])  

# topic = 'all'
# search_keywords = ["LG Energy Solution battery", "LG Chem battery"]
# sort_type = 'new'
# start_date, end_date =  "2021-06-23", "2021-07-23"
time_filter = 'all' # default
num_posts = None # default
# save_id = 'lg_battery'
# filter_keywords = ['LG'] #중복 가능 예시: ['lg', 'Tesla', 'battery', 'batteries']
# search_in = ['comment_text'] #중복 가능 예시: ['title', 'text']

if 'run' not in st.session_state:
    st.session_state['run'] = False
if st.sidebar.button('Crawl!'):
    st.session_state['run'] = True



###### Functions

@st.cache
def get_reddit_submissions(reddit, search_keywords, topic='all', 
                           sort_type='new', time_filter='all', num_posts = None, start_date=None, end_date=None):
    subreddit = reddit.subreddit(topic)
    submission_rows=[]
    for keyword in search_keywords:
        for submission in subreddit.search(keyword, sort=sort_type, time_filter=time_filter, limit=num_posts): 
            submission_rows.append([
                keyword,
                submission.subreddit,
                submission.title,
                submission.author,
                submission.score,
                submission.id,
                submission.url,
                "https://reddit.com"+submission.permalink,
                submission.num_comments,
                datetime.fromtimestamp(submission.created),
                submission.selftext])

    submission_df = pd.DataFrame(submission_rows, columns = ['search_word','topic', 'title','username', 'upvotes', 'id','url', 'permalink', 'num_comments', 'created', 'text'])
    submission_df = submission_df.drop_duplicates(subset=['id', 'permalink']).reset_index(drop=True)
    if start_date is not None:
        submission_df = submission_df[submission_df['created']>=start_date].reset_index(drop=True)
    if end_date is not None:
        submission_df = submission_df[submission_df['created']<=(end_date+" 23:59:59")].reset_index(drop=True)
    return submission_df

@st.cache(allow_output_mutation=True)
def get_reddit_comments(reddit, submission_df):
    comment_rows = []
    for i, r in submission_df.iterrows():
        comment_submission = reddit.submission(url=submission_df["permalink"][i])
        comment_submission.comments.replace_more(limit=0)

        for comment in comment_submission.comments.list():
            comment_rows.append([submission_df["permalink"][i],
            comment.author, 
            comment.score, 
            comment.id, 
            datetime.fromtimestamp(comment.created_utc),
            comment.body])

    comment_df = pd.DataFrame(comment_rows, columns = ['permalink','comment_username', 'comment_upvotes', 'comment_id','comment_created', 'comment_text'])
    return comment_df

def reddit_2_str(df):
    for col in df.columns:
        if df[col].dtype=='O':
            df[col] = df[col].astype(str)
    return df

def make_regex(filter_keywords):
    filter_string = r''
    for word in filter_keywords:
        filter_string += r'\b{}\w*\b'.format(word.lower()) + '|'
    filter_string = filter_string[:-1]
    return filter_string

def get_relevent_comments(all_df, regex, search_in=['comment_text']):
    temp_post = None
    string_df = all_df[all_df[search_in].apply(lambda x: x.str.contains(regex, na = False, regex=True, case=False)).any(axis=1)]

#     if ['comment_text']==search_in:
#         st.write("Number of comments: {}".format(string_df.shape[0]))
#     else:
#         st.write("Number of posts: {}".format(string_df['title'].nunique()))
    
#     for i, r in string_df.iterrows():        
#         if temp_post != string_df['text'][i]:
#             temp_post = string_df['text'][i]
            
#             st.write("""
#             ***
#             ## **ID {}. POST /r/{} | {}**
#             """.format(i, string_df['topic'][i], string_df['created'][i].strftime("%y-%m-%d")))
#             st.write('### TITLE:',string_df['title'][i])

#             if temp_post == "":
#                 st.write(string_df['url'][i])
#             else:
#                 st.write(string_df['text'][i])
#         if re.search(regex, str(string_df['comment_text'][i]).lower()):
#             st.write("""
#                 ### ID {}. COMMENT | {}
#                 """.format(i, string_df['comment_created'][i].strftime("%y-%m-%d")))
#             st.write(string_df['comment_text'][i])
    return string_df

def get_report(string_df, regex, search_in=['comment_text']):
    temp_post = None    
    if ['comment_text']==search_in:
        st.write("Number of comments: {}".format(string_df.shape[0]))
    else:
        st.write("Number of posts: {}".format(string_df['title'].nunique()))
    
    for i, r in string_df.iterrows():        
        if temp_post != string_df['text'][i]:
            temp_post = string_df['text'][i]
            
            st.write("""
            ---
            ## **ID {}. POST /r/{} | {}**
            """.format(i, string_df['topic'][i], string_df['created'][i].strftime("%y-%m-%d")))
            st.write('### TITLE:',string_df['title'][i])

            if temp_post == "":
                st.write(string_df['url'][i])
            else:
                st.write(string_df['text'][i])
        if re.search(regex, str(string_df['comment_text'][i]).lower()):
            st.write("""
                ### ID {}. COMMENT | {}
                """.format(i, string_df['comment_created'][i].strftime("%y-%m-%d")))
            st.write(string_df['comment_text'][i])

@st.cache
def create_wordcloud(long_string):
    long_string = re.sub(r'[^\w\s \n]',' ',long_string)

    ## WORDCLOUD
    wordcloud = WordCloud(background_color="white", 
                          width=1000, height=1000,
                          min_word_length=2,
                          max_words=300, contour_width=3, contour_color='steelblue', prefer_horizontal=0.95)

    wordcloud.generate(long_string)
    return wordcloud

# Save
import base64
from io import BytesIO

def make_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index = False, sheet_name='Sheet1',float_format="%.2f")
    writer.save()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, filename):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    val = make_excel(df)
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">{filename}</a>' # decode b'abc' => abc

def save_reddit(save_id, start_date, end_date, submission_df=None, comment_df=None, all_df=None, string_df=None, filter_keywords=None, search_in=None):

    save_id_date = save_id+'_'+datetime.strftime(datetime.strptime(start_date, '%Y-%m-%d'), '%y%m%d')+'-'+datetime.strftime(datetime.strptime(end_date, '%Y-%m-%d'), '%y%m%d')
    
    if submission_df is not None:
        st.markdown(get_table_download_link(submission_df, "{}_{}_reddit_posts.xlsx".format(datetime.now().strftime("%y%m%d"),save_id_date)), unsafe_allow_html=True)

    if comment_df is not None:    
        st.markdown(get_table_download_link(comment_df, "{}_{}_reddit_comments.xlsx".format(datetime.now().strftime("%y%m%d"),save_id_date)), unsafe_allow_html=True)

    if all_df is not None:
        st.markdown(get_table_download_link(all_df, "{}_{}_reddit_all.xlsx".format(datetime.now().strftime("%y%m%d"),save_id_date)), unsafe_allow_html=True)
        st.markdown(get_table_download_link(all_df.set_index(['search_word', 'topic', 'title', 'username', 'upvotes', 'id', 
                      'url', 'permalink', 'num_comments', 'created', 'text', 'comment_text']), "{}_{}_reddit_all_merged.xlsx".format(datetime.now().strftime("%y%m%d"),save_id_date)), unsafe_allow_html=True)

    if string_df is not None:
        st.markdown(get_table_download_link(string_df, "{}_{}_reddit_filtered_{}_{}.xlsx".format(datetime.now().strftime("%y%m%d"),save_id_date, filter_keywords, search_in)), unsafe_allow_html=True)
        
        
            
###### RUN

if st.session_state['run']:

    status_text = st.text('Crawling Reddit posts...')
    submission_df = get_reddit_submissions(reddit=reddit, search_keywords=search_keywords, topic=topic, 
                               sort_type=sort_type, time_filter=time_filter, num_posts = num_posts, 
                           start_date=start_date, end_date=end_date)
    status_text.text('Converting...')
    submission_df = reddit_2_str(submission_df)
    status_text.text(f'Done, Number of posts: {submission_df.shape[0]}')
    time.sleep(2)

    status_text.text('Crawling relevant comments...')
    comment_df = get_reddit_comments(reddit=reddit, submission_df=submission_df)
    status_text.text('Converting...')
    comment_df = reddit_2_str(comment_df)
    status_text.text(f'Done, Number of comments: {comment_df.shape[0]}')
    time.sleep(2)
    status_text.text(f'Number of posts: {submission_df.shape[0]}, Number of comments: {comment_df.shape[0]}')

    all_df = pd.merge(submission_df, comment_df, on='permalink', how='outer')

    string_df = get_relevent_comments(all_df, make_regex(filter_keywords), search_in)

    if st.checkbox('Show Data'):
        data_type = st.selectbox('Sort Type:', ['All', 'Posts', 'Comments', 'Filtered'])
        if data_type == 'Posts':
            st.write('## Posts Dataframe:')
            st.dataframe(submission_df)
        if data_type == 'Comments':
            st.write('## Comments Dataframe:')
            st.dataframe(comment_df)
        if data_type == 'All':
            st.write('## Posts & Comments Dataframe:')
            st.dataframe(all_df)
        if data_type == 'Filtered':
            st.write('## Filtered Dataframe:')
            st.dataframe(string_df)

    if st.checkbox('Create Save Files'):
        st.write('## Saved :heart::')
        save_reddit(save_id, start_date, end_date, submission_df, comment_df, all_df, string_df, filter_keywords, search_in)
        
    if st.checkbox('Create WordCloud'):
        st.write('## WordCloud of Filtered :cloud::')
        long_string = ','.join(string_df[string_df['text'].duplicated()]['text'].astype(str)) + ','.join(string_df['comment_text'].astype(str))
        wordcloud = create_wordcloud(long_string)
        fig, ax = plt.subplots()
        ax.imshow(wordcloud)
        ax.axis("off") 
        st.pyplot(fig)

    if st.checkbox('Show Filtered'):
        st.write('## Filtered Posts & Comments:')
        get_report(string_df, make_regex(filter_keywords), search_in)
