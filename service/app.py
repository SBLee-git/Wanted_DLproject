import streamlit as st
import requests
from PIL import Image
import io
import time

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
# **이미지 업로드 및 캡션 생성**
# ==============================
st.title("Deep Diary")

uploaded_file = st.file_uploader("오늘의 사진을 업로드해주세요", type=["jpg", "jpeg", "png"])

if uploaded_file:
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
        st.session_state.caption_generated = False
        st.session_state.last_uploaded_file = uploaded_file.name

    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)

    if not st.session_state.caption_generated:
        # 백엔드 호출하여 캡션 생성
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=image.format)
        img_bytes = img_bytes.getvalue()

        files = {'file': (uploaded_file.name, img_bytes, f'image/{image.format.lower()}')}
        
        response = st.session_state.session.post(f"{API_URL}/generate_caption", files=files)
        if response.status_code == 200:
            st.session_state.caption_generated = True
            caption = response.json().get("caption", "")
            # add_message("assistant", caption)
            st.success("이미지 분석 완료! 이제 질문을 받아볼 수 있어요.")
        else:
            st.error("이미지 캡션 생성 실패: " + response.text)


# ==============================
# **일기 쓰기 시작**
# ==============================
if st.button("일기 쓰기 시작"):
    resp = st.session_state.session.get(f"{API_URL}/initial_question")
    if resp.status_code == 200:
        question = resp.json().get("question", "")
        add_message("assistant", question)
    else:
        st.error("첫 번째 질문 가져오기 실패: " + resp.text)


# ==============================
# **대화 내역 표시**
# ==============================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ==============================
# **사용자 입력 및 후속 질문**
# ==============================
user_input = st.chat_input("답변을 입력해보세요")

if user_input:
    add_message("user", user_input)
    
    # 백엔드에 사용자 입력 전송
    resp = st.session_state.session.post(f"{API_URL}/followup_question", json={"user_answer": user_input})
    if resp.status_code == 200:
        data = resp.json()
        emotion = data["emotion"]
        next_q = data["followup_question"]
        add_message("assistant", f"감정: {emotion}\n\n{next_q}")
    else:
        add_message("assistant", f"오류가 발생했습니다: {resp.text}")
    
    time.sleep(0.2)
    st.rerun()


# ==============================
# **일기 마무리하기 (초안 생성)**
# ==============================
def summarize_conversation():
    """백엔드에서 대화 요약 및 감정 분석 요청"""
    try:
        resp = st.session_state.session.get(f"{API_URL}/summarize_conversation")
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.diary_summary = data["diary_summary"]
            st.session_state.diary_completed = True
            add_message("assistant", st.session_state.diary_summary)
        else:
            st.error(f"요약 실패: {resp.text}")
    except Exception as e:
        st.error(f"서버 요청 실패: {e}")

with st.sidebar:
    st.button("일기 마무리하기", on_click=summarize_conversation)


# ==============================
# **일기 초안 수정 및 재생성**
# ==============================
def regenerate_diary(user_changes):
    """백엔드에 수정된 초안 요청"""
    user_changes = user_changes.strip()  # 공백 제거

    if user_changes:  # 빈 입력이 아닐 때만 실행
        resp = st.session_state.session.post(f"{API_URL}/regenerate_summarize", json={"user_changes": user_changes})
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.diary_summary = data["diary_summary"]
            add_message("assistant", f"수정된 일기 초안:\n\n{st.session_state.diary_summary}")

            # `session_state.user_changes`를 직접 변경하지 않음
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(f"초안 재생성 실패: {resp.text}")

if st.session_state.diary_completed:
    st.subheader("일기 초안 새로 생성")

    # `st.text_area`의 `value=`를 직접 설정하지 않고, 변수로 관리
    user_changes = st.text_area("수정이 필요한 부분을 알려주세요.", height=70)

    col1, col2 = st.columns(2)
    with col1:
        # 버튼 클릭 시 `user_changes` 값을 매개변수로 전달
        if st.button("일기 초안 새로 생성"):
            if user_changes.strip():  # 입력값이 있을 때만 실행
                add_message("user", user_changes)
                regenerate_diary(user_changes)

    with col2:
        if st.button("일기 작성"):
            st.session_state.show_final_diary = True  # 최종 일기 UI 표시


# ==============================
# **최종 일기 작성 및 저장**
# ==============================
if st.session_state.get("show_final_diary", False):  # "최종 일기 작성" 버튼이 눌렸을 때만 표시
    st.subheader("일기 작성")

    # 기본값을 일기 초안으로 설정
    if "final_diary" not in st.session_state or not st.session_state.final_diary:
        st.session_state.final_diary = st.session_state.diary_summary

    final_diary = st.text_area(
        "초안을 바탕으로 일기를 작성하세요.",
        value=st.session_state.final_diary,
        height=max(70, len(st.session_state.final_diary)),
        key="final_diary"
    )

    if st.button("일기 저장"):
        add_message("assistant", f"저장된 일기:\n\n{final_diary}")
        st.success("일기가 저장되었습니다.")


# ==============================
# **트로트 추천 기능**
# ==============================
def recommend_song():
    """백엔드에서 트로트 추천 요청"""
    if "recommended_song" not in st.session_state:
        st.session_state.recommended_song = None  # 초기화

    try:
        resp = st.session_state.session.get(f"{API_URL}/recommend_song")
        if resp.status_code == 200:
            st.session_state.recommended_song = resp.json().get("recommended_song", {})
            st.session_state.show_trot = True  # 트로트 추천 UI 활성화
        else:
            st.error(f"추천 실패: {resp.text}")
    except Exception as e:
        st.error(f"서버 요청 실패: {e}")


with st.sidebar:
    if st.button("트로트 추천 받기"):
        recommend_song()

if st.session_state.get("show_trot", False):  # 버튼 클릭 후 활성화
    st.divider()  # 구분선 추가
    st.subheader("🎵 트로트 추천")

    if st.session_state.get("recommended_song"):
        song = st.session_state.recommended_song
        st.write(f"**추천 곡:** {song.get('title', '제목 없음')}")
        st.write(f"**가수:** {song.get('artist', '정보 없음')}")
        st.write(f"**가사:** {song.get('lyrics', '정보 없음')}")

