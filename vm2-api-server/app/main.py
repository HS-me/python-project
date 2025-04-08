from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import votes, results

app = FastAPI(title="?ы몴 ?쒖뒪??API")

# CORS ?ㅼ젙
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ?ㅼ젣 諛고룷 ?쒖뿉???뱀젙 ?꾨찓?몄쑝濡??쒗븳?댁빞 ?⑸땲??
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ?쇱슦???깅줉
app.include_router(votes.router)
app.include_router(results.router)

@app.get("/")
async def root():
    return {"message": "?ы몴 ?쒖뒪??API???ㅼ떊 寃껋쓣 ?섏쁺?⑸땲??"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
