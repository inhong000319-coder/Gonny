from fastapi import FastAPI


app = FastAPI(title="Gonny API")


@app.get("/")
def read_root():
    return {"message": "Gonny API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
