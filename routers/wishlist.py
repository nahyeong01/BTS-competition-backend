from fastapi import APIRouter, Depends
from database import supabase
from auth import get_current_user

router = APIRouter()

# ==================== 병원 ====================
@router.post("/api/wishlist/hospitals/{hosp_id}")
def add_hospital_wishlist(hosp_id: str, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("hospital_wishlist").insert({
        "hosp_id": hosp_id,
        "user_id": user_id,
    }).execute()
    return {"status": "ok", "message": "병원 찜 추가됨"}

@router.delete("/api/wishlist/hospitals/{hosp_id}")
def delete_hospital_wishlist(hosp_id: str, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("hospital_wishlist")\
        .delete()\
        .eq("hosp_id", hosp_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "병원 찜 해제됨"}

@router.get("/api/wishlist/hospitals")
def get_hospital_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("hospital_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 숙소 ====================
@router.post("/api/wishlist/accommodations/{acc_id}")
def add_accommodation_wishlist(acc_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("accommodation_wishlist").insert({
        "acc_id": acc_id,
        "user_id": user_id,
    }).execute()
    return {"status": "ok", "message": "숙소 찜 추가됨"}

@router.delete("/api/wishlist/accommodations/{acc_id}")
def delete_accommodation_wishlist(acc_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("accommodation_wishlist")\
        .delete()\
        .eq("acc_id", acc_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "숙소 찜 해제됨"}

@router.get("/api/wishlist/accommodations")
def get_accommodation_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("accommodation_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 관광지 ====================
@router.post("/api/wishlist/tourist-spots/{tour_id}")
def add_tourist_wishlist(tour_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("tourist_wishlist").insert({
        "tour_id": tour_id,
        "user_id": user_id,
    }).execute()
    return {"status": "ok", "message": "관광지 찜 추가됨"}

@router.delete("/api/wishlist/tourist-spots/{tour_id}")
def delete_tourist_wishlist(tour_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("tourist_wishlist")\
        .delete()\
        .eq("tour_id", tour_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "관광지 찜 해제됨"}

@router.get("/api/wishlist/tourist-spots")
def get_tourist_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("tourist_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 코스 ====================
@router.post("/api/wishlist/courses/{course_id}")
def add_course_wishlist(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("course_wishlist").insert({
        "course_id": course_id,
        "user_id": user_id,
    }).execute()
    return {"status": "ok", "message": "코스 찜 추가됨"}

@router.delete("/api/wishlist/courses/{course_id}")
def delete_course_wishlist(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("course_wishlist")\
        .delete()\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "코스 찜 해제됨"}

@router.get("/api/wishlist/courses")
def get_course_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data