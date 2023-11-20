import streamlit as st
import openai
import pymysql
import datetime
from prettytable import PrettyTable


######## 사용자가 입력 ########
OPENAI_API_KEY =
db_config = {
    'host': '127.0.0.1', # localhost
    'user': 'root',
    'password': ,
    'db': ,
    'charset': 'utf8'
}
##############################


class CalenderChatGPT:
    def __init__(self, openai_api_key, db_config, log_file="gpt_queries.log"):
        # 초기화 함수: CalenderChatGPT 인스턴스를 초기화합니다.
        # openai_api_key: OpenAI API 키를 저장합니다.
        # db_config: 데이터베이스 연결 설정을 저장합니다.
        # log_file: 로그 파일의 이름을 저장합니다. 기본값은 'gpt_queries.log'입니다.
        self.openai_api_key = openai_api_key
        self.db_config = db_config
        self.log_file = log_file
        self.messages = []  # 사용자와 시스템 메시지를 저장할 리스트입니다.
    
    # 로그 기록 함수: 실행된 쿼리를 로그 파일에 기록
    def log_query(self, query):
        with open(self.log_file, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{timestamp} - {query}\n")
            
    # OpenAI GPT로부터 응답을 받는 함수: 주어진 프롬프트로 GPT 모델에 쿼리를 요청하고 응답을 반환
    def get_response_from_gpt(self, prompt):
        openai.api_key = self.openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message['content'].strip()       
    
    
    # 사용자 프롬프트 처리 함수: 사용자의 입력에 대한 SQL 쿼리를 생성하기 위해 GPT에 프롬프트를 전송    
    def prompt(self, text):

        user_prompt = (
            "you are db manager. if user says some comment, you should do it via sql query. you now have calendar db, which is consist of column day, clock, location, passage. below is some example of dataset. "
            "CREATE TABLE calendar ( day INT, clock INT, location VARCHAR(255), passage VARCHAR(255) ); \n"
            "INSERT INTO calendar (day, clock, location, passage) VALUES (231101, 1330, 'jack''s home', 'home party'); \n"
            "=====================================\n"
            "give me a sql query for users's intent and do not include anything in answer except sql query.\n"
        )
        if text is not None:
            user_prompt += text

        self.messages.append({
            "role": "user",
            "content": user_prompt,
        })

        response = self.get_response_from_gpt(user_prompt)
        self.messages.append({
            "role": "system",
            "content": response
        })

        # Log the generated query 오류 발생했을 경우 어떤 쿼리 생성했는지 확인
        self.log_query(response)
        return response
    
    
    # SQL 쿼리 실행 함수: 주어진 쿼리를 데이터베이스에서 실행하고 결과를 반환    
    def execute_query(self, query):
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if any(keyword in query.upper() for keyword in ["INSERT", "UPDATE", "DELETE"]):
                    # 변경 쿼리의 경우, 커밋을 수행합니다.
                    conn.commit()
                    return "Your request has been processed."
                else:
                    # 조회 쿼리의 경우, 결과를 테이블 형태로 포맷팅하여 반환
                    result = cursor.fetchall()
                    conn.commit()
                    if result:
                        table = PrettyTable()
                        fields = [desc[0] for desc in cursor.description]
                        table.field_names = fields
                        for row in result:
                            table.add_row(row)
                        return table
                    else:
                        return "No results found."
        finally:
            conn.close()

    # calendar table의 모든 row 삭제 
    def clear_table(self):
        conn = pymysql.connect(**self.db_config)
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE calendar;")
        conn.close()
        print('cleared table')



def run(CalenderChatGPT):
    st.title("🗓️ CalendarDB")
    st.text('Team BDAI')

    try:
        if "messages" not in st.session_state.keys(): # Initialize the chat message history
            st.session_state.messages = [
                {"role": "assistant", "content": "I'm your DB manager. INSERT, SELECT, UPDATE, or DELETE your schedule by chatting 😃"}
            ]
        
        if prompt := st.chat_input("Query CalendarDB"): # Prompt for user input and save to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

        for message in st.session_state.messages: # Display the prior chat messages
            with st.chat_message(message["role"]):
                st.write(message["content"])

        # ChatGPT로부터 응답을 받아 SQL 쿼리를 생성하고 실행
        query_made_by_gpt = CalenderChatGPT.prompt(prompt)
        result = CalenderChatGPT.execute_query(query_made_by_gpt)

        # If last message is not from assistant, generate a new response
        if st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant"):
                st.write(result)
                message = {"role": "assistant", "content": result}
                st.session_state.messages.append(message) # Add response to message history

    except Exception as e:
        # 예외가 발생하면 사용자에게 오류 메시지를 표시
        print("An error occurred:", e)


calender_chatgpt = CalenderChatGPT(openai_api_key=OPENAI_API_KEY, db_config=db_config)
run(calender_chatgpt)