from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter()

@router.get("/api/hospitals")
def get_hospitals():
    response = supabase.table("hospital")\
        .select("*, hospital_dept(medi_dept_id), hospital_procedure(proc_id)")\
        .execute()
    return response.data

@router.get("/api/hospitals/{hosp_id}")
def get_hospital(hosp_id: str):
    response = supabase.table("hospital")\
        .select("*, hospital_dept(medi_dept_id), hospital_procedure(proc_id)")\
        .eq("hosp_id", hosp_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다")
    return response.data[0]