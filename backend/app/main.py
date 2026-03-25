from fastapi import FastAPI

app = FastAPI(title="PAM Tool API", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "PAM Tool API"}
