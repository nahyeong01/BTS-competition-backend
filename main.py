from fastapi import FastAPI
from database import supabase
from routers import auth, hospitals, accommodations, tourist_spots, procedures, wishlist, courses
from routers import translations


app = FastAPI()

app.include_router(auth.router)
app.include_router(hospitals.router)
app.include_router(accommodations.router)
app.include_router(tourist_spots.router)
app.include_router(procedures.router)
app.include_router(wishlist.router)
app.include_router(courses.router)
app.include_router(translations.router)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/api/nationalities")
def get_nationalities():
    response = supabase.table("nationality").select("*").execute()
    return response.data
    