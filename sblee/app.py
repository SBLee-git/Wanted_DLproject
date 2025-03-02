import streamlit as st
import requests

st.title("AI 일기 도우미")

# 사용자 입력
user_input = st.text_area("오늘 하루는 어떠셨나요? 자유롭게 적어주세요.")

if st.button("일기 분석하기"):
    if user_input:
        # FastAPI 서버에 요청 보내기
        response = requests.post("http://localhost:8000/process_diary", json={"text": user_input})
        
        if response.status_code == 200:
            result = response.json()
            
            # 결과 표시
            st.subheader("감정 분석 결과")
            st.write(f"당신의 감정: {result['emotion']}")
            
            st.subheader("추천 노래")
            song = result['recommended_song']
            if song:
                st.write(f"제목: {song[0]}")
                st.write(f"아티스트: {song[1]}")
                st.write(f"가사 일부: {song[2][:100]}...")  # 가사 일부만 표시
            
            st.subheader("AI의 응답")
            st.write(result['gemini_response'])
            
            st.subheader("일기 초안")
            st.write(result['diary_draft'])
            
            st.subheader("기분 전환 활동 및 상품 추천")
            st.write(result['suggestions'])
        else:
            st.error("서버 오류가 발생했습니다. 다시 시도해주세요.")
    else:
        st.warning("일기를 입력해주세요.")

