from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import votes, results

app = FastAPI(title="투표 시스템 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 특정 도메인으로 제한해야 합니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(votes.router)
app.include_router(results.router)

@app.get("/")
async def root():
    return {"message": "투표 시스템 API에 오신 것을 환영합니다!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 