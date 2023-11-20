import streamlit as st
import os
from langchain.llms import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader, UnstructuredURLLoader, SeleniumURLLoader
from langchain.vectorstores import FAISS, Chroma
from langchain.prompts import PromptTemplate
import openai


######## 사용자가 입력 ########
OPENAI_API_KEY =
##############################


# 시작 시 db 폴더 비우고, restrat, clear all outputs 실행
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
text_splitter = RecursiveCharacterTextSplitter()
embeddings = OpenAIEmbeddings()
llm = OpenAI()

# Set the chroma vector store (for non link, for link)
chroma_directory = './db/'
chroma_directory_link = './db_link/'
db = Chroma(persist_directory=chroma_directory, embedding_function=embeddings)
db_link = Chroma(persist_directory=chroma_directory_link, embedding_function=embeddings)

## Function to detect user intent
def split_intent_passage(query):
    print('query:', query)
    token1 = query.find('<')
    token2 = query.find('>')

    if token1 == -1 or token2 == -1:
        return None, query

    return query[token1:token2+1], query[token2+2:]

# Funtion to save non link input
def save_input(query, db):
    query = text_splitter.split_text(query)
    db.add_texts(texts=query)

# Function to save link input
def save_link(query, db):
    loader = SeleniumURLLoader(urls=[query])
    data = loader.load()
    documents = text_splitter.split_documents(data)
    db.add_documents(documents)

## Function to summarize the link
def summarize_link(query, db):
    loader = SeleniumURLLoader(urls=[query])
    data = loader.load()
    documents = text_splitter.split_documents(data)
    db.add_documents(documents)

    prompt_template = """Write a concise summary of the following:
                        {text}
                        CONCISE SUMMARY:"""
    prompt = PromptTemplate.from_template(template=prompt_template)

    combine_template = (""" {text}
                            Your job is to produce a final summary
                            Please write the results of your summary in the following format:
                            Title: Title of article
                            Link: URL of the article
                            Main content: Summary in one line
                            Content: Write main contents in bullet point format"""
                        )
    combine_prompt = PromptTemplate.from_template(combine_template)

    chain = load_summarize_chain(llm, 
                             map_prompt=prompt, 
                             combine_prompt=combine_prompt, 
                             chain_type="map_reduce", 
                             verbose=False)
    
    summary = chain.run(documents)
    return summary[2:]


## Function to retrieve documents related to the user query
def retriv_one(query):
    retriever = db.as_retriever(search_kwargs={"k": 1})
    docs = retriever.get_relevant_documents(query)
    return([x.page_content[:200] for x in docs[:5]])

## Function to retrieve information related to the user query
def retrieval_answer(query, db):
    prompt_template = """
    As an AI secretary, retrieve information related to the query and answer the query.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Question: {query}
    Answer: """

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["query"]
        )

    chain_type_kwargs = {"prompt": PROMPT}

    qa = RetrievalQA.from_chain_type(llm=llm, 
                                    chain_type="stuff",
                                    retriever=db.as_retriever(search_kwargs={"k": 1}),
                                    return_source_documents=True
                                    )
    # answer = qa(query)
    # return answer
    answer = qa(query)['result']
    source = qa(query)['source_documents'][0].page_content

    return answer, source

## Function to update
def update(memo, information):
    prompt  = f'''you are update assistant. you will get original memo and update information of it. below is example.\n\n\
            memo : my naver id : ididid123, passwd : pwpwpw321, i have to memory\n \
            information : my naver pw is change to abababc1233\n \
            changed memo : my naver id : ididid123, passwd : abababc1233, i have to memory\n\n \
            memo : I have some appoint ment in 2023 11 15 at seoul. i have to wake up at 11am\n \
            information : my location of appointment in 2023 11 15 is changed to newyork\n \
            changed memo : I have some appoint ment in 2023 11 15 at newyork. i have to wake up at 11am\n\n \
            memo : {memo}\n\
            information : {information}\n\
            changed memo : '''

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
            max_tokens=10
        )
    return(completion.choices[0].message["content"])

def generate_response(intent, passage):
    if intent == None:        
        return ['No intent detected.']
     
    elif intent == '<del>':
        found_source = retriv_one(passage)
        docs = db.similarity_search(found_source[0], k=1)[0].page_content                
        db.delete(db.get(where_document={'$contains': docs})['ids'])
        return ['Deleted below passage.', found_source[0]]

    elif intent == '<qa>':
        answer, source = retrieval_answer(passage, db)
        return [answer, f'Source document: {source}']
    
    elif intent == '<save>':
        link_cls = passage[:5]
        if link_cls == 'https':
            save_link(passage, db_link)
            return ['Save completed.']
        else:
            save_input(passage, db)
            return ['Save completed.']
        
    elif intent == '<show>':
        return ['Your memo is below.', '============================='] + ['-' + memo for memo in db.get(where_document={'$contains': ' '})['documents']] + ['=============================']

    elif intent == '<update>':
        found_source = retriv_one(passage)
        # Delete
        docs = db.similarity_search(found_source[0], k=1)[0].page_content                
        db.delete(db.get(where_document={'$contains': docs})['ids'])
        # Update
        new_data = update(found_source[0], passage)
        save_input(new_data, db)
        return ['Update completed. Check below.', f'Before: {found_source[0]}', f'After: {new_data}']
    
    elif intent == '<summarize>':
        summary = summarize_link(passage, db_link)
        return ['The summary is as follows', summary]

    else:        
        return ['No intent detected.']

def split_session_state(messages):
    # Initialize variables
    current_role = None
    current_messages = []

    # Create a list to store the split messages
    split_messages = []

    # Iterate through the messages
    for message in messages:
        role = message["role"]

        # Check if the role has changed
        if current_role is None or role == current_role:
            current_messages.append(message)
        else:
            split_messages.append(current_messages.copy())
            current_messages = [message]

        current_role = role

    # Add the last set of messages to the result
    split_messages.append(current_messages)

    return split_messages

#####################################################################################################################

st.title("📝 MemoDB")
st.text('Team BDAI')
# col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])
# with col1: st.button('<save>', key='<save>')
# with col2: st.button('<del>', key='<del>')
# with col3: st.button('<qa>', key='<qa>')
# with col4: st.button('<show>', key='<show>')
# with col5: st.button('<update>', key='<update>')
# with col6: st.button('<summarize>', key='<summarize>')

try:
    if "messages" not in st.session_state.keys(): # Initialize the chat message history
        st.session_state.messages = [
            {"role": "assistant", "content": "I'm your DB manager. You can <save>, <del>, <qa>, <show>, <update>, or <summarize> memos by chatting 😃"}
        ]
    
    if prompt := st.chat_input("Query MemoDB"): # Prompt for user input and save to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

    for split in split_session_state(st.session_state.messages):# Display the prior chat messages
        with st.chat_message(split[0]["role"]): # 각 split 리스트의 role은 모두 동일
            for message in split:
                st.write(message["content"])

    intent, passage = split_intent_passage(prompt)
    result_list = generate_response(intent, passage)

    # If last message is not from assistant, generate a new response
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            for result in result_list:
                st.write(result)
                message = {"role": "assistant", "content": result}
                st.session_state.messages.append(message) # Add response to message history


except Exception as e:
    # 예외가 발생하면 사용자에게 오류 메시지를 표시
    print("An error occurred:", e)

