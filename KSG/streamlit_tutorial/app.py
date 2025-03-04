import streamlit as st
import requests
from PIL import Image
import io

# FastAPI 서버 주소
API_URL = "http://localhost:8031"

st.set_page_config(page_title="Deep Diary", layout="centered")

# 세션 객체 생성 (쿠키 유지)
if "session" not in st.session_state:
    st.session_state.session = requests.Session()

# 상태 변수 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "caption_generated" not in st.session_state:
    st.session_state.caption_generated = False
if "diary_summary" not in st.session_state:
    st.session_state.diary_summary = ""
if "final_diary" not in st.session_state:
    st.session_state.final_diary = ""
if "diary_completed" not in st.session_state:
    st.session_state.diary_completed = False

def add_message(role, content):
    """채팅 메시지를 session_state에 저장"""
    st.session_state.chat_history.append({"role": role, "content": content})

# ==============================
# 이미지 업로드 및 분석
# ==============================
st.title("Deep Diary")

uploaded_file = st.file_uploader("오늘의 사진을 업로드해주세요", type=["jpg", "jpeg", "png"])

if uploaded_file:
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
        st.session_state.caption_generated = False
        st.session_state.last_uploaded_file = uploaded_file.name

    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    if not st.session_state.caption_generated:
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=image.format)
        img_bytes = img_bytes.getvalue()

        files = {'file': (uploaded_file.name, img_bytes, f'image/{image.format.lower()}')}
        
        response = st.session_state.session.post(f"{API_URL}/generate_caption", files=files)
        if response.status_code == 200:
            st.session_state.caption_generated = True
        else:
            st.error("이미지 캡션 생성 실패: " + response.text)

# ==============================
# 일기 쓰기 시작
# ==============================
if st.button("일기 쓰기 시작"):
    resp = st.session_state.session.get(f"{API_URL}/initial_question")
    if resp.status_code == 200:
        question = resp.json().get("question", "")
        add_message("assistant", question)
    else:
        st.error("첫 번째 질문 가져오기 실패: " + resp.text)

# ==============================
# 사용자 입력 및 후속 질문 처리
# ==============================
user_input = st.chat_input("답변을 입력해보세요")

if user_input:
    add_message("user", user_input)
    resp = st.session_state.session.post(f"{API_URL}/followup_question", json={"user_answer": user_input})
    if resp.status_code == 200:
        data = resp.json()
        emotion = data["emotion"]
        next_q = data["followup_question"]
        add_message("assistant", f"감정: {emotion}\n\n{next_q}")
    else:
        add_message("assistant", f"오류가 발생했습니다: {resp.text}")

# ==============================
# 일기 마무리하기 (초안 생성)
# ==============================
def summarize_conversation():
    try:
        resp = st.session_state.session.get(f"{API_URL}/summarize_conversation")
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.diary_summary = data["diary_summary"]
            st.session_state.diary_completed = True
            add_message("assistant", "일기 초안이 생성되었습니다.")
        else:
            st.error(f"요약 실패: {resp.text}")
    except Exception as e:
        st.error(f"서버 요청 실패: {e}")

with st.sidebar:
    st.button("일기 마무리하기", on_click=summarize_conversation)

# ==============================
# 일기 초안 수정 및 재생성
# ==============================
if st.session_state.diary_completed:
    st.subheader("일기 초안")
    st.write(st.session_state.diary_summary)

    user_changes = st.text_area("수정할 내용을 입력하세요", height=150)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("일기 초안 재생성"):
            if user_changes.strip():
                resp = st.session_state.session.post(f"{API_URL}/regenerate_summarize", json={"user_changes": user_changes})
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.diary_summary = data["diary_summary"]
                    add_message("assistant", "일기 초안이 업데이트되었습니다.")
                else:
                    st.error(f"초안 재생성 실패: {resp.text}")

    with col2:
        if st.button("최종 일기 저장"):
            st.session_state.final_diary = user_changes if user_changes.strip() else st.session_state.diary_summary
            add_message("assistant", f"최종 일기가 저장되었습니다.")

# ==============================
# 트로트 추천
# ==============================
def recommend_song():
    try:
        resp = st.session_state.session.get(f"{API_URL}/recommend_song")
        if resp.status_code == 200:
            data = resp.json()
            song = data.get("recommended_song", {})
            add_message("assistant", f"추천 곡: {song.get('title', '')}\n"
                                     f"가수: {song.get('artist', '')}\n"
                                     f"가사:\n{song.get('lyrics', '')}")
        else:
            st.error(f"추천 실패: {resp.text}")
    except Exception as e:
        st.error(f"서버 요청 실패: {e}")

with st.sidebar:
    st.button("트로트 추천 받기", on_click=recommend_song)

# ==============================
# 대화 내역 표시
# ==============================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
