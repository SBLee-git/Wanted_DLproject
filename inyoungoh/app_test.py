import streamlit as st
import requests
from PIL import Image
import io

# FastAPI 서버 URL
API_URL = "http://localhost:8031"  # FastAPI 서버 주소에 맞게 수정해주세요

st.title("AI 일기 도우미")

# 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# 1. 이미지 업로드 및 캡션 생성
uploaded_file = st.file_uploader("오늘의 사진을 업로드해주세요", type=["jpg", "jpeg", "png"])
if uploaded_file is not None and st.session_state.current_image != uploaded_file:
    st.session_state.current_image = uploaded_file
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
        st.session_state.messages.append({"role": "assistant", "content": f"이미지 캡션: {caption}"})
        st.session_state.conversation_started = True

# 채팅 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. 첫 번째 질문 생성 (이미지 업로드 후 자동으로 시작)
if st.session_state.conversation_started and len(st.session_state.messages) == 1:
    response = requests.get(f"{API_URL}/initial_question")
    if response.status_code == 200:
        question = response.json()["question"]
        st.session_state.messages.append({"role": "assistant", "content": question})

# 3. 사용자 답변 및 후속 질문
if prompt := st.chat_input("답변을 입력해주세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # FastAPI 서버에 요청 보내기
    response = requests.post(f"{API_URL}/followup_question", json={"user_answer": prompt})
    if response.status_code == 200:
        result = response.json()
        
        # 응답 표시
        with st.chat_message("assistant"):
            st.markdown(f"감정: {result['emotion']}")
            st.markdown(f"Q: {result['followup_question']}")
        st.session_state.messages.append({"role": "assistant", "content": f"감정: {result['emotion']}\nQ: {result['followup_question']}"})

# 4. 대화 요약 및 감정 분석
if st.button("일기 마무리하기"):
    response = requests.get(f"{API_URL}/summarize_conversation")
    if response.status_code == 200:
        result = response.json()
        with st.chat_message("assistant"):
            st.markdown("**일기 요약**")
            st.markdown(result['diary_summary'])
            st.markdown(f"**최종 감정**: {result['final_emotion']}")
        st.session_state.messages.append({"role": "assistant", "content": f"**일기 요약**\n{result['diary_summary']}\n**최종 감정**: {result['final_emotion']}"})

        # 5. 트로트 추천
        response = requests.get(f"{API_URL}/recommend_song")
        if response.status_code == 200:
            recommended_song = response.json()['recommended_song']
            with st.chat_message("assistant"):
                st.markdown("**추천 트로트**")
                st.markdown(f"제목: {recommended_song['title']}")
                st.markdown(f"가수: {recommended_song['artist']}")
                st.markdown(f"가사: {recommended_song['lyrics']}")
            st.session_state.messages.append({"role": "assistant", "content": f"**추천 트로트**\n제목: {recommended_song['title']}\n가수: {recommended_song['artist']}\n가사: {recommended_song['lyrics']}"})
