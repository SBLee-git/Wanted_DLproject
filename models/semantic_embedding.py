import torch
import re
import pandas as pd
from transformers import AutoTokenizer, AutoModel, BertForSequenceClassification
from sklearn.metrics.pairwise import cosine_similarity


# E5 임베딩 생성 클래스
class E5Embedder:
    """
    E5 모델을 활용하여 텍스트를 임베딩 벡터로 변환하는 클래스.
    """
    def __init__(self, model_path="intfloat/e5-large"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path).to(self.device)

    def get_embedding(self, text):
        """
        텍스트를 E5 임베딩 벡터로 변환
        Args:
            text (str): 입력 텍스트
        Returns:
            torch.Tensor: 임베딩 벡터
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.device)
        outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach().cpu()
    
    
class SongRecommender:
    """
    감정이 동일한 트로트 가사 중 가장 유사한 가사를 추천하는 클래스.
    """
    def __init__(self, df_path="data/trot_embeddings_emotion.pkl"):
        """
        트로트 데이터셋을 로드하고, 감정 분석이 추가된 경우 사용.
        Args:
            df_path (str): 저장된 트로트 데이터프레임 경로 (PKL 파일)
        """
        self.df = pd.read_pickle(df_path)
        if "embedding" not in self.df.columns or "emotion" not in self.df.columns:
            raise ValueError("데이터프레임에 'embedding' 또는 'emotion' 컬럼이 없습니다. 확인해주세요.")
        self.embedder = E5Embedder()

    def recommend_song(self, text, emotion):
        """
        감정이 동일한 노래 중에서 가장 유사한 노래 추천.
        Args:
            diary_embedding (torch.Tensor): 사용자의 다이어리 텍스트 임베딩 벡터
            emotion (str): 감정 분류 결과 (예: "행복", "슬픔" 등)
        Returns:
            dict: 가장 유사한 트로트 가사 정보
        """
        diary_embedding = self.embedder.get_embedding(text)
        
        filtered_df = self.df[self.df["emotion"] == emotion]

        # 감정이 일치하는 곡이 없는 경우
        if filtered_df.empty:
            return {"message": f"'{emotion}' 감정에 해당하는 트로트 곡을 찾을 수 없습니다."}

        similarities = []
        for _, row in filtered_df.iterrows():
            similarity = cosine_similarity(diary_embedding.numpy(), row["embedding"].numpy())[0][0]
            similarities.append((row["title"], row["artist"], row["cleaned_lyrics"], similarity))

        # 가장 유사한 곡 찾기
        best_match = sorted(similarities, key=lambda x: x[3], reverse=True)[0]

        return {
            "title": best_match[0],
            "artist": best_match[1],
            "lyrics": best_match[2],
            "similarity": round(float(best_match[3]), 4)
        }
        
        
if __name__ == "__main__":
    # 모델 및 데이터 로드
    embedder = E5Embedder()
    recommender = SongRecommender()  # 트로트 데이터 로드

    # 사용자가 작성한 요약된 일기
    diary_text = "오늘은 너무 행복한 하루였어! 친구들과 바다에 가서 신나게 놀고 맛있는 것도 먹었어."

    # 감정 예측
    predicted_emotion = "행복"
    print(f"📝 감정 분석 결과: {predicted_emotion}")

    # 임베딩 생성
    diary_embedding = embedder.get_embedding(diary_text)

    # 유사한 트로트 가사 추천
    recommended_song = recommender.recommend_song(diary_embedding, predicted_emotion)

    print("\n🎶 추천 트로트 곡:")
    print(recommended_song)