import streamlit as st
import requests
from PIL import Image
import io

#############################################
# 1. 세션 준비: requests.Session() -> 쿠키 유지
#############################################
if "s" not in st.session_state:
    st.session_state.s = requests.Session()

# 채팅 내역 저장
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 일기 요약 (초안) 저장
if "diary_summary" not in st.session_state:
    st.session_state.diary_summary = ""

# 사용자가 수정한 최종 일기 저장
if "final_diary" not in st.session_state:
    st.session_state.final_diary = ""

# 수정 입력 텍스트 저장
if "user_changes" not in st.session_state:
    st.session_state.user_changes = ""

# 일기 마무리 여부
if "diary_completed" not in st.session_state:
    st.session_state.diary_completed = False  # False: 마무리 전, True: 마무리 후

# 노래 추천 결과 저장
if "song_recommendation" not in st.session_state:
    st.session_state.song_recommendation = ""

def add_message(role, content):
    """채팅 메시지를 session_state에 저장"""
    st.session_state.chat_history.append({"role": role, "content": content})

#############################################
# 2. 페이지 설정
#############################################
st.set_page_config(page_title="Deep Diary", layout="centered")
st.title("📖 Deep Diary")

API_URL = "http://localhost:8031"

#############################################
# 3. (A) 이미지 업로드 섹션
#############################################
st.subheader("📷 오늘의 사진 업로드")

uploaded_file = st.file_uploader("이미지를 업로드하세요", type=["jpg", "jpeg", "png"])

col1, col2 = st.columns([2,1], gap="small")
with col1:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption=None, use_container_width=True)

with col2:
    if st.button("이미지 분석하기"):
        if uploaded_file is None:
            st.warning("이미지를 먼저 업로드해주세요.")
        else:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")
            img_bytes = img_bytes.getvalue()

            files = {'file': ('uploaded_image.png', img_bytes, 'image/png')}
            try:
                resp = st.session_state.s.post(f"{API_URL}/generate_caption", files=files)
                if resp.status_code == 200:
                    st.success("이미지 분석 완료! 이제 질문을 받아볼 수 있어요.")
                else:
                    st.error(f"이미지 분석 실패: {resp.text}")
            except Exception as e:
                st.error(f"서버 요청 실패: {e}")

#############################################
# 4. (B) 첫 질문 섹션 (현재 질문 제거)
#############################################
st.subheader("📝 일기 쓰기 시작")
if st.button("첫 질문 받기"):
    try:
        cookies = st.session_state.s.cookies.get_dict()
        resp = st.session_state.s.get(f"{API_URL}/initial_question", cookies=cookies)
        if resp.status_code == 200:
            data = resp.json()
            question = data.get("question", "질문을 가져오지 못했습니다.")
            add_message("assistant", question)
        else:
            st.error(f"첫 질문 가져오기 실패: {resp.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"서버 요청 실패: {e}")

#############################################
# 5. (C) 챗봇 대화 즉시 출력 (수정 완료)
#############################################
st.subheader("💬 챗봇 대화 진행")

# 대화 내역을 출력
for msg in st.session_state.chat_history:
    role = msg["role"]
    content = msg["content"]
    with st.chat_message(role):
        st.write(content)

# 사용자 입력
user_input = st.chat_input("답변을 입력해보세요")
if user_input:
    add_message("user", user_input)  # 🔹 사용자 입력 즉시 출력

    # 🔹 FastAPI 요청 후 즉시 응답 추가
    try:
        resp = st.session_state.s.post(
            f"{API_URL}/followup_question",
            json={"user_answer": user_input},
        )
        if resp.status_code == 200:
            data = resp.json()
            emotion = data.get("emotion", "")
            followup_q = data.get("followup_question", "")
            answer_text = f"감정: {emotion}\n\n{followup_q}"
            add_message("assistant", answer_text)  # 🔹 AI 응답 즉시 출력
    except Exception as e:
        add_message("assistant", f"서버 요청 실패: {e}")

#############################################
# 6. (D) "일기 마무리하기" 버튼 -> 초안 생성
#############################################
def on_click_summarize():
    """일기 마무리 버튼 클릭 시"""
    try:
        r = st.session_state.s.get(f"{API_URL}/summarize_conversation")
        if r.status_code == 200:
            data = r.json()
            st.session_state.diary_summary = data.get("diary_summary", "")
            st.session_state.diary_completed = True
            add_message("assistant", "**✅ 일기 초안 생성 완료**")
        else:
            st.error(f"요약 실패: {r.text}")
    except Exception as e:
        st.error(f"서버 요청 실패: {e}")

with st.sidebar:
    st.title("🛠 메뉴")
    st.markdown("---")
    st.button("일기 마무리하기", on_click=on_click_summarize)

#############################################
# 7. (E) "일기 초안 & 수정"
#############################################
if st.session_state.diary_completed:
    st.subheader("📝 일기 초안")
    st.write(st.session_state.diary_summary)

    st.subheader("✍️ 일기 수정 & 최종 일기")
    user_changes = st.text_area(
        "수정 사항(여러 줄 가능)",
        value=st.session_state.diary_summary,
        height=150
    )

    if st.button("최종 일기 만들기"):
        st.session_state.final_diary = user_changes.strip()
        st.success("수정된 최종 일기가 생성되었습니다.")
        st.write(f"**✍️ 최종 일기:**\n{st.session_state.final_diary}")  # 🔹 버튼 아래에 출력

#############################################
# 8. (F) 노래 추천 (출력 정상화 + 유사도 & 감정 추가)
#############################################
if st.session_state.final_diary:
    def on_click_recommend():
        """최종 일기를 바탕으로 트로트 추천"""
        try:
            r = st.session_state.s.get(f"{API_URL}/recommend_song")
            if r.status_code == 200:
                data = r.json()
                song = data.get("recommended_song", {})
                title = song.get("title", "제목 없음")
                artist = song.get("artist", "알 수 없음")
                lyrics = "\n".join(song.get("lyrics", "").split("\n")[:3])  # 🔹 가사 2~3줄만 표시
                similarity = data.get("similarity", "N/A")
                final_emotion = data.get("final_emotion", "N/A")

                st.session_state.song_recommendation = f"""
                ### 🎵 {title} - {artist}  
                **유사도:** {similarity}  
                **최종 감정:** {final_emotion}  
                **🎼 가사:**  
                {lyrics}...
                """

            else:
                st.error(f"추천 실패: {r.text}")
        except Exception as e:
            st.error(f"서버 요청 실패: {e}")

    with st.sidebar:
        st.button("🎶 노래 추천 받기", on_click=on_click_recommend)

    if st.session_state.song_recommendation:
        st.markdown(st.session_state.song_recommendation)  # 🔹 노래 추천 출력

