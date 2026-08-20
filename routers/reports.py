# routers/reports.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import supabase
from auth import get_current_user

router = APIRouter()

class ReportCreate(BaseModel):
    report_reason: str

# 이 코스를 지금 로그인한 유저가 이미 신고했는지 확인. CourseDetailScreen이 화면 진입
# 시점에 이걸 불러와서, 이미 신고한 코스면 신고 버튼을 비활성화한다(중복 신고 방지 UI).
@router.get("/api/courses/{course_id}/report/status")
def get_report_status(course_id: int, current_user = Depends(get_current_user)):
    existing = supabase.table("course_report")\
        .select("report_id")\
        .eq("course_id", course_id)\
        .eq("reporter_user_id", current_user.id)\
        .execute()
    return {"reported": len(existing.data) > 0}

# 신고 접수. 같은 유저가 같은 코스를 이미 신고했으면 새 행을 또 만들지 않고
# "already_reported"만 반환한다(UI가 이미 신고 버튼을 막아주지만, 방어적으로 서버에서도
# 한 번 더 막는다 - 동시에 두 번 눌렀을 때 등).
@router.post("/api/courses/{course_id}/report")
def report_course(course_id: int, body: ReportCreate, current_user = Depends(get_current_user)):
    existing = supabase.table("course_report")\
        .select("report_id")\
        .eq("course_id", course_id)\
        .eq("reporter_user_id", current_user.id)\
        .execute()
    if existing.data:
        return {"status": "already_reported"}

    supabase.table("course_report").insert({
        "course_id": course_id,
        "reporter_user_id": current_user.id,
        "report_reason": body.report_reason,
        "status": "PENDING",
    }).execute()
    return {"status": "created"}