import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel, BertForSequenceClassification
from sklearn.metrics.pairwise import cosine_similarity
import re


# E5 임베딩 생성 클래스
class E5Embedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("intfloat/e5-large")
        self.model = AutoModel.from_pretrained("intfloat/e5-large")

    def get_embedding(self, text):
        """텍스트를 E5 임베딩 벡터로 변환"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach()


# KoBERT 기반 감정 분류 클래스
class EmotionClassifier:
    def __init__(self, model_path="monologg/kobert", num_labels=7, device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = BertForSequenceClassification.from_pretrained(model_path, num_labels=num_labels)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model.to(self.device)

        # 감정 매핑
        self.label_to_emotion = {
            0: "중립",
            1: "놀람",
            2: "분노",
            3: "슬픔",
            4: "행복",
            5: "혐오",
            6: "공포"
        }

    def load_model(self, model_file):
        """학습된 감정 분류 모델 불러오기"""
        state_dict = torch.load(model_file, map_location=self.device)
        self.model.load_state_dict(state_dict)

    def preprocess_text(self, text):
        """텍스트 전처리"""
        return re.sub("[^0-9a-zA-Z가-힣\s+]", "", text)

    def predict_emotion(self, text):
        """감정 분류 및 예측"""
        cleaned_text = self.preprocess_text(text)
        encoded_input = self.tokenizer(cleaned_text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        encoded_input = {key: val.to(self.device) for key, val in encoded_input.items()}

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**encoded_input)
            predicted_label = outputs.logits.argmax(dim=1).item()

        return self.label_to_emotion[predicted_label]


# 추천 시스템 클래스
class SongRecommender:
    def __init__(self, df):
        """
        df: 노래 데이터가 담긴 Pandas 데이터프레임
            컬럼: ['title', 'artist', 'cleaned_lyrics', 'emotion', 'embedding']
        """
        self.df = df

    def recommend_song(self, diary_embedding, emotion):
        """
        감정이 동일한 노래 중에서 가장 유사한 노래 추천
        """
        # 감정이 동일한 노래 필터링
        filtered_df = self.df[self.df['emotion'] == emotion]

        # 코사인 유사도 계산 (PyTorch 사용)
        similarities = []
        for _, row in filtered_df.iterrows():
            # 텐서를 1차원으로 변환
            diary_vector = diary_embedding.squeeze()  # (1024,)
            song_vector = row['embedding'].squeeze()  # (1024,)
            
            # 코사인 유사도 계산
            similarity = torch.nn.functional.cosine_similarity(
                diary_vector, song_vector, dim=0
            ).item()
            similarities.append((row['title'], row['artist'], row['cleaned_lyrics'], similarity))

        # 유사도 순으로 정렬하여 가장 유사한 노래 선택
        if similarities:
            best_match = sorted(similarities, key=lambda x: x[3], reverse=True)[0]
            return best_match  # (title, artist, lyrics, similarity)
        else:
            return None

# 메인 실행 코드
if __name__ == "__main__":
    # 데이터 로드 및 초기화
    song_data_path = "trot_embeddings_emotion.pkl"  # 저장된 트로트 데이터 경로
    emotion_model_path = "new_data_test.pth"  # 학습된 KoBERT 모델 경로

    # 데이터프레임 로드
    df = pd.read_pickle(song_data_path)

    # KoBERT 기반 감정 분류 모델 초기화 및 학습된 가중치 로드
    emotion_classifier = EmotionClassifier()
    emotion_classifier.load_model(emotion_model_path)

    # E5 임베딩 모델 초기화
    embedder = E5Embedder()

    # 추천 시스템 초기화
    recommender = SongRecommender(df)

    # 사용자 입력 처리 (Gemini에서 요약된 일기 입력)
    user_input = input("오늘의 일기를 입력하세요: ")

    # 감정 예측
    predicted_emotion = emotion_classifier.predict_emotion(user_input)

    # 사용자 입력 텍스트의 임베딩 생성
    diary_embedding = embedder.get_embedding(user_input)

    # 노래 추천 실행
    recommended_song = recommender.recommend_song(diary_embedding, predicted_emotion)

    # 결과 출력 (보기 좋게 포맷팅)
    print("\n--- 당신의 감정에 어울리는 트로트 추천 ---")
    print(f"예측된 감정: {predicted_emotion}")

    if recommended_song:
        title, artist, lyrics, similarity = recommended_song
        print(f"🎵 제목: {title}")
        print(f"👤 가수: {artist}")
        print(f"📜 가사:\n{lyrics}")
        print(f"🔗 유사도 점수: {similarity:.4f}")
    else:
        print("추천할 노래가 없습니다.")
