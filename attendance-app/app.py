import streamlit as st
import pandas as pd
import datetime
import requests
import json
import os

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="🎻 오케스트라 통합 관리 시스템",
    page_icon="🎻",
    layout="wide"
)

# --- 커스텀 CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.hero-header { text-align: center; padding: 1.5rem 0; }
.hero-title {
    font-size: 2.5rem; font-weight: 700;
    background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.kiosk-container {
    background: #ffffff; border-radius: 20px; padding: 2.5rem;
    text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin: 1rem auto;
    max-width: 800px; border: 1px solid #eee;
}
.kiosk-input input {
    font-size: 2.5rem !important; height: 4rem !important;
    text-align: center !important; border-radius: 15px !important;
    border: 2px solid #FF8E53 !important;
}
</style>
""", unsafe_allow_html=True)

# --- 데이터 연동 함수 (GAS API) ---
def call_gas_api(url, action, payload=None):
    if not url: return None
    try:
        params = {"action": action}
        if payload:
            response = requests.post(url, params=params, data=json.dumps(payload), timeout=10)
        else:
            response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"데이터 연동 오류: {e}")
        return None

# --- 사이드바 내비게이션 및 설정 ---
with st.sidebar:
    st.markdown("## 🎼 메뉴")
    app_mode = st.radio("기능 선택", ["✅ 출결 체크 (키오스크)", "🎵 AI 연습 피드백"], index=0)
    
    st.markdown("---")
    st.markdown("## ⚙️ 시스템 설정")
    
    if "gas_url" not in st.session_state:
        st.session_state.gas_url = ""
        
    gas_url_input = st.text_input("구글 시트 웹 앱 URL", value=st.session_state.gas_url, placeholder="https://script.google.com/macros/s/...")
    if gas_url_input != st.session_state.gas_url:
        st.session_state.gas_url = gas_url_input
        st.rerun()

    if app_mode == "✅ 출결 체크 (키오스크)":
        admin_mode = st.toggle("관리자 모드 (명단/통계)", value=False)
    else:
        st.markdown("### 🤖 AI 피드백")
        use_ai = st.toggle("Gemini AI 피드백 사용", value=False)
        api_key = st.text_input("Gemini API 키", type="password") if use_ai else ""

# --- [1] 출결 체크 모드 ---
if app_mode == "✅ 출결 체크 (키오스크)":
    if not st.session_state.gas_url:
        st.markdown('<div class="hero-header"><div class="hero-title">🎻 오케스트라 출결 시스템</div><p>시작하려면 사이드바에 구글 시트 웹 앱 URL을 입력해 주세요.</p></div>', unsafe_allow_html=True)
    else:
        with st.spinner("데이터 동기화 중..."):
            all_data = call_gas_api(st.session_state.gas_url, "getAllData")
        
        if all_data:
            df_students = pd.DataFrame(all_data.get("students", [])).astype(str)
            df_logs = pd.DataFrame(all_data.get("logs", [])).astype(str)
            
            if not admin_mode:
                # 키오스크 UI
                st.markdown('<div class="hero-header"><div class="hero-title">🎼 입·퇴실 확인</div></div>', unsafe_allow_html=True)
                st.markdown('<div class="kiosk-container">', unsafe_allow_html=True)
                with st.form("kiosk_form", clear_on_submit=True):
                    scanned_code = st.text_input("학번을 입력하거나 QR을 스캔하세요", key="kiosk_input")
                    submitted = st.form_submit_button("확인", use_container_width=True)
                
                if submitted and scanned_code:
                    student_match = df_students[(df_students['학번'] == scanned_code) | (df_students['QR코드ID'] == scanned_code)]
                    if student_match.empty:
                        st.error(f"❌ 등록되지 않은 학번입니다: {scanned_code}")
                    else:
                        student_info = student_match.iloc[0]
                        res = call_gas_api(st.session_state.gas_url, "recordAttendance", {"id": student_info['학번'], "name": student_info['이름']})
                        if res and res.get("success"):
                            st.balloons()
                            st.success(f"✅ {res.get('message')}")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # 관리자 모드
                st.markdown("### 🛠️ 관리자 대시보드")
                t1, t2 = st.tabs(["👥 명단 관리", "📊 연습 기록"])
                with t1: st.dataframe(df_students, use_container_width=True, hide_index=True)
                with t2: st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.error("연동 실패: URL을 확인하세요.")

# --- [2] AI 연습 피드백 모드 ---
else:
    st.markdown('<div class="hero-header"><div class="hero-title">🎵 AI 연습 피드백</div><p>모범 연주와 학생 연주를 비교 분석합니다.</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎼 모범 연주")
        ref_file = st.file_uploader("모범 파일 업로드", type=["mp3", "wav", "m4a"], key="ref")
    with col2:
        st.subheader("🎵 학생 연주")
        stu_file = st.file_uploader("학생 파일 업로드", type=["mp3", "wav", "m4a"], key="stu")
        
    if st.button("🔍 분석 시작", use_container_width=True):
        if ref_file and stu_file:
            with st.spinner("AI 분석 엔진 가동 중..."):
                try:
                    import analyzer
                    import visualizer
                    import feedback as fb
                    
                    # 오디오 로드 및 분석
                    result = analyzer.analyze(ref_file.read(), ref_file.name, stu_file.read(), stu_file.name)
                    
                    st.success("✅ 분석 완료!")
                    
                    # 결과 요약
                    sc_col1, sc_col2, sc_col3 = st.columns(3)
                    sc_col1.metric("종합 점수", f"{result.total_score}점", f"등급: {result.grade}")
                    sc_col2.metric("피치 점수", f"{result.pitch_score}점")
                    sc_col3.metric("템포 점수", f"{result.tempo_score}점")
                    
                    # 그래프
                    st.plotly_chart(visualizer.pitch_comparison_chart(result), use_container_width=True)
                    
                    # 피드백
                    st.markdown("### 💬 AI 피드백")
                    if use_ai and api_key:
                        feedback_text = fb.generate_ai_feedback(result, api_key)
                    else:
                        feedback_text = fb.generate_rule_based_feedback(result)
                    st.info(feedback_text)
                    
                    # 다운로드 버튼
                    st.download_button("📥 결과 보고서 다운로드", feedback_text, file_name="feedback_report.txt")
                    
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")
        else:
            st.warning("두 파일을 모두 업로드해 주세요.")
