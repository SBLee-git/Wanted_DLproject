import streamlit as st
import requests
from PIL import Image
import io

# FastAPI 서버 URL
API_URL = "http://localhost:8031"  # FastAPI 서버 주소에 맞게 수정해주세요

st.title("AI 일기 도우미")

# 1. 이미지 업로드 및 캡션 생성
uploaded_file = st.file_uploader("오늘의 사진을 업로드해주세요", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='업로드된 이미지', use_column_width=True)
    
    # 이미지를 바이트로 변환
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    # 이미지 파일을 FastAPI 서버로 전송
    files = {'file': ('image.png', img_byte_arr, 'image/png')}
    response = requests.post(f"{API_URL}/generate_caption", files=files)
    if response.status_code == 200:
        caption = response.json()["caption"]
        st.write(f"이미지 캡션: {caption}")

# 2. 첫 번째 질문 생성
if st.button("일기 쓰기 시작"):
    response = requests.get(f"{API_URL}/initial_question")
    if response.status_code == 200:
        question = response.json()["question"]
        st.session_state.current_question = question
        st.write(f"Q: {question}")

# 3. 사용자 답변 및 후속 질문
user_answer = st.text_input("답변을 입력해주세요")
if st.button("답변 제출"):
    if user_answer:
        response = requests.post(f"{API_URL}/followup_question", json={"user_answer": user_answer})
        if response.status_code == 200:
            result = response.json()
            st.write(f"감정: {result['emotion']}")
            st.write(f"Q: {result['followup_question']}")
            st.session_state.current_question = result['followup_question']

# 4. 대화 요약 및 감정 분석
if st.button("일기 마무리하기"):
    response = requests.get(f"{API_URL}/summarize_conversation")
    if response.status_code == 200:
        result = response.json()
        st.subheader("일기 요약")
        st.write(result['diary_summary'])
        st.write(f"최종 감정: {result['final_emotion']}")

# 5. 트로트 추천
if st.button("오늘의 트로트 추천받기"):
    response = requests.get(f"{API_URL}/recommend_song")
    if response.status_code == 200:
        recommended_song = response.json()['recommended_song']
        st.subheader("추천 트로트")
        st.write(f"제목: {recommended_song['title']}")
        st.write(f"가수: {recommended_song['artist']}")
        st.write(f"가사: {recommended_song['lyrics']}")

