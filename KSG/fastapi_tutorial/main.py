from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException
import json
from datetime import datetime
import shutil
import os


app = FastAPI()
basic_router = APIRouter(prefix="/basic", tags=["basic"])


@app.get("/")
def home():
    return {"message": "안녕하세요! 반갑습니다!"}

@basic_router.get(
    "/all",
    summary="모든 데이터 조회",
    description="sample_data.json의 모든 정보를 조회합니다."
)
def get_data():
    """
    sample_data.json을 읽고 데이터를 다음과 같은 형식으로 반환
    output:
    {
        "status": "success",
        "results": [{'id': 1, ...}]
    }
    """
    with open("app/sample_data.json") as f:
        data = json.load(f)
        
    return {
        "status": "success",
        "results": data
    }

@basic_router.get("/query")
def get_data_with_condition(category: str):
    """카테고리를 입력받아 조건에 만족하는 데이터만 조회"""
    with open("app/sample_data.json", "r") as f:
        data = json.load(f)
    
    result = []
    for item in data:
        if item["category"] == category:
            result.append(item)
    
    return {
        "status": "success",
        "results": result
    }


class TextData(BaseModel):
    name: str
    category: str
    price: int
    
    
@basic_router.post("/body/text")
def create_text_data(text_data: TextData):
    """JSON 데이터가 입력되면 sample_data.json에 추가"""
    text_data = text_data.model_dump()
    
    with open("app/sample_data.json", "r") as f:
        data = json.load(f)
    
    # 새로운 데이터 생성
    new_data = {"id": len(data) + 1}
    new_data.update(text_data)
    data.append(new_data)
    
    # 새로운 데이터 저장
    with open("app/sample_data.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return {
        "status": "success",
    }
    

@basic_router.post(
    "/body/image/binary"
)
def create_image_binary_data(file: bytes=File(...)):
    """
    이미지 바이너리 데이터를 JSON으로 받아와 저장
    데이터 파일 명은 현재 시간('%Y%m%d-%H%M%S')으로 저장
    확장자는 jpg로 고정
    """
    file_size = len(file)
    file_dir = "app/resources/"
    file_name = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_ext = ".jpg"
    file_path = file_dir + file_name + file_ext
    with open(file_path, "wb") as buffer:
        buffer.write(file)
    
    return {
        "status": "success",
        "file_path": file_path,
        "file_size": file_size
    }


@basic_router.post(
    "/body/image/file"
)
def create_image_file_data(file: UploadFile=File(...)):
    """
    이미지 파일을 받아와 저장
    데이터 파일 명은 현재 시간('%Y%m%d-%H%M%S')으로 저장
    확장자는 파일의 확장자를 따른다
    """
    file_size = file.size
    file_dir = "app/resources/"
    file_name = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_ext = "." + file.filename.split(".")[-1]
    
    file_path = file_dir + file_name + file_ext
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "status": "success",
        "file_path": file_path,
        "file_size": file_size
    }
    
    
app.include_router(basic_router)


###########################################################
predict_router = APIRouter(prefix="/predict", tags=["predict"])
    
from KSG.fastapi_tutorial.models.Kobert_emotion import EmotionClassifier
classifier = EmotionClassifier()
classifier.load_model("./inyoungoh/new_data_test.pth")

@predict_router.post("/txt_cls")
def predict_text_cls(text: str):
    emotion_label = classifier.predict_emotion(text)
    print(f"Predicted Emotion Label: {emotion_label}")
    return {
        "status": "success",
        "emotion": emotion_label
    }

###########################################################
from models.image_captioning import LlavaImageCaptioning
caption_generator = LlavaImageCaptioning()
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@predict_router.post("/image_caption")
def predict_image_caption(
    img_url: str = None,
    file: UploadFile = File(None)
):
    """
    하나의 엔드포인트에서 URL 또는 업로드된 파일을 통한 이미지 캡션 생성 API.

    Args:
        img_url (Optional[str]): 분석할 이미지의 URL (JSON 입력)
        file (Optional[UploadFile]): 업로드된 이미지 파일 (Form-data)

    Returns:
        dict: { "caption": "생성된 캡션", "execution_time": "실행 시간" }
    """
    # 둘 다 제공되지 않은 경우 → 에러 반환
    if not img_url and not file:
        raise HTTPException(status_code=400, detail="URL 또는 파일 중 하나를 제공해야 합니다.")

    image = None  # 이미지 객체 저장용 변수

    try:
        if img_url:
            # URL에서 이미지 로드
            image = caption_generator.load_image_from_url(img_url)
            if image is None:
                raise HTTPException(status_code=400, detail="이미지를 불러오지 못했습니다.")

        elif file:
            # 파일 저장 후 이미지 로드
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            image = caption_generator.load_image_from_file(file_path)
            if image is None:
                raise HTTPException(status_code=400, detail="업로드된 이미지를 불러오지 못했습니다.")

        # 캡션 생성
        caption, exec_time = caption_generator.generate_caption(image)

        return {
            "status": "success",
            "caption": caption,
            "execution_time": str(exec_time)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(predict_router)



# uvicorn KSG.fastapi_tutorial.main:app --host 0.0.0.0 --port 8080 --reload
# http://localhost:8080/docs#/
# http://192.168.10.87:8080/docs#/
