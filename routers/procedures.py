from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter()

@router.get("/api/procedures")
def get_procedures():
    response = supabase.table("medical_procedure").select("*").execute()
    return response.data

@router.get("/api/procedures/{proc_id}")
def get_procedure(proc_id: int):
    response = supabase.table("medical_procedure")\
        .select("*")\
        .eq("proc_id", proc_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="시술을 찾을 수 없습니다")
    return response.data[0]