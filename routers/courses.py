from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user

router = APIRouter()

class CourseCreate(BaseModel):
    course_name: str
    trip_start: str
    trip_end: str
    proc_id: str

class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    trip_start: Optional[str] = None
    trip_end: Optional[str] = None
    status: Optional[str] = None

class CourseDetailItem(BaseModel):
    tour_id: int
    day: int
    visit_order: int

class CourseDetailsCreate(BaseModel):
    details: list[CourseDetailItem]

@router.post("/api/courses")
def create_course(body: CourseCreate, current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course").insert({
        "user_id": user_id,
        "proc_id": body.proc_id,
        "course_name": body.course_name,
        "trip_start": body.trip_start,
        "trip_end": body.trip_end,
        "status": "DRAFT",
    }).execute()
    return response.data[0]

@router.get("/api/courses")
def get_courses(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

@router.get("/api/courses/{course_id}")
def get_course(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    course = supabase.table("course")\
        .select("*")\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    details = supabase.table("course_detail")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("day")\
        .order("visit_order")\
        .execute()
    result = course.data[0]
    result["details"] = details.data
    return result

@router.patch("/api/courses/{course_id}")
def update_course(
    course_id: int,
    body: CourseUpdate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id
    update_data = body.model_dump(exclude_none=True)
    response = supabase.table("course")\
        .update(update_data)\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    return response.data[0]

@router.delete("/api/courses/{course_id}")
def delete_course(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("course")\
        .delete()\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "코스 삭제됨"}

@router.post("/api/courses/{course_id}/details")
def add_course_details(
    course_id: int,
    body: CourseDetailsCreate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id
    course = supabase.table("course")\
        .select("course_id")\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    supabase.table("course_detail")\
        .delete()\
        .eq("course_id", course_id)\
        .execute()
    rows = [
        {
            "course_id": course_id,
            "tour_id": d.tour_id,
            "day": d.day,
            "visit_order": d.visit_order,
        }
        for d in body.details
    ]
    response = supabase.table("course_detail").insert(rows).execute()
    return response.data