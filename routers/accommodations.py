from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter()

@router.get("/api/accommodations")
def get_accommodations():
    response = supabase.table("accommodation").select("*").execute()
    return response.data

@router.get("/api/accommodations/{acc_id}")
def get_accommodation(acc_id: int):
    response = supabase.table("accommodation")\
        .select("*")\
        .eq("acc_id", acc_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="숙소를 찾을 수 없습니다")
    return response.data[0]