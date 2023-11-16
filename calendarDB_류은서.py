#!/usr/bin/env python
# coding: utf-8

# **구현 쿼리문 - 네가지 (INSERT, SELECT, UPDATE, DELETE)**
# 
# - SELECT 외 쿼리 결과 - Your request has been processed. 
# 
# - 네 가지 외 기능 관련 input 시  - An error occurred. Please enter again.
# 
# - 검색 결과 없으면 No result found
# 
# 
# **mysql에 Table 생성 후 실행**
# 
# "CREATE TABLE calendar ( day INT, clock INT, location VARCHAR(255), passage VARCHAR(255) ); \n"
# 
# 

# **Input 예시**
# 
# **약속 추가**
# 
# i have  a new appointment in 231116 4pm. go to Jenny's home for meeting her
# 
# i have a new appointment in 231117 5pm. go to the movie theatre for watching movie
# 
# i have a new appointment in 231118 6pm. go to the amusement park with Jack just for having a good time.
# 
# I have a new appointment in 231119 7pm. go to grampa's home for his birthday
# 
# i have a new appointment in 231120 4pm. go to eunseo's school for her graduation
# 
# I want to add a new appointment with Harry going to his favorite restaurent in 231211 11am.
# 
# **약속 확인**
# 
# i want to see my all of my appointments before 231201
# 
# i want to see my all of my appointments after 231201
# 
# i want to see my appointment location in 231116  
# 
# i want to see my appointment location in 231120
# 
# I want to see/check what I just input
# 
# 
# **약속 변경** 
# 
# I want to update that appointment to 231121
# 
# I want to chage the appointment in 231121 4pm to 231122 3pm
# 
# I want to change the time of the appointment of going grampa's home from 7pm to 6pm.
# 
# **약속 삭제**
# 
# I want to delete my appoinment in 231120 4pm.
# 
# I want to erase the appointment in amusement park with Jack.
# 
# I want to delete the appoinments in with Harry.
# 

# In[31]:


get_ipython().system('pip install openai==0.28')


# In[30]:


get_ipython().system('pip install pymysql')


# In[1]:


pip install prettytable


# In[1]:


import openai
import pymysql
import datetime
from prettytable import PrettyTable

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

        


# In[2]:


#본인 mysql 정보 기입(user(이름 변경하였을 경우),password, db)
# host랑 charset은 디폴트

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',
    'db': 'firstdb',
    'charset': 'utf8'
}


# In[11]:


# def run(CalenderChatGPT):
#         while True:
#             user_input = input("User: ")
#             # Exit the loop if the user entered "exit"
#             if user_input == "exit":
#                 break
            
#             #chatgpt응답받기
#             query_made_by_gpt = CalenderChatGPT.prompt(user_input)
#             result = CalenderChatGPT.execute_query(query_made_by_gpt)
#             print("MySQL Result:", result)


def run(CalenderChatGPT):
    while True:
        try:
            user_input = input("User: ")
            # 사용자가 "exit"을 입력하면 반복문을 종료
            if user_input == "exit":
                break
            
            # ChatGPT로부터 응답을 받아 SQL 쿼리를 생성하고 실행
            query_made_by_gpt = CalenderChatGPT.prompt(user_input)
            result = CalenderChatGPT.execute_query(query_made_by_gpt)
            print("CalendarDB Chat:", result)

        except Exception as e:
            # 예외가 발생하면 사용자에게 오류 메시지를 표시
            print("An error occurred. Please enter again")


# In[ ]:


calender_chatgpt = CalenderChatGPT(openai_api_key="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", db_config=db_config)
run(calender_chatgpt)


# In[ ]:




