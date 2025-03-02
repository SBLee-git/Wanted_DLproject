# Wanted_DLproject

https://www.notion.so/DL_project-1a0aa52f04eb80798a9cc87b0f1f506f


## GIT 명령어 관련
### git clone
```$ git clone https://github.com/DeepDiary/Wanted_DLproject.git```

### 대용량 파일 관리
```$ git lfs install```

### 자주쓰는 git 명령어

```
$ git log  # commit 내역 확인
```
```
$ git status  # 현재 파일 변경 상태 확인
```
```
$ git diff  # 파일 변경 내용 확인
```
```
$ git restore [파일경로]
  # 특정 파일의 수정 내용을 마지막 커밋으로 되돌리기
  # ex. git restore notebooks/eda_ikh.ipynb
  # (주의) 수정한 내용이 사라집니다
```
```
$ git branch
$ git checkout
$ git merge
```


### 서버에서 작업할 때
```
$ git -c user.name="YourName" -c user.email="YourEmail@example.com" add .  
$ git -c user.name="YourName" -c user.email="YourEmail@example.com" commit -m "커밋 메시지"  
$ git -c user.name="YourName" -c user.email="YourEmail@example.com" push
```

### 서버 접속 (교육장 내에서)
$ ssh wanted-1@192.168.10.96

### 샘플 테스트 실행
```
python ./service/deep_diary.py
```

### API 서버 실행 및 테스트
```
$ uvicorn service.main:app --host 0.0.0.0 --port 8031 --reload
```
http://localhost:8031/docs
