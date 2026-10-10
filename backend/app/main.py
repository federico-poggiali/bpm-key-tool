from fastapi import FastAPI

app = FastAPI(title="Vinyl Second-Brain")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
