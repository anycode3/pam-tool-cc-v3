from fastapi import FastAPI
import uvicorn

from app.api.gds import router as gds_router

app = FastAPI(title="PAM Tool API", version="1.0.0")

# 注册路由
app.include_router(gds_router)


@app.get("/")
async def root():
    return {"message": "PAM Tool API"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
