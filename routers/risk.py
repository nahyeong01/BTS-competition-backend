from fastapi import APIRouter, HTTPException, Query
from database import supabase

router = APIRouter()

HARD_FILTER_SENSITIVITY = 1.0
HARD_FILTER_EXPOSURE_THRESHOLD = 0.7
SOFT_SCORE_CAP = 60
# 하드 필터(민감도·노출도 모두 임계값 이상) 조건을 만족하면 계산을 건너뛰고 이 값을
# 그대로 반환한다. 100은 "확실성"을 의미하는 것처럼 보일 수 있어 99로 낮춘다(팀 결정) -
# 일반 계산 경로(SOFT_SCORE_CAP=60)와는 별개로, 이 값은 risk_status="not_recommended"를
# 직접 반환하는 이 분기에서만 쓰인다.
HARD_FILTER_RISK_PERCENT = 99

# Supabase(PostgREST) 클라이언트는 단일 .execute() 호출당 기본 1000행으로 응답을 자른다
# (테이블 전체 select 시 흔히 걸리는 제한). 이 페이지 크기로 range를 반복 호출해 결과가
# page_size보다 작아질 때까지(=마지막 페이지) 계속 모은다.
SUPABASE_PAGE_SIZE = 1000


def _fetch_all_rows(table_name):
    """table_name의 전체 행을 페이지네이션으로 빠짐없이 가져온다."""
    all_rows = []
    start = 0
    while True:
        res = supabase.table(table_name).select("*").range(start, start + SUPABASE_PAGE_SIZE - 1).execute()
        rows = res.data
        all_rows.extend(rows)
        if len(rows) < SUPABASE_PAGE_SIZE:
            break
        start += SUPABASE_PAGE_SIZE
    return all_rows


def get_risk_status(percent):
    if percent < 25:
        return "safe"
    if percent < 45:
        return "caution"
    return "not_recommended"


def calc_risk(proc_tags, tourist_tags):
    if not proc_tags:
        return None

    for pt in proc_tags:
        sensitivity = float(pt["sensitivity_score"])
        exposure = float(tourist_tags.get(pt["after_caut_tag_id"], 0))
        if sensitivity >= HARD_FILTER_SENSITIVITY and exposure >= HARD_FILTER_EXPOSURE_THRESHOLD:
            return {
                "risk_percent": HARD_FILTER_RISK_PERCENT,
                "risk_status": "not_recommended",
                "top_tags": [{"after_caut_tag_id": pt["after_caut_tag_id"], "contribution": HARD_FILTER_RISK_PERCENT}],
            }

    total_weight = sum(float(pt["sensitivity_score"]) for pt in proc_tags)
    if total_weight == 0:
        return None

    weighted_sum = 0
    contributions = []
    for pt in proc_tags:
        sensitivity = float(pt["sensitivity_score"])
        exposure = float(tourist_tags.get(pt["after_caut_tag_id"], 0))
        contribution = sensitivity * exposure
        weighted_sum += contribution
        contributions.append({
            "after_caut_tag_id": pt["after_caut_tag_id"],
            "contribution": round((contribution / total_weight) * 100, 1),
        })

    risk_percent = min(round((weighted_sum / total_weight) * 100), SOFT_SCORE_CAP)
    contributions.sort(key=lambda x: x["contribution"], reverse=True)

    return {
        "risk_percent": risk_percent,
        "risk_status": get_risk_status(risk_percent),
        "top_tags": contributions[:3],
    }


def _attach_tag_names(top_tags, tag_names):
    for tag in top_tags:
        tag["tag_name"] = tag_names.get(tag["after_caut_tag_id"], tag["after_caut_tag_id"])
    return top_tags


@router.get("/api/tourist-spots/risk")
def get_all_tourist_spots_risk(proc_id: str = Query(...)):
    """선택한 시술 기준으로 전체 관광지에 위험도를 붙여서 반환"""
    proc_tag_res = supabase.table("proc_tag").select("*").eq("proc_id", proc_id).execute()
    proc_tags = proc_tag_res.data
    if not proc_tags:
        raise HTTPException(status_code=404, detail="해당 시술의 주의태그 정보가 없습니다")

    # tourist_tag는 관광지 783개 x 태그 7종 = 총 5,474행이라 단일 .execute()로는
    # Supabase 기본 1000행 제한에 걸려 앞쪽 143개 관광지분(143*7=1001행)에서 잘린 채
    # 반환되고 있었다(2026-08-29 확인 - production risk API가 시술 종류와 무관하게
    # 항상 정확히 143개 관광지만 반환하던 원인). _fetch_all_rows로 range 페이지네이션을
    # 적용해 5,474행을 빠짐없이 가져온다. 이 함수 아래의 계산/응답 구조는 그대로 둔다.
    tourist_tag_rows = _fetch_all_rows("tourist_tag")
    tourist_tags_by_tour = {}
    for row in tourist_tag_rows:
        tourist_tags_by_tour.setdefault(row["tour_id"], {})[row["after_caut_tag_id"]] = row["exposure_score"]

    tag_name_res = supabase.table("after_caution_tag").select("*").execute()
    tag_names = {t["after_caut_tag_id"]: t["after_caut_tag_name"] for t in tag_name_res.data}

    results = []
    for tour_id, tags in tourist_tags_by_tour.items():
        risk = calc_risk(proc_tags, tags)
        if risk:
            risk["top_tags"] = _attach_tag_names(risk["top_tags"], tag_names)
            results.append({"tour_id": tour_id, **risk})

    return results


@router.get("/api/tourist-spots/{tour_id}/risk")
def get_tourist_spot_risk(tour_id: int, proc_id: str = Query(...)):
    """관광지 하나의 상세 위험도(태그 이름 포함)를 반환"""
    proc_tag_res = supabase.table("proc_tag").select("*").eq("proc_id", proc_id).execute()
    proc_tags = proc_tag_res.data
    if not proc_tags:
        raise HTTPException(status_code=404, detail="해당 시술의 주의태그 정보가 없습니다")

    # 단일 tour_id로 필터링되어 최대 7행(태그 종류 수)만 반환되므로 1000행 제한에
    # 걸릴 일이 없다 - 여기는 페이지네이션 대상이 아니다.
    tourist_tag_res = supabase.table("tourist_tag").select("*").eq("tour_id", tour_id).execute()
    if not tourist_tag_res.data:
        raise HTTPException(status_code=404, detail="해당 관광지의 주의태그 정보가 없습니다")

    tags = {row["after_caut_tag_id"]: row["exposure_score"] for row in tourist_tag_res.data}
    risk = calc_risk(proc_tags, tags)
    if not risk:
        raise HTTPException(status_code=404, detail="위험도를 계산할 수 없습니다")

    tag_name_res = supabase.table("after_caution_tag").select("*").execute()
    tag_names = {t["after_caut_tag_id"]: t["after_caut_tag_name"] for t in tag_name_res.data}
    risk["top_tags"] = _attach_tag_names(risk["top_tags"], tag_names)

    return {"tour_id": tour_id, **risk}


@router.get("/api/procedures/{proc_id}/caution-tags")
def get_procedure_caution_tags(proc_id: str):
    """이 시술이 신경쓰는 주의태그 목록(이름 + 민감도)을 반환 - 화면 상단 요약 박스용"""
    proc_tag_res = supabase.table("proc_tag").select("*").eq("proc_id", proc_id).execute()
    if not proc_tag_res.data:
        raise HTTPException(status_code=404, detail="해당 시술의 주의태그 정보가 없습니다")

    tag_name_res = supabase.table("after_caution_tag").select("*").execute()
    tag_names = {t["after_caut_tag_id"]: t["after_caut_tag_name"] for t in tag_name_res.data}

    return [
        {
            "after_caut_tag_id": pt["after_caut_tag_id"],
            "tag_name": tag_names.get(pt["after_caut_tag_id"], pt["after_caut_tag_id"]),
            "sensitivity_score": float(pt["sensitivity_score"]),
        }
        for pt in proc_tag_res.data
    ]