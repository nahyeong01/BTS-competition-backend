import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 계정 삭제(auth.admin API) 등 관리자 권한이 필요한 작업 전용. 일반 supabase 클라이언트
# (Publishable key)로는 auth.admin.* 호출이 권한 오류로 실패한다. 이 클라이언트는
# DB 접근 제한(RLS)을 전부 우회할 수 있으므로, 반드시 필요한 곳(계정 삭제 등)에서만
# 제한적으로 사용한다 - 일반 CRUD에는 절대 쓰지 않는다.
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)