from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter()

@router.get("/api/tourist-spots")
def get_tourist_spots():
    response = supabase.table("tourist").select("*").execute()
    return response.data

@router.get("/api/tourist-spots/{tour_id}")
def get_tourist_spot(tour_id: int):
    response = supabase.table("tourist")\
        .select("*")\
        .eq("tour_id", tour_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다")
    return response.data[0]