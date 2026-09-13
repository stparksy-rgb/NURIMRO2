import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import hashlib

# Google Sheets 연동
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# 한국 시간대 설정 (UTC+9) - timezone-naive로 반환
def get_kst_now():
    """한국 현재 시간 반환 (UTC+9)"""
    import time
    # UTC 시간에 9시간 더해서 한국 시간 계산
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now

def get_kst_today():
    """한국 오늘 날짜 반환"""
    return get_kst_now().date()

# Google Sheets 연결 함수
def get_google_sheets_connection():
    """Google Sheets API 연결"""
    if not GSPREAD_AVAILABLE:
        return None, None
    
    try:
        if "gcp_service_account" not in st.secrets:
            return None, None
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        return client, spreadsheet
    except Exception as e:
        st.error(f"Google Sheets 연결 오류: {e}")
        return None, None

def sync_to_google_sheets(df, sheet_name):
    """데이터프레임을 Google Sheets에 동기화"""
    try:
        _, spreadsheet = get_google_sheets_connection()
        if spreadsheet is None:
            return False
        
        # 시트 찾기 또는 생성
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        
        # 데이터프레임을 시트에 쓰기
        worksheet.clear()
        
        if len(df) > 0:
            # 헤더와 데이터 준비
            df_copy = df.copy()
            # 날짜 컬럼 문자열로 변환
            for col in df_copy.columns:
                if df_copy[col].dtype == 'datetime64[ns]':
                    df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d')
                df_copy[col] = df_copy[col].astype(str).replace('nan', '').replace('NaT', '')
            
            # 헤더 + 데이터
            data = [df_copy.columns.tolist()] + df_copy.values.tolist()
            worksheet.update('A1', data)
        else:
            # 빈 데이터프레임이면 헤더만
            worksheet.update('A1', [df.columns.tolist()])
        
        return True
    except Exception as e:
        st.error(f"Google Sheets 동기화 오류: {e}")
        return False

def load_from_google_sheets(sheet_name):
    """Google Sheets에서 데이터 불러오기"""
    try:
        _, spreadsheet = get_google_sheets_connection()
        if spreadsheet is None:
            return None
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            if data:
                return pd.DataFrame(data)
            return None
        except gspread.exceptions.WorksheetNotFound:
            return None
    except Exception as e:
        return None

# 페이지 설정
st.set_page_config(
    page_title="누리엠알오 장부관리",
    page_icon="📊",
    layout="wide"
)

# ========== 전체 UI 스타일 개선 CSS ==========
st.markdown("""
<style>
/* 모든 selectbox 선택된 항목 - 검정색 글자 */
div[data-baseweb="select"] > div {
    color: #000000 !important;
}
div[data-baseweb="select"] span {
    color: #000000 !important;
}

/* selectbox 드롭다운 옵션 - 검정색 글자 */
ul[role="listbox"] li {
    color: #000000 !important;
}

/* multiselect 태그 스타일 유지 (거래유형 태그) */
span[data-baseweb="tag"] {
    background-color: #4a90e2 !important;
    color: white !important;
}

/* text input 글자색 */
input[type="text"], textarea {
    color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)

# 비밀번호 해싱 함수
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 로그인 체크
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    return st.session_state.logged_in

# 로그인 화면
def login_page():
    st.markdown("<h1 style='text-align: center; color: #4a90e2;'>🔐 누리엠알오 장부관리</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #cccccc;'>로그인이 필요합니다</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("🔓 로그인", use_container_width=True, type="primary"):
                # 비밀번호: 1248
                correct_hash = hash_password("1248")
                input_hash = hash_password(password)
                
                if input_hash == correct_hash:
                    st.session_state.logged_in = True
                    st.success("✅ 로그인 성공!")
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 틀렸습니다.")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **비밀번호를 잊으셨나요?**\n\n관리자에게 문의하세요.")

# 로그아웃 함수
def logout():
    st.session_state.logged_in = False
    st.rerun()

# 커스텀 CSS - 세련된 다크 테마 (글자 2/3 크기)
st.markdown("""
<style>
    /* ==================== 전체 배경 ==================== */
    .stApp {
        background-color: #0f0f0f !important;
        color: #e0e0e0 !important;
    }
    
    /* 메인 컨텐츠 영역 */
    .main .block-container {
        background-color: #0f0f0f !important;
        padding: 1.5rem !important;
        max-width: 1400px !important;
    }
    
    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #ffffff !important;
    }
    
    /* ==================== 텍스트 스타일 (2/3 크기) ==================== */
    /* 일반 텍스트 */
    .stApp p, .stApp span, .stApp div, .stApp label {
        color: #e0e0e0 !important;
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }
    
    /* 제목 */
    h1 {
        color: #4fc3f7 !important;
        font-size: 2.0rem !important;
        font-weight: 700 !important;
        margin-bottom: 1.5rem !important;
        border-bottom: 2px solid #1e88e5 !important;
        padding-bottom: 0.5rem !important;
    }
    
    h2 {
        color: #81c784 !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        color: #ffb74d !important;
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        margin-bottom: 0.8rem !important;
    }
    
    h4 {
        color: #e0e0e0 !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }
    
    /* ==================== 입력 필드 ==================== */
    /* 텍스트 입력 */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 3px solid #666666 !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 8px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #4a90e2 !important;
        box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2) !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #888888 !important;
        font-weight: 500 !important;
    }
    
    /* 텍스트 영역 */
    .stTextArea > div > div > textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 3px solid #666666 !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 8px !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #4a90e2 !important;
        box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2) !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: #888888 !important;
        font-weight: 500 !important;
    }
    
    /* 숫자 입력 */
    .stNumberInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 3px solid #666666 !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 8px !important;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #4a90e2 !important;
        box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2) !important;
    }
    
    /* 날짜 입력 */
    .stDateInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 3px solid #666666 !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 8px !important;
    }
    
    .stDateInput > div > div > input:focus {
        border-color: #4a90e2 !important;
        box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2) !important;
    }
    
    /* ==================== 드롭다운 (셀렉트박스) - 선택값 보이게! ==================== */
    /* 드롭다운 컨테이너 */
    .stSelectbox > div > div {
        background-color: #ffffff !important;
        border: 3px solid #666666 !important;
        border-radius: 8px !important;
    }
    
    /* 드롭다운 기본 스타일 */
    .stSelectbox [data-baseweb="select"] {
        background-color: #ffffff !important;
    }
    
    /* 드롭다운 선택된 값을 담는 컨테이너 */
    .stSelectbox [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        padding: 10px !important;
    }
    
    /* 선택된 값 텍스트 - 최우선 적용! */
    .stSelectbox [data-baseweb="select"] > div > div {
        color: #000000 !important;
        background-color: transparent !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div > div > div {
        color: #000000 !important;
    }
    
    /* 모든 span 태그 */
    .stSelectbox [data-baseweb="select"] span {
        color: #000000 !important;
    }
    
    /* input 태그 (검색용) */
    .stSelectbox [data-baseweb="select"] input {
        color: #000000 !important;
        caret-color: #000000 !important;
    }
    
    /* placeholder */
    .stSelectbox [data-baseweb="select"] input::placeholder {
        color: #666666 !important;
    }
    
    /* 선택된 값을 보여주는 모든 요소에 강제 적용 */
    .stSelectbox div[role="button"] {
        color: #000000 !important;
    }
    
    .stSelectbox div[role="button"] * {
        color: #000000 !important;
    }
    
    /* 드롭다운 화살표 */
    .stSelectbox svg {
        fill: #000000 !important;
    }
    
    /* 드롭다운 열렸을 때 메뉴 */
    [data-baseweb="popover"] {
        background-color: #ffffff !important;
        border: 2px solid #666666 !important;
    }
    
    /* 드롭다운 옵션 리스트 */
    [role="listbox"] {
        background-color: #ffffff !important;
    }
    
    /* 드롭다운 각 옵션 */
    [role="option"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        padding: 12px 16px !important;
    }
    
    /* 드롭다운 옵션 호버 */
    [role="option"]:hover {
        background-color: #e8e8e8 !important;
        color: #000000 !important;
    }
    
    /* 드롭다운 선택된 옵션 */
    [role="option"][aria-selected="true"] {
        background-color: #d0d0d0 !important;
        color: #000000 !important;
        font-weight: 700 !important;
    }
    
    /* ==================== 멀티셀렉트 ==================== */
    .stMultiSelect [data-baseweb="select"] {
        background-color: #1e1e1e !important;
        border: 2px solid #424242 !important;
    }
    
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #1e88e5 !important;
        color: #ffffff !important;
        font-size: 0.95rem !important;
    }
    
    /* ==================== 버튼 ==================== */
    .stButton > button {
        background-color: #4a90e2 !important;
        color: #ffffff !important;
        border: none !important;
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        padding: 16px 32px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #357abd !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4) !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #28a745 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #218838 !important;
    }
    
    .stButton > button[kind="secondary"] {
        background-color: #6c757d !important;
    }
    
    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background-color: #17a2b8 !important;
        color: #ffffff !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        padding: 14px 28px !important;
    }
    
    /* ==================== 라디오 버튼 ==================== */
    .stRadio > div {
        gap: 1rem !important;
    }
    
    .stRadio [role="radiogroup"] label {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
        padding: 12px 20px !important;
        border-radius: 8px !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        border: 2px solid #4a4a4a !important;
        cursor: pointer !important;
    }
    
    .stRadio [role="radiogroup"] label:hover {
        background-color: #3a3a3a !important;
        border-color: #6a6a6a !important;
    }
    
    .stRadio [role="radiogroup"] [data-checked="true"] label {
        background-color: #4a90e2 !important;
        border-color: #4a90e2 !important;
        color: #ffffff !important;
    }
    
    /* 라디오 버튼 원형 아이콘 */
    .stRadio input[type="radio"] {
        width: 20px !important;
        height: 20px !important;
    }
    
    /* ==================== 체크박스 ==================== */
    .stCheckbox label {
        font-size: 1.0rem !important;
        font-weight: 500 !important;
        color: #e0e0e0 !important;
    }
    
    /* ==================== 메트릭 (지표) ==================== */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #4fc3f7 !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        color: #b0b0b0 !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem !important;
    }
    
    /* ==================== 데이터프레임 ==================== */
    .stDataFrame {
        font-size: 0.95rem !important;
    }
    
    .stDataFrame [data-testid="stDataFrameResizable"] {
        background-color: #1a1a1a !important;
        border: 1px solid #424242 !important;
        border-radius: 6px !important;
    }
    
    /* ==================== 정보 박스 ==================== */
    .stInfo {
        background-color: #1e3a5f !important;
        border-left: 4px solid #1e88e5 !important;
        padding: 12px 16px !important;
        border-radius: 6px !important;
        font-size: 1.0rem !important;
    }
    
    .stSuccess {
        background-color: #1b5e20 !important;
        border-left: 4px solid #43a047 !important;
        padding: 12px 16px !important;
        border-radius: 6px !important;
        font-size: 1.0rem !important;
    }
    
    .stWarning {
        background-color: #5d4037 !important;
        border-left: 4px solid #ff9800 !important;
        padding: 12px 16px !important;
        border-radius: 6px !important;
        font-size: 1.0rem !important;
    }
    
    .stError {
        background-color: #5d1f1f !important;
        border-left: 4px solid #f44336 !important;
        padding: 12px 16px !important;
        border-radius: 6px !important;
        font-size: 1.0rem !important;
    }
    
    /* ==================== 탭 ==================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1e1e1e !important;
        color: #b0b0b0 !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 10px 20px !important;
        font-size: 1.0rem !important;
        font-weight: 500 !important;
        border: none !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1e88e5 !important;
        color: #ffffff !important;
    }
    
    /* ==================== 마크다운 ==================== */
    .stMarkdown {
        color: #e0e0e0 !important;
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }
    
    .stMarkdown a {
        color: #4fc3f7 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
    }
    
    .stMarkdown a:hover {
        color: #81d4fa !important;
        text-decoration: underline !important;
    }
    
    /* ==================== 로딩 스피너 ==================== */
    .stSpinner > div {
        border-top-color: #1e88e5 !important;
    }
    
    /* ==================== 사이드바 메뉴 ==================== */
    [data-testid="stSidebar"] .stRadio > label {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    
    /* ==================== 추가 미세 조정 ==================== */
    input::placeholder, textarea::placeholder {
        color: #757575 !important;
        opacity: 1 !important;
    }
    
    /* 포커스 상태 */
    input:focus, textarea:focus, select:focus {
        outline: none !important;
        border-color: #1e88e5 !important;
        box-shadow: 0 0 0 3px rgba(30, 136, 229, 0.2) !important;
    }
    
    /* 스크롤바 */
    ::-webkit-scrollbar {
        width: 8px !important;
        height: 8px !important;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a1a !important;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #424242 !important;
        border-radius: 4px !important;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #616161 !important;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 파일 경로
DATA_FILE = "data/ledger.csv"
BASE_RECEIVABLE_FILE = "data/base_receivables.csv"
PRODUCTS_FILE = "data/products.csv"
INVENTORY_FILE = "data/inventory.csv"
COMPANY_FILE = "data/company_info.csv"

# 세션 상태 초기화
if True:  # 항상 최신 파일 읽기
    if os.path.exists(DATA_FILE):
        try:
            st.session_state.ledger_df = pd.read_csv(DATA_FILE)
            # 날짜 컬럼 변환
            if '날짜' in st.session_state.ledger_df.columns:
                st.session_state.ledger_df['날짜'] = pd.to_datetime(st.session_state.ledger_df['날짜'], errors='coerce')
            # 기존 데이터에 비고 컬럼이 없으면 추가
            if '비고' not in st.session_state.ledger_df.columns:
                st.session_state.ledger_df['비고'] = ''
            # 합계 컬럼이 없으면 추가
            if '합계' not in st.session_state.ledger_df.columns:
                st.session_state.ledger_df['합계'] = st.session_state.ledger_df['공급가액'].fillna(0) + st.session_state.ledger_df['부가세'].fillna(0)
            # ✅ 2019-08-01 이전 불필요한 데이터 필터링 (로딩 속도 향상)
            st.session_state.ledger_df = st.session_state.ledger_df[
                st.session_state.ledger_df['날짜'] >= '2019-08-01'
            ].reset_index(drop=True)
        except Exception as e:
            st.error(f"데이터 로딩 오류: {e}")
            st.session_state.ledger_df = pd.DataFrame(columns=['날짜', '거래처', '품목', '수량', '단가', '공급가액', '부가세', '합계', '참조', '비고'])
    else:
        st.session_state.ledger_df = pd.DataFrame(columns=['날짜', '거래처', '품목', '수량', '단가', '공급가액', '부가세', '합계', '참조', '비고'])

# 기초 미수금 초기화
if 'base_receivables_df' not in st.session_state:
    if os.path.exists(BASE_RECEIVABLE_FILE):
        st.session_state.base_receivables_df = pd.read_csv(BASE_RECEIVABLE_FILE)
    else:
        st.session_state.base_receivables_df = pd.DataFrame(columns=['거래처', '기초미수금', '기준일자'])

# 품목 데이터 초기화
if 'products_df' not in st.session_state:
    if os.path.exists(PRODUCTS_FILE):
        st.session_state.products_df = pd.read_csv(PRODUCTS_FILE)
    else:
        st.session_state.products_df = pd.DataFrame(columns=['품목코드', '품목명', '카테고리', '규격'])

# 재고 데이터 초기화
if 'inventory_df' not in st.session_state:
    if os.path.exists(INVENTORY_FILE):
        st.session_state.inventory_df = pd.read_csv(INVENTORY_FILE)
    else:
        st.session_state.inventory_df = pd.DataFrame(columns=['품목명', '기초재고', '현재재고', '기준일자', '안전재고', '단위'])

# 사업자 정보 초기화
if 'company_info' not in st.session_state:
    import json
    company_json_file = "data/company_info.json"
    
    # JSON 파일 우선 시도
    if os.path.exists(company_json_file):
        try:
            with open(company_json_file, 'r', encoding='utf-8') as f:
                st.session_state.company_info = json.load(f)
        except:
            st.session_state.company_info = {
                '상호': '누리엠알오',
                '대표자': '박수영',
                '사업자번호': '320-14-00707',
                '주소': '대전광역시 유성구 복용로11번길 6-35',
                '전화번호': '010-6473-1246',
                '팩스번호': '042-367-1246'
            }
    # 기존 CSV 파일 시도 (하위 호환)
    elif os.path.exists(COMPANY_FILE):
        try:
            company_df = pd.read_csv(COMPANY_FILE)
            if len(company_df) > 0:
                st.session_state.company_info = company_df.iloc[0].to_dict()
            else:
                st.session_state.company_info = {
                    '상호': '누리엠알오',
                    '대표자': '박수영',
                    '사업자번호': '320-14-00707',
                    '주소': '대전광역시 유성구 복용로11번길 6-35',
                    '전화번호': '010-6473-1246',
                    '팩스번호': '042-367-1246'
                }
        except:
            st.session_state.company_info = {
                '상호': '누리엠알오',
                '대표자': '박수영',
                '사업자번호': '320-14-00707',
                '주소': '대전광역시 유성구 복용로11번길 6-35',
                '전화번호': '010-6473-1246',
                '팩스번호': '042-367-1246'
            }
    else:
        st.session_state.company_info = {
            '상호': '누리엠알오',
            '대표자': '박수영',
            '사업자번호': '320-14-00707',
            '주소': '대전광역시 유성구 복용로11번길 6-35',
            '전화번호': '010-6473-1246',
            '팩스번호': '042-367-1246'
        }

# 데이터 저장 함수
def save_data():
    # 저장 전 날짜순 정렬
    if len(st.session_state.ledger_df) > 0:
        st.session_state.ledger_df['날짜'] = pd.to_datetime(st.session_state.ledger_df['날짜'])
        st.session_state.ledger_df = st.session_state.ledger_df.sort_values('날짜').reset_index(drop=True)
    st.session_state.ledger_df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

def calculate_receivable(거래처, df=None):
    """거래처별 미수금 계산 - 기초미수금에 등록된 거래처만"""
    if df is None:
        df = st.session_state.ledger_df
    
    base_recv = st.session_state.base_receivables_df
    
    if len(base_recv) == 0:
        return 0
    
    거래처_기초 = base_recv[base_recv['거래처'] == 거래처]
    if len(거래처_기초) == 0:
        return 0  # 등록 안된 거래처는 미수금 0
    
    기초값 = 거래처_기초['기초미수금'].values[0]
    if 기초값 <= 0:
        return 0
    
    기초미수금 = 기초값
    
    try:
        기준일자 = pd.to_datetime(str(거래처_기초['기준일자'].values[0]))
    except:
        return 기초미수금
    
    if len(df) == 0:
        return 기초미수금
    
    거래처df = df[df['거래처'] == 거래처].copy()
    if len(거래처df) == 0:
        return 기초미수금
    
    거래처df['날짜'] = pd.to_datetime(거래처df['날짜'])
    거래처df = 거래처df[거래처df['날짜'] > 기준일자]
    
    if len(거래처df) == 0:
        return 기초미수금
    
    판매m = (거래처df['참조'] == '=외출') | ((거래처df['공급가액'] > 0) & (~거래처df['참조'].fillna('').str.contains('입금|출금')))
    입금m = (거래처df['참조'] == '=입금') | (거래처df['참조'].fillna('').str.contains('입금'))
    
    총판매 = 거래처df.loc[판매m, '공급가액'].sum()
    총부가세 = 거래처df.loc[판매m, '부가세'].sum()
    총입금 = 거래처df.loc[입금m, '공급가액'].sum()
    
    return 기초미수금 + 총판매 + 총부가세 - 총입금

def calculate_payable(거래처, df=None):
    """거래처별 미지급금 계산 - 기초미수금에 등록된 거래처만"""
    if df is None:
        df = st.session_state.ledger_df
    
    base_recv = st.session_state.base_receivables_df
    
    if len(base_recv) == 0:
        return 0
    
    거래처_기초 = base_recv[base_recv['거래처'] == 거래처]
    if len(거래처_기초) == 0:
        return 0
    
    기초값 = 거래처_기초['기초미수금'].values[0]
    if 기초값 >= 0:
        return 0
    
    기초미지급금 = abs(기초값)
    
    try:
        기준일자 = pd.to_datetime(str(거래처_기초['기준일자'].values[0]))
    except:
        return 기초미지급금
    
    if len(df) == 0:
        return 기초미지급금
    
    거래처df = df[df['거래처'] == 거래처].copy()
    if len(거래처df) == 0:
        return 기초미지급금
    
    거래처df['날짜'] = pd.to_datetime(거래처df['날짜'])
    거래처df = 거래처df[거래처df['날짜'] > 기준일자]
    
    if len(거래처df) == 0:
        return 기초미지급금
    
    매입m = (거래처df['참조'] == '=외입') | ((거래처df['공급가액'] < 0) & (~거래처df['참조'].fillna('').str.contains('출금|입금')))
    출금m = (거래처df['참조'] == '=출금') | (거래처df['참조'].fillna('').str.contains('출금'))
    
    총매입 = abs(거래처df.loc[매입m, '공급가액'].sum())
    총부가세 = abs(거래처df.loc[매입m, '부가세'].sum())
    총출금 = abs(거래처df.loc[출금m, '공급가액'].sum())
    
    return 기초미지급금 + 총매입 + 총부가세 - 총출금

def calculate_all_receivables(df=None):
    """전체 미수금 - 기초미수금에 등록된 거래처만"""
    if df is None:
        df = st.session_state.ledger_df
    base_recv = st.session_state.base_receivables_df.copy()
    
    if len(base_recv) == 0:
        return pd.DataFrame(columns=['거래처', '미수금', '최근거래일'])
    
    미수금_거래처 = base_recv[base_recv['기초미수금'] > 0]['거래처'].unique()
    
    결과 = []
    for 거래처 in 미수금_거래처:
        미수금 = calculate_receivable(거래처, df)
        if 미수금 > 0:
            거래처df = df[df['거래처'] == 거래처] if len(df) > 0 else pd.DataFrame()
            if len(거래처df) > 0:
                최근일 = pd.to_datetime(거래처df['날짜']).max().strftime('%Y-%m-%d')
            else:
                거래처_기초 = base_recv[base_recv['거래처'] == 거래처]
                최근일 = 거래처_기초['기준일자'].values[0] if len(거래처_기초) > 0 else ''
            결과.append({'거래처': 거래처, '미수금': 미수금, '최근거래일': 최근일})
    
    if not 결과:
        return pd.DataFrame(columns=['거래처', '미수금', '최근거래일'])
    return pd.DataFrame(결과).sort_values('미수금', ascending=False)

def calculate_all_payables(df=None):
    """전체 미지급금 - 기초미수금에 등록된 거래처만"""
    if df is None:
        df = st.session_state.ledger_df
    base_recv = st.session_state.base_receivables_df.copy()
    
    if len(base_recv) == 0:
        return pd.DataFrame(columns=['거래처', '미지급금', '최근거래일'])
    
    미지급금_거래처 = base_recv[base_recv['기초미수금'] < 0]['거래처'].unique()
    
    결과 = []
    for 거래처 in 미지급금_거래처:
        미지급금 = calculate_payable(거래처, df)
        if 미지급금 > 0:
            거래처df = df[df['거래처'] == 거래처] if len(df) > 0 else pd.DataFrame()
            if len(거래처df) > 0:
                최근일 = pd.to_datetime(거래처df['날짜']).max().strftime('%Y-%m-%d')
            else:
                거래처_기초 = base_recv[base_recv['거래처'] == 거래처]
                최근일 = 거래처_기초['기준일자'].values[0] if len(거래처_기초) > 0 else ''
            결과.append({'거래처': 거래처, '미지급금': 미지급금, '최근거래일': 최근일})
    
    if not 결과:
        return pd.DataFrame(columns=['거래처', '미지급금', '최근거래일'])
    return pd.DataFrame(결과).sort_values('미지급금', ascending=False)


def save_base_receivables():
    st.session_state.base_receivables_df.to_csv(BASE_RECEIVABLE_FILE, index=False, encoding='utf-8-sig')

def save_products():
    st.session_state.products_df.to_csv(PRODUCTS_FILE, index=False, encoding='utf-8-sig')

def save_inventory():
    st.session_state.inventory_df.to_csv(INVENTORY_FILE, index=False, encoding='utf-8-sig')

def save_company_info():
    """사업자 정보를 JSON 파일로 저장"""
    import json
    company_json_file = "data/company_info.json"
    try:
        with open(company_json_file, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.company_info, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"사업자 정보 저장 오류: {e}")

def create_invoice_html(거래처, 날짜, 거래_목록):
    """거래명세서 HTML 생성 - A4 세로 2분할 (공급받는자용/공급자용)"""
    
    # 사업자 정보 가져오기
    company = st.session_state.company_info
    
    총공급가액 = sum([g.get('공급가액', 0) for g in 거래_목록])
    총부가세 = sum([g.get('부가세', 0) for g in 거래_목록])
    
    # 거래 항목 HTML (최대 10개 표시)
    거래_rows = ""
    for i, 거래 in enumerate(거래_목록[:10], 1):
        품목 = str(거래.get('품목', ''))[:25]
        수량 = 거래.get('수량', 0)
        단가 = 거래.get('단가', 0)
        금액 = 거래.get('공급가액', 0)
        
        거래_rows += f"""
        <tr>
            <td class="center">{i}</td>
            <td>{품목}</td>
            <td class="right">{수량:,.0f}</td>
            <td class="right">{단가:,.0f}</td>
            <td class="right">{금액:,.0f}</td>
        </tr>
        """
    
    # 빈 행 추가 (10행 맞추기)
    for i in range(len(거래_목록[:10]), 10):
        거래_rows += """
        <tr>
            <td class="center">&nbsp;</td>
            <td>&nbsp;</td>
            <td>&nbsp;</td>
            <td>&nbsp;</td>
            <td>&nbsp;</td>
        </tr>
        """
    
    # 한 장에 들어갈 명세서 HTML (공급받는자용 또는 공급자용)
    def make_invoice_section(용도):
        return f"""
        <div class="invoice-section">
            <div class="invoice-header">
                <span class="title">거 래 명 세 서</span>
                <span class="usage">({용도})</span>
            </div>
            
            <table class="info-table">
                <tr>
                    <td class="label" style="width:15%;">공급받는자</td>
                    <td style="width:35%;">{거래처}</td>
                    <td class="label" style="width:15%;">공 급 자</td>
                    <td style="width:35%;">{company.get('상호', '누리엠알오')}</td>
                </tr>
                <tr>
                    <td class="label">거 래 일</td>
                    <td>{날짜}</td>
                    <td class="label">대 표 자</td>
                    <td>{company.get('대표자', '')} (인)</td>
                </tr>
                <tr>
                    <td class="label">사업자번호</td>
                    <td></td>
                    <td class="label">사업자번호</td>
                    <td>{company.get('사업자번호', '320-14-00707')}</td>
                </tr>
                <tr>
                    <td class="label">주 소</td>
                    <td></td>
                    <td class="label">주 소</td>
                    <td style="font-size:9px;">{company.get('주소', '')}</td>
                </tr>
                <tr>
                    <td class="label">전 화</td>
                    <td></td>
                    <td class="label">전 화</td>
                    <td>{company.get('전화번호', '')}</td>
                </tr>
            </table>
            
            <table class="main-table">
                <thead>
                    <tr>
                        <th style="width:8%;">No</th>
                        <th style="width:40%;">품 목</th>
                        <th style="width:14%;">수량</th>
                        <th style="width:18%;">단가</th>
                        <th style="width:20%;">금액</th>
                    </tr>
                </thead>
                <tbody>
                    {거래_rows}
                </tbody>
            </table>
            
            <table class="summary-table">
                <tr>
                    <td class="label">공급가액</td>
                    <td class="right">{총공급가액:,.0f}</td>
                    <td class="label">부가세</td>
                    <td class="right">{총부가세:,.0f}</td>
                    <td class="label total-label">합 계</td>
                    <td class="right total-value">{총공급가액 + 총부가세:,.0f}</td>
                </tr>
            </table>
            
            <div class="footer-text">위와 같이 거래합니다.</div>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>거래명세서 - {거래처}</title>
        <style>
            @page {{ size: A4 portrait; margin: 5mm; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; 
                font-size: 10px;
                width: 210mm;
                background: white;
            }}
            .page {{
                width: 200mm;
                height: 290mm;
                margin: 0 auto;
                padding: 3mm;
            }}
            .invoice-section {{
                height: 143mm;
                border: 1px solid #000;
                padding: 3mm;
                margin-bottom: 2mm;
            }}
            .invoice-header {{
                text-align: center;
                margin-bottom: 3mm;
                border-bottom: 2px solid #000;
                padding-bottom: 2mm;
            }}
            .title {{
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 8px;
            }}
            .usage {{
                font-size: 11px;
                margin-left: 10px;
            }}
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 3mm;
            }}
            .info-table td {{
                border: 1px solid #333;
                padding: 2px 4px;
                height: 18px;
            }}
            .info-table .label {{
                background-color: #f0f0f0;
                font-weight: bold;
                text-align: center;
            }}
            .main-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 3mm;
            }}
            .main-table th, .main-table td {{
                border: 1px solid #333;
                padding: 2px 4px;
                height: 16px;
            }}
            .main-table th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 2mm;
            }}
            .summary-table td {{
                border: 1px solid #333;
                padding: 3px 5px;
                height: 22px;
            }}
            .summary-table .label {{
                background-color: #f0f0f0;
                font-weight: bold;
                text-align: center;
                width: 12%;
            }}
            .summary-table .right {{
                text-align: right;
                width: 18%;
            }}
            .summary-table .total-label {{
                background-color: #ddd;
            }}
            .summary-table .total-value {{
                font-weight: bold;
                font-size: 12px;
            }}
            .center {{ text-align: center; }}
            .right {{ text-align: right; }}
            .footer-text {{
                text-align: center;
                margin-top: 3mm;
                font-size: 10px;
            }}
            @media print {{
                body {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
            }}
        </style>
    </head>
    <body>
        <div class="page">
            {make_invoice_section("공급받는자 보관용")}
            {make_invoice_section("공급자 보관용")}
        </div>
    </body>
    </html>
    """
    return html

# ==================== 로그인 체크 ====================
if not check_login():
    login_page()
    st.stop()

# ==================== 메인 애플리케이션 ====================
# 사이드바 - 메뉴
st.sidebar.title("📋 장부 관리 시스템")
st.sidebar.markdown("---")

# 첫 화면을 거래처 관리로 설정
if 'first_load' not in st.session_state:
    st.session_state.first_load = True
    st.session_state.default_menu = "👥 거래처 관리"

menu_list = ["🏠 대시보드", "➕ 거래 입력", "📄 거래 내역", "📊 통계 분석", "💰 외상 관리", "🧾 회계 관리", "📦 품목 관리", "📋 재고 관리", "👥 거래처 관리", "📅 방문 일정", "📝 영업 일지", "📜 협약서 관리", "🔧 설정"]
default_index = menu_list.index("👥 거래처 관리") if st.session_state.get('first_load', False) else 0

menu = st.sidebar.radio(
    "메뉴 선택",
    menu_list,
    index=default_index
)

# 첫 로드 후 플래그 해제
if st.session_state.get('first_load', False):
    st.session_state.first_load = False

# ==================== 대시보드 ====================
if menu == "🏠 대시보드":
    st.title("📊 대시보드")
    
    df = st.session_state.ledger_df.copy()
    
    if len(df) == 0:
        st.info("아직 거래 내역이 없습니다. '거래 입력' 메뉴에서 데이터를 추가해주세요.")
    else:
        # 최근 4개년도만 표시
        당해연도 = get_kst_now().year
        연도_목록 = [당해연도, 당해연도-1, 당해연도-2, 당해연도-3]
        연도_라벨 = [f"{당해연도}년 (당해)", f"{당해연도-1}년", f"{당해연도-2}년", f"{당해연도-3}년"]
        
        # 연도 선택 + 월 선택
        col1, col2 = st.columns(2)
        with col1:
            선택_연도_idx = st.selectbox("연도 선택", range(len(연도_라벨)), format_func=lambda i: 연도_라벨[i])
            선택_연도 = 연도_목록[선택_연도_idx]
        with col2:
            월_옵션 = ["전체"] + [f"{m}월" for m in range(1, 13)]
            선택_월 = st.selectbox("월 선택", 월_옵션, index=get_kst_now().month if 선택_연도 == 당해연도 else 0)
        
        # 날짜 필터링
        df['연도'] = df['날짜'].dt.year
        df_filtered = df[df['연도'] == 선택_연도].copy()
        
        if 선택_월 != "전체":
            월_숫자 = int(선택_월.replace("월", ""))
            df_filtered = df_filtered[df_filtered['날짜'].dt.month == 월_숫자]
        
        # 주요 지표
        st.markdown(f"### 📈 {선택_연도}년 {선택_월} 주요 지표")
        
        # 수입/지출 계산
        입금_df = df_filtered[df_filtered['참조'].str.contains('입금', na=False)]
        출금_df = df_filtered[df_filtered['참조'].str.contains('출금', na=False)]
        외입_df = df_filtered[df_filtered['참조'].str.contains('외입', na=False)]
        외출_df = df_filtered[df_filtered['참조'].str.contains('외출', na=False)]
        
        총수입 = 입금_df['공급가액'].sum()
        총지출 = abs(출금_df['공급가액'].sum())
        # 외입은 음수이므로 절대값으로 매입금액 계산
        총매입 = abs(외입_df['공급가액'].sum())
        총매입부가세 = abs(외입_df['부가세'].sum())
        # 외출(판매) 금액
        총매출 = 외출_df['공급가액'].sum() + 외출_df['부가세'].sum()
        순이익 = 총수입 - 총지출
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("💰 총 수입", f"{총수입:,.0f}원")
        with col2:
            st.metric("💸 총 지출", f"{총지출:,.0f}원")
        with col3:
            st.metric("📦 총 매입", f"{총매입:,.0f}원")
        with col4:
            st.metric("💵 순이익", f"{순이익:,.0f}원", delta=f"{(순이익/총수입*100):.1f}%" if 총수입 > 0 else "0%")
        with col5:
            st.metric("🧾 총 매출", f"{총매출:,.0f}원")
        
        st.markdown("---")
        
        # 차트
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📅 일별 수입/지출 추이")
            
            # 일별 집계
            입금_daily = 입금_df.groupby(입금_df['날짜'].dt.date)['공급가액'].sum().reset_index()
            입금_daily.columns = ['날짜', '수입']
            
            출금_daily = 출금_df.groupby(출금_df['날짜'].dt.date)['공급가액'].sum().abs().reset_index()
            출금_daily.columns = ['날짜', '지출']
            
            # 병합
            daily_df = pd.merge(입금_daily, 출금_daily, on='날짜', how='outer').fillna(0)
            
            if len(daily_df) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=daily_df['날짜'], y=daily_df['수입'], name='수입', marker_color='#2E7D32'))
                fig.add_trace(go.Bar(x=daily_df['날짜'], y=daily_df['지출'], name='지출', marker_color='#C62828'))
                fig.update_layout(barmode='group', height=400, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("해당 기간 데이터가 없습니다.")
        
        with col2:
            st.markdown("### 🏢 주요 거래처 TOP 10")
            
            # 거래처별 집계
            거래처_sum = df_filtered[df_filtered['참조'].str.contains('입금', na=False)].groupby('거래처')['공급가액'].sum().sort_values(ascending=False).head(10)
            
            if len(거래처_sum) > 0:
                fig = px.bar(
                    x=거래처_sum.values,
                    y=거래처_sum.index,
                    orientation='h',
                    labels={'x': '금액 (원)', 'y': '거래처'},
                    color=거래처_sum.values,
                    color_continuous_scale='Greens'
                )
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("해당 기간 데이터가 없습니다.")
        
        # 월별 통계
        st.markdown("### 📆 월별 통계")
        
        df_filtered['년월'] = df_filtered['날짜'].dt.to_period('M').astype(str)
        
        월별_입금 = df_filtered[df_filtered['참조'].str.contains('입금', na=False)].groupby('년월')['공급가액'].sum()
        월별_출금 = df_filtered[df_filtered['참조'].str.contains('출금', na=False)].groupby('년월')['공급가액'].sum().abs()
        월별_매입 = df_filtered[df_filtered['참조'].str.contains('외입', na=False)].groupby('년월')['공급가액'].sum().abs()
        
        월별_df = pd.DataFrame({
            '수입': 월별_입금,
            '지출': 월별_출금,
            '매입': 월별_매입,
            '순이익': 월별_입금 - 월별_출금
        }).fillna(0)
        
        월별_df = 월별_df.applymap(lambda x: f"{x:,.0f}")
        st.dataframe(월별_df, use_container_width=True)

# ==================== 거래 입력 ====================
elif menu == "➕ 거래 입력":
    st.title("➕ 거래 입력")
    
    df = st.session_state.ledger_df
    products_df = st.session_state.products_df
    
    # 기존 거래처 목록
    거래처_list = sorted(df['거래처'].dropna().unique().tolist()) if len(df) > 0 else []
    
    # ========== 다중 품목 입력을 위한 session_state 초기화 ==========
    if '입력중_품목_리스트' not in st.session_state:
        st.session_state.입력중_품목_리스트 = []
    
    # ========== 상단: 거래 기본 정보 ==========
    st.markdown("### 📋 거래 기본 정보")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        거래일자 = st.date_input("거래 날짜", value=get_kst_now())
    with col2:
        # 거래처 입력
        거래처_입력방식 = st.radio("", ["기존 거래처", "새 거래처"], horizontal=True, key="거래처방식")
        if 거래처_입력방식 == "기존 거래처":
            거래처 = st.selectbox("거래처 선택", [""] + 거래처_list, key="거래처선택")
        else:
            거래처 = st.text_input("거래처명 입력", key="거래처입력")
    with col3:
        거래유형 = st.selectbox("거래 유형", ["=외출 (판매)", "=입금 (수금)", "=외입 (매입)", "=출금 (결제)", "=기타 (할인/조정)", "=샘플 (무상제공)"])
        거래유형_값 = 거래유형.split(" ")[0]
    
    # ✅ 선택된 거래처 표시 + 미수금 (시인성 개선 - 검정색 글자)
    if 거래처:
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"""
            <div style='background-color: #e3f2fd; border: 2px solid #1565c0; border-radius: 10px; padding: 15px;'>
                <h3 style='color: #000000; margin: 0; font-size: 20px;'>🏢 {거래처}</h3>
            </div>
            """, unsafe_allow_html=True)
        with col_info2:
            미수금 = calculate_receivable(거래처)
            if 미수금 > 0:
                st.markdown(f"""
                <div style='background-color: #fff3e0; border: 2px solid #e65100; border-radius: 10px; padding: 15px;'>
                    <h3 style='color: #000000; margin: 0; font-size: 20px;'>⚠️ 미수금: {미수금:,.0f}원</h3>
                </div>
                """, unsafe_allow_html=True)
            elif 미수금 < 0:
                st.markdown(f"""
                <div style='background-color: #e8f5e9; border: 2px solid #2e7d32; border-radius: 10px; padding: 15px;'>
                    <h3 style='color: #000000; margin: 0; font-size: 20px;'>💰 선수금: {abs(미수금):,.0f}원</h3>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background-color: #e8f5e9; border: 2px solid #2e7d32; border-radius: 10px; padding: 15px;'>
                    <h3 style='color: #000000; margin: 0; font-size: 20px;'>✅ 미수금 없음</h3>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== 입금/출금인 경우 금액만 입력 ==========
    if 거래유형_값 in ["=입금", "=출금"]:
        st.markdown("### 💰 입금/출금 입력")
        
        col_money1, col_money2 = st.columns(2)
        with col_money1:
            입금_금액 = st.number_input("금액", min_value=0, value=0, step=10000, key="입금금액")
        with col_money2:
            입금_비고 = st.text_input("비고 (선택)", placeholder="예: 현금, 계좌이체 등", key="입금비고")
        
        st.markdown(f"**입력 금액:** {입금_금액:,.0f}원")
        
        if st.button("💾 저장", type="primary", use_container_width=True, key="입금저장"):
            if 거래처 and 입금_금액 > 0:
                # 입금/출금 거래 저장
                new_row = pd.DataFrame([{
                    '날짜': pd.to_datetime(거래날짜).strftime('%Y-%m-%d'),
                    '거래처': 거래처,
                    '품목': '입금' if 거래유형_값 == "=입금" else '출금',
                    '수량': 0,
                    '단가': 0,
                    '매입단가': 0,
                    '공급가액': 입금_금액,
                    '부가세': 0,
                    '합계': 입금_금액,
                    '마진': 0,
                    '참조': 거래유형_값,
                    '비고': 입금_비고 if 입금_비고 else ''
                }])
                
                st.session_state.ledger_df = pd.concat([st.session_state.ledger_df, new_row], ignore_index=True)
                save_data()
                
                st.success(f"✅ {거래처} {'입금' if 거래유형_값 == '=입금' else '출금'} {입금_금액:,.0f}원 저장!")
                st.rerun()
            else:
                st.error("❌ 거래처와 금액을 입력해주세요.")
    
    # ========== 판매/매입인 경우 품목 입력 ==========
    else:
        st.markdown("### 📦 품목 추가")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # 품목 입력 방식
        품목입력방식 = st.radio("", ["품목 검색", "직접 입력"], horizontal=True, key="품목방식")
        
        # 선택된 품목의 최근 가격 정보 저장용
        if '선택품목_최근단가' not in st.session_state:
            st.session_state.선택품목_최근단가 = 0
        
        if 품목입력방식 == "품목 검색":
            검색어 = st.text_input("품목명 또는 코드 검색", placeholder="예: 절단석, 001", key="품목검색")
            
            if len(products_df) > 0 and 검색어:
                if 검색어.isdigit():
                    검색코드 = f"P-{검색어.zfill(3)}"
                    검색결과 = products_df[products_df['품목코드'].str.contains(검색코드, case=False, na=False)]
                else:
                    검색결과 = products_df[
                        products_df['품목코드'].str.contains(검색어, case=False, na=False) |
                        products_df['품목명'].str.contains(검색어, case=False, na=False)
                    ]
                
                if len(검색결과) > 0:
                    품목_옵션 = []
                    for _, row in 검색결과.head(20).iterrows():
                        코드숫자 = row['품목코드'].replace('P-', '')
                        옵션 = f"[{코드숫자}] {row['품목명']}"
                        if pd.notna(row.get('규격', '')):
                            옵션 += f" @ {row['규격']}"
                        품목_옵션.append((옵션, row))
                    
                    선택idx = st.selectbox("검색 결과", range(len(품목_옵션)+1),
                                          format_func=lambda x: "선택하세요" if x == 0 else 품목_옵션[x-1][0],
                                          key="검색결과")
                    
                    if 선택idx > 0:
                        선택품목정보 = 품목_옵션[선택idx-1][1]
                        품목명 = f"{선택품목정보['품목명']} @ {선택품목정보.get('규격', '')}"
                        
                        # ✅ 선택된 품목 표시 (시인성 개선 - 검정색 글자)
                        st.markdown(f"""
                        <div style='background-color: #fff3e0; border: 2px solid #e65100; border-radius: 10px; padding: 12px; margin: 10px 0;'>
                            <h3 style='color: #000000; margin: 0; font-size: 18px;'>📦 {품목명}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ✅ 최근 가격 조회 - 해당 거래처 기준!
                        품목_검색명 = 선택품목정보['품목명']
                        
                        st.markdown("#### 📊 최근 거래 가격")
                        
                        # 해당 거래처의 최근 판매/매입 내역만 조회
                        if 거래처:
                            # 해당 거래처 + 해당 품목의 최근 판매 내역
                            판매내역 = df[
                                (df['거래처'] == 거래처) &
                                (df['품목'].str.contains(품목_검색명, case=False, na=False)) &
                                (df['참조'] == '=외출') &
                                (df['공급가액'] > 0)
                            ].sort_values('날짜', ascending=False)
                            
                            # 해당 거래처 + 해당 품목의 최근 매입 내역
                            매입내역 = df[
                                (df['거래처'] == 거래처) &
                                (df['품목'].str.contains(품목_검색명, case=False, na=False)) &
                                (df['참조'] == '=외입')
                            ].sort_values('날짜', ascending=False)
                        else:
                            판매내역 = pd.DataFrame()
                            매입내역 = pd.DataFrame()
                        
                        col_price1, col_price2 = st.columns(2)
                        
                        with col_price1:
                            st.markdown(f"**🔵 {거래처} 최근 판매**")
                            if len(판매내역) > 0:
                                최근단가 = 0
                                for _, row in 판매내역.head(3).iterrows():
                                    날짜_str = row['날짜'].strftime('%m/%d') if pd.notna(row['날짜']) else ''
                                    단가_값 = abs(row['단가']) if row['단가'] != 0 else (abs(row['공급가액']) / row['수량'] if row['수량'] > 0 else 0)
                                    if 최근단가 == 0 and 단가_값 > 0:
                                        최근단가 = int(단가_값)
                                    st.markdown(f"""
                                    <div style='background-color: #e3f2fd; border-radius: 5px; padding: 8px; margin: 3px 0;'>
                                        <span style='color:#1565c0;'>📅 {날짜_str}</span><br>
                                        <b style='color:#1565c0; font-size: 16px;'>💵 단가: {단가_값:,.0f}원</b>
                                    </div>
                                    """, unsafe_allow_html=True)
                                st.session_state.선택품목_최근단가 = 최근단가
                            else:
                                st.info(f"📭 {거래처} 판매 이력 없음")
                                st.session_state.선택품목_최근단가 = 0
                        
                        with col_price2:
                            st.markdown(f"**🟠 {거래처} 최근 매입**")
                            if len(매입내역) > 0:
                                for _, row in 매입내역.head(3).iterrows():
                                    날짜_str = row['날짜'].strftime('%m/%d') if pd.notna(row['날짜']) else ''
                                    단가_값 = abs(row['단가']) if row['단가'] != 0 else (abs(row['공급가액']) / abs(row['수량']) if row['수량'] != 0 else 0)
                                    st.markdown(f"""
                                    <div style='background-color: #fff3e0; border-radius: 5px; padding: 8px; margin: 3px 0;'>
                                        <span style='color:#e65100;'>📅 {날짜_str}</span><br>
                                        <b style='color:#e65100; font-size: 16px;'>💵 단가: {단가_값:,.0f}원</b>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.info(f"📭 {거래처} 매입 이력 없음")
                    else:
                        품목명 = ""
                        st.session_state.선택품목_최근단가 = 0
                else:
                    st.warning("검색 결과가 없습니다.")
                    품목명 = ""
            else:
                품목명 = ""
        else:
            품목명 = st.text_input("품목명 직접 입력", key="품목직접")
    
    with col_right:
        입력_수량 = st.number_input("수량", min_value=0, value=1, step=1, key="입력수량")
        
        # 최근 단가가 있으면 기본값으로 사용
        기본단가 = st.session_state.get('선택품목_최근단가', 0)
        입력_단가 = st.number_input("단가", min_value=0, value=기본단가, step=100, key="입력단가")
        
        # 최근 단가 참고 표시
        if 기본단가 > 0:
            st.caption(f"💡 최근 거래 단가: {기본단가:,}원")
        
        # 공급가액 자동 계산
        입력_공급가액 = 입력_수량 * 입력_단가
        
        # 부가세
        if 거래유형_값 in ["=외출", "=외입"]:
            부가세_적용 = st.checkbox("부가세 10%", value=True, key="부가세적용")
            입력_부가세 = round(입력_공급가액 * 0.1) if 부가세_적용 else 0
        else:
            입력_부가세 = 0
        
        st.markdown(f"**공급가액:** {입력_공급가액:,.0f}원")
        st.markdown(f"**부가세:** {입력_부가세:,.0f}원")
        st.markdown(f"**합계:** {입력_공급가액 + 입력_부가세:,.0f}원")
    
    # 품목 추가 버튼
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("➕ 품목 추가", type="primary", use_container_width=True):
            if 품목명 and 입력_공급가액 > 0:
                새품목 = {
                    '품목': 품목명,
                    '수량': 입력_수량,
                    '단가': 입력_단가,
                    '공급가액': 입력_공급가액 if 거래유형_값 != "=외입" else -입력_공급가액,
                    '부가세': 입력_부가세 if 거래유형_값 != "=외입" else -입력_부가세
                }
                st.session_state.입력중_품목_리스트.append(새품목)
                st.success(f"✅ '{품목명}' 추가됨!")
                st.rerun()
            else:
                st.error("❌ 품목명과 금액을 입력해주세요.")
    
    with col_btn2:
        if st.button("🗑️ 전체 삭제", use_container_width=True):
            st.session_state.입력중_품목_리스트 = []
            st.rerun()
    
    st.markdown("---")
    
    # ========== 입력된 품목 목록 ==========
    st.markdown("### 📋 입력된 품목 목록")
    
    if len(st.session_state.입력중_품목_리스트) > 0:
        # 합계 계산
        총_공급가액 = sum(abs(item['공급가액']) for item in st.session_state.입력중_품목_리스트)
        총_부가세 = sum(abs(item['부가세']) for item in st.session_state.입력중_품목_리스트)
        총_합계 = 총_공급가액 + 총_부가세
        
        # 요약 정보
        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        with col_sum1:
            st.metric("품목 수", f"{len(st.session_state.입력중_품목_리스트)}건")
        with col_sum2:
            st.metric("공급가액", f"{총_공급가액:,.0f}원")
        with col_sum3:
            st.metric("부가세", f"{총_부가세:,.0f}원")
        with col_sum4:
            st.metric("총 합계", f"{총_합계:,.0f}원")
        
        st.markdown("---")
        
        # 품목 목록 테이블
        for i, item in enumerate(st.session_state.입력중_품목_리스트):
            col_no, col_item, col_qty, col_price, col_amount, col_del = st.columns([0.5, 3, 1, 1, 1.5, 0.5])
            with col_no:
                st.markdown(f"**{i+1}**")
            with col_item:
                st.markdown(f"📦 {item['품목']}")
            with col_qty:
                st.markdown(f"{item['수량']:,}")
            with col_price:
                st.markdown(f"{item['단가']:,}")
            with col_amount:
                st.markdown(f"**{abs(item['공급가액']) + abs(item['부가세']):,.0f}원**")
            with col_del:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.입력중_품목_리스트.pop(i)
                    st.rerun()
        
        st.markdown("---")
        
        # ========== 저장 버튼 ==========
        col_save1, col_save2, col_save3 = st.columns([1, 1, 1])
        
        with col_save1:
            저장_버튼 = st.button("💾 일괄 저장", type="primary", use_container_width=True)
        with col_save2:
            저장_명세서_버튼 = st.button("💾 저장 + 📄 명세서", use_container_width=True)
        with col_save3:
            명세서만_버튼 = st.button("📄 명세서만 출력", use_container_width=True)
        
        # 저장 처리
        if 저장_버튼 or 저장_명세서_버튼:
            if not 거래처:
                st.error("❌ 거래처를 선택해주세요.")
            else:
                # 모든 품목 저장
                for item in st.session_state.입력중_품목_리스트:
                    new_row = pd.DataFrame([{
                        '날짜': pd.to_datetime(거래일자),
                        '거래처': 거래처,
                        '품목': item['품목'],
                        '수량': item['수량'],
                        '단가': item['단가'],
                        '공급가액': item['공급가액'],
                        '부가세': item['부가세'],
                        '합계': abs(item['공급가액']) + abs(item['부가세']),
                        '참조': 거래유형_값,
                        '비고': ''
                    }])
                    st.session_state.ledger_df = pd.concat([st.session_state.ledger_df, new_row], ignore_index=True)
                
                save_data()
                st.success(f"✅ {len(st.session_state.입력중_품목_리스트)}건 거래가 저장되었습니다!")
                
                # 명세서 출력
                if 저장_명세서_버튼:
                    html_content = create_invoice_html(거래처, 거래일자.strftime('%Y-%m-%d'), st.session_state.입력중_품목_리스트)
                    st.download_button(
                        label="📄 거래명세서 다운로드 (HTML)",
                        data=html_content.encode('utf-8'),
                        file_name=f"거래명세서_{거래처}_{거래일자.strftime('%Y%m%d')}.html",
                        mime="text/html; charset=utf-8"
                    )
                    st.info("💡 다운로드 후 브라우저에서 열어 Ctrl+P로 인쇄하세요!")
                
                # 리스트 초기화
                st.session_state.입력중_품목_리스트 = []
                
                if not 저장_명세서_버튼:
                    st.balloons()
                    st.rerun()
        
        # 명세서만 출력
        if 명세서만_버튼:
            if not 거래처:
                st.error("❌ 거래처를 선택해주세요.")
            else:
                html_content = create_invoice_html(거래처, 거래일자.strftime('%Y-%m-%d'), st.session_state.입력중_품목_리스트)
                st.download_button(
                    label="📄 거래명세서 다운로드 (HTML)",
                    data=html_content.encode('utf-8'),
                    file_name=f"거래명세서_{거래처}_{거래일자.strftime('%Y%m%d')}.html",
                    mime="text/html; charset=utf-8"
                )
                st.info("💡 다운로드 후 브라우저에서 열어 Ctrl+P로 인쇄하세요!")
    else:
        st.info("📝 위에서 품목을 추가해주세요. 여러 품목을 추가한 후 일괄 저장할 수 있습니다.")

# ==================== 거래 내역 ====================
elif menu == "📄 거래 내역":
    st.title("📄 거래 내역")
    
    df = st.session_state.ledger_df.copy()
    products_df = st.session_state.products_df
    
    # ===== 빠른 입력 (컴장부 스타일) =====
    with st.expander("➕ 빠른 거래 입력", expanded=False):
        st.markdown("##### 컴장부처럼 빠르게 입력하세요!")
        
        # 기존 거래처 목록
        거래처_list = sorted(df['거래처'].dropna().unique().tolist()) if len(df) > 0 else []
        
        # 기존 품목 목록 (ledger에서 추출)
        품목_list = sorted(df['품목'].dropna().unique().tolist()) if len(df) > 0 else []
        
        # 1줄: 날짜, 거래처, 거래유형
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            입력_날짜 = st.date_input("날짜", value=get_kst_now(), key="quick_date")
        with col2:
            입력_거래처 = st.selectbox("거래처", [""] + 거래처_list, key="quick_customer")
        with col3:
            # 거래 유형 (외출이 기본 - 판매가 더 많음)
            입력_거래유형 = st.selectbox(
                "유형", 
                ["=외출 (판매)", "=입금 (수금)", "=외입 (매입)", "=출금 (결제)", "=기타 (할인/조정)", "=샘플 (무상제공)"], 
                key="quick_type"
            )
            # 실제 저장할 값 추출
            입력_거래유형_값 = 입력_거래유형.split(" ")[0]
        
        # 2줄: 입금/출금인 경우 금액만, 판매/매입인 경우 품목 입력
        if 입력_거래유형_값 in ["=입금", "=출금"]:
            # 입금/출금: 금액만 입력
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                입력_금액 = st.number_input("금액", min_value=0, value=0, step=10000, format="%d", key="quick_money")
            with col2:
                st.metric("합계", f"{입력_금액:,.0f}원")
            with col3:
                입력_비고 = st.text_input("📝 비고", key="quick_memo", placeholder="현금, 계좌이체 등")
            
            입력_품목 = "입금" if 입력_거래유형_값 == "=입금" else "출금"
            입력_수량 = 0
            입력_단가 = 0
            입력_공급가액 = 입력_금액
            입력_부가세 = 0
        else:
            # 판매/매입: 품목, 수량, 단가 입력
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                # 품목 자동완성 - selectbox + 검색 기능
                품목_검색어 = st.text_input("품목 검색 (2글자 이상)", key="quick_product_search", placeholder="품목명 입력...")
                
                # 2글자 이상 입력시 필터링된 품목 표시
                if len(품목_검색어) >= 2:
                    필터_품목 = [p for p in 품목_list if 품목_검색어.lower() in p.lower()]
                    if 필터_품목:
                        입력_품목 = st.selectbox(
                            f"🔍 검색결과 ({len(필터_품목)}건)", 
                            ["직접입력: " + 품목_검색어] + 필터_품목[:20],  # 최대 20개
                            key="quick_product_select"
                        )
                        # "직접입력:" 선택시 검색어 그대로 사용
                        if 입력_품목.startswith("직접입력:"):
                            입력_품목 = 품목_검색어
                    else:
                        입력_품목 = 품목_검색어
                        st.caption("검색 결과 없음 - 직접 입력됩니다")
                else:
                    입력_품목 = 품목_검색어
                    if 품목_검색어:
                        st.caption("2글자 이상 입력하면 품목 검색")
            
            with col2:
                입력_수량 = st.number_input("수량", min_value=0, value=0, step=1, format="%d", key="quick_qty")
            with col3:
                입력_단가 = st.number_input("단가", min_value=0, value=0, step=100, format="%d", key="quick_price")
            with col4:
                # 공급가액 자동 계산 (수정 불가)
                자동_공급가액 = 입력_수량 * 입력_단가
                st.text_input("공급가액", value=f"{자동_공급가액:,}", disabled=True, key="quick_amount_display")
                입력_공급가액 = 자동_공급가액
            
            # 부가세 및 비고
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                부가세_적용 = st.checkbox("부가세 10%", value=True if 입력_거래유형_값 in ["=외출", "=외입"] else False, key="quick_tax")
                입력_부가세 = round(입력_공급가액 * 0.1) if 부가세_적용 else 0
            with col2:
                st.metric("합계", f"{입력_공급가액 + 입력_부가세:,.0f}원")
            with col3:
                입력_비고 = st.text_input("📝 비고", key="quick_memo", placeholder="특이사항")
        
        # 저장 버튼
        if st.button("💾 저장", type="primary", use_container_width=True, key="quick_save"):
            if not 입력_거래처:
                st.error("❌ 거래처를 선택해주세요.")
            elif 입력_거래유형_값 in ["=입금", "=출금"] and 입력_공급가액 <= 0:
                st.error("❌ 금액을 입력해주세요.")
            elif 입력_거래유형_값 in ["=외출", "=외입"] and (not 입력_품목 or 입력_공급가액 <= 0):
                st.error("❌ 품목과 금액을 입력해주세요.")
            else:
                new_row = pd.DataFrame([{
                    '날짜': pd.to_datetime(입력_날짜),
                    '거래처': 입력_거래처,
                    '품목': 입력_품목 if 입력_품목 else 입력_거래유형_값.replace("=", ""),
                    '수량': 입력_수량,
                    '단가': 입력_단가,
                    '공급가액': 입력_공급가액,
                    '부가세': 입력_부가세,
                    '합계': 입력_공급가액 + 입력_부가세,
                    '참조': 입력_거래유형_값,
                    '비고': 입력_비고
                }])
                
                st.session_state.ledger_df = pd.concat([st.session_state.ledger_df, new_row], ignore_index=True)
                save_data()
                st.success(f"✅ 저장 완료! {입력_거래처} - {입력_공급가액 + 입력_부가세:,.0f}원")
                st.rerun()
    
    st.markdown("---")
    
    if len(df) == 0:
        st.warning("⚠️ 아직 거래 내역이 없습니다.")
        st.info("""
        **데이터가 표시되지 않는 경우 확인하세요:**
        1. GitHub에 `data/ledger.csv` 파일이 업로드되어 있는지 확인
        2. 파일명이 정확히 `ledger.csv`인지 확인
        3. 위의 '빠른 거래 입력'으로 새 거래를 입력해보세요
        """)
    else:
        # 필터
        col1, col2, col3 = st.columns(3)
        
        with col1:
            거래유형_필터 = st.multiselect("거래 유형", df['참조'].unique(), default=df['참조'].unique())
        with col2:
            거래처_필터 = st.multiselect("거래처", ["전체"] + sorted(df['거래처'].dropna().unique().tolist()), default=["전체"])
        with col3:
            검색어 = st.text_input("품목 검색", "")
        
        # 미수금 실시간 표시 - base_receivables에서 GULREST 값 직접 사용
        if "전체" not in 거래처_필터 and len(거래처_필터) == 1:
            선택거래처 = 거래처_필터[0]
            
            # 미수금은 base_receivables에서 직접 가져옴 (컴장부 GULREST)
            기초미수금_dict = st.session_state.base_receivables_df.set_index('거래처')['기초미수금'].to_dict() if len(st.session_state.base_receivables_df) > 0 else {}
            미수금 = 기초미수금_dict.get(선택거래처, 0)
            
            # 미수금 표시 (검정색 글자)
            if 미수금 > 0:
                st.markdown(f"""
                <div style='background-color: #fff3e0; border: 2px solid #e65100; border-radius: 10px; padding: 15px; margin: 10px 0;'>
                    <h3 style='color: #000000; margin: 0;'>⚠️ 미수금: {미수금:,.0f}원</h3>
                </div>
                """, unsafe_allow_html=True)
            elif 미수금 < 0:
                st.markdown(f"""
                <div style='background-color: #e3f2fd; border: 2px solid #1e88e5; border-radius: 10px; padding: 15px; margin: 10px 0;'>
                    <h3 style='color: #000000; margin: 0;'>💰 선수금: {abs(미수금):,.0f}원</h3>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background-color: #e8f5e9; border: 2px solid #2e7d32; border-radius: 10px; padding: 15px; margin: 10px 0;'>
                    <h3 style='color: #000000; margin: 0;'>✅ 미수금 없음</h3>
                </div>
                """, unsafe_allow_html=True)
        
        # 필터링
        df_filtered = df[df['참조'].isin(거래유형_필터)]
        
        if "전체" not in 거래처_필터:
            df_filtered = df_filtered[df_filtered['거래처'].isin(거래처_필터)]
        
        if 검색어:
            df_filtered = df_filtered[df_filtered['품목'].str.contains(검색어, na=False)]
        
        # 정렬
        df_filtered = df_filtered.sort_values('날짜', ascending=False)
        
        st.markdown(f"### 총 {len(df_filtered)}건")
        
        # 누적 미수금 계산 함수
        def 누적_미수금_계산(df):
            """각 거래 시점까지의 누적 미수금 계산 (기준일자 당일 거래도 개별 누적)"""
            if len(df) == 0:
                return df
            
            # 기초미수금 딕셔너리
            base_recv = st.session_state.base_receivables_df
            기초미수금_dict = {}
            기준일자_dict = {}
            if len(base_recv) > 0:
                for _, row in base_recv.iterrows():
                    거래처 = row['거래처']
                    기초값 = row['기초미수금']
                    if 기초값 > 0:  # 미수금인 경우만
                        기초미수금_dict[거래처] = 기초값
                        기준일자_dict[거래처] = pd.to_datetime(row['기준일자'])
            
            # 원본 인덱스 보존
            df = df.copy()
            df['원본인덱스'] = df.index
            
            # 날짜순 정렬 (오래된 것부터, 같은 날짜면 인덱스순)
            df['날짜_dt'] = pd.to_datetime(df['날짜'])
            df_sorted = df.sort_values(['거래처', '날짜_dt', '원본인덱스']).reset_index(drop=True)
            
            # 기준일자 당일 거래 총합 계산 (시작값 역산용)
            기준일_거래합계 = {}
            for 거래처 in 기초미수금_dict.keys():
                기준일자 = 기준일자_dict.get(거래처)
                if 기준일자:
                    # 해당 거래처의 기준일자 당일 거래만 필터
                    당일_거래 = df_sorted[(df_sorted['거래처'] == 거래처) & 
                                        (df_sorted['날짜_dt'] == 기준일자)]
                    합계 = 0
                    for _, row in 당일_거래.iterrows():
                        공급가액 = row['공급가액'] if pd.notna(row['공급가액']) else 0
                        부가세 = row['부가세'] if pd.notna(row['부가세']) else 0
                        참조 = str(row['참조']) if pd.notna(row['참조']) else ''
                        if 참조 == '=입금' or '입금' in 참조:
                            합계 -= 공급가액
                        elif 참조 == '=외출' or (공급가액 > 0 and '입금' not in 참조 and '출금' not in 참조):
                            합계 += 공급가액 + 부가세
                    기준일_거래합계[거래처] = 합계
            
            # 누적 미수금 계산
            누적미수금_list = []
            현재_미수금 = {}
            
            for idx, row in df_sorted.iterrows():
                거래처 = row['거래처']
                날짜 = row['날짜_dt']
                공급가액 = row['공급가액'] if pd.notna(row['공급가액']) else 0
                부가세 = row['부가세'] if pd.notna(row['부가세']) else 0
                참조 = str(row['참조']) if pd.notna(row['참조']) else ''
                
                # 기초미수금 등록 안 된 거래처는 0
                if 거래처 not in 기초미수금_dict:
                    누적미수금_list.append(0)
                    continue
                
                기준일자 = 기준일자_dict.get(거래처)
                
                # 해당 거래처 첫 계산시 시작값 설정
                if 거래처 not in 현재_미수금:
                    # 기준일자 이전 거래는: 기초미수금 - 기준일자 당일 거래합계
                    당일합계 = 기준일_거래합계.get(거래처, 0)
                    현재_미수금[거래처] = 기초미수금_dict[거래처] - 당일합계
                
                # 기준일자 이전 거래 (당일 제외)
                if 기준일자 and 날짜 < 기준일자:
                    누적미수금_list.append(현재_미수금[거래처])
                    continue
                
                # 기준일자 당일 및 이후 거래: 순차적으로 누적 계산
                if 참조 == '=입금' or '입금' in 참조:
                    현재_미수금[거래처] -= 공급가액
                elif 참조 == '=외출' or (공급가액 > 0 and '입금' not in 참조 and '출금' not in 참조):
                    현재_미수금[거래처] += 공급가액 + 부가세
                
                누적미수금_list.append(현재_미수금[거래처])
            
            df_sorted['미수금'] = 누적미수금_list
            
            # 원본 인덱스 순서로 복원 후 최신이 위로 오도록 역순 정렬
            df_sorted = df_sorted.sort_values('원본인덱스', ascending=False)
            df_sorted = df_sorted.drop(columns=['원본인덱스', '날짜_dt'])
            
            return df_sorted
        
        # 데이터 표시
        display_df = df_filtered.copy()
        
        # 합계 컬럼 생성 또는 NaN 처리 (공급가액 + 부가세)
        if '합계' not in display_df.columns:
            display_df['합계'] = display_df['공급가액'].fillna(0) + display_df['부가세'].fillna(0)
        else:
            # 합계가 NaN인 경우 공급가액 + 부가세로 계산
            display_df['합계'] = display_df['합계'].fillna(display_df['공급가액'].fillna(0) + display_df['부가세'].fillna(0))
        
        # 누적 미수금 계산
        display_df = 누적_미수금_계산(display_df)
        
        display_df['날짜'] = pd.to_datetime(display_df['날짜']).dt.strftime('%Y-%m-%d')
        
        # 미수금 포맷팅
        display_df['미수금'] = display_df['미수금'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x != 0 else "")
        
        display_df['공급가액'] = display_df['공급가액'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")
        display_df['부가세'] = display_df['부가세'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")
        display_df['합계'] = display_df['합계'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")
        
        # 비고 컬럼이 없으면 추가
        if '비고' not in display_df.columns:
            display_df['비고'] = ''
        
        # 컬럼 순서 정리 (합계 추가)
        표시_컬럼 = ['날짜', '거래처', '품목', '수량', '단가', '공급가액', '부가세', '합계', '참조', '미수금', '비고']
        표시_컬럼 = [col for col in 표시_컬럼 if col in display_df.columns]
        display_df = display_df[표시_컬럼]
        
        st.dataframe(display_df, use_container_width=True, height=500)
        
        # 🗑️ 거래 삭제 기능
        st.markdown("---")
        with st.expander("🗑️ 거래 삭제", expanded=False):
            st.warning("⚠️ 삭제된 거래는 복구할 수 없습니다!")
            
            # 최근 거래 목록 (삭제용)
            최근_거래 = df_filtered.head(20).copy()
            최근_거래['삭제용_표시'] = 최근_거래.apply(
                lambda x: f"{x['날짜'].strftime('%Y-%m-%d') if isinstance(x['날짜'], pd.Timestamp) else x['날짜']} | {x['거래처']} | {x['품목'][:20] if pd.notna(x['품목']) else ''} | {x['공급가액']}", 
                axis=1
            )
            
            삭제_선택 = st.selectbox(
                "삭제할 거래 선택 (최근 20건)",
                ["선택하세요"] + 최근_거래['삭제용_표시'].tolist(),
                key="delete_select"
            )
            
            if 삭제_선택 != "선택하세요":
                # 선택된 거래의 인덱스 찾기
                선택_idx = 최근_거래[최근_거래['삭제용_표시'] == 삭제_선택].index[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    삭제_확인 = st.checkbox("정말 삭제하시겠습니까?", key="delete_confirm")
                with col2:
                    if 삭제_확인:
                        if st.button("🗑️ 삭제 실행", type="primary", use_container_width=True):
                            st.session_state.ledger_df = st.session_state.ledger_df.drop(선택_idx).reset_index(drop=True)
                            save_data()
                            st.success("✅ 삭제 완료!")
                            st.rerun()
        
        # 거래명세서 출력 (거래처 1개 선택 시)
        st.markdown("---")
        
        if "전체" not in 거래처_필터 and len(거래처_필터) == 1:
            선택거래처_명세 = 거래처_필터[0]
            
            st.markdown("#### 📄 거래명세서 출력")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                명세서_시작일 = st.date_input("시작일", value=get_kst_now().replace(day=1), key="invoice_start")
            with col2:
                명세서_종료일 = st.date_input("종료일", value=get_kst_now(), key="invoice_end")
            with col3:
                명세서_출력 = st.button("📄 거래명세서 생성", type="primary", use_container_width=True)
            
            if 명세서_출력:
                # 해당 기간 + 거래처 + 판매(외출)만 필터
                명세_df = df_filtered[
                    (df_filtered['참조'] == '=외출')
                ].copy()
                
                # 날짜 필터 (원본 df_filtered 사용)
                원본_df = st.session_state.ledger_df.copy()
                원본_df = 원본_df[
                    (원본_df['거래처'] == 선택거래처_명세) &
                    (원본_df['참조'] == '=외출') &
                    (원본_df['날짜'] >= pd.to_datetime(명세서_시작일)) &
                    (원본_df['날짜'] <= pd.to_datetime(명세서_종료일))
                ]
                
                if len(원본_df) > 0:
                    거래_목록 = []
                    for _, row in 원본_df.iterrows():
                        거래_목록.append({
                            '품목': row['품목'],
                            '수량': row['수량'],
                            '단가': row['단가'],
                            '공급가액': row['공급가액'],
                            '부가세': row['부가세']
                        })
                    
                    날짜_문자열 = f"{명세서_시작일.strftime('%Y-%m-%d')} ~ {명세서_종료일.strftime('%Y-%m-%d')}"
                    html_content = create_invoice_html(선택거래처_명세, 날짜_문자열, 거래_목록)
                    
                    st.download_button(
                        label="📥 거래명세서 다운로드 (HTML)",
                        data=html_content.encode('utf-8'),
                        file_name=f"거래명세서_{선택거래처_명세}_{명세서_시작일.strftime('%Y%m%d')}_{명세서_종료일.strftime('%Y%m%d')}.html",
                        mime="text/html; charset=utf-8"
                    )
                    st.success(f"✅ {선택거래처_명세} 거래명세서 생성 완료! ({len(원본_df)}건)")
                    st.info("💡 다운로드 후 브라우저에서 열어 Ctrl+P로 인쇄하세요!")
                else:
                    st.warning("해당 기간에 판매 거래가 없습니다.")
        
        # 엑셀 다운로드
        st.markdown("---")
        
        @st.cache_data
        def convert_to_excel(dataframe):
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='거래내역')
            return output.getvalue()
        
        excel_data = convert_to_excel(df_filtered)
        
        st.download_button(
            label="📥 엑셀 다운로드",
            data=excel_data,
            file_name=f"거래내역_{get_kst_now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==================== 통계 분석 ====================
elif menu == "📊 통계 분석":
    st.title("📊 통계 분석")
    
    df = st.session_state.ledger_df.copy()
    
    if len(df) == 0:
        st.info("아직 거래 내역이 없습니다.")
    else:
        # 최근 4개년도 필터
        당해연도 = get_kst_now().year
        연도_목록 = [당해연도, 당해연도-1, 당해연도-2, 당해연도-3]
        
        col1, col2 = st.columns(2)
        with col1:
            분석유형 = st.selectbox("분석 유형", ["월별 분석", "거래처별 분석", "품목별 분석", "부가세 분석"])
        with col2:
            선택_연도 = st.selectbox("연도 선택", ["전체 (최근4년)"] + [f"{y}년" for y in 연도_목록])
        
        # 연도 필터링
        df['연도'] = df['날짜'].dt.year
        if 선택_연도 == "전체 (최근4년)":
            df = df[df['연도'].isin(연도_목록)]
        else:
            선택_연도_숫자 = int(선택_연도.replace("년", ""))
            df = df[df['연도'] == 선택_연도_숫자]
        
        if 분석유형 == "월별 분석":
            st.markdown("### 📆 월별 수입/지출 분석")
            
            df['년월'] = df['날짜'].dt.to_period('M').astype(str)
            
            입금_df = df[df['참조'].str.contains('입금', na=False)].groupby('년월')['공급가액'].sum()
            출금_df = df[df['참조'].str.contains('출금', na=False)].groupby('년월')['공급가액'].sum().abs()
            # 외입은 음수이므로 절대값
            매입_df = df[df['참조'].str.contains('외입', na=False)].groupby('년월')['공급가액'].sum().abs()
            부가세_df = df[df['참조'].str.contains('외입', na=False)].groupby('년월')['부가세'].sum().abs()
            # 외출(판매)
            매출_df = df[df['참조'].str.contains('외출', na=False)].groupby('년월').apply(
                lambda x: x['공급가액'].sum() + x['부가세'].sum()
            )
            
            월별_df = pd.DataFrame({
                '수입': 입금_df,
                '지출': 출금_df,
                '매입': 매입_df,
                '매출': 매출_df,
                '순이익': 입금_df - 출금_df
            }).fillna(0)
            
            # 최신순 정렬 (역순)
            월별_df = 월별_df.sort_index(ascending=False)
            
            # 그래프
            fig = go.Figure()
            fig.add_trace(go.Bar(name='수입', x=월별_df.index, y=월별_df['수입'], marker_color='#2E7D32'))
            fig.add_trace(go.Bar(name='지출', x=월별_df.index, y=월별_df['지출'], marker_color='#C62828'))
            fig.add_trace(go.Scatter(name='순이익', x=월별_df.index, y=월별_df['순이익'], mode='lines+markers', line=dict(color='#1976D2', width=3)))
            
            fig.update_layout(height=500, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            # 테이블
            st.dataframe(월별_df.applymap(lambda x: f"{x:,.0f}"), use_container_width=True)
        
        elif 분석유형 == "거래처별 분석":
            st.markdown("### 🏢 거래처별 분석")
            
            거래처별 = df[df['참조'].str.contains('입금', na=False)].groupby('거래처').agg({
                '공급가액': 'sum',
                '날짜': 'count'
            }).rename(columns={'날짜': '거래횟수'}).sort_values('공급가액', ascending=False)
            
            거래처별['평균거래액'] = 거래처별['공급가액'] / 거래처별['거래횟수']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### TOP 20 거래처")
                top20 = 거래처별.head(20).copy()
                top20['공급가액'] = top20['공급가액'].apply(lambda x: f"{x:,.0f}")
                top20['평균거래액'] = top20['평균거래액'].apply(lambda x: f"{x:,.0f}")
                st.dataframe(top20, use_container_width=True)
            
            with col2:
                st.markdown("#### 거래처별 매출 비중")
                fig = px.pie(거래처별.head(10), values='공급가액', names=거래처별.head(10).index, hole=0.4)
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
        
        elif 분석유형 == "품목별 분석":
            st.markdown("### 📦 품목별 매출 분석")
            
            # 품목에서 키워드 추출 (간단히)
            df_입금 = df[df['참조'].str.contains('입금', na=False)].copy()
            
            if len(df_입금) > 0:
                품목별 = df_입금.groupby('품목')['공급가액'].sum().sort_values(ascending=False).head(20)
                
                st.bar_chart(품목별)
                
                st.dataframe(품목별.apply(lambda x: f"{x:,.0f}"), use_container_width=True)
            else:
                st.info("입금 데이터가 없습니다.")
        
        elif 분석유형 == "부가세 분석":
            st.markdown("### 🧾 부가세 분석")
            
            df['년월'] = df['날짜'].dt.to_period('M').astype(str)
            
            # 외입(매입)은 음수이므로 절대값
            매입부가세 = df[df['참조'].str.contains('외입', na=False)].groupby('년월')['부가세'].sum().abs()
            # 외출(매출) 부가세
            매출부가세 = df[df['참조'].str.contains('외출', na=False)].groupby('년월')['부가세'].sum()
            
            부가세_df = pd.DataFrame({
                '매입부가세': 매입부가세,
                '매출부가세': 매출부가세,
                '납부세액': 매출부가세 - 매입부가세
            }).fillna(0)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 월별 부가세")
                fig = go.Figure()
                fig.add_trace(go.Bar(name='매출부가세', x=부가세_df.index, y=부가세_df['매출부가세'], marker_color='#2E7D32'))
                fig.add_trace(go.Bar(name='매입부가세', x=부가세_df.index, y=부가세_df['매입부가세'], marker_color='#C62828'))
                fig.update_layout(barmode='group', height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 통계")
                st.metric("총 매출부가세", f"{부가세_df['매출부가세'].sum():,.0f}원")
                st.metric("총 매입부가세", f"{부가세_df['매입부가세'].sum():,.0f}원")
                st.metric("납부세액 (매출-매입)", f"{부가세_df['납부세액'].sum():,.0f}원")

# ==================== 외상 관리 ====================
elif menu == "💰 외상 관리":
    st.title("💰 외상 관리")
    
    df = st.session_state.ledger_df.copy()
    base_recv = st.session_state.base_receivables_df.copy()
    
    if len(base_recv) == 0:
        st.info("아직 미수금 데이터가 없습니다.")
    else:
        # 탭으로 미수금/미지급금 분리
        tab_recv, tab_pay = st.tabs(["📤 미수금 (받을 돈)", "📥 미지급금 (줄 돈)"])
        
        # ===== 미수금 탭 (판매처) =====
        with tab_recv:
            st.markdown("### 📤 외상 매출금 (미수금)")
            st.caption("💡 미수금 = 컴장부 GULREST 값 (2025.12.20 기준)")
            
            # base_receivables에서 미수금 가져오기 (양수)
            미수금_df = base_recv[base_recv['기초미수금'] > 0].copy()
            미수금_df = 미수금_df.sort_values('기초미수금', ascending=False)
            
            if len(미수금_df) > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 미수금", f"{미수금_df['기초미수금'].sum():,.0f}원")
                with col2:
                    st.metric("미수 거래처 수", f"{len(미수금_df)}개")
                with col3:
                    st.metric("최대 미수금", f"{미수금_df['기초미수금'].max():,.0f}원")
                
                st.markdown("---")
                
                # 표시용 데이터프레임
                display_df = 미수금_df[['거래처', '기초미수금', '기준일자']].copy()
                display_df.columns = ['거래처', '미수금', '기준일자']
                display_df['미수금'] = display_df['미수금'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # 다운로드 버튼
                csv = 미수금_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 미수금 목록 다운로드 (CSV)",
                    data=csv,
                    file_name=f"미수금목록_{get_kst_now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ 미수금이 없습니다!")
        
        # ===== 미지급금 탭 (매입처) =====
        with tab_pay:
            st.markdown("### 📥 외상 매입금 (미지급금)")
            st.caption("💡 미지급금 = 컴장부 GULREST 값 (음수, 2025.12.20 기준)")
            
            # base_receivables에서 미지급금 가져오기 (음수)
            미지급금_raw = base_recv[base_recv['기초미수금'] < 0].copy()
            
            if len(미지급금_raw) > 0:
                미지급금_df = 미지급금_raw.copy()
                미지급금_df['미지급금'] = 미지급금_df['기초미수금'].abs()
                미지급금_df = 미지급금_df.sort_values('미지급금', ascending=False)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 미지급금", f"{미지급금_df['미지급금'].sum():,.0f}원")
                with col2:
                    st.metric("미지급 거래처 수", f"{len(미지급금_df)}개")
                with col3:
                    st.metric("최대 미지급금", f"{미지급금_df['미지급금'].max():,.0f}원")
                
                st.markdown("---")
                
                # 표시용 데이터프레임
                display_df = 미지급금_df[['거래처', '미지급금', '기준일자']].copy()
                display_df['미지급금'] = display_df['미지급금'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # 다운로드 버튼
                csv = 미지급금_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 미지급금 목록 다운로드 (CSV)",
                    data=csv,
                    file_name=f"미지급금목록_{get_kst_now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ 미지급금이 없습니다!")

# ==================== 회계 관리 ====================
elif menu == "🧾 회계 관리":
    st.title("🧾 회계 관리")
    
    df = st.session_state.ledger_df.copy()
    
    if len(df) == 0:
        st.info("아직 거래 내역이 없습니다.")
    else:
        # 최근 4개년도 필터
        당해연도 = get_kst_now().year
        연도_목록 = [당해연도, 당해연도-1, 당해연도-2, 당해연도-3]
        
        # 탭 생성 (유영찬 매출 탭 추가)
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 손익 현황", "🧾 부가세 현황", "💹 마진 분석", "🏢 거래처별 마진", "👤 유영찬 매출"])
        
        # ===== 탭1: 손익 현황 =====
        with tab1:
            st.markdown("### 📊 연도별 손익 현황")
            
            df['연도'] = df['날짜'].dt.year
            df_4년 = df[df['연도'].isin(연도_목록)]
            
            손익_데이터 = []
            for 연도 in sorted(연도_목록, reverse=True):
                연도_df = df_4년[df_4년['연도'] == 연도]
                
                # 수입 (입금)
                수입 = 연도_df[연도_df['참조'] == '=입금']['공급가액'].sum()
                
                # 지출 (출금) - 음수이므로 절대값
                지출 = abs(연도_df[연도_df['참조'] == '=출금']['공급가액'].sum())
                
                # 매출 (외출)
                외출_df = 연도_df[연도_df['참조'] == '=외출']
                매출 = 외출_df['공급가액'].sum()
                매출부가세 = 외출_df['부가세'].sum()
                
                # 매입 (외입) - 음수이므로 절대값
                외입_df = 연도_df[연도_df['참조'] == '=외입']
                매입 = abs(외입_df['공급가액'].sum())
                매입부가세 = abs(외입_df['부가세'].sum())
                
                # 마진 (매입단가가 있는 경우)
                마진 = 외출_df['마진'].sum() if '마진' in 외출_df.columns else 0
                
                손익_데이터.append({
                    '연도': f"{연도}년",
                    '매출': 매출,
                    '매입': 매입,
                    '마진': 마진,
                    '마진율': (마진 / 매출 * 100) if 매출 > 0 else 0,
                    '수입(입금)': 수입,
                    '지출(출금)': 지출,
                    '순이익': 수입 - 지출
                })
            
            손익_df = pd.DataFrame(손익_데이터)
            
            # 요약 지표
            col1, col2, col3, col4 = st.columns(4)
            당해_데이터 = 손익_df[손익_df['연도'] == f"{당해연도}년"].iloc[0] if len(손익_df[손익_df['연도'] == f"{당해연도}년"]) > 0 else None
            
            if 당해_데이터 is not None:
                with col1:
                    st.metric(f"{당해연도}년 매출", f"{당해_데이터['매출']:,.0f}원")
                with col2:
                    st.metric(f"{당해연도}년 마진", f"{당해_데이터['마진']:,.0f}원", delta=f"{당해_데이터['마진율']:.1f}%")
                with col3:
                    st.metric(f"{당해연도}년 수입", f"{당해_데이터['수입(입금)']:,.0f}원")
                with col4:
                    st.metric(f"{당해연도}년 순이익", f"{당해_데이터['순이익']:,.0f}원")
            
            st.markdown("---")
            
            # 연도별 비교 차트
            fig = go.Figure()
            fig.add_trace(go.Bar(name='매출', x=손익_df['연도'], y=손익_df['매출'], marker_color='#1976D2'))
            fig.add_trace(go.Bar(name='마진', x=손익_df['연도'], y=손익_df['마진'], marker_color='#43A047'))
            fig.add_trace(go.Bar(name='순이익', x=손익_df['연도'], y=손익_df['순이익'], marker_color='#FF9800'))
            fig.update_layout(barmode='group', height=400, title='연도별 손익 비교')
            st.plotly_chart(fig, use_container_width=True)
            
            # 상세 테이블
            display_손익 = 손익_df.copy()
            for col in ['매출', '매입', '마진', '수입(입금)', '지출(출금)', '순이익']:
                display_손익[col] = display_손익[col].apply(lambda x: f"{x:,.0f}")
            display_손익['마진율'] = display_손익['마진율'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_손익, use_container_width=True, hide_index=True)
        
        # ===== 탭2: 부가세 현황 =====
        with tab2:
            st.markdown("### 🧾 월별 부가세 장부")
            
            선택_연도_부가세 = st.selectbox("연도 선택", 연도_목록, format_func=lambda x: f"{x}년", key="vat_year")
            
            df['연도'] = df['날짜'].dt.year
            df['월'] = df['날짜'].dt.month
            연도_df = df[df['연도'] == 선택_연도_부가세]
            
            # 월별 부가세 계산
            월별_데이터 = []
            
            # 분기/반기 누적용
            q1_data = {'총매출액': 0, '계산서매출': 0, '매출부가세': 0, '현금매출': 0, '매입액': 0, '매입부가세': 0, '납부세액': 0}
            q2_data = {'총매출액': 0, '계산서매출': 0, '매출부가세': 0, '현금매출': 0, '매입액': 0, '매입부가세': 0, '납부세액': 0}
            q3_data = {'총매출액': 0, '계산서매출': 0, '매출부가세': 0, '현금매출': 0, '매입액': 0, '매입부가세': 0, '납부세액': 0}
            q4_data = {'총매출액': 0, '계산서매출': 0, '매출부가세': 0, '현금매출': 0, '매입액': 0, '매입부가세': 0, '납부세액': 0}
            
            for 월 in range(1, 13):
                월_df = 연도_df[연도_df['월'] == 월]
                
                # 매출
                외출_df = 월_df[월_df['참조'] == '=외출']
                총매출액 = 외출_df['공급가액'].sum() + 외출_df['부가세'].sum()
                계산서매출 = 외출_df[외출_df['부가세'] > 0]['공급가액'].sum()
                매출부가세 = 외출_df['부가세'].sum()
                현금매출 = 외출_df[외출_df['부가세'] == 0]['공급가액'].sum()
                
                # 매입
                외입_df = 월_df[월_df['참조'] == '=외입']
                매입액 = abs(외입_df['공급가액'].sum())
                매입부가세 = abs(외입_df['부가세'].sum())
                
                # 납부세액
                납부세액 = 매출부가세 - 매입부가세
                
                row_data = {
                    '구분': f"{월}월",
                    '총매출액': 총매출액,
                    '계산서매출': 계산서매출,
                    '매출부가세': 매출부가세,
                    '현금매출': 현금매출,
                    '매입액': 매입액,
                    '매입부가세': 매입부가세,
                    '납부세액': 납부세액
                }
                월별_데이터.append(row_data)
                
                # 분기별 누적
                if 월 <= 3:
                    for k in q1_data: q1_data[k] += row_data.get(k, 0) if isinstance(row_data.get(k, 0), (int, float)) else 0
                elif 월 <= 6:
                    for k in q2_data: q2_data[k] += row_data.get(k, 0) if isinstance(row_data.get(k, 0), (int, float)) else 0
                elif 월 <= 9:
                    for k in q3_data: q3_data[k] += row_data.get(k, 0) if isinstance(row_data.get(k, 0), (int, float)) else 0
                else:
                    for k in q4_data: q4_data[k] += row_data.get(k, 0) if isinstance(row_data.get(k, 0), (int, float)) else 0
                
                # 3월 후 1분기 합산
                if 월 == 3:
                    월별_데이터.append({'구분': '▶ 1분기 합계', **q1_data})
                
                # 6월 후 2분기 + 상반기 합산
                if 월 == 6:
                    월별_데이터.append({'구분': '▶ 2분기 합계', **q2_data})
                    상반기 = {k: q1_data[k] + q2_data[k] for k in q1_data}
                    월별_데이터.append({'구분': '★ 상반기 합계', **상반기})
                
                # 9월 후 3분기 합산
                if 월 == 9:
                    월별_데이터.append({'구분': '▶ 3분기 합계', **q3_data})
                
                # 12월 후 4분기 + 하반기 + 연간 합산
                if 월 == 12:
                    월별_데이터.append({'구분': '▶ 4분기 합계', **q4_data})
                    하반기 = {k: q3_data[k] + q4_data[k] for k in q3_data}
                    월별_데이터.append({'구분': '★ 하반기 합계', **하반기})
                    연간 = {k: q1_data[k] + q2_data[k] + q3_data[k] + q4_data[k] for k in q1_data}
                    월별_데이터.append({'구분': '◆ 연간 합계', **연간})
            
            월별_df = pd.DataFrame(월별_데이터)
            
            # 연간 요약 (상단)
            연간_매출부가세 = q1_data['매출부가세'] + q2_data['매출부가세'] + q3_data['매출부가세'] + q4_data['매출부가세']
            연간_매입부가세 = q1_data['매입부가세'] + q2_data['매입부가세'] + q3_data['매입부가세'] + q4_data['매입부가세']
            연간_납부세액 = 연간_매출부가세 - 연간_매입부가세
            
            st.markdown(f"#### {선택_연도_부가세}년 연간 요약")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📤 매출부가세", f"{연간_매출부가세:,.0f}원")
            with col2:
                st.metric("📥 매입부가세", f"{연간_매입부가세:,.0f}원")
            with col3:
                if 연간_납부세액 >= 0:
                    st.metric("💸 납부할 부가세", f"{연간_납부세액:,.0f}원")
                else:
                    st.metric("💰 환급받을 부가세", f"{abs(연간_납부세액):,.0f}원")
            
            st.markdown("---")
            
            # 월별 상세 테이블 (st.dataframe 사용)
            st.markdown("#### 월별 상세")
            
            display_df = 월별_df.copy()
            for col in ['총매출액', '계산서매출', '매출부가세', '현금매출', '매입액', '매입부가세', '납부세액']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=700)
            
            # 차트
            st.markdown("---")
            st.markdown("#### 월별 부가세 추이")
            월_only = 월별_df[~월별_df['구분'].str.contains('합계')]
            fig = go.Figure()
            fig.add_trace(go.Bar(name='매출부가세', x=월_only['구분'], y=월_only['매출부가세'], marker_color='#1976D2'))
            fig.add_trace(go.Bar(name='매입부가세', x=월_only['구분'], y=월_only['매입부가세'], marker_color='#FF5722'))
            fig.add_trace(go.Scatter(name='납부세액', x=월_only['구분'], y=월_only['납부세액'], mode='lines+markers', line=dict(color='#43A047', width=3)))
            fig.update_layout(barmode='group', height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # ===== 탭3: 마진 분석 =====
        with tab3:
            st.markdown("### 💹 월별 마진 분석")
            
            col1, col2 = st.columns(2)
            with col1:
                선택_연도_마진 = st.selectbox("연도 선택", 연도_목록, format_func=lambda x: f"{x}년", key="margin_year")
            
            df['연도'] = df['날짜'].dt.year
            df['월'] = df['날짜'].dt.month
            연도_df = df[df['연도'] == 선택_연도_마진]
            
            # 월별 마진 계산
            월별_마진 = []
            for 월 in range(1, 13):
                월_df = 연도_df[(연도_df['월'] == 월) & (연도_df['참조'] == '=외출')]
                
                매출 = 월_df['공급가액'].sum()
                마진 = 월_df['마진'].sum() if '마진' in 월_df.columns else 0
                마진율 = (마진 / 매출 * 100) if 매출 > 0 else 0
                
                월별_마진.append({
                    '월': f"{월}월",
                    '매출': 매출,
                    '마진': 마진,
                    '마진율': 마진율
                })
            
            월별_마진_df = pd.DataFrame(월별_마진)
            
            # 차트
            fig = go.Figure()
            fig.add_trace(go.Bar(name='매출', x=월별_마진_df['월'], y=월별_마진_df['매출'], marker_color='#1976D2', yaxis='y'))
            fig.add_trace(go.Bar(name='마진', x=월별_마진_df['월'], y=월별_마진_df['마진'], marker_color='#43A047', yaxis='y'))
            fig.add_trace(go.Scatter(name='마진율', x=월별_마진_df['월'], y=월별_마진_df['마진율'], mode='lines+markers', line=dict(color='#FF5722', width=3), yaxis='y2'))
            
            fig.update_layout(
                barmode='group',
                height=450,
                title=f'{선택_연도_마진}년 월별 매출/마진',
                yaxis=dict(title='금액 (원)'),
                yaxis2=dict(title='마진율 (%)', overlaying='y', side='right', range=[0, 50])
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 테이블
            display_마진 = 월별_마진_df.copy()
            display_마진['매출'] = display_마진['매출'].apply(lambda x: f"{x:,.0f}")
            display_마진['마진'] = display_마진['마진'].apply(lambda x: f"{x:,.0f}")
            display_마진['마진율'] = display_마진['마진율'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_마진, use_container_width=True, hide_index=True)
            
            # 연간 합계
            총매출 = 월별_마진_df['매출'].sum()
            총마진 = 월별_마진_df['마진'].sum()
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("연간 총매출", f"{총매출:,.0f}원")
            with col2:
                st.metric("연간 총마진", f"{총마진:,.0f}원")
            with col3:
                st.metric("연간 평균 마진율", f"{(총마진/총매출*100):.1f}%" if 총매출 > 0 else "0%")
        
        # ===== 탭4: 거래처별 마진 =====
        with tab4:
            st.markdown("### 🏢 거래처별 마진 분석")
            
            col1, col2 = st.columns(2)
            with col1:
                선택_연도_거래처 = st.selectbox("연도 선택", 연도_목록, format_func=lambda x: f"{x}년", key="customer_margin_year")
            
            df['연도'] = df['날짜'].dt.year
            연도_df = df[(df['연도'] == 선택_연도_거래처) & (df['참조'] == '=외출')]
            
            # 거래처별 마진 계산
            거래처별_마진 = 연도_df.groupby('거래처').agg({
                '공급가액': 'sum',
                '마진': 'sum',
                '날짜': 'count'
            }).rename(columns={'날짜': '거래횟수'})
            
            거래처별_마진['마진율'] = (거래처별_마진['마진'] / 거래처별_마진['공급가액'] * 100).round(1)
            거래처별_마진 = 거래처별_마진.sort_values('마진', ascending=False)
            
            # 상위/하위 분석
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏆 마진 TOP 10")
                top10 = 거래처별_마진.head(10).copy()
                display_top = top10.reset_index()
                display_top['공급가액'] = display_top['공급가액'].apply(lambda x: f"{x:,.0f}")
                display_top['마진'] = display_top['마진'].apply(lambda x: f"{x:,.0f}")
                display_top['마진율'] = display_top['마진율'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_top, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### ⚠️ 마진율 하위 10 (주의 필요)")
                # 마진율 기준 하위 (매출이 있는 거래처만)
                마진율_하위 = 거래처별_마진[거래처별_마진['공급가액'] > 100000].sort_values('마진율').head(10).copy()
                display_bottom = 마진율_하위.reset_index()
                display_bottom['공급가액'] = display_bottom['공급가액'].apply(lambda x: f"{x:,.0f}")
                display_bottom['마진'] = display_bottom['마진'].apply(lambda x: f"{x:,.0f}")
                display_bottom['마진율'] = display_bottom['마진율'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_bottom, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # 마진율 분포 차트
            st.markdown("#### 거래처 마진율 분포")
            fig = px.histogram(거래처별_마진, x='마진율', nbins=20, title='마진율 분포')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            # 전체 거래처 목록
            with st.expander("📋 전체 거래처 마진 보기"):
                display_전체 = 거래처별_마진.reset_index()
                display_전체['공급가액'] = display_전체['공급가액'].apply(lambda x: f"{x:,.0f}")
                display_전체['마진'] = display_전체['마진'].apply(lambda x: f"{x:,.0f}")
                display_전체['마진율'] = display_전체['마진율'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_전체, use_container_width=True, hide_index=True, height=400)
        
        # ===== 탭5: 유영찬 매출 =====
        with tab5:
            st.markdown("### 👤 유영찬 매출 관리")
            
            # 유영찬 거래만 필터
            유영찬_df = df[df['거래처'] == '유영찬'].copy()
            
            if len(유영찬_df) == 0:
                st.info("유영찬 거래 내역이 없습니다.")
            else:
                유영찬_df['연도'] = 유영찬_df['날짜'].dt.year
                유영찬_df['월'] = 유영찬_df['날짜'].dt.month
                
                # 연도 선택
                col1, col2 = st.columns(2)
                with col1:
                    선택_연도_유영찬 = st.selectbox("연도 선택", 연도_목록, format_func=lambda x: f"{x}년", key="yoo_year")
                
                연도_유영찬 = 유영찬_df[유영찬_df['연도'] == 선택_연도_유영찬]
                
                # 거래 유형 분류
                # 1. 제품 출고 (판매) - 입금, 수당, 택배 제외
                제품_df = 연도_유영찬[~연도_유영찬['품목'].str.contains('입금|수당|택배', na=False)]
                제품_df = 제품_df[제품_df['공급가액'] > 0]  # 양수만 (판매)
                
                # 2. 입금 (유영찬이 받아온 돈)
                입금_df = 연도_유영찬[연도_유영찬['품목'].str.contains('입금', na=False)]
                
                # 3. 수당
                수당_df = 연도_유영찬[연도_유영찬['품목'].str.contains('수당', na=False)]
                
                # 요약 지표
                총_제품출고 = 제품_df['공급가액'].sum()
                총_입금 = 입금_df['공급가액'].sum()
                총_수당 = abs(수당_df['공급가액'].sum())
                총_마진 = 제품_df['마진'].sum() if '마진' in 제품_df.columns else 0
                
                st.markdown(f"#### {선택_연도_유영찬}년 유영찬 실적 요약")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 제품 출고액", f"{총_제품출고:,.0f}원")
                with col2:
                    st.metric("💰 입금액", f"{총_입금:,.0f}원")
                with col3:
                    st.metric("💵 수당 지급", f"{총_수당:,.0f}원")
                with col4:
                    st.metric("📈 마진", f"{총_마진:,.0f}원")
                
                # 미수금 표시 - base_receivables에서 직접 가져옴
                기초미수금_dict = st.session_state.base_receivables_df.set_index('거래처')['기초미수금'].to_dict() if len(st.session_state.base_receivables_df) > 0 else {}
                유영찬_미수금 = 기초미수금_dict.get('유영찬', 0)
                
                if 유영찬_미수금 > 0:
                    st.markdown(f"""
                    <div style='background-color: #fff3e0; border: 2px solid #ff9800; border-radius: 8px; padding: 15px; margin: 15px 0;'>
                        <h3 style='color: #000000; margin: 0;'>⚠️ 유영찬 미수금: {유영찬_미수금:,.0f}원</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 월별 실적
                st.markdown("#### 📊 월별 실적")
                
                월별_실적 = []
                for 월 in range(1, 13):
                    월_제품 = 제품_df[제품_df['월'] == 월]
                    월_입금 = 입금_df[입금_df['월'] == 월]
                    월_수당 = 수당_df[수당_df['월'] == 월]
                    
                    월별_실적.append({
                        '월': f"{월}월",
                        '제품출고': 월_제품['공급가액'].sum(),
                        '입금': 월_입금['공급가액'].sum(),
                        '수당': abs(월_수당['공급가액'].sum()),
                        '마진': 월_제품['마진'].sum() if '마진' in 월_제품.columns else 0
                    })
                
                월별_df = pd.DataFrame(월별_실적)
                
                # 차트
                fig = go.Figure()
                fig.add_trace(go.Bar(name='제품출고', x=월별_df['월'], y=월별_df['제품출고'], marker_color='#1976D2'))
                fig.add_trace(go.Bar(name='입금', x=월별_df['월'], y=월별_df['입금'], marker_color='#43A047'))
                fig.add_trace(go.Scatter(name='마진', x=월별_df['월'], y=월별_df['마진'], mode='lines+markers', line=dict(color='#FF5722', width=3)))
                fig.update_layout(barmode='group', height=400, title=f'{선택_연도_유영찬}년 월별 실적')
                st.plotly_chart(fig, use_container_width=True)
                
                # 테이블
                display_월별 = 월별_df.copy()
                for col in ['제품출고', '입금', '수당', '마진']:
                    display_월별[col] = display_월별[col].apply(lambda x: f"{x:,.0f}")
                st.dataframe(display_월별, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # 제품별 판매 내역
                st.markdown("#### 📦 제품별 판매 내역")
                
                if len(제품_df) > 0:
                    제품별 = 제품_df.groupby('품목').agg({
                        '수량': 'sum',
                        '공급가액': 'sum',
                        '마진': 'sum'
                    }).reset_index()
                    제품별 = 제품별.sort_values('공급가액', ascending=False)
                    제품별['마진율'] = (제품별['마진'] / 제품별['공급가액'] * 100).round(1)
                    
                    display_제품 = 제품별.copy()
                    display_제품['수량'] = display_제품['수량'].apply(lambda x: f"{x:,.0f}")
                    display_제품['공급가액'] = display_제품['공급가액'].apply(lambda x: f"{x:,.0f}")
                    display_제품['마진'] = display_제품['마진'].apply(lambda x: f"{x:,.0f}")
                    display_제품['마진율'] = display_제품['마진율'].apply(lambda x: f"{x:.1f}%")
                    
                    st.dataframe(display_제품, use_container_width=True, hide_index=True, height=400)
                
                st.markdown("---")
                
                # 입금 내역 (어디서 받아온 돈인지)
                st.markdown("#### 💰 입금 내역 (유영찬이 받아온 돈)")
                
                if len(입금_df) > 0:
                    입금_표시 = 입금_df[['날짜', '품목', '공급가액']].copy()
                    입금_표시 = 입금_표시.sort_values('날짜', ascending=False)
                    입금_표시['날짜'] = 입금_표시['날짜'].dt.strftime('%Y-%m-%d')
                    입금_표시['공급가액'] = 입금_표시['공급가액'].apply(lambda x: f"{x:,.0f}")
                    
                    st.dataframe(입금_표시.head(30), use_container_width=True, hide_index=True)

# ==================== 품목 관리 ====================
elif menu == "📦 품목 관리":
    st.title("📦 품목 관리")
    
    products_df = st.session_state.products_df
    ledger_df = st.session_state.ledger_df
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📋 품목 목록", "➕ 품목 추가", "🔍 품목 검색"])
    
    # ===== 탭1: 품목 목록 (3단 레이아웃) =====
    with tab1:
        if len(products_df) > 0:
            # ========== 3단 레이아웃: 카테고리 | 품목 | 상세정보 ==========
            col_category, col_product, col_detail = st.columns([1, 1.5, 2.5])
            
            # ========== 1단: 카테고리 선택 ==========
            with col_category:
                st.markdown("### 📂 카테고리")
                
                # NaN 값 제거 후 정렬
                카테고리_unique = products_df['카테고리'].dropna().unique().tolist()
                카테고리_list = ["전체"] + sorted([x for x in 카테고리_unique if x])
                
                # 절단석이 있으면 기본 선택
                기본_인덱스 = 카테고리_list.index("절단석") if "절단석" in 카테고리_list else 0
                
                선택카테고리 = st.radio("", 카테고리_list, index=기본_인덱스, label_visibility="collapsed")
                
                st.markdown("---")
                
                # 카테고리별 개수 표시
                if 선택카테고리 == "전체":
                    st.info(f"📦 전체 {len(products_df)}개 품목")
                else:
                    개수 = len(products_df[products_df['카테고리'] == 선택카테고리])
                    st.info(f"📦 {개수}개 품목")
            
            # ========== 2단: 품목 선택 ==========
            with col_product:
                st.markdown("### 📦 품목 선택")
                
                # 카테고리 필터링
                if 선택카테고리 != "전체":
                    filtered_df = products_df[products_df['카테고리'] == 선택카테고리].copy()
                else:
                    filtered_df = products_df.copy()
                
                # 최근 6개월 거래 횟수 기준 정렬
                기준일_6개월 = get_kst_now() - timedelta(days=180)
                
                if len(ledger_df) > 0:
                    최근거래 = ledger_df[ledger_df['날짜'] >= 기준일_6개월]
                    품목별_거래수 = 최근거래.groupby('품목').size().to_dict()
                    
                    filtered_df['최근거래수'] = filtered_df['품목명'].apply(
                        lambda x: sum(cnt for 품목, cnt in 품목별_거래수.items() if str(x) in str(품목))
                    )
                    filtered_df = filtered_df.sort_values('최근거래수', ascending=False)
                
                if len(filtered_df) > 0:
                    # 품목 리스트를 라디오 버튼으로
                    품목_옵션 = []
                    for _, row in filtered_df.iterrows():
                        옵션 = f"{row['품목명']}"
                        if pd.notna(row['규격']):
                            옵션 += f" ({row['규격']})"
                        품목_옵션.append((옵션, row['품목코드']))
                    
                    # 선택 상태 저장
                    if 'selected_product' not in st.session_state:
                        st.session_state.selected_product = None
                    
                    선택된_인덱스 = 0
                    if st.session_state.selected_product:
                        try:
                            선택된_인덱스 = [x[1] for x in 품목_옵션].index(st.session_state.selected_product)
                        except:
                            선택된_인덱스 = 0
                    
                    선택품목 = st.radio(
                        "",
                        range(len(품목_옵션)),
                        format_func=lambda x: 품목_옵션[x][0],
                        index=선택된_인덱스,
                        label_visibility="collapsed"
                    )
                    
                    if 선택품목 is not None:
                        st.session_state.selected_product = 품목_옵션[선택품목][1]
                else:
                    st.warning("해당 카테고리에 품목이 없습니다.")
                    st.session_state.selected_product = None
            
            # ========== 3단: 품목 상세 정보 ==========
            with col_detail:
                if st.session_state.selected_product:
                    품목코드 = st.session_state.selected_product
                    품목정보 = products_df[products_df['품목코드'] == 품목코드].iloc[0]
                    
                    st.markdown("### 📊 품목 상세 정보")
                    
                    # 기본 정보
                    st.markdown("#### 📦 기본 정보")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**품목코드:** `{품목정보['품목코드']}`")
                        st.markdown(f"**품목명:** **{품목정보['품목명']}**")
                    with col2:
                        st.markdown(f"**카테고리:** {품목정보['카테고리']}")
                        st.markdown(f"**규격:** {품목정보['규격']}")
                    
                    st.markdown("---")
                    
                    # 이 품목의 거래 내역 필터링
                    품목명 = 품목정보['품목명']
                    품목_거래 = ledger_df[ledger_df['품목'].str.contains(품목명, na=False)]
                    
                    if len(품목_거래) > 0:
                        # 구매 거래 (공급가액 < 0 = 내가 매입)
                        구매_거래 = 품목_거래[품목_거래['공급가액'] < 0]
                        
                        # 판매 거래 (공급가액 > 0 = 내가 판매, 입금/출금 제외)
                        판매_거래 = 품목_거래[(품목_거래['공급가액'] > 0) & (~품목_거래['참조'].str.contains('입금|출금', na=False))]
                        
                        # 💰 구매 정보
                        st.markdown("#### 💰 구매 정보 (내가 사는 가격)")
                        
                        if len(구매_거래) > 0:
                            평균_구매가 = 구매_거래['단가'].mean()
                            최저_구매가 = 구매_거래['단가'].min()
                            최고_구매가 = 구매_거래['단가'].max()
                            총_구매수량 = 구매_거래['수량'].sum()
                            
                            # 최저가/최고가 거래처
                            최저가_row = 구매_거래[구매_거래['단가'] == 최저_구매가].iloc[0]
                            최고가_row = 구매_거래[구매_거래['단가'] == 최고_구매가].iloc[0]
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("평균 구매가", f"{평균_구매가:,.0f}원")
                            with col2:
                                st.metric("최저가", f"{최저_구매가:,.0f}원")
                            with col3:
                                st.metric("최고가", f"{최고_구매가:,.0f}원")
                            
                            st.markdown(f"""
                            - **최저가 거래처:** {최저가_row['거래처']} ({최저가_row['날짜'].strftime('%m/%d')})
                            - **최고가 거래처:** {최고가_row['거래처']} ({최고가_row['날짜'].strftime('%m/%d')})
                            - **총 구매 횟수:** {len(구매_거래)}건
                            - **총 구매 수량:** {총_구매수량:,.0f}개
                            """)
                        else:
                            st.info("구매 내역이 없습니다.")
                        
                        st.markdown("---")
                        
                        # 🏢 판매 현황
                        st.markdown("#### 🏢 판매 현황 (내가 판 거래처)")
                        
                        if len(판매_거래) > 0:
                            # 당월 판매수량
                            현재월 = get_kst_now().month
                            당월_판매 = 판매_거래[판매_거래['날짜'].dt.month == 현재월]
                            당월_판매수량 = 당월_판매['수량'].sum()
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("당월 판매수량", f"{당월_판매수량:,.0f}개", f"{get_kst_now().month}월")
                            with col2:
                                st.metric("총 판매수량", f"{판매_거래['수량'].sum():,.0f}개")
                            
                            # 최근 판매 거래처 (최근 5건)
                            st.markdown("**최근 판매 거래처:**")
                            최근_판매 = 판매_거래.sort_values('날짜', ascending=False).head(5)
                            
                            for idx, row in 최근_판매.iterrows():
                                st.markdown(f"- **{row['거래처']}** - {row['수량']:,.0f}개 ({row['날짜'].strftime('%m/%d')})")
                        else:
                            st.info("판매 내역이 없습니다.")
                        
                        st.markdown("---")
                        
                        # 📅 최근 거래 내역
                        st.markdown("#### 📅 최근 거래 내역 (최근 10건)")
                        
                        최근_거래 = 품목_거래.sort_values('날짜', ascending=False).head(10)
                        
                        # 거래 내역을 표로 표시
                        display_df = 최근_거래[['날짜', '거래처', '참조', '수량', '단가']].copy()
                        display_df['날짜'] = display_df['날짜'].dt.strftime('%Y-%m-%d')
                        display_df['구분'] = display_df['참조'].apply(lambda x: '구매' if '외입' in x else '판매' if '외출' in x else x)
                        display_df['수량'] = display_df['수량'].apply(lambda x: f"{x:,.0f}개")
                        display_df['단가'] = display_df['단가'].apply(lambda x: f"{x:,.0f}원")
                        display_df = display_df[['날짜', '거래처', '구분', '수량', '단가']]
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                    else:
                        st.info("이 품목의 거래 내역이 없습니다.")
                else:
                    st.info("👈 좌측에서 품목을 선택하세요.")
        else:
            st.info("등록된 품목이 없습니다. '품목 추가' 탭에서 품목을 추가하세요.")
    
    # ===== 탭2: 품목 추가 =====
    with tab2:
        st.markdown("### ➕ 새 품목 추가")
        
        col1, col2 = st.columns(2)
        
        with col1:
            새품목코드 = st.text_input("품목코드", placeholder="예: P-001")
            새품목명 = st.text_input("품목명", placeholder="예: TURBO Premium 절단석")
        
        with col2:
            새카테고리 = st.text_input("카테고리", placeholder="예: 절단석")
            새규격 = st.text_input("규격", placeholder="예: 4인치")
        
        if st.button("💾 품목 추가", type="primary", use_container_width=True):
            if not 새품목코드 or not 새품목명:
                st.error("품목코드와 품목명은 필수입니다!")
            elif 새품목코드 in products_df['품목코드'].values:
                st.error(f"품목코드 '{새품목코드}'는 이미 존재합니다!")
            else:
                new_row = pd.DataFrame([{
                    '품목코드': 새품목코드,
                    '품목명': 새품목명,
                    '카테고리': 새카테고리,
                    '규격': 새규격
                }])
                st.session_state.products_df = pd.concat([products_df, new_row], ignore_index=True)
                save_products()
                st.success(f"✅ 품목 '{새품목명}' (코드: {새품목코드})이 추가되었습니다!")
                st.rerun()
    
    # ===== 탭3: 품목 검색 =====
    with tab3:
        st.markdown("### 🔍 품목 검색")
        
        검색어 = st.text_input("검색어 입력", placeholder="품목명, 품목코드, 카테고리로 검색...")
        
        if 검색어:
            검색결과 = products_df[
                products_df['품목코드'].str.contains(검색어, case=False, na=False) |
                products_df['품목명'].str.contains(검색어, case=False, na=False) |
                products_df['카테고리'].str.contains(검색어, case=False, na=False) |
                products_df['규격'].str.contains(검색어, case=False, na=False)
            ]
            
            if len(검색결과) > 0:
                st.success(f"🔍 {len(검색결과)}개 품목을 찾았습니다!")
                st.dataframe(검색결과, use_container_width=True)
            else:
                st.warning("검색 결과가 없습니다.")

# ==================== 재고 관리 ====================
elif menu == "📋 재고 관리":
    st.title("📋 재고 관리")
    
    inventory_df = st.session_state.inventory_df
    ledger_df = st.session_state.ledger_df
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📊 재고 현황", "➕ 입고/출고", "⚠️ 재고 부족", "🔧 재고 설정"])
    
    # ===== 탭1: 재고 현황 =====
    with tab1:
        st.markdown("### 📊 현재 재고 현황")
        st.markdown(f"**기준일:** 2025년 12월 20일")
        
        if len(inventory_df) > 0:
            # 검색 필터
            col1, col2 = st.columns([3, 1])
            with col1:
                검색어 = st.text_input("🔍 품목 검색", placeholder="품목명으로 검색...")
            with col2:
                정렬기준 = st.selectbox("정렬", ["재고 많은 순", "재고 적은 순", "품목명순"])
            
            # 필터링
            display_df = inventory_df.copy()
            if 검색어:
                display_df = display_df[display_df['품목명'].str.contains(검색어, case=False, na=False)]
            
            # 정렬
            if 정렬기준 == "재고 많은 순":
                display_df = display_df.sort_values('현재재고', ascending=False)
            elif 정렬기준 == "재고 적은 순":
                display_df = display_df.sort_values('현재재고', ascending=True)
            else:
                display_df = display_df.sort_values('품목명')
            
            # 통계
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📦 총 품목 수", f"{len(inventory_df)}개")
            with col2:
                st.metric("📊 총 재고 수량", f"{inventory_df['현재재고'].sum():,.0f}개")
            with col3:
                총평가액 = inventory_df['재고평가액'].sum() if '재고평가액' in inventory_df.columns else 0
                st.metric("💰 총 재고평가액", f"{총평가액:,.0f}원")
            with col4:
                재고없음 = len(inventory_df[inventory_df['현재재고'] <= 0])
                st.metric("❌ 재고 없음", f"{재고없음}개")
            
            # 🔥 핵심 제품: 4인치/5인치 절단석 요약
            st.markdown("#### 🔥 핵심 제품 (절단석)")
            
            # 4인치 절단석
            절단석_4인치 = inventory_df[inventory_df['품목명'].str.contains('4.*인치|4"|4인치|@4|@ 4', na=False, regex=True)]
            절단석_4인치 = 절단석_4인치[절단석_4인치['품목명'].str.contains('절단석|절단', na=False)]
            
            # 5인치 절단석
            절단석_5인치 = inventory_df[inventory_df['품목명'].str.contains('5.*인치|5"|5인치|@5|@ 5', na=False, regex=True)]
            절단석_5인치 = 절단석_5인치[절단석_5인치['품목명'].str.contains('절단석|절단', na=False)]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div style='background-color: #e3f2fd; border: 2px solid #1976d2; border-radius: 10px; padding: 15px; margin: 5px 0;'>
                    <h4 style='color: #000000; margin: 0 0 10px 0;'>📦 4인치 절단석</h4>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("품목 수", f"{len(절단석_4인치)}개")
                with c2:
                    st.metric("재고 수량", f"{절단석_4인치['현재재고'].sum():,.0f}개")
                with c3:
                    평가액_4 = 절단석_4인치['재고평가액'].sum() if '재고평가액' in 절단석_4인치.columns else 0
                    st.metric("평가액", f"{평가액_4:,.0f}원")
            
            with col2:
                st.markdown("""
                <div style='background-color: #fff3e0; border: 2px solid #ff9800; border-radius: 10px; padding: 15px; margin: 5px 0;'>
                    <h4 style='color: #000000; margin: 0 0 10px 0;'>📦 5인치 절단석</h4>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("품목 수", f"{len(절단석_5인치)}개")
                with c2:
                    st.metric("재고 수량", f"{절단석_5인치['현재재고'].sum():,.0f}개")
                with c3:
                    평가액_5 = 절단석_5인치['재고평가액'].sum() if '재고평가액' in 절단석_5인치.columns else 0
                    st.metric("평가액", f"{평가액_5:,.0f}원")
            
            st.markdown("---")
            
            # 재고 목록 표시 (품목명, 재고수량, 매입단가, 재고평가액, 매입업체)
            표시_컬럼 = ['품목명', '현재재고', '매입단가', '재고평가액', '매입업체']
            표시_컬럼 = [col for col in 표시_컬럼 if col in display_df.columns]
            
            # 금액 포맷팅
            display_formatted = display_df[표시_컬럼].copy()
            if '매입단가' in display_formatted.columns:
                display_formatted['매입단가'] = display_formatted['매입단가'].apply(lambda x: f"{x:,.0f}원" if pd.notna(x) else "")
            if '재고평가액' in display_formatted.columns:
                display_formatted['재고평가액'] = display_formatted['재고평가액'].apply(lambda x: f"{x:,.0f}원" if pd.notna(x) else "")
            
            display_formatted = display_formatted.rename(columns={'현재재고': '재고수량'})
            
            st.dataframe(
                display_formatted,
                use_container_width=True,
                height=500
            )
            
            # 다운로드 버튼
            csv = inventory_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 재고 목록 다운로드 (CSV)",
                data=csv,
                file_name="inventory_list.csv",
                mime="text/csv"
            )
        else:
            st.info("등록된 재고가 없습니다. '재고 설정' 탭에서 기초 재고를 등록해주세요.")
    
    # ===== 탭2: 입고/출고 =====
    with tab2:
        st.markdown("### ➕ 수동 입고/출고")
        st.info("💡 일반 거래 입력 시에는 자동으로 재고가 차감됩니다. 이 화면은 수동 조정용입니다.")
        
        if len(inventory_df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 품목 선택")
                품목_list = inventory_df['품목명'].tolist()
                선택_품목 = st.selectbox("품목", [""] + 품목_list)
                
                if 선택_품목:
                    현재_재고 = inventory_df[inventory_df['품목명'] == 선택_품목]['현재재고'].values[0]
                    st.info(f"📦 현재 재고: **{현재_재고:,.0f}개**")
            
            with col2:
                st.markdown("#### 수량 입력")
                입출고_유형 = st.radio("유형", ["입고 (+)", "출고 (-)"], horizontal=True)
                수량 = st.number_input("수량", min_value=0, value=0, step=1)
                사유 = st.text_input("사유", placeholder="예: 재고 실사 조정, 파손 등")
            
            if st.button("✅ 적용", type="primary", use_container_width=True):
                if 선택_품목 and 수량 > 0:
                    idx = inventory_df[inventory_df['품목명'] == 선택_품목].index[0]
                    if 입출고_유형 == "입고 (+)":
                        st.session_state.inventory_df.loc[idx, '현재재고'] += 수량
                        st.success(f"✅ {선택_품목} +{수량}개 입고 완료!")
                    else:
                        st.session_state.inventory_df.loc[idx, '현재재고'] -= 수량
                        st.success(f"✅ {선택_품목} -{수량}개 출고 완료!")
                    save_inventory()
                    st.rerun()
                else:
                    st.error("품목과 수량을 입력해주세요.")
        else:
            st.warning("재고 데이터가 없습니다.")
    
    # ===== 탭3: 재고 부족 =====
    with tab3:
        st.markdown("### ⚠️ 재고 부족 알림")
        st.info("💡 최근 10개월 내 거래된 품목만 표시됩니다.")
        
        if len(inventory_df) > 0 and len(ledger_df) > 0:
            # 최근 10개월 거래 품목 필터링
            기준일_10개월 = get_kst_now() - timedelta(days=300)
            
            최근거래 = ledger_df[ledger_df['날짜'] >= 기준일_10개월]
            최근거래_품목 = 최근거래['품목'].dropna().unique().tolist()
            
            # 품목별 거래 횟수 계산
            품목별_거래수 = 최근거래.groupby('품목').size().to_dict()
            
            # 재고 부족 기준 설정
            부족_기준 = st.slider("재고 부족 기준 (개)", min_value=0, max_value=1000, value=100, step=10)
            
            # 최근 10개월 거래 품목 중 재고 부족 품목
            부족_df = inventory_df[inventory_df['현재재고'] <= 부족_기준].copy()
            
            # 최근 거래된 품목만 필터링
            부족_df['최근거래'] = 부족_df['품목명'].apply(
                lambda x: any(str(x) in str(품목) for 품목 in 최근거래_품목)
            )
            부족_df = 부족_df[부족_df['최근거래'] == True]
            
            # 거래 횟수 추가 및 정렬
            부족_df['거래횟수'] = 부족_df['품목명'].apply(
                lambda x: sum(cnt for 품목, cnt in 품목별_거래수.items() if str(x) in str(품목))
            )
            부족_df = 부족_df.sort_values('거래횟수', ascending=False)
            
            if len(부족_df) > 0:
                st.error(f"⚠️ 재고 부족 품목: **{len(부족_df)}개** (최근 10개월 거래 품목 중)")
                
                for _, row in 부족_df.iterrows():
                    재고 = row['현재재고']
                    품목 = row['품목명']
                    거래수 = row['거래횟수']
                    
                    if 재고 <= 0:
                        st.markdown(f"❌ **{품목}** - 재고 없음! (거래 {거래수}회)")
                    elif 재고 <= 부족_기준 / 2:
                        st.markdown(f"🔴 **{품목}** - {재고:,.0f}개 (긴급, 거래 {거래수}회)")
                    else:
                        st.markdown(f"🟡 **{품목}** - {재고:,.0f}개 (거래 {거래수}회)")
            else:
                st.success(f"✅ 재고 {부족_기준}개 이하인 품목이 없습니다!")
        else:
            st.info("재고 데이터가 없습니다.")
    
    # ===== 탭4: 재고 설정 =====
    with tab4:
        st.markdown("### 🔧 재고 설정")
        
        st.markdown("#### 📥 기초 재고 일괄 등록")
        st.info("CSV 파일을 업로드하여 기초 재고를 등록할 수 있습니다.")
        
        uploaded_file = st.file_uploader("재고 CSV 파일 업로드", type=['csv'])
        
        if uploaded_file:
            try:
                new_inventory = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                st.success(f"✅ {len(new_inventory)}개 품목 로드 완료!")
                st.dataframe(new_inventory.head(10))
                
                if st.button("📥 재고 데이터 적용", type="primary"):
                    # 컬럼명 맞추기
                    if '재고수량' in new_inventory.columns:
                        new_inventory = new_inventory.rename(columns={'재고수량': '현재재고'})
                    if '현재재고' not in new_inventory.columns and '기초재고' in new_inventory.columns:
                        new_inventory['현재재고'] = new_inventory['기초재고']
                    
                    # 필수 컬럼 확인
                    if '품목명' in new_inventory.columns and '현재재고' in new_inventory.columns:
                        new_inventory['기초재고'] = new_inventory['현재재고']
                        new_inventory['기준일자'] = '2025-12-20'
                        if '안전재고' not in new_inventory.columns:
                            new_inventory['안전재고'] = 100
                        if '단위' not in new_inventory.columns:
                            new_inventory['단위'] = '개'
                        
                        st.session_state.inventory_df = new_inventory[['품목명', '기초재고', '현재재고', '기준일자', '안전재고', '단위']]
                        save_inventory()
                        st.success("✅ 재고 데이터가 적용되었습니다!")
                        st.rerun()
                    else:
                        st.error("CSV 파일에 '품목명'과 '현재재고(또는 재고수량)' 컬럼이 필요합니다.")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")
        
        st.markdown("---")
        st.markdown("#### 📊 현재 재고 통계")
        if len(inventory_df) > 0:
            st.write(f"- 총 품목 수: {len(inventory_df)}개")
            st.write(f"- 총 재고 수량: {inventory_df['현재재고'].sum():,.0f}개")
            st.write(f"- 기준일자: {inventory_df['기준일자'].iloc[0] if len(inventory_df) > 0 else 'N/A'}")

# ==================== 거래처 관리 ====================
elif menu == "👥 거래처 관리":
    st.title("👥 거래처 관리")
    
    ledger_df = st.session_state.ledger_df
    base_recv_df = st.session_state.base_receivables_df
    
    # 거래처 목록 추출
    거래처_list = sorted(ledger_df['거래처'].dropna().unique().tolist()) if len(ledger_df) > 0 else []
    
    # ========== 구매 주기 분석 함수 ==========
    def 구매주기_분석(거래처명, ledger_df):
        """거래처의 품목별 구매 주기 분석 (고객이 구매하는 주기)"""
        거래처_df = ledger_df[ledger_df['거래처'] == 거래처명]
        # 내가 판매한 것 = 공급가액 > 0
        판매_df = 거래처_df[거래처_df['공급가액'] > 0]
        # 입금/출금 제외
        판매_df = 판매_df[~판매_df['참조'].str.contains('입금|출금', na=False)]
        
        if len(판매_df) < 2:
            return []
        
        결과 = []
        품목_list = 판매_df['품목'].unique()
        
        for 품목 in 품목_list:
            if pd.isna(품목):
                continue
            품목_df = 판매_df[판매_df['품목'] == 품목].sort_values('날짜')
            
            if len(품목_df) >= 2:
                # 구매일 간격 계산
                날짜들 = 품목_df['날짜'].tolist()
                간격들 = []
                for i in range(1, len(날짜들)):
                    간격 = (날짜들[i] - 날짜들[i-1]).days
                    if 간격 > 0:
                        간격들.append(간격)
                
                if 간격들:
                    평균_주기 = sum(간격들) / len(간격들)
                    마지막_구매일 = 날짜들[-1]
                    다음_예상일 = 마지막_구매일 + timedelta(days=평균_주기)
                    남은_일수 = (다음_예상일 - get_kst_now()).days
                    
                    결과.append({
                        '품목': 품목[:30] + '...' if len(품목) > 30 else 품목,
                        '평균주기': int(평균_주기),
                        '마지막구매': 마지막_구매일,
                        '다음예상': 다음_예상일,
                        '남은일수': 남은_일수,
                        '구매횟수': len(품목_df)
                    })
        
        # 남은 일수 기준 정렬 (임박한 것 먼저)
        결과.sort(key=lambda x: x['남은일수'])
        return 결과
    
    def 판매기대치_계산(거래처명, ledger_df):
        """거래처의 판매 기대치 점수 계산"""
        거래처_df = ledger_df[ledger_df['거래처'] == 거래처명]
        # 내가 판매한 것 = 공급가액 > 0
        판매_df = 거래처_df[거래처_df['공급가액'] > 0]
        # 입금/출금 제외
        판매_df = 판매_df[~판매_df['참조'].str.contains('입금|출금', na=False)]
        
        if len(판매_df) == 0:
            return 0, {}
        
        # 최근 3개월 데이터만
        최근3개월 = get_kst_now() - timedelta(days=90)
        최근_판매 = 판매_df[판매_df['날짜'] >= 최근3개월]
        
        # 월평균 구매금액
        월평균_금액 = (최근_판매['공급가액'].sum() + 최근_판매['부가세'].sum()) / 3 if len(최근_판매) > 0 else 0
        
        # 구매 빈도 (월평균)
        월평균_횟수 = len(최근_판매) / 3
        
        # 구매 주기 임박 품목 수 (3개월 = 90일 내)
        주기_분석 = 구매주기_분석(거래처명, ledger_df)
        임박_품목 = len([x for x in 주기_분석 if x['남은일수'] <= 90])
        
        # 기대치 점수 계산 (0~100)
        점수 = 0
        점수 += min(임박_품목 * 20, 40)  # 임박 품목 (최대 40점)
        점수 += min(월평균_금액 / 100000, 30)  # 금액 (최대 30점)
        점수 += min(월평균_횟수 * 5, 30)  # 빈도 (최대 30점)
        
        상세 = {
            '월평균금액': 월평균_금액,
            '월평균횟수': 월평균_횟수,
            '임박품목수': 임박_품목,
            '주기분석': 주기_분석[:3] if 주기_분석 else []  # 상위 3개만
        }
        
        return min(점수, 100), 상세
    
    # ========== 거래처 분류 함수 ==========
    def 거래처_분류(ledger_df):
        """거래처를 매입/고객으로 분류하고 최근 거래일 기준 정렬
        
        분류 기준 (공급가액 부호):
        - 공급가액 < 0 (마이너스): 매입업체 (내가 구입)
        - 공급가액 > 0 (플러스): 고객업체 (내가 판매)
        """
        # 최근 6개월 데이터만 사용
        기준일_6개월 = get_kst_now() - timedelta(days=180)
        최근_ledger = ledger_df[ledger_df['날짜'] >= 기준일_6개월]
        
        매입업체 = {}  # 내가 사는 곳 (공급가액 마이너스)
        고객업체 = {}  # 내가 파는 곳 (공급가액 플러스)
        
        for _, row in 최근_ledger.iterrows():
            거래처 = row['거래처']
            날짜 = row['날짜']
            참조 = row['참조'] if pd.notna(row['참조']) else ''
            공급가액 = row['공급가액'] if pd.notna(row['공급가액']) else 0
            
            # 입금/출금은 제외 (거래처 분류에서)
            if '입금' in 참조 or '출금' in 참조:
                continue
            
            # 공급가액 부호로 분류
            if 공급가액 < 0:  # 마이너스 = 매입 (내가 구입)
                if 거래처 not in 매입업체 or 날짜 > 매입업체[거래처]:
                    매입업체[거래처] = 날짜
            elif 공급가액 > 0:  # 플러스 = 판매 (내가 판매)
                if 거래처 not in 고객업체 or 날짜 > 고객업체[거래처]:
                    고객업체[거래처] = 날짜
        
        # 3개월 기준으로 활성/휴면 분류
        기준일 = get_kst_now() - timedelta(days=90)
        
        매입_활성 = [(k, v) for k, v in 매입업체.items() if v >= 기준일]
        매입_휴면 = [(k, v) for k, v in 매입업체.items() if v < 기준일]
        고객_활성 = [(k, v) for k, v in 고객업체.items() if v >= 기준일]
        고객_휴면 = [(k, v) for k, v in 고객업체.items() if v < 기준일]
        
        # 최근 거래일 기준 정렬 (최신순)
        매입_활성.sort(key=lambda x: x[1], reverse=True)
        매입_휴면.sort(key=lambda x: x[1], reverse=True)
        고객_활성.sort(key=lambda x: x[1], reverse=True)
        고객_휴면.sort(key=lambda x: x[1], reverse=True)
        
        return {
            '매입_활성': 매입_활성,
            '매입_휴면': 매입_휴면,
            '고객_활성': 고객_활성,
            '고객_휴면': 고객_휴면
        }
    
    # 거래처 분류 실행
    분류된_거래처 = 거래처_분류(ledger_df) if len(ledger_df) > 0 else {'매입_활성': [], '매입_휴면': [], '고객_활성': [], '고객_휴면': []}
    
    # ========== 탭 구성 (4개 탭) ==========
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 오늘의 영업", "📤 고객업체", "📥 매입업체", "➕ 거래처 추가"])
    
    # ===== 탭1: 오늘의 영업 대시보드 =====
    with tab1:
        st.markdown("### 🎯 오늘의 영업 대시보드")
        st.markdown(f"**{get_kst_now().strftime('%Y년 %m월 %d일 %A')}** 기준")
        
        # 제외할 거래처 (영업직원, 위탁판매 등)
        제외_거래처 = ['유영찬']
        
        # 최근 6개월 데이터
        기준일_6개월 = get_kst_now() - timedelta(days=180)
        최근6개월_df = ledger_df[ledger_df['날짜'] >= 기준일_6개월]
        
        # 6개월 내 2회 이상 거래 + 매출 계산
        고객_매출 = []
        for 거래처 in ledger_df['거래처'].dropna().unique():
            if 거래처 in 제외_거래처:
                continue
            
            거래처_df = 최근6개월_df[최근6개월_df['거래처'] == 거래처]
            # 판매 거래만 (공급가액 > 0, 입금/출금 제외)
            판매_df = 거래처_df[(거래처_df['공급가액'] > 0) & (~거래처_df['참조'].str.contains('입금|출금', na=False))]
            
            거래횟수 = len(판매_df)
            if 거래횟수 >= 2:  # 2회 이상 거래
                총매출 = 판매_df['공급가액'].sum() + 판매_df['부가세'].sum()
                고객_매출.append({
                    '거래처': 거래처,
                    '거래횟수': 거래횟수,
                    '총매출': 총매출
                })
        
        # 매출 높은 순 정렬
        고객_매출.sort(key=lambda x: x['총매출'], reverse=True)
        
        if len(고객_매출) > 0:
            st.markdown("---")
            st.markdown("### 📞 오늘 연락 추천 TOP 5")
            st.caption("💡 최근 6개월 내 2회 이상 거래, 매출 높은 순")
            
            for i, item in enumerate(고객_매출[:5]):
                거래처명 = item['거래처']
                총매출 = item['총매출']
                거래횟수 = item['거래횟수']
                
                # 미수금은 base_receivables에서 직접 가져옴 (컴장부 GULREST)
                기초미수금_dict = base_recv_df.set_index('거래처')['기초미수금'].to_dict() if len(base_recv_df) > 0 else {}
                미수금 = 기초미수금_dict.get(거래처명, 0)
                
                # 구매 주기 임박 품목 (최근 6개월 거래 품목 중)
                주기_분석 = 구매주기_분석(거래처명, ledger_df)
                # 최근 6개월 내 거래된 품목만 필터링
                최근_품목 = 최근6개월_df[최근6개월_df['거래처'] == 거래처명]['품목'].dropna().unique()
                주기_분석 = [x for x in 주기_분석 if any(str(x['품목']) in str(p) for p in 최근_품목)]
                
                임박_품목_텍스트 = ""
                if 주기_분석:
                    임박 = 주기_분석[0]
                    if 임박['남은일수'] <= 0:
                        임박_품목_텍스트 = f"📦 {임박['품목']} - 구매 예상일 지남!"
                    elif 임박['남은일수'] <= 14:
                        임박_품목_텍스트 = f"📦 {임박['품목']} - {임박['남은일수']}일 후 예상"
                
                # 순위별 아이콘
                순위_아이콘 = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
                
                # 깔끔한 카드 스타일
                with st.container():
                    col1, col2 = st.columns([2, 3])
                    with col1:
                        st.markdown(f"**{순위_아이콘} {거래처명}**")
                    with col2:
                        st.markdown(f"💰 6개월 매출: **{총매출:,.0f}원** | 거래 {거래횟수}회 | 미수금: {미수금:,.0f}원")
                    
                    if 임박_품목_텍스트:
                        st.caption(임박_품목_텍스트)
                    st.markdown("---")
            
            # 구매 주기 임박 품목 - TOP 5 다음 업체 (6~15위)
            st.markdown("### ⏰ 구매 주기 임박 (TOP 6~15 업체)")
            st.caption("💡 TOP 5 다음 순위 업체 중 재구매 예상 품목")
            
            다음_업체 = 고객_매출[5:15] if len(고객_매출) > 5 else []
            
            모든_임박 = []
            for item in 다음_업체:
                거래처 = item['거래처']
                주기_분석 = 구매주기_분석(거래처, ledger_df)
                # 최근 6개월 내 거래된 품목만 필터링
                최근_품목 = 최근6개월_df[최근6개월_df['거래처'] == 거래처]['품목'].dropna().unique()
                주기_분석 = [x for x in 주기_분석 if any(str(x['품목']) in str(p) for p in 최근_품목)]
                
                for 품목 in 주기_분석:
                    if 품목['남은일수'] <= 14:  # 2주 이내
                        모든_임박.append({
                            '거래처': 거래처,
                            '매출': item['총매출'],
                            **품목
                        })
            
            모든_임박.sort(key=lambda x: x['남은일수'])
            
            if 모든_임박:
                임박_df = pd.DataFrame(모든_임박[:15])  # 상위 15개
                임박_df['다음예상'] = pd.to_datetime(임박_df['다음예상']).dt.strftime('%m/%d')
                임박_df['마지막구매'] = pd.to_datetime(임박_df['마지막구매']).dt.strftime('%m/%d')
                임박_df['상태'] = 임박_df['남은일수'].apply(
                    lambda x: '🔴 지남' if x <= 0 else '🟠 임박' if x <= 3 else '🟡 이번주' if x <= 7 else '🟢 여유'
                )
                
                display_df = 임박_df[['상태', '거래처', '품목', '평균주기', '마지막구매', '다음예상', '남은일수']]
                display_df.columns = ['상태', '거래처', '품목', '주기', '마지막', '예상일', 'D-day']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("2주 이내 구매 예상 품목이 없습니다.")
        else:
            st.info("거래처 데이터가 없습니다. 거래를 입력하면 자동으로 분석됩니다.")
    
    # ===== 탭2: 고객업체 (내가 판매하는 곳) =====
    with tab2:
        st.markdown("### 📤 고객업체")
        st.markdown("*내가 물건을 판매하는 업체*")
        
        # 고객업체 = 공급가액이 플러스인 거래
        고객_활성 = 분류된_거래처['고객_활성']
        고객_휴면 = 분류된_거래처['고객_휴면']
        
        # 전체 고객 목록 (활성 + 휴면)
        전체_고객 = []
        for x in 고객_활성:
            전체_고객.append((x[0], x[1], "🟢"))
        for x in 고객_휴면:
            전체_고객.append((x[0], x[1], "⚪"))
        
        if len(전체_고객) > 0:
            # 고객 선택 드롭다운
            고객_옵션 = [f"{x[2]} {x[0]} ({x[1].strftime('%m/%d')})" for x in 전체_고객]
            선택_idx = st.selectbox(
                f"고객 선택 (🟢활성 {len(고객_활성)}개 / ⚪휴면 {len(고객_휴면)}개)",
                range(len(고객_옵션)),
                format_func=lambda i: 고객_옵션[i],
                key="고객업체_선택"
            )
            
            선택_고객 = 전체_고객[선택_idx][0]
            
            st.markdown("---")
            st.markdown(f"## 🏢 {선택_고객}")
            
            # 이 고객에게 판매한 거래 데이터 (공급가액 > 0)
            고객_df = ledger_df[(ledger_df['거래처'] == 선택_고객) & (ledger_df['공급가액'] > 0) & (~ledger_df['참조'].str.contains('입금|출금', na=False))]
            
            # ===== 미수금 현황 (base_receivables에서 가져옴) =====
            st.markdown("### 💰 미수금 현황")
            
            # 미수금은 base_receivables에서 직접 가져옴 (컴장부 GULREST)
            기초미수금_dict = base_recv_df.set_index('거래처')['기초미수금'].to_dict() if len(base_recv_df) > 0 else {}
            미수금 = 기초미수금_dict.get(선택_고객, 0)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("총 거래 횟수", f"{len(고객_df)}건")
            with col_b:
                총_판매금액 = 고객_df['공급가액'].sum() + 고객_df['부가세'].sum()
                st.metric("총 판매금액", f"{총_판매금액:,.0f}원")
            with col_c:
                delta_color = "inverse" if 미수금 > 0 else "normal"
                st.metric("현재 미수금", f"{미수금:,.0f}원", delta="미수" if 미수금 > 0 else "완납", delta_color=delta_color)
            
            st.markdown("---")
            
            # ===== 연도별 매출 현황 =====
            st.markdown("### 📅 연도별 매출 현황")
            
            전체_거래처_df = ledger_df[ledger_df['거래처'] == 선택_고객].copy()
            
            if len(전체_거래처_df) > 0:
                # 연도 추출
                전체_거래처_df['연도'] = 전체_거래처_df['날짜'].dt.year
                
                # 당해년도, 전년도
                당해연도 = get_kst_now().year
                전년도 = 당해연도 - 1
                
                연도별_데이터 = []
                for 연도 in [당해연도, 전년도]:
                    연도_df = 전체_거래처_df[전체_거래처_df['연도'] == 연도]
                    
                    # 판매 (입금/출금 제외, 공급가액 > 0)
                    판매_df = 연도_df[(연도_df['공급가액'] > 0) & (~연도_df['참조'].str.contains('입금|출금', na=False))]
                    매출액 = 판매_df['공급가액'].sum()
                    부가세 = 판매_df['부가세'].sum()
                    합계 = 매출액 + 부가세
                    
                    # 입금
                    입금_df = 연도_df[연도_df['참조'].str.contains('입금', na=False)]
                    입금액 = abs(입금_df['공급가액'].sum())
                    
                    연도별_데이터.append({
                        '연도': f"{연도}년",
                        '매출액': 매출액,
                        '부가세': 부가세,
                        '합계': 합계,
                        '입금액': 입금액
                    })
                
                # 테이블 형식으로 표시
                col1, col2 = st.columns(2)
                
                for i, data in enumerate(연도별_데이터):
                    with col1 if i == 0 else col2:
                        st.markdown(f"#### {data['연도']} {'(당해)' if i == 0 else '(전년)'}")
                        st.markdown(f"""
                        | 항목 | 금액 |
                        |------|------|
                        | 매출액 | {data['매출액']:,.0f}원 |
                        | 부가세 | {data['부가세']:,.0f}원 |
                        | **합계** | **{data['합계']:,.0f}원** |
                        | 입금액 | {data['입금액']:,.0f}원 |
                        """)
            
            st.markdown("---")
            
            # ===== 최근 60일 판매 내역 =====
            st.markdown("### 📦 최근 60일 판매 내역")
            
            if len(고객_df) > 0:
                # 60일 이내 거래만
                기준일_60 = get_kst_now() - timedelta(days=60)
                최근60일_df = 고객_df[고객_df['날짜'] >= 기준일_60].sort_values('날짜', ascending=False)
                
                if len(최근60일_df) > 0:
                    st.success(f"🔍 최근 60일 내 {len(최근60일_df)}건 판매")
                    
                    # 테이블로 표시
                    for _, row in 최근60일_df.iterrows():
                        품목명 = row['품목'] if pd.notna(row['품목']) else ''
                        수량 = abs(row['수량']) if pd.notna(row['수량']) else 0
                        단가 = row['단가'] if pd.notna(row['단가']) else 0
                        공급가액 = row['공급가액'] if pd.notna(row['공급가액']) else 0
                        날짜 = row['날짜'].strftime('%m/%d')
                        
                        st.markdown(f"**{날짜}** | {품목명} | {수량:,.0f}개 × {단가:,.0f}원 = **{공급가액:,.0f}원**")
                else:
                    st.info("최근 60일 내 판매 내역이 없습니다.")
            else:
                st.info("판매 내역이 없습니다.")
            
            st.markdown("---")
            
            # ===== 구매 패턴 분석 =====
            st.markdown("### 📊 구매 패턴 분석")
            
            주기_분석 = 구매주기_분석(선택_고객, ledger_df)
            
            if 주기_분석:
                for item in 주기_분석[:5]:
                    남은일 = item['남은일수']
                    if 남은일 <= 0:
                        상태 = "🔴 구매일 지남!"
                    elif 남은일 <= 7:
                        상태 = f"🟠 {남은일}일 후"
                    elif 남은일 <= 14:
                        상태 = f"🟡 {남은일}일 후"
                    else:
                        상태 = f"🟢 {남은일}일 후"
                    
                    st.markdown(f"**{item['품목']}** - 주기: {item['평균주기']}일 | 마지막: {item['마지막구매'].strftime('%m/%d')} | {상태}")
            else:
                st.info("구매 패턴을 분석하려면 동일 품목 2회 이상 거래가 필요합니다.")
        else:
            st.info("고객업체 데이터가 없습니다.")
    
    # ===== 탭3: 매입업체 (내가 물건 사오는 곳) =====
    with tab3:
        st.markdown("### 📥 매입업체")
        st.markdown("*내가 물건을 구입하는 업체*")
        
        매입_활성 = 분류된_거래처['매입_활성']
        매입_휴면 = 분류된_거래처['매입_휴면']
        
        # 전체 매입업체 목록 (활성 + 휴면)
        전체_매입 = []
        for x in 매입_활성:
            전체_매입.append((x[0], x[1], "🟢"))
        for x in 매입_휴면:
            전체_매입.append((x[0], x[1], "⚪"))
        
        if len(전체_매입) > 0:
            # 매입업체 선택 드롭다운
            매입_옵션 = [f"{x[2]} {x[0]} ({x[1].strftime('%m/%d')})" for x in 전체_매입]
            선택_idx = st.selectbox(
                f"매입업체 선택 (🟢활성 {len(매입_활성)}개 / ⚪휴면 {len(매입_휴면)}개)",
                range(len(매입_옵션)),
                format_func=lambda i: 매입_옵션[i],
                key="매입업체_선택"
            )
            
            선택_매입업체 = 전체_매입[선택_idx][0]
            
            st.markdown("---")
            st.markdown(f"## 🏭 {선택_매입업체}")
            
            # 이 업체에서 매입한 거래 데이터 (공급가액 < 0)
            매입_df = ledger_df[(ledger_df['거래처'] == 선택_매입업체) & (ledger_df['공급가액'] < 0)]
            
            # ===== 매입 현황 =====
            st.markdown("### 💰 매입 현황")
            
            if len(매입_df) > 0:
                # 당월 매입
                현재월 = get_kst_now().month
                당월_df = 매입_df[매입_df['날짜'].dt.month == 현재월]
                당월_금액 = abs(당월_df['공급가액'].sum() + 당월_df['부가세'].sum())
                
                # 총 매입 (절대값)
                총_금액 = abs(매입_df['공급가액'].sum() + 매입_df['부가세'].sum())
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("총 매입 횟수", f"{len(매입_df)}건")
                with col_b:
                    st.metric("당월 매입", f"{len(당월_df)}건 / {당월_금액:,.0f}원")
                with col_c:
                    st.metric("총 매입금액", f"{총_금액:,.0f}원")
                
                st.markdown("---")
                
                # ===== 최근 60일 매입 내역 =====
                st.markdown("### 📦 최근 60일 매입 내역")
                
                기준일_60 = get_kst_now() - timedelta(days=60)
                최근60일_df = 매입_df[매입_df['날짜'] >= 기준일_60].sort_values('날짜', ascending=False)
                
                if len(최근60일_df) > 0:
                    st.success(f"🔍 최근 60일 내 {len(최근60일_df)}건 매입")
                    
                    for _, row in 최근60일_df.iterrows():
                        품목명 = row['품목'] if pd.notna(row['품목']) else ''
                        수량 = abs(row['수량']) if pd.notna(row['수량']) else 0
                        단가 = row['단가'] if pd.notna(row['단가']) else 0
                        공급가액 = abs(row['공급가액']) if pd.notna(row['공급가액']) else 0
                        날짜 = row['날짜'].strftime('%m/%d')
                        
                        st.markdown(f"**{날짜}** | {품목명} | {수량:,.0f}개 × {단가:,.0f}원 = **{공급가액:,.0f}원**")
                else:
                    st.info("최근 60일 내 매입 내역이 없습니다.")
                
                st.markdown("---")
                
                # ===== 주요 매입 품목 =====
                st.markdown("### 📊 주요 매입 품목")
                
                품목별_매입 = 매입_df.groupby('품목').agg({
                    '수량': 'sum',
                    '공급가액': 'sum',
                    '단가': 'mean'
                }).reset_index()
                품목별_매입['공급가액'] = 품목별_매입['공급가액'].abs()
                품목별_매입 = 품목별_매입.sort_values('공급가액', ascending=False).head(10)
                
                for _, row in 품목별_매입.iterrows():
                    품목명 = str(row['품목'])[:40] + '...' if len(str(row['품목'])) > 40 else row['품목']
                    st.markdown(f"**{품목명}** - {abs(row['수량']):,.0f}개 / 평균 {row['단가']:,.0f}원")
            else:
                st.info("매입 내역이 없습니다.")
        else:
            st.info("매입업체 데이터가 없습니다.")
    
    # ===== 탭4: 거래처 추가 (미래 기능) =====
    with tab4:
        st.markdown("### ➕ 거래처 정보 관리")
        
        # 거래처 정보 파일 경로
        from pathlib import Path
        data_dir = Path("data")
        customers_file = data_dir / "customers.csv"
        
        # 거래처 정보 로드
        if customers_file.exists():
            customers_df = pd.read_csv(customers_file)
            # 기존 데이터에 지역 컬럼이 없으면 추가
            if '지역' not in customers_df.columns:
                customers_df['지역'] = ''
        else:
            customers_df = pd.DataFrame(columns=[
                '거래처명', '구분', '지역', '사업자번호', '대표자명', '업태', '종목',
                '주소', '전화번호', '팩스번호', '휴대폰', '이메일',
                '대신화물_지점', '경동화물_지점', '담당자명', '담당자연락처', '메모'
            ])
        
        # 서브탭
        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📝 거래처 등록/수정", "📋 거래처 목록", "📤 지역 일괄 업로드"])
        
        # ===== 서브탭1: 거래처 등록/수정 =====
        with sub_tab1:
            st.markdown("#### 거래처 정보 입력")
            
            # 기존 거래처 선택 또는 신규 입력
            try:
                ledger_data = st.session_state.get('ledger_df', None)
                if ledger_data is not None and isinstance(ledger_data, pd.DataFrame) and len(ledger_data) > 0 and '거래처' in ledger_data.columns:
                    기존_거래처_list = sorted(ledger_data['거래처'].dropna().unique().tolist())
                else:
                    기존_거래처_list = []
            except:
                기존_거래처_list = []
            
            등록된_거래처_list = customers_df['거래처명'].tolist() if len(customers_df) > 0 else []
            
            입력_방식 = st.radio("입력 방식", ["기존 거래처 선택", "신규 거래처 입력"], horizontal=True, label_visibility="collapsed")
            
            if 입력_방식 == "기존 거래처 선택":
                if 기존_거래처_list:
                    선택_거래처 = st.selectbox("거래처 선택", 기존_거래처_list, key="customer_select")
                    # 이미 등록된 거래처면 기존 정보 불러오기
                    if 선택_거래처 in 등록된_거래처_list:
                        기존_정보 = customers_df[customers_df['거래처명'] == 선택_거래처].iloc[0].to_dict()
                        st.info(f"✅ '{선택_거래처}'의 기존 정보를 불러왔습니다. 수정 후 저장하세요.")
                    else:
                        기존_정보 = {}
                else:
                    st.warning("거래 내역이 없습니다. 먼저 거래를 입력하세요.")
                    선택_거래처 = ""
                    기존_정보 = {}
            else:
                선택_거래처 = st.text_input("거래처명 입력", key="new_customer_name")
                기존_정보 = {}
            
            if 선택_거래처:
                st.markdown("---")
                
                # 구분
                구분_옵션 = ["고객업체 (판매)", "매입업체 (구매)", "혼합 (판매+구매)"]
                구분_기본값 = 구분_옵션.index(기존_정보.get('구분', '고객업체 (판매)')) if 기존_정보.get('구분') in 구분_옵션 else 0
                구분 = st.selectbox("구분", 구분_옵션, index=구분_기본값)
                
                # 지역 선택 (방문 일정용)
                지역_옵션 = ["", "청주시 상당구", "청주시 서원구", "청주시 흥덕구", "청주시 청원구", 
                          "세종시", "대전시", "천안시", "아산시", "음성군", "진천군", "증평군", 
                          "괴산군", "보은군", "옥천군", "영동군", "충주시", "제천시", "단양군",
                          "공주시", "논산시", "계룡시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군", "당진시",
                          "기타지역"]
                지역_기본값 = 지역_옵션.index(기존_정보.get('지역', '')) if 기존_정보.get('지역', '') in 지역_옵션 else 0
                지역 = st.selectbox("📍 지역 (방문 일정용)", 지역_옵션, index=지역_기본값, help="영업 방문 일정표 작성에 사용됩니다")
                
                st.markdown("##### 📋 사업자 정보")
                col1, col2 = st.columns(2)
                with col1:
                    사업자번호 = st.text_input("사업자등록번호", value=기존_정보.get('사업자번호', ''), placeholder="000-00-00000")
                    대표자명 = st.text_input("대표자명", value=기존_정보.get('대표자명', ''))
                with col2:
                    업태 = st.text_input("업태", value=기존_정보.get('업태', ''), placeholder="도소매")
                    종목 = st.text_input("종목", value=기존_정보.get('종목', ''), placeholder="공구, 철물")
                
                주소 = st.text_input("사업장 주소", value=기존_정보.get('주소', ''), placeholder="시/도 구/군 상세주소")
                
                st.markdown("##### 📞 연락처 정보")
                col1, col2, col3 = st.columns(3)
                with col1:
                    전화번호 = st.text_input("전화번호", value=기존_정보.get('전화번호', ''), placeholder="043-000-0000")
                with col2:
                    팩스번호 = st.text_input("팩스번호", value=기존_정보.get('팩스번호', ''), placeholder="043-000-0001")
                with col3:
                    휴대폰 = st.text_input("휴대폰", value=기존_정보.get('휴대폰', ''), placeholder="010-0000-0000")
                
                이메일 = st.text_input("이메일 (홈택스용)", value=기존_정보.get('이메일', ''), placeholder="example@email.com")
                
                st.markdown("##### 🚚 화물/배송 정보")
                col1, col2 = st.columns(2)
                with col1:
                    대신화물_지점 = st.text_input("대신화물 지점", value=기존_정보.get('대신화물_지점', ''), placeholder="청주 지점명")
                with col2:
                    경동화물_지점 = st.text_input("경동화물 지점", value=기존_정보.get('경동화물_지점', ''), placeholder="청주 지점명")
                
                st.markdown("##### 👤 담당자 정보")
                col1, col2 = st.columns(2)
                with col1:
                    담당자명 = st.text_input("담당자명", value=기존_정보.get('담당자명', ''))
                with col2:
                    담당자연락처 = st.text_input("담당자 연락처", value=기존_정보.get('담당자연락처', ''), placeholder="010-0000-0000")
                
                메모 = st.text_area("메모", value=기존_정보.get('메모', ''), placeholder="특이사항, 배송 요청사항 등", height=80)
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 저장", type="primary", use_container_width=True):
                        # 새 데이터 생성
                        new_data = {
                            '거래처명': 선택_거래처,
                            '구분': 구분,
                            '지역': 지역,
                            '사업자번호': 사업자번호,
                            '대표자명': 대표자명,
                            '업태': 업태,
                            '종목': 종목,
                            '주소': 주소,
                            '전화번호': 전화번호,
                            '팩스번호': 팩스번호,
                            '휴대폰': 휴대폰,
                            '이메일': 이메일,
                            '대신화물_지점': 대신화물_지점,
                            '경동화물_지점': 경동화물_지점,
                            '담당자명': 담당자연락처,
                            '담당자연락처': 담당자연락처,
                            '메모': 메모
                        }
                        
                        # 기존 거래처면 업데이트, 신규면 추가
                        if 선택_거래처 in 등록된_거래처_list:
                            customers_df.loc[customers_df['거래처명'] == 선택_거래처] = pd.DataFrame([new_data]).values[0]
                            st.success(f"✅ '{선택_거래처}' 정보가 수정되었습니다!")
                        else:
                            customers_df = pd.concat([customers_df, pd.DataFrame([new_data])], ignore_index=True)
                            st.success(f"✅ '{선택_거래처}' 정보가 등록되었습니다!")
                        
                        # 저장
                        customers_df.to_csv(customers_file, index=False, encoding='utf-8-sig')
                        st.rerun()
                
                with col2:
                    if 선택_거래처 in 등록된_거래처_list:
                        if st.button("🗑️ 삭제", type="secondary", use_container_width=True):
                            customers_df = customers_df[customers_df['거래처명'] != 선택_거래처]
                            customers_df.to_csv(customers_file, index=False, encoding='utf-8-sig')
                            st.success(f"'{선택_거래처}' 정보가 삭제되었습니다.")
                            st.rerun()
        
        # ===== 서브탭2: 거래처 목록 =====
        with sub_tab2:
            st.markdown("#### 등록된 거래처 목록")
            
            if len(customers_df) > 0:
                # 검색
                검색어 = st.text_input("🔍 거래처 검색", placeholder="거래처명, 사업자번호, 담당자명으로 검색")
                
                표시_df = customers_df.copy()
                if 검색어:
                    표시_df = 표시_df[
                        표시_df['거래처명'].str.contains(검색어, na=False) |
                        표시_df['사업자번호'].str.contains(검색어, na=False) |
                        표시_df['담당자명'].str.contains(검색어, na=False)
                    ]
                
                st.markdown(f"**총 {len(표시_df)}개 거래처**")
                
                # 주요 정보만 표시 (지역 추가)
                표시_컬럼 = ['거래처명', '구분', '지역', '사업자번호', '전화번호', '팩스번호', '대신화물_지점', '경동화물_지점', '담당자명']
                # 지역 컬럼이 없는 경우 처리
                표시_컬럼 = [col for col in 표시_컬럼 if col in 표시_df.columns]
                표시_df_short = 표시_df[표시_컬럼].fillna('')
                
                st.dataframe(표시_df_short, use_container_width=True, hide_index=True)
                
                # CSV 다운로드
                csv_data = customers_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 거래처 목록 다운로드 (CSV)",
                    data=csv_data,
                    file_name=f"거래처목록_{get_kst_now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("등록된 거래처가 없습니다. '거래처 등록/수정' 탭에서 거래처를 등록하세요.")
        
        # ===== 서브탭3: 지역 일괄 업로드 =====
        with sub_tab3:
            st.markdown("### 📤 지역 일괄 업로드")
            st.info("""
            **사용 방법:**
            1. 📅 방문 일정 → 🗺️ 지역별 현황에서 **지역 미지정 거래처 엑셀** 다운로드
            2. 엑셀 파일의 **E열(지역)**에 지역명 입력
            3. 아래에 엑셀 파일 업로드
            4. **적용하기** 버튼 클릭
            """)
            
            st.markdown("---")
            
            업로드_파일 = st.file_uploader("📁 지역 정보 엑셀 파일 업로드", type=['xlsx', 'xls'])
            
            if 업로드_파일 is not None:
                try:
                    업로드_df = pd.read_excel(업로드_파일)
                    
                    # 필수 컬럼 확인
                    if '거래처명' in 업로드_df.columns and '지역' in 업로드_df.columns:
                        st.success(f"✅ {len(업로드_df)}개 거래처 데이터 확인!")
                        
                        # 미리보기
                        st.markdown("#### 📋 업로드 데이터 미리보기")
                        st.dataframe(업로드_df[['거래처명', '지역']].head(20), use_container_width=True, hide_index=True)
                        
                        # 지역별 통계
                        지역_통계 = 업로드_df['지역'].value_counts()
                        st.markdown(f"**지역 종류:** {len(지역_통계)}개")
                        
                        if st.button("✅ 지역 정보 적용하기", type="primary", use_container_width=True):
                            # 기존 데이터에 지역 업데이트
                            업데이트_수 = 0
                            추가_수 = 0
                            
                            for _, row in 업로드_df.iterrows():
                                거래처명 = row['거래처명']
                                지역 = row['지역'] if pd.notna(row['지역']) else ''
                                
                                if 거래처명 in customers_df['거래처명'].values:
                                    # 기존 거래처 업데이트
                                    customers_df.loc[customers_df['거래처명'] == 거래처명, '지역'] = 지역
                                    업데이트_수 += 1
                                else:
                                    # 신규 거래처 추가
                                    new_row = pd.DataFrame([{
                                        '거래처명': 거래처명,
                                        '구분': '',
                                        '지역': 지역,
                                        '사업자번호': '',
                                        '대표자명': '',
                                        '업태': '',
                                        '종목': '',
                                        '주소': '',
                                        '전화번호': '',
                                        '팩스번호': '',
                                        '휴대폰': '',
                                        '이메일': '',
                                        '대신화물_지점': '',
                                        '경동화물_지점': '',
                                        '담당자명': '',
                                        '담당자연락처': '',
                                        '메모': ''
                                    }])
                                    customers_df = pd.concat([customers_df, new_row], ignore_index=True)
                                    추가_수 += 1
                            
                            # 저장
                            customers_df.to_csv(customers_file, index=False, encoding='utf-8-sig')
                            
                            st.success(f"""
                            ✅ **적용 완료!**
                            - 업데이트: {업데이트_수}개 거래처
                            - 신규 추가: {추가_수}개 거래처
                            """)
                            st.balloons()
                            st.rerun()
                    else:
                        st.error("❌ '거래처명'과 '지역' 컬럼이 필요합니다. 올바른 형식의 파일을 업로드해주세요.")
                
                except Exception as e:
                    st.error(f"파일 읽기 오류: {str(e)}")
            
            st.markdown("---")
            st.markdown("#### 📝 지역 목록 참고")
            st.markdown("""
            충북: 청주시, 충주시, 제천시, 음성군, 진천군, 증평군, 괴산군, 보은군, 옥천군, 영동군  
            충남: 천안시, 아산시, 논산시, 계룡시, 공주시, 금산군, 부여군, 서천군, 청양군, 홍성군, 예산군, 당진시, 서산시, 태안군, 보령시  
            세종: 세종시  
            대전: 대전시  
            기타: 직원명(담당구역) 또는 기타지역
            """)

# ==================== 방문 일정 ====================
elif menu == "📅 방문 일정":
    st.title("📅 영업 방문 일정표")
    
    try:
        from pathlib import Path
        data_dir = Path("data")
        
        df = st.session_state.ledger_df.copy()
        
        # 거래처 정보 로드
        customers_file = data_dir / "customers.csv"
        if customers_file.exists():
            customers_df = pd.read_csv(customers_file)
            if '지역' not in customers_df.columns:
                customers_df['지역'] = ''
            # 거래처명 공백 제거
            customers_df['거래처명'] = customers_df['거래처명'].astype(str).str.strip()
            st.caption(f"✅ 거래처 정보 로드: {len(customers_df)}건")
        else:
            customers_df = pd.DataFrame(columns=['거래처명', '지역'])
            st.warning("⚠️ 거래처 정보 파일(data/customers.csv)이 없습니다. GitHub에 업로드해주세요.")
        
        if len(df) == 0:
            st.warning("거래 데이터가 없습니다. 먼저 거래를 입력해주세요.")
        else:
            # 날짜 변환
            df['날짜'] = pd.to_datetime(df['날짜'])
            
            # 현재 시간 (timezone-naive)
            현재시간 = get_kst_now().replace(tzinfo=None)
            
            # 최근 1년 데이터만
            기준일_1년 = 현재시간 - timedelta(days=365)
            최근1년_df = df[df['날짜'] >= 기준일_1년]
            
            # 판매 거래만 (외출)
            판매_df = 최근1년_df[최근1년_df['참조'].str.contains('외출', na=False)]
            
            if len(판매_df) == 0:
                st.info("📊 최근 1년간 판매(외출) 거래 데이터가 필요합니다.")
                st.markdown("""
                **방문 일정표 사용 방법:**
                1. **거래 입력**에서 판매 거래(외출)를 입력하세요
                2. **거래처 관리**에서 각 거래처의 **지역**을 설정하세요
                3. 2회 이상 반복 거래가 있으면 자동으로 방문 주기가 계산됩니다
                """)
            else:
                # 탭 구성
                tab1, tab2, tab3 = st.tabs(["📅 월간 방문 일정", "📊 거래처별 방문 주기", "🗺️ 지역별 현황"])
                
                # ===== 탭1: 월간 방문 일정 =====
                with tab1:
                    st.markdown("### 📅 월간 방문 일정표")
                    
                    # 월 선택
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        현재연도 = get_kst_now().year
                        선택_연도 = st.selectbox("연도", [현재연도, 현재연도 + 1], index=0, key="visit_year")
                        선택_월 = st.selectbox("월", list(range(1, 13)), index=get_kst_now().month - 1, key="visit_month")
                    
                    # 거래처별 방문 주기 계산
                    def 방문주기_계산(거래처명):
                        try:
                            거래처_df = 판매_df[판매_df['거래처'] == 거래처명].sort_values('날짜')
                            if len(거래처_df) < 2:
                                return None
                            
                            날짜들 = 거래처_df['날짜'].tolist()
                            간격들 = []
                            for i in range(1, len(날짜들)):
                                간격 = (날짜들[i] - 날짜들[i-1]).days
                                if 간격 > 0:
                                    간격들.append(간격)
                            
                            if not 간격들:
                                return None
                            
                            평균_주기 = sum(간격들) / len(간격들)
                            마지막_거래일 = 날짜들[-1]
                            다음_예상일 = 마지막_거래일 + timedelta(days=평균_주기)
                            
                            return {
                                '거래처': 거래처명,
                                '거래횟수': len(거래처_df),
                                '평균주기': int(평균_주기),
                                '마지막거래': 마지막_거래일,
                                '다음예상': 다음_예상일
                            }
                        except:
                            return None
                    
                    # 2회 이상 반복 거래처만
                    거래처_목록 = 판매_df['거래처'].value_counts()
                    반복_거래처 = 거래처_목록[거래처_목록 >= 2].index.tolist()
                    
                    if len(반복_거래처) == 0:
                        st.info("2회 이상 반복 거래한 거래처가 없습니다. 거래 데이터가 쌓이면 자동으로 표시됩니다.")
                    else:
                        방문_일정 = []
                        for 거래처 in 반복_거래처:
                            결과 = 방문주기_계산(거래처)
                            if 결과:
                                # 지역 정보 추가 (공백 제거 후 매칭)
                                거래처_정리 = str(거래처).strip()
                                지역_info = customers_df[customers_df['거래처명'] == 거래처_정리]
                                
                                # 정확히 일치하지 않으면 부분 매칭 시도
                                if len(지역_info) == 0:
                                    지역_info = customers_df[customers_df['거래처명'].str.contains(거래처_정리, na=False, regex=False)]
                                
                                if len(지역_info) > 0:
                                    지역값 = 지역_info['지역'].values[0]
                                    if pd.notna(지역값) and str(지역값).strip() != '':
                                        결과['지역'] = str(지역값).strip()
                                    else:
                                        결과['지역'] = '미지정'
                                else:
                                    결과['지역'] = '미지정'
                                방문_일정.append(결과)
                        
                        if 방문_일정:
                            일정_df = pd.DataFrame(방문_일정)
                            
                            # 선택한 월에 해당하는 방문 예상 거래처
                            월_시작 = pd.Timestamp(f"{선택_연도}-{선택_월:02d}-01")
                            월_끝 = 월_시작 + pd.offsets.MonthEnd(1)
                            
                            # 해당 월 방문 예상
                            월간_일정 = 일정_df[
                                (일정_df['다음예상'] <= 월_끝) | 
                                (일정_df['다음예상'] < pd.Timestamp(현재시간))
                            ].copy()
                            
                            if len(월간_일정) > 0:
                                월간_일정['주차'] = 월간_일정['다음예상'].apply(
                                    lambda x: min(4, max(1, (x.day - 1) // 7 + 1)) if pd.notna(x) else 1
                                )
                                월간_일정 = 월간_일정.sort_values(['지역', '주차', '다음예상'])
                                
                                st.success(f"📅 {선택_연도}년 {선택_월}월 방문 예정: **{len(월간_일정)}개 거래처**")
                                
                                # 지역별로 그룹화해서 표시
                                지역_목록 = 월간_일정['지역'].unique()
                                
                                for 지역 in sorted(지역_목록):
                                    지역_df = 월간_일정[월간_일정['지역'] == 지역]
                                    
                                    with st.expander(f"📍 {지역} ({len(지역_df)}개 업체)", expanded=True):
                                        for 주차 in sorted(지역_df['주차'].unique()):
                                            주차_df = 지역_df[지역_df['주차'] == 주차]
                                            st.markdown(f"**{주차}주차**")
                                            
                                            for _, row in 주차_df.iterrows():
                                                예상일 = row['다음예상'].strftime('%m/%d')
                                                상태 = "🔴 지남" if row['다음예상'] < pd.Timestamp(현재시간) else "🟢 예정"
                                                st.markdown(f"- {상태} **{row['거래처']}** - {예상일} (주기: {row['평균주기']}일, 거래: {row['거래횟수']}회)")
                                            
                                            st.markdown("")
                            else:
                                st.info(f"{선택_월}월에 방문 예정인 거래처가 없습니다.")
                            
                            # 지역 미지정 거래처 안내
                            미지정_수 = len(일정_df[일정_df['지역'] == '미지정'])
                            if 미지정_수 > 0:
                                st.warning(f"⚠️ 지역 미지정 거래처: {미지정_수}개\n\n👥 거래처 관리에서 지역을 설정해주세요.")
                        else:
                            st.info("방문 주기를 계산할 수 있는 거래처가 없습니다.")
                
                # ===== 탭2: 거래처별 방문 주기 =====
                with tab2:
                    st.markdown("### 📊 거래처별 방문 주기 분석")
                    
                    if len(반복_거래처) > 0 and 방문_일정:
                        일정_df = pd.DataFrame(방문_일정)
                        일정_df = 일정_df.sort_values('다음예상')
                        
                        # 상태 표시
                        일정_df['상태'] = 일정_df['다음예상'].apply(
                            lambda x: '🔴 방문필요' if x < pd.Timestamp(현재시간) else '🟢 예정'
                        )
                        일정_df['다음예상_표시'] = 일정_df['다음예상'].dt.strftime('%Y-%m-%d')
                        일정_df['마지막거래_표시'] = 일정_df['마지막거래'].dt.strftime('%Y-%m-%d')
                        
                        # 필터
                        지역_필터 = st.multiselect(
                            "지역 필터", 
                            ['전체'] + sorted(일정_df['지역'].unique().tolist()),
                            default=['전체']
                        )
                        
                        표시_df = 일정_df.copy()
                        if '전체' not in 지역_필터:
                            표시_df = 표시_df[표시_df['지역'].isin(지역_필터)]
                        
                        st.dataframe(
                            표시_df[['상태', '지역', '거래처', '거래횟수', '평균주기', '마지막거래_표시', '다음예상_표시']].rename(columns={
                                '마지막거래_표시': '마지막거래',
                                '다음예상_표시': '다음예상'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 통계
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("총 반복 거래처", f"{len(일정_df)}개")
                        with col2:
                            방문필요 = len(일정_df[일정_df['다음예상'] < pd.Timestamp(현재시간)])
                            st.metric("방문 필요 (지남)", f"{방문필요}개", delta=f"-{방문필요}" if 방문필요 > 0 else None, delta_color="inverse")
                        with col3:
                            평균주기_전체 = 일정_df['평균주기'].mean()
                            st.metric("평균 방문 주기", f"{평균주기_전체:.0f}일")
                    else:
                        st.info("2회 이상 반복 거래한 거래처 데이터가 필요합니다.")
                
                # ===== 탭3: 지역별 현황 =====
                with tab3:
                    st.markdown("### 🗺️ 지역별 거래처 현황")
                    
                    # ========== 지역 검색 기능 ==========
                    st.markdown("#### 🔍 지역 검색")
                    지역_검색어 = st.text_input("지역명 검색 (예: 청주, 대전, 논산)", placeholder="지역명을 입력하세요", key="region_search")
                    
                    if len(customers_df) > 0:
                        if 지역_검색어:
                            # 지역 또는 주소에서 검색
                            검색_결과 = customers_df[
                                (customers_df['지역'].str.contains(지역_검색어, case=False, na=False)) |
                                (customers_df['주소'].str.contains(지역_검색어, case=False, na=False))
                            ]
                            
                            if len(검색_결과) > 0:
                                st.success(f"🔍 '{지역_검색어}' 검색 결과: **{len(검색_결과)}개** 거래처")
                                
                                # 검색 결과 표시
                                표시_컬럼 = ['거래처명', '지역', '주소', '전화번호', '휴대폰']
                                표시_컬럼 = [c for c in 표시_컬럼 if c in 검색_결과.columns]
                                st.dataframe(검색_결과[표시_컬럼], use_container_width=True, hide_index=True)
                                
                                # 거래처 목록 (클릭 용이하게)
                                st.markdown("##### 📋 거래처 목록")
                                for idx, row in 검색_결과.iterrows():
                                    거래처명 = row['거래처명']
                                    지역 = row.get('지역', '')
                                    전화 = row.get('전화번호', '') or row.get('휴대폰', '')
                                    st.markdown(f"- **{거래처명}** | {지역} | 📞 {전화}")
                            else:
                                st.warning(f"'{지역_검색어}'에 해당하는 거래처가 없습니다.")
                        else:
                            # 지역별 통계 표시
                            지역_통계 = customers_df['지역'].value_counts().reset_index()
                            지역_통계.columns = ['지역', '거래처수']
                            지역_통계 = 지역_통계[지역_통계['지역'] != '']
                            
                            st.markdown("##### 📊 지역별 거래처 수")
                            st.dataframe(지역_통계.head(20), use_container_width=True, hide_index=True)
                    else:
                        st.warning("거래처 정보가 없습니다. customers.csv를 GitHub에 업로드해주세요.")
                    
                    st.markdown("---")
                    
                    # ========== 기존 방문 일정 기반 지역별 현황 ==========
                    st.markdown("### 📊 반복 거래 기준 지역별 현황")
                    
                    if len(반복_거래처) > 0 and 방문_일정:
                        일정_df = pd.DataFrame(방문_일정)
                        
                        지역별_통계 = 일정_df.groupby('지역').agg({
                            '거래처': 'count',
                            '거래횟수': 'sum',
                            '평균주기': 'mean'
                        }).reset_index()
                        지역별_통계.columns = ['지역', '거래처수', '총거래횟수', '평균주기']
                        지역별_통계 = 지역별_통계.sort_values('거래처수', ascending=False)
                        지역별_통계['평균주기'] = 지역별_통계['평균주기'].round(0).astype(int)
                        
                        st.dataframe(지역별_통계, use_container_width=True, hide_index=True)
                        
                        # 차트
                        if len(지역별_통계) > 1:
                            fig = px.bar(
                                지역별_통계, 
                                x='지역', 
                                y='거래처수',
                                title='지역별 반복 거래처 수',
                                color='거래처수',
                                color_continuous_scale='Blues'
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # 지역 미지정 거래처 목록
                        미지정_df = 일정_df[일정_df['지역'] == '미지정']
                        if len(미지정_df) > 0:
                            st.markdown("---")
                            st.markdown("### ⚠️ 지역 미지정 거래처")
                            st.info("아래 거래처들의 지역을 설정해주세요. (👥 거래처 관리)")
                            
                            # 엑셀 다운로드용 데이터 준비
                            다운로드_df = 미지정_df[['거래처', '거래횟수', '평균주기', '마지막거래']].copy()
                            다운로드_df['마지막거래'] = 다운로드_df['마지막거래'].dt.strftime('%Y-%m-%d')
                            다운로드_df.columns = ['거래처명', '거래횟수', '평균방문주기(일)', '마지막거래일']
                            
                            # 엑셀 다운로드 버튼
                            from io import BytesIO
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                다운로드_df.to_excel(writer, index=False, sheet_name='지역미지정거래처')
                            excel_data = output.getvalue()
                            
                            st.download_button(
                                label="📥 지역 미지정 거래처 엑셀 다운로드",
                                data=excel_data,
                                file_name=f"지역미지정거래처_{get_kst_now().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            st.markdown("")
                            for _, row in 미지정_df.iterrows():
                                st.markdown(f"- **{row['거래처']}** (거래 {row['거래횟수']}회)")
                    else:
                        st.info("지역별 통계를 표시하려면 반복 거래 데이터가 필요합니다.")
    
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        st.info("거래 데이터가 충분히 쌓이면 정상적으로 표시됩니다.")

# ==================== 영업 일지 ====================
elif menu == "📝 영업 일지":
    st.title("📝 영업 일지")
    
    from pathlib import Path
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 상담 일지 파일
    journal_file = data_dir / "sales_journal.csv"
    if journal_file.exists():
        try:
            journal_df = pd.read_csv(journal_file)
            if len(journal_df) > 0 and '날짜' in journal_df.columns:
                journal_df['날짜'] = pd.to_datetime(journal_df['날짜'], errors='coerce')
            else:
                journal_df = pd.DataFrame(columns=['날짜', '거래처명', '거래처구분', '상담내용', '다음액션', '영업단계', '작성일시'])
        except Exception as e:
            st.error(f"⚠️ 영업일지 파일 로드 오류: {e}")
            journal_df = pd.DataFrame(columns=['날짜', '거래처명', '거래처구분', '상담내용', '다음액션', '영업단계', '작성일시'])
    else:
        journal_df = pd.DataFrame(columns=['날짜', '거래처명', '거래처구분', '상담내용', '다음액션', '영업단계', '작성일시'])
    
    # 잠재거래처 파일
    prospects_file = data_dir / "prospects.csv"
    if prospects_file.exists():
        try:
            prospects_df = pd.read_csv(prospects_file)
        except Exception as e:
            st.error(f"⚠️ 잠재거래처 파일 로드 오류: {e}")
            prospects_df = pd.DataFrame(columns=['업체명', '지역', '업종', '전화번호', '주소', '담당자', '영업단계', '메모', '등록일'])
    else:
        prospects_df = pd.DataFrame(columns=['업체명', '지역', '업종', '전화번호', '주소', '담당자', '영업단계', '메모', '등록일'])
    
    # 기존 거래처 목록
    try:
        ledger_data = st.session_state.get('ledger_df', None)
        if ledger_data is not None and len(ledger_data) > 0:
            기존_거래처_list = sorted(ledger_data['거래처'].dropna().unique().tolist())
        else:
            기존_거래처_list = []
    except:
        기존_거래처_list = []
    
    # 잠재거래처 목록
    잠재_거래처_list = prospects_df['업체명'].tolist() if len(prospects_df) > 0 else []
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📝 상담 일지", "🎯 잠재거래처 관리", "📤 엑셀 업로드"])
    
    # ===== 탭1: 상담 일지 =====
    with tab1:
        st.markdown("### 📝 영업 상담 일지")
        
        col_input, col_search = st.columns([1, 1])
        
        with col_input:
            st.markdown("#### ✏️ 상담 내용 기록")
            
            # 날짜
            상담_날짜 = st.date_input("📅 상담 날짜", value=get_kst_now(), key="journal_date")
            
            # 거래처 구분
            거래처_구분 = st.radio("거래처 구분", ["기존 거래처", "잠재 거래처", "직접 입력"], horizontal=True, key="customer_type")
            
            if 거래처_구분 == "기존 거래처":
                if 기존_거래처_list:
                    상담_거래처 = st.selectbox("거래처 선택", [""] + 기존_거래처_list, key="journal_existing")
                else:
                    st.warning("기존 거래처가 없습니다.")
                    상담_거래처 = ""
            elif 거래처_구분 == "잠재 거래처":
                if 잠재_거래처_list:
                    상담_거래처 = st.selectbox("잠재거래처 선택", [""] + 잠재_거래처_list, key="journal_prospect")
                else:
                    st.info("잠재거래처를 먼저 등록해주세요.")
                    상담_거래처 = ""
            else:
                상담_거래처 = st.text_input("거래처명 직접 입력", key="journal_new")
            
            # 상담 내용
            상담_내용 = st.text_area("📋 상담 내용", height=100, placeholder="상담한 내용을 기록하세요...", key="journal_content")
            
            # 다음 액션
            다음_액션 = st.text_input("📌 다음 액션", placeholder="예: 견적서 발송, 샘플 전달, 재방문 예정", key="journal_action")
            
            # 영업 단계
            영업단계_옵션 = ["발굴", "접촉", "상담중", "견적", "협상", "계약완료", "보류", "실패"]
            영업_단계 = st.selectbox("📊 영업 단계", 영업단계_옵션, key="journal_stage")
            
            # 저장 버튼
            if st.button("💾 상담 일지 저장", type="primary", use_container_width=True):
                if 상담_거래처 and 상담_내용:
                    new_journal = pd.DataFrame([{
                        '날짜': 상담_날짜,
                        '거래처명': 상담_거래처,
                        '거래처구분': 거래처_구분,
                        '상담내용': 상담_내용,
                        '다음액션': 다음_액션,
                        '영업단계': 영업_단계,
                        '작성일시': get_kst_now().strftime('%Y-%m-%d %H:%M:%S')
                    }])
                    journal_df = pd.concat([journal_df, new_journal], ignore_index=True)
                    journal_df.to_csv(journal_file, index=False, encoding='utf-8-sig')
                    st.success(f"✅ '{상담_거래처}' 상담 일지가 저장되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ 거래처명과 상담 내용을 입력해주세요.")
        
        with col_search:
            st.markdown("#### 🔍 상담 이력 검색")
            
            검색_거래처 = st.text_input("거래처명 검색", placeholder="거래처명을 입력하세요", key="journal_search")
            
            if 검색_거래처 and len(journal_df) > 0:
                검색_결과 = journal_df[journal_df['거래처명'].str.contains(검색_거래처, case=False, na=False)]
                검색_결과 = 검색_결과.sort_values('날짜', ascending=False)
                
                if len(검색_결과) > 0:
                    st.success(f"🔍 '{검색_거래처}' 검색 결과: **{len(검색_결과)}건**")
                    
                    for idx, row in 검색_결과.iterrows():
                        날짜_str = row['날짜'].strftime('%Y-%m-%d') if pd.notna(row['날짜']) else ''
                        with st.expander(f"📅 {날짜_str} - {row['거래처명']} ({row['영업단계']})"):
                            st.markdown(f"**상담 내용:** {row['상담내용']}")
                            if pd.notna(row['다음액션']) and row['다음액션']:
                                st.markdown(f"**다음 액션:** {row['다음액션']}")
                            st.caption(f"구분: {row['거래처구분']} | 작성: {row['작성일시']}")
                else:
                    st.warning(f"'{검색_거래처}'에 대한 상담 이력이 없습니다.")
            elif len(journal_df) > 0:
                st.markdown("##### 📋 최근 상담 일지")
                최근_일지 = journal_df.sort_values('날짜', ascending=False).head(10)
                for idx, row in 최근_일지.iterrows():
                    날짜_str = row['날짜'].strftime('%Y-%m-%d') if pd.notna(row['날짜']) else ''
                    st.markdown(f"- **{날짜_str}** | {row['거래처명']} | {row['영업단계']}")
            else:
                st.info("상담 일지가 없습니다. 첫 상담을 기록해보세요!")
        
        # 전체 상담 일지 표시
        if len(journal_df) > 0:
            st.markdown("---")
            st.markdown("### 📊 전체 상담 일지")
            
            # 필터
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                단계_필터 = st.multiselect("영업 단계 필터", 영업단계_옵션, default=영업단계_옵션, key="journal_filter_stage")
            with col_f2:
                구분_필터 = st.multiselect("거래처 구분", ["기존 거래처", "잠재 거래처", "직접 입력"], default=["기존 거래처", "잠재 거래처", "직접 입력"], key="journal_filter_type")
            
            필터_df = journal_df[
                (journal_df['영업단계'].isin(단계_필터)) &
                (journal_df['거래처구분'].isin(구분_필터))
            ].sort_values('날짜', ascending=False)
            
            st.dataframe(필터_df[['날짜', '거래처명', '상담내용', '다음액션', '영업단계']], use_container_width=True, hide_index=True)
            
            st.caption(f"총 {len(필터_df)}건")
    
    # ===== 탭2: 잠재거래처 관리 =====
    with tab2:
        st.markdown("### 🎯 잠재거래처 관리 (전국)")
        
        # 영업단계 컬럼 없으면 추가
        if '영업단계' not in prospects_df.columns:
            prospects_df['영업단계'] = '미방문'
        if '방문일' not in prospects_df.columns:
            prospects_df['방문일'] = ''
        if '규모' not in prospects_df.columns:
            prospects_df['규모'] = ''
        
        # 상단 통계
        if len(prospects_df) > 0:
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            총_건수 = len(prospects_df)
            미방문 = len(prospects_df[prospects_df['영업단계'] == '미방문'])
            유망 = len(prospects_df[prospects_df['영업단계'] == '유망'])
            상담중 = len(prospects_df[prospects_df['영업단계'].isin(['상담중', '견적', '협상'])])
            탈락 = len(prospects_df[prospects_df['영업단계'] == '탈락'])
            
            col_s1.metric("📊 전체", f"{총_건수:,}개")
            col_s2.metric("🆕 미방문", f"{미방문:,}개")
            col_s3.metric("⭐ 유망", f"{유망:,}개")
            col_s4.metric("💬 상담중", f"{상담중:,}개")
            col_s5.metric("❌ 탈락", f"{탈락:,}개")
        
        st.markdown("---")
        
        # 서브탭
        subtab1, subtab2, subtab3 = st.tabs(["📋 목록 조회", "➕ 개별 등록", "📊 현황 분석"])
        
        # ===== 서브탭1: 목록 조회 (메인) =====
        with subtab1:
            if len(prospects_df) > 0:
                # 지역 계층 검색
                st.markdown("#### 🗺️ 지역 검색")
                
                col_search1, col_search2 = st.columns([1, 2])
                
                with col_search1:
                    지역_검색어 = st.text_input("🔍 지역 검색", placeholder="예: 청주, 대전, 강원", key="region_search")
                
                with col_search2:
                    if 지역_검색어:
                        # 검색어가 포함된 모든 지역 찾기
                        매칭_지역 = prospects_df[prospects_df['지역'].astype(str).str.contains(지역_검색어, case=False, na=False)]['지역'].unique()
                        매칭_지역 = sorted(매칭_지역.tolist())
                        
                        if 매칭_지역:
                            # 지역별 업체 수 표시
                            지역_옵션 = ['전체 선택']
                            for 지역 in 매칭_지역:
                                cnt = len(prospects_df[prospects_df['지역'] == 지역])
                                지역_옵션.append(f"{지역} ({cnt}개)")
                            
                            선택_지역_표시 = st.selectbox(
                                f"📍 '{지역_검색어}' 검색 결과: {len(매칭_지역)}개 지역", 
                                지역_옵션, 
                                key="region_select"
                            )
                            
                            # 선택한 지역 추출 (업체수 제거)
                            if 선택_지역_표시 == '전체 선택':
                                선택_지역 = 지역_검색어  # 검색어로 필터
                            else:
                                선택_지역 = 선택_지역_표시.rsplit(' (', 1)[0]
                        else:
                            st.warning(f"'{지역_검색어}' 검색 결과가 없습니다.")
                            선택_지역 = '전체'
                    else:
                        # 검색어 없으면 전체 지역 목록
                        지역_목록 = ['전체'] + sorted(prospects_df['지역'].dropna().unique().tolist())
                        선택_지역 = st.selectbox("📍 지역 선택", 지역_목록, key="region_select_all")
                
                # 추가 필터
                st.markdown("#### 🔍 추가 필터")
                col_f2, col_f3, col_f4 = st.columns(3)
                
                with col_f2:
                    업종_목록 = ['전체'] + sorted(prospects_df['업종'].dropna().unique().tolist())
                    선택_업종 = st.selectbox("업종", 업종_목록, key="filter_type")
                
                with col_f3:
                    단계_목록 = ['전체', '미방문', '유망', '상담중', '견적', '협상', '보류', '탈락']
                    선택_단계 = st.selectbox("영업단계", 단계_목록, key="filter_stage")
                
                with col_f4:
                    검색어 = st.text_input("업체명 검색", placeholder="검색어", key="filter_search")
                
                # 필터 적용
                필터_df = prospects_df.copy()
                
                # 지역 필터
                if 지역_검색어:
                    if 선택_지역 == 지역_검색어:  # 전체 선택
                        필터_df = 필터_df[필터_df['지역'].astype(str).str.contains(지역_검색어, case=False, na=False)]
                    else:
                        필터_df = 필터_df[필터_df['지역'] == 선택_지역]
                elif 선택_지역 != '전체':
                    필터_df = 필터_df[필터_df['지역'] == 선택_지역]
                
                if 선택_업종 != '전체':
                    필터_df = 필터_df[필터_df['업종'] == 선택_업종]
                if 선택_단계 != '전체':
                    필터_df = 필터_df[필터_df['영업단계'] == 선택_단계]
                if 검색어:
                    필터_df = 필터_df[
                        (필터_df['업체명'].astype(str).str.contains(검색어, case=False, na=False)) |
                        (필터_df['주소'].astype(str).str.contains(검색어, case=False, na=False))
                    ]
                
                # 탈락 제외 옵션
                탈락_제외 = st.checkbox("❌ 탈락 업체 숨기기", value=True, key="hide_failed")
                if 탈락_제외:
                    필터_df = 필터_df[필터_df['영업단계'] != '탈락']
                
                st.success(f"🔍 검색 결과: **{len(필터_df):,}개** 업체")
                
                # 목록 표시 (페이지네이션)
                페이지_크기 = 20
                총_페이지 = max(1, (len(필터_df) - 1) // 페이지_크기 + 1)
                
                col_pg1, col_pg2 = st.columns([1, 3])
                with col_pg1:
                    현재_페이지 = st.number_input("페이지", min_value=1, max_value=총_페이지, value=1, key="page_num")
                with col_pg2:
                    st.caption(f"총 {총_페이지} 페이지")
                
                시작_idx = (현재_페이지 - 1) * 페이지_크기
                끝_idx = min(시작_idx + 페이지_크기, len(필터_df))
                페이지_df = 필터_df.iloc[시작_idx:끝_idx]
                
                # 데이터 테이블 표시
                st.markdown("---")
                
                for idx, row in 페이지_df.iterrows():
                    실제_idx = row.name  # 원본 인덱스
                    단계_색상 = {
                        '미방문': '🔵', '유망': '⭐', '상담중': '💬', 
                        '견적': '📋', '협상': '🤝', '보류': '⏸️', '탈락': '❌'
                    }
                    영업단계 = row.get('영업단계', '미방문')
                    단계_아이콘 = 단계_색상.get(영업단계, '🔵')
                    
                    # 세부 주소 추출 (시군구 이후 부분)
                    주소_전체 = str(row.get('주소', ''))
                    주소_parts = 주소_전체.split()
                    if len(주소_parts) > 3:
                        # 시도, 시군구 제외하고 나머지 (도로명 + 번지)
                        세부주소 = ' '.join(주소_parts[-3:]) if len(주소_parts) > 3 else 주소_전체
                    else:
                        세부주소 = 주소_전체
                    
                    # 표시: 업체명 | 영업단계 | 세부주소
                    with st.expander(f"{단계_아이콘} **{row['업체명']}** | {영업단계} | {세부주소}"):
                        col_info, col_action = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"**📍 전체주소:** {주소_전체}")
                            st.markdown(f"**🏭 업종:** {row.get('업종', '')}")
                            st.markdown(f"**📞 전화:** {row.get('전화번호', '')}")
                            st.markdown(f"**📝 메모:** {row.get('메모', '')}")
                            if pd.notna(row.get('방문일', '')) and row.get('방문일', '') != '':
                                st.markdown(f"**📅 최근방문:** {row['방문일']}")
                            if pd.notna(row.get('규모', '')) and row.get('규모', '') != '':
                                st.markdown(f"**📏 규모:** {row['규모']}")
                        
                        with col_action:
                            st.markdown("**상태 변경:**")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("⭐ 유망", key=f"fav_{실제_idx}", use_container_width=True):
                                    prospects_df.loc[실제_idx, '영업단계'] = '유망'
                                    prospects_df.loc[실제_idx, '방문일'] = get_kst_now().strftime('%Y-%m-%d')
                                    prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                                    st.rerun()
                            
                            with col_btn2:
                                if st.button("💬 상담중", key=f"talk_{실제_idx}", use_container_width=True):
                                    prospects_df.loc[실제_idx, '영업단계'] = '상담중'
                                    prospects_df.loc[실제_idx, '방문일'] = get_kst_now().strftime('%Y-%m-%d')
                                    prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                                    st.rerun()
                            
                            col_btn3, col_btn4 = st.columns(2)
                            with col_btn3:
                                if st.button("⏸️ 보류", key=f"hold_{실제_idx}", use_container_width=True):
                                    prospects_df.loc[실제_idx, '영업단계'] = '보류'
                                    prospects_df.loc[실제_idx, '방문일'] = get_kst_now().strftime('%Y-%m-%d')
                                    prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                                    st.rerun()
                            
                            with col_btn4:
                                if st.button("❌ 탈락", key=f"fail_{실제_idx}", use_container_width=True):
                                    prospects_df.loc[실제_idx, '영업단계'] = '탈락'
                                    prospects_df.loc[실제_idx, '방문일'] = get_kst_now().strftime('%Y-%m-%d')
                                    prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                                    st.rerun()
                            
                            # 규모 입력
                            규모_옵션 = ['', '대형', '중형', '소형']
                            현재_규모 = row.get('규모', '') if pd.notna(row.get('규모', '')) else ''
                            규모_idx = 규모_옵션.index(현재_규모) if 현재_규모 in 규모_옵션 else 0
                            새_규모 = st.selectbox("규모", 규모_옵션, index=규모_idx, key=f"size_{실제_idx}")
                            if 새_규모 != 현재_규모:
                                prospects_df.loc[실제_idx, '규모'] = 새_규모
                                prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                            
                            st.markdown("---")
                            
                            # 완전 삭제
                            if st.button("🗑️ 완전삭제", key=f"del_{실제_idx}", type="secondary"):
                                prospects_df = prospects_df.drop(실제_idx).reset_index(drop=True)
                                prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                                st.success(f"'{row['업체명']}' 삭제됨")
                                st.rerun()
                
                # 일괄 처리
                st.markdown("---")
                st.markdown("#### 🔄 일괄 처리")
                col_bulk1, col_bulk2 = st.columns(2)
                
                with col_bulk1:
                    if st.button("🗑️ 탈락 업체 전체 삭제", type="secondary"):
                        탈락_수 = len(prospects_df[prospects_df['영업단계'] == '탈락'])
                        if 탈락_수 > 0:
                            prospects_df = prospects_df[prospects_df['영업단계'] != '탈락'].reset_index(drop=True)
                            prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                            st.success(f"✅ 탈락 업체 {탈락_수}개 삭제됨")
                            st.rerun()
                        else:
                            st.info("탈락 업체가 없습니다.")
                
            else:
                st.info("등록된 잠재거래처가 없습니다. '📤 엑셀 업로드' 탭에서 데이터를 업로드하세요.")
        
        # ===== 서브탭2: 개별 등록 =====
        with subtab2:
            st.markdown("#### ➕ 잠재거래처 개별 등록")
            
            col_reg1, col_reg2 = st.columns(2)
            
            with col_reg1:
                신규_업체명 = st.text_input("🏢 업체명", placeholder="예: 대전종합철물", key="prospect_name")
                신규_지역 = st.text_input("📍 지역", placeholder="예: 대전광역시", key="prospect_region")
                업종_옵션 = ["철물점", "건자재점", "농자재점"]
                신규_업종 = st.selectbox("🏭 업종", 업종_옵션, key="prospect_type")
            
            with col_reg2:
                신규_전화 = st.text_input("📞 전화번호", placeholder="000-000-0000", key="prospect_phone")
                신규_주소 = st.text_input("🏠 주소", placeholder="상세 주소", key="prospect_address")
                신규_메모 = st.text_input("📝 메모", placeholder="특이사항", key="prospect_memo")
            
            if st.button("💾 잠재거래처 등록", type="primary"):
                if 신규_업체명:
                    # 기존 거래처 중복 체크
                    if 신규_업체명 in 기존_거래처_list:
                        st.warning(f"⚠️ '{신규_업체명}'은(는) 이미 기존 거래처에 있습니다!")
                    elif 신규_업체명 in 잠재_거래처_list:
                        st.warning(f"⚠️ '{신규_업체명}'은(는) 이미 잠재거래처에 있습니다!")
                    else:
                        new_prospect = pd.DataFrame([{
                            '업체명': 신규_업체명,
                            '지역': 신규_지역,
                            '업종': 신규_업종,
                            '전화번호': 신규_전화,
                            '주소': 신규_주소,
                            '담당자': '',
                            '영업단계': '미방문',
                            '메모': 신규_메모,
                            '등록일': get_kst_now().strftime('%Y-%m-%d'),
                            '방문일': '',
                            '규모': ''
                        }])
                        prospects_df = pd.concat([prospects_df, new_prospect], ignore_index=True)
                        prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                        st.success(f"✅ '{신규_업체명}' 등록 완료!")
                        st.rerun()
                else:
                    st.error("❌ 업체명을 입력해주세요.")
        
        # ===== 서브탭3: 현황 분석 =====
        with subtab3:
            if len(prospects_df) > 0:
                st.markdown("#### 📊 잠재거래처 현황 분석")
                
                col_a1, col_a2 = st.columns(2)
                
                with col_a1:
                    st.markdown("##### 🗺️ 지역별 현황")
                    지역_통계 = prospects_df.groupby('지역').agg({
                        '업체명': 'count'
                    }).reset_index()
                    지역_통계.columns = ['지역', '업체수']
                    지역_통계 = 지역_통계.sort_values('업체수', ascending=False).head(15)
                    st.dataframe(지역_통계, use_container_width=True, hide_index=True)
                
                with col_a2:
                    st.markdown("##### 📈 영업단계별 현황")
                    단계_통계 = prospects_df['영업단계'].value_counts().reset_index()
                    단계_통계.columns = ['영업단계', '업체수']
                    st.dataframe(단계_통계, use_container_width=True, hide_index=True)
                
                # 업종별 현황
                st.markdown("##### 🏭 업종별 현황")
                업종_통계 = prospects_df['업종'].value_counts().reset_index()
                업종_통계.columns = ['업종', '업체수']
                
                import plotly.express as px
                fig = px.bar(업종_통계, x='업종', y='업체수', title='업종별 잠재거래처 수')
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # 규모별 현황 (데이터 있으면)
                if '규모' in prospects_df.columns:
                    규모_df = prospects_df[prospects_df['규모'].notna() & (prospects_df['규모'] != '')]
                    if len(규모_df) > 0:
                        st.markdown("##### 📏 규모별 현황")
                        규모_통계 = 규모_df['규모'].value_counts().reset_index()
                        규모_통계.columns = ['규모', '업체수']
                        st.dataframe(규모_통계, use_container_width=True, hide_index=True)
            else:
                st.info("데이터가 없습니다.")
    
    # ===== 탭3: 엑셀 업로드 =====
    with tab3:
        st.markdown("### 📤 전국 잠재거래처 일괄 업로드")
        st.info("""
        **전국 6,618개 잠재거래처 업로드 가능!**
        
        소상공인시장진흥공단 데이터 또는 직접 정리한 엑셀을 업로드하세요.
        
        **필수 컬럼:** 업체명, 지역, 업종
        **선택 컬럼:** 전화번호, 주소, 담당자, 메모
        """)
        
        # 양식 다운로드
        st.markdown("#### 📥 양식 다운로드")
        양식_df = pd.DataFrame(columns=['업체명', '지역', '업종', '전화번호', '주소', '담당자', '메모'])
        양식_df.loc[0] = ['예시철물', '대전광역시', '철물점', '042-000-0000', '대전시 서구 예시로 123', '홍길동', '대형 매장']
        
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            양식_df.to_excel(writer, index=False, sheet_name='잠재거래처')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 엑셀 양식 다운로드",
            data=excel_data,
            file_name="잠재거래처_양식.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        
        # 파일 업로드
        st.markdown("#### 📤 파일 업로드")
        uploaded_file = st.file_uploader("엑셀 파일 선택 (.xlsx, .xls, .csv)", type=['xlsx', 'xls', 'csv'], key="prospect_upload")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    upload_df = pd.read_csv(uploaded_file)
                else:
                    upload_df = pd.read_excel(uploaded_file)
                
                st.success(f"📊 **{len(upload_df):,}개** 업체 데이터 확인")
                
                # 미리보기
                st.markdown("##### 미리보기 (처음 10개)")
                st.dataframe(upload_df.head(10), use_container_width=True, hide_index=True)
                
                # 업종 분포
                if '업종' in upload_df.columns:
                    st.markdown("##### 업종별 분포")
                    업종_분포 = upload_df['업종'].value_counts()
                    st.write(업종_분포.to_string())
                
                # 기존 거래처와 중복 체크 옵션
                기존_거래처_제외 = st.checkbox("✅ 기존 거래처와 중복된 업체 제외", value=True)
                잠재_중복_제외 = st.checkbox("✅ 이미 등록된 잠재거래처 제외", value=True)
                
                if st.button("💾 일괄 등록", type="primary", use_container_width=True):
                    # 필수 컬럼 확인
                    if '업체명' not in upload_df.columns:
                        st.error("'업체명' 컬럼이 필요합니다.")
                    else:
                        # 필요한 컬럼 추가
                        for col in ['지역', '업종', '전화번호', '주소', '담당자', '메모']:
                            if col not in upload_df.columns:
                                upload_df[col] = ''
                        
                        upload_df['영업단계'] = '미방문'
                        upload_df['등록일'] = get_kst_now().strftime('%Y-%m-%d')
                        upload_df['방문일'] = ''
                        upload_df['규모'] = ''
                        
                        원본_수 = len(upload_df)
                        제외_기존 = 0
                        제외_잠재 = 0
                        
                        # 기존 거래처 중복 제외
                        if 기존_거래처_제외 and 기존_거래처_list:
                            before = len(upload_df)
                            upload_df = upload_df[~upload_df['업체명'].isin(기존_거래처_list)]
                            제외_기존 = before - len(upload_df)
                        
                        # 잠재거래처 중복 제외
                        if 잠재_중복_제외 and len(prospects_df) > 0:
                            기존_잠재 = set(prospects_df['업체명'].tolist())
                            before = len(upload_df)
                            upload_df = upload_df[~upload_df['업체명'].isin(기존_잠재)]
                            제외_잠재 = before - len(upload_df)
                        
                        if len(upload_df) > 0:
                            # 필요한 컬럼만 선택
                            필요_컬럼 = ['업체명', '지역', '업종', '전화번호', '주소', '담당자', '영업단계', '메모', '등록일', '방문일', '규모']
                            upload_df = upload_df[[col for col in 필요_컬럼 if col in upload_df.columns]]
                            
                            prospects_df = pd.concat([prospects_df, upload_df], ignore_index=True)
                            prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                            
                            st.success(f"""
                            ✅ **{len(upload_df):,}개** 업체 등록 완료!
                            
                            - 원본: {원본_수:,}개
                            - 기존 거래처 중복 제외: {제외_기존:,}개
                            - 잠재거래처 중복 제외: {제외_잠재:,}개
                            - **최종 등록: {len(upload_df):,}개**
                            """)
                            st.rerun()
                        else:
                            st.warning("모든 업체가 이미 등록되어 있거나 기존 거래처와 중복됩니다.")
            except Exception as e:
                st.error(f"파일 처리 오류: {str(e)}")
        
        # 전체 데이터 관리
        if len(prospects_df) > 0:
            st.markdown("---")
            st.markdown("#### 🗄️ 데이터 관리")
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # 전체 다운로드
                output2 = BytesIO()
                with pd.ExcelWriter(output2, engine='openpyxl') as writer:
                    prospects_df.to_excel(writer, index=False, sheet_name='잠재거래처')
                excel_data2 = output2.getvalue()
                
                st.download_button(
                    label=f"📥 전체 다운로드 ({len(prospects_df):,}개)",
                    data=excel_data2,
                    file_name=f"잠재거래처_전체_{get_kst_now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col_dl2:
                # 전체 삭제 (위험)
                삭제_확인 = st.checkbox("⚠️ 전체 삭제 확인 (체크 후 삭제 버튼 클릭)", key="delete_confirm_check")
                
                if 삭제_확인:
                    if st.button("🗑️ 전체 데이터 삭제", type="secondary", key="delete_all_btn"):
                        prospects_df = pd.DataFrame(columns=['업체명', '지역', '업종', '전화번호', '주소', '담당자', '영업단계', '메모', '등록일', '방문일', '규모'])
                        prospects_df.to_csv(prospects_file, index=False, encoding='utf-8-sig')
                        st.success("✅ 전체 삭제 완료")
                        st.rerun()

# ==================== 협약서 관리 ====================
elif menu == "📜 협약서 관리":
    st.title("📜 협약서 관리")
    st.info("거래처와 판매협약을 체결하고 전자서명으로 협약서를 생성합니다.")
    
    # 데이터 디렉토리
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 협약 데이터 파일
    agreement_file = os.path.join(data_dir, "agreements.csv")
    if os.path.exists(agreement_file):
        agreements_df = pd.read_csv(agreement_file, encoding='utf-8-sig')
    else:
        agreements_df = pd.DataFrame(columns=['협약번호', '구매자_상호', '구매자_대표', '구매자_사업자번호', '결제방식', '외상한도', '협약시작일', '협약종료일', '체결일', '상태'])
    
    # 탭
    tab1, tab2 = st.tabs(["📝 협약서 작성", "📋 협약 이력"])
    
    # ===== 탭1: 협약서 작성 =====
    with tab1:
        st.markdown("### 📝 신규 협약서 작성")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏭 공급자 (갑)")
            st.text("상호: 누리엠알오")
            st.text("대표: 박수영")
            st.text("사업자번호: 320-14-00707")
        
        with col2:
            st.markdown("#### 🏢 구매자 (을)")
            구매자_상호 = st.text_input("상호", key="buyer_company")
            구매자_대표 = st.text_input("대표자", key="buyer_ceo")
            구매자_사업자번호 = st.text_input("사업자번호", placeholder="000-00-00000", key="buyer_bizno")
        
        st.markdown("---")
        st.markdown("#### 📋 협약 조건")
        
        col3, col4 = st.columns(2)
        with col3:
            결제방식 = st.selectbox("결제방식", ["현금", "월말결제", "익월결제", "기타"], key="payment_method")
            외상한도 = st.number_input("외상한도 (원)", min_value=0, step=100000, value=1000000, key="credit_limit")
        
        with col4:
            협약시작일 = st.date_input("협약 시작일", value=get_kst_today(), key="start_date")
            협약종료일 = st.date_input("협약 종료일", value=get_kst_today().replace(year=get_kst_today().year + 1), key="end_date")
        
        st.markdown("---")
        st.markdown("#### ✍️ 전자서명")
        st.info("✍️ 아래 서명 확인란에 체크해주세요.")
        
        # 서명 확인 (체크박스 방식)
        col_sign1, col_sign2 = st.columns(2)
        with col_sign1:
            st.markdown("**공급자 (갑)**")
            공급자_서명확인 = st.checkbox("✅ 박수영 서명 확인", key="supplier_sign_check")
        with col_sign2:
            st.markdown(f"**구매자 (을)**")
            구매자_서명확인 = st.checkbox(f"✅ {구매자_대표 if 구매자_대표 else '구매자'} 서명 확인", key="buyer_sign_check")
        
        st.markdown("---")
        
        # 협약서 생성 버튼
        if st.button("📄 협약서 생성 및 저장", type="primary", use_container_width=True):
            if not 구매자_상호:
                st.error("❌ 구매자 상호를 입력해주세요.")
            elif not 구매자_대표:
                st.error("❌ 구매자 대표자를 입력해주세요.")
            else:
                # 협약번호 생성
                협약번호 = f"AGR-{get_kst_now().strftime('%Y%m%d%H%M%S')}"
                
                # 데이터 저장
                new_agreement = {
                    '협약번호': 협약번호,
                    '구매자_상호': 구매자_상호,
                    '구매자_대표': 구매자_대표,
                    '구매자_사업자번호': 구매자_사업자번호,
                    '결제방식': 결제방식,
                    '외상한도': 외상한도,
                    '협약시작일': str(협약시작일),
                    '협약종료일': str(협약종료일),
                    '체결일': get_kst_now().strftime('%Y-%m-%d %H:%M'),
                    '상태': '유효'
                }
                
                agreements_df = pd.concat([agreements_df, pd.DataFrame([new_agreement])], ignore_index=True)
                agreements_df.to_csv(agreement_file, index=False, encoding='utf-8-sig')
                
                # 협약서 HTML 생성
                협약서_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }}
                        h1 {{ text-align: center; font-size: 28px; margin-bottom: 30px; }}
                        .section {{ margin-bottom: 15px; }}
                        .section-title {{ font-weight: bold; font-size: 14px; margin-bottom: 5px; }}
                        .section-content {{ font-size: 13px; line-height: 1.6; }}
                        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                        th, td {{ border: 1px solid #000; padding: 8px; text-align: left; font-size: 12px; }}
                        th {{ background-color: #f0f0f0; text-align: center; }}
                        .signature-area {{ display: flex; justify-content: space-around; margin-top: 40px; }}
                        .signature-box {{ text-align: center; width: 45%; }}
                        .signature-line {{ border-bottom: 1px solid #000; height: 60px; margin-bottom: 10px; }}
                        .center {{ text-align: center; }}
                        .small {{ font-size: 11px; color: #666; }}
                    </style>
                </head>
                <body>
                    <h1>판 매 협 약 서</h1>
                    
                    <div class="section">
                        <div class="section-title">제1조 (목적)</div>
                        <div class="section-content">본 협약은 공급자와 구매자 간의 상호 신뢰를 바탕으로 장기적이고 안정적인 거래관계를 구축하며, 특별 할인가격으로 물품을 공급함에 있어 필요한 사항을 정함을 목적으로 한다.</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제2조 (당사자)</div>
                        <table>
                            <tr><th>구분</th><th>공급자 (갑)</th><th>구매자 (을)</th></tr>
                            <tr><td>상호</td><td>누리엠알오</td><td>{구매자_상호}</td></tr>
                            <tr><td>대표</td><td>박수영</td><td>{구매자_대표}</td></tr>
                            <tr><td>사업자번호</td><td>320-14-00707</td><td>{구매자_사업자번호}</td></tr>
                        </table>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제3조 (공급품목)</div>
                        <div class="section-content">"갑"은 "을"에게 누리엠알오 절단석 제품 등을 공급한다.</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제4조 (가격 및 결제조건)</div>
                        <div class="section-content">
                            1. "갑"은 "을"에게 특별 할인된 협약가격으로 공급한다.<br>
                            2. 결제방식: {결제방식} / 외상한도: {외상한도:,}원
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제5조 (납품조건)</div>
                        <div class="section-content">1. 납품장소: "을"이 지정하는 장소 / 배송비: 무료(100,000원 이상), 유료(100,000원 이하)</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제6조 (협약기간)</div>
                        <div class="section-content">1. 협약기간: {협약시작일} ~ {협약종료일} / 만료 30일 전 이의 없으면 자동 연장</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">제7조 (기타)</div>
                        <div class="section-content">1. 품질 불량 시 무상 교환 또는 환불 2. 협약 내용은 영업비밀로 제3자 누설 금지 3. 분쟁 시 "갑" 소재지 관할법원</div>
                    </div>
                    
                    <p class="center" style="margin-top: 30px;">위 협약 내용을 확인하고 신의성실의 원칙에 따라 이행할 것을 확약하며,<br>협약서 2부를 작성하여 서명 날인 후 각 1부씩 보관한다.</p>
                    
                    <p class="center" style="font-weight: bold; margin-top: 20px;">협약 체결일: {get_kst_now().strftime('%Y년 %m월 %d일')}</p>
                    
                    <div class="signature-area">
                        <div class="signature-box">
                            <div style="font-weight: bold;">공급자 (갑)</div>
                            <div>누리엠알오</div>
                            <div>대표: 박수영</div>
                            <div class="signature-line"></div>
                            <div>(서명날인)</div>
                        </div>
                        <div class="signature-box">
                            <div style="font-weight: bold;">구매자 (을)</div>
                            <div>{구매자_상호}</div>
                            <div>대표: {구매자_대표}</div>
                            <div class="signature-line"></div>
                            <div>(서명날인)</div>
                        </div>
                    </div>
                    
                    <p class="small center" style="margin-top: 30px;">협약번호: {협약번호}</p>
                </body>
                </html>
                """
                
                st.success(f"✅ 협약서가 생성되었습니다! (협약번호: {협약번호})")
                
                # HTML 다운로드 (UTF-8 인코딩)
                st.download_button(
                    label="📥 협약서 다운로드 (HTML)",
                    data=협약서_html.encode('utf-8'),
                    file_name=f"판매협약서_{구매자_상호}_{get_kst_now().strftime('%Y%m%d')}.html",
                    mime="text/html; charset=utf-8"
                )
                
                # 미리보기
                with st.expander("📄 협약서 미리보기", expanded=True):
                    st.components.v1.html(협약서_html, height=800, scrolling=True)
    
    # ===== 탭2: 협약 이력 =====
    with tab2:
        st.markdown("### 📋 협약 이력")
        
        if len(agreements_df) > 0:
            # 상태별 필터
            상태_필터 = st.selectbox("상태 필터", ["전체", "유효", "만료", "해지"], key="agreement_status_filter")
            
            if 상태_필터 != "전체":
                표시_df = agreements_df[agreements_df['상태'] == 상태_필터]
            else:
                표시_df = agreements_df
            
            st.info(f"📊 총 {len(표시_df)}건의 협약")
            
            for idx, row in 표시_df.iterrows():
                with st.expander(f"📜 {row['구매자_상호']} ({row['협약번호']}) - {row['상태']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**구매자:** {row['구매자_상호']}")
                        st.markdown(f"**대표:** {row['구매자_대표']}")
                        st.markdown(f"**사업자번호:** {row['구매자_사업자번호']}")
                    with col2:
                        st.markdown(f"**결제방식:** {row['결제방식']}")
                        st.markdown(f"**외상한도:** {row['외상한도']:,}원")
                        st.markdown(f"**기간:** {row['협약시작일']} ~ {row['협약종료일']}")
                    
                    st.markdown(f"**체결일:** {row['체결일']}")
                    
                    # 상태 변경
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if row['상태'] == '유효':
                            if st.button("🚫 해지", key=f"terminate_{idx}"):
                                agreements_df.loc[idx, '상태'] = '해지'
                                agreements_df.to_csv(agreement_file, index=False, encoding='utf-8-sig')
                                st.rerun()
                    with col_btn2:
                        if st.button("🗑️ 삭제", key=f"delete_{idx}"):
                            agreements_df = agreements_df.drop(idx)
                            agreements_df.to_csv(agreement_file, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("📭 등록된 협약이 없습니다.")

# ==================== 설정 ====================
elif menu == "🔧 설정":
    st.title("🔧 설정")
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 사업자 정보", "🗄️ 데이터 관리", "💰 외상 현황", "📊 통계"])
    
    # ===== 탭1: 사업자 정보 =====
    with tab1:
        st.markdown("### 🏢 사업자 정보 설정")
        st.info("거래명세서 출력 시 사용되는 정보입니다.")
        
        company = st.session_state.company_info
        
        col1, col2 = st.columns(2)
        
        with col1:
            상호 = st.text_input("상호 (업체명)", value=company.get('상호', ''), key="company_name")
            대표자 = st.text_input("대표자명", value=company.get('대표자', ''), key="company_ceo")
            사업자번호 = st.text_input("사업자번호", value=company.get('사업자번호', ''), key="company_bizno")
        
        with col2:
            전화번호 = st.text_input("전화번호", value=company.get('전화번호', ''), key="company_tel")
            팩스번호 = st.text_input("팩스번호", value=company.get('팩스번호', ''), key="company_fax")
        
        주소 = st.text_input("주소", value=company.get('주소', ''), key="company_addr")
        
        if st.button("💾 사업자 정보 저장", type="primary"):
            st.session_state.company_info = {
                '상호': 상호,
                '대표자': 대표자,
                '사업자번호': 사업자번호,
                '주소': 주소,
                '전화번호': 전화번호,
                '팩스번호': 팩스번호
            }
            save_company_info()
            st.success("✅ 사업자 정보가 저장되었습니다!")
        
        st.markdown("---")
        st.markdown("#### 📄 현재 저장된 정보")
        st.markdown(f"""
        | 항목 | 내용 |
        |------|------|
        | 상호 | {company.get('상호', '-')} |
        | 대표자 | {company.get('대표자', '-')} |
        | 사업자번호 | {company.get('사업자번호', '-')} |
        | 주소 | {company.get('주소', '-')} |
        | 전화번호 | {company.get('전화번호', '-')} |
        | 팩스번호 | {company.get('팩스번호', '-')} |
        """)
    
    # ===== 탭2: 데이터 관리 =====
    with tab2:
        st.markdown("### 🗄️ 데이터 관리")
        
        # Google Sheets 동기화 섹션
        st.markdown("#### ☁️ Google Sheets 동기화")
        if GSPREAD_AVAILABLE and "gcp_service_account" in st.secrets:
            st.success("✅ Google Sheets 연결됨")
            
            col_gs1, col_gs2 = st.columns(2)
            
            with col_gs1:
                if st.button("📤 Google Sheets에 백업", type="primary", use_container_width=True):
                    with st.spinner("동기화 중..."):
                        success_count = 0
                        
                        # 거래 데이터 동기화
                        if sync_to_google_sheets(st.session_state.ledger_df, "거래내역"):
                            success_count += 1
                        
                        # 품목 데이터 동기화
                        if sync_to_google_sheets(st.session_state.products_df, "품목목록"):
                            success_count += 1
                        
                        # 거래처 데이터 동기화
                        try:
                            from pathlib import Path
                            customers_file = Path("data") / "customers.csv"
                            if customers_file.exists():
                                customers_df = pd.read_csv(customers_file)
                                if sync_to_google_sheets(customers_df, "거래처목록"):
                                    success_count += 1
                        except:
                            pass
                        
                        if success_count > 0:
                            st.success(f"✅ {success_count}개 시트 동기화 완료!")
                            st.balloons()
                        else:
                            st.error("동기화 실패. 설정을 확인해주세요.")
            
            with col_gs2:
                if st.button("📥 Google Sheets에서 복원", use_container_width=True):
                    with st.spinner("데이터 불러오는 중..."):
                        # 거래 데이터 복원
                        loaded_df = load_from_google_sheets("거래내역")
                        if loaded_df is not None and len(loaded_df) > 0:
                            # 날짜 컬럼 변환
                            if '날짜' in loaded_df.columns:
                                loaded_df['날짜'] = pd.to_datetime(loaded_df['날짜'])
                            # 숫자 컬럼 변환
                            for col in ['수량', '단가', '공급가액', '부가세']:
                                if col in loaded_df.columns:
                                    loaded_df[col] = pd.to_numeric(loaded_df[col], errors='coerce').fillna(0)
                            
                            # ✅ 2019-08-01 이전 불필요한 데이터 필터링
                            loaded_df = loaded_df[loaded_df['날짜'] >= '2019-08-01'].reset_index(drop=True)
                            
                            st.session_state.ledger_df = loaded_df
                            save_data()
                            st.success(f"✅ {len(loaded_df)}건 거래 데이터 복원 완료!")
                            st.rerun()
                        else:
                            st.warning("Google Sheets에 복원할 데이터가 없습니다.")
            
            st.caption("💡 데이터가 영구 보존됩니다. 정기적으로 '백업' 버튼을 눌러주세요!")
        else:
            st.warning("⚠️ Google Sheets 연결이 설정되지 않았습니다.")
            st.caption("Streamlit Cloud → Settings → Secrets에서 설정해주세요.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💾 로컬 백업")
            if st.button("📥 백업 파일 다운로드"):
                df = st.session_state.ledger_df
                excel_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=excel_data,
                    file_name=f"장부백업_{get_kst_now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            st.markdown("#### 🗑️ 데이터 초기화")
            if st.button("🗑️ 모든 데이터 삭제", type="secondary"):
                if st.checkbox("정말 삭제하시겠습니까?"):
                    st.session_state.ledger_df = pd.DataFrame(columns=['날짜', '거래처', '품목', '수량', '단가', '공급가액', '부가세', '참조', '비고'])
                    save_data()
                    st.success("데이터가 초기화되었습니다.")
                    st.rerun()
    
    # ===== 탭3: 외상 현황 (자동 계산) =====
    with tab3:
        st.markdown("### 💰 외상 현황 (실시간 자동 계산)")
        
        st.success("""
        **✅ 자동 계산 방식:**
        - **미수금** = 판매(양수) + 부가세 - 입금 → 판매처에서 받을 돈
        - **미지급금** = |매입(음수)| + |부가세| - |출금| → 매입처에 줄 돈
        - 컴장부 전체 데이터 기반으로 자동 계산됩니다.
        """)
        
        st.markdown("---")
        
        df = st.session_state.ledger_df
        
        if len(df) > 0:
            # 미수금/미지급금 계산
            미수금_결과 = calculate_all_receivables(df)
            미지급금_결과 = calculate_all_payables(df)
            
            # 요약 통계
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                미수금_df = 미수금_결과[미수금_결과['미수금'] > 0] if len(미수금_결과) > 0 else pd.DataFrame()
                총_미수금 = 미수금_df['미수금'].sum() if len(미수금_df) > 0 else 0
                st.metric("총 미수금", f"{총_미수금:,.0f}원", help="판매처에서 받을 돈")
            
            with col2:
                st.metric("미수 거래처", f"{len(미수금_df)}개")
            
            with col3:
                미지급금_df = 미지급금_결과[미지급금_결과['미지급금'] > 0] if len(미지급금_결과) > 0 else pd.DataFrame()
                총_미지급금 = 미지급금_df['미지급금'].sum() if len(미지급금_df) > 0 else 0
                st.metric("총 미지급금", f"{총_미지급금:,.0f}원", help="매입처에 줄 돈")
            
            with col4:
                st.metric("미지급 거래처", f"{len(미지급금_df)}개")
            
            st.markdown("---")
            
            # 거래처별 조회
            st.markdown("#### 🔍 거래처별 외상 조회")
            거래처_list = sorted(df['거래처'].dropna().unique().tolist())
            선택_거래처 = st.selectbox("거래처 선택", [""] + 거래처_list, key="settings_recv_search")
            
            if 선택_거래처:
                거래처_미수금 = calculate_receivable(선택_거래처)
                거래처_미지급금 = calculate_payable(선택_거래처)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 거래처_미수금 > 0:
                        st.warning(f"⚠️ **미수금**: {거래처_미수금:,.0f}원")
                    elif 거래처_미수금 < 0:
                        st.info(f"💰 **선수금**: {abs(거래처_미수금):,.0f}원")
                    else:
                        st.success("✅ 미수금 없음")
                
                with col2:
                    if 거래처_미지급금 > 0:
                        st.error(f"💸 **미지급금**: {거래처_미지급금:,.0f}원")
                    elif 거래처_미지급금 < 0:
                        st.info(f"💵 **선급금**: {abs(거래처_미지급금):,.0f}원")
                    else:
                        st.success("✅ 미지급금 없음")
                
                # 최근 거래 내역
                거래처_df = df[df['거래처'] == 선택_거래처].sort_values('날짜', ascending=False)
                if len(거래처_df) > 0:
                    st.markdown(f"#### 📋 {선택_거래처} 최근 거래 내역")
                    
                    display_거래 = 거래처_df.head(20).copy()
                    display_거래['날짜'] = pd.to_datetime(display_거래['날짜']).dt.strftime('%Y-%m-%d')
                    display_거래 = display_거래[['날짜', '품목', '공급가액', '부가세']]
                    
                    for col in ['공급가액', '부가세']:
                        display_거래[col] = display_거래[col].apply(lambda x: f"{x:,.0f}")
                    
                    st.dataframe(display_거래, use_container_width=True, hide_index=True)
        else:
            st.info("아직 거래 데이터가 없습니다.")
    
    # ===== 탭4: 통계 =====
    with tab4:
        st.markdown("### 📊 통계")
        
        df = st.session_state.ledger_df
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 거래 건수", f"{len(df)}건")
        with col2:
            st.metric("거래처 수", f"{df['거래처'].nunique()}개")
        with col3:
            st.metric("데이터 기간", f"{(df['날짜'].max() - df['날짜'].min()).days}일" if len(df) > 0 else "0일")
        
        st.markdown("---")
        
        # 실시간 외상 통계
        미수금_결과 = calculate_all_receivables(df)
        미지급금_결과 = calculate_all_payables(df)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📤 미수금 (받을 돈)")
            미수금_df = 미수금_결과[미수금_결과['미수금'] > 0] if len(미수금_결과) > 0 else pd.DataFrame()
            총_미수금 = 미수금_df['미수금'].sum() if len(미수금_df) > 0 else 0
            st.metric("총 미수금", f"{총_미수금:,.0f}원")
        
        with col2:
            st.markdown("##### 📥 미지급금 (줄 돈)")
            미지급금_df = 미지급금_결과[미지급금_결과['미지급금'] > 0] if len(미지급금_결과) > 0 else pd.DataFrame()
            총_미지급금 = 미지급금_df['미지급금'].sum() if len(미지급금_df) > 0 else 0
            st.metric("총 미지급금", f"{총_미지급금:,.0f}원")

# 푸터
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 정보")
st.sidebar.info(f"""
**프로그램:** 누리엠알오 장부관리  
**버전:** 1.2.0  
**데이터:** {len(st.session_state.ledger_df)}건  
**최종 수정:** {get_kst_now().strftime('%Y-%m-%d %H:%M')}
""")

st.sidebar.markdown("---")
if st.sidebar.button("🔒 로그아웃", use_container_width=True):
    logout()