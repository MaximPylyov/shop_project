from fastapi import FastAPI

app = FastAPI(title="Reviews Service")

@app.post("/reviews/")
def create_review():
    return {"message": "Отзыв создан"}

@app.get("/reviews/{product_id}")
def get_review(product_id: int):
    return {"data": "Отзыв 1"}

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int):
    return {"message": "Отзыв удалён"}