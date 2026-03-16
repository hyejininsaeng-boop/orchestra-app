"""
feedback.py — Gemini AI 피드백 텍스트 생성 (선택 기능)
API 키가 없어도 앱이 작동합니다.
"""

import os
from analyzer import AnalysisResult

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


def _format_problem_segments(segments: list) -> str:
    if not segments:
        return "피치 이탈 구간이 감지되지 않았습니다."
    lines = []
    for seg in segments:
        m_start, s_start = divmod(seg["start"], 60)
        m_end, s_end = divmod(seg["end"], 60)
        lines.append(
            f"  - {int(m_start)}:{s_start:04.1f} ~ {int(m_end)}:{s_end:04.1f} "
            f"(지속: {seg['duration']:.1f}초, 평균 이탈: {seg['avg_diff_cents']} cents)"
        )
    return "\n".join(lines)


def generate_ai_feedback(result: AnalysisResult, api_key: str) -> str:
    """Gemini API를 사용한 AI 피드백 생성"""
    if not _GENAI_AVAILABLE:
        return "google-generativeai 패키지가 설치되지 않았습니다. `pip install google-generativeai`를 실행해 주세요."

    if not api_key or not api_key.strip():
        return "Gemini API 키가 입력되지 않았습니다."

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-1.5-flash")

        problem_text = _format_problem_segments(result.problem_segments)

        prompt = f"""당신은 오케스트라 지도 선생님을 돕는 전문 음악 AI 코치입니다.
학생의 연주를 분석한 데이터를 바탕으로 친절하고 구체적인 피드백을 작성해 주세요.

## 분석 데이터
- **모범 연주 템포**: {result.ref_tempo:.1f} BPM
- **학생 연주 템포**: {result.stu_tempo:.1f} BPM
- **템포 차이**: {abs(result.ref_tempo - result.stu_tempo):.1f} BPM ({'+' if result.stu_tempo > result.ref_tempo else '-'})
- **피치 일치율**: {result.pitch_score:.1f}%
- **템포 일치율**: {result.tempo_score:.1f}%
- **다이나믹 유사도**: {result.dynamic_score:.1f}%
- **종합 점수**: {result.total_score:.1f}% (등급: {result.grade})

## 피치 이탈 구간
{problem_text}

## 피드백 작성 요청
위 데이터를 바탕으로 아래 형식으로 피드백을 작성해 주세요:
1. **전반적인 평가** (2~3문장, 긍정적 시작)
2. **개선이 필요한 부분** (구체적 구간과 이유 포함, 2~3항목)
3. **연습 방법 제안** (실용적인 조언 2~3가지)

말투는 학생을 격려하면서도 정확한 교사의 어투로 작성해 주세요.
"""
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"AI 피드백 생성 중 오류가 발생했습니다: {str(e)}"


def generate_rule_based_feedback(result: AnalysisResult) -> str:
    """API 키 없이 사용하는 규칙 기반 피드백 (항상 사용 가능)"""
    lines = []

    # 종합 평가
    if result.grade == "A":
        lines.append("✅ **전반적으로 매우 훌륭한 연주입니다!** 모범 연주와 높은 일치도를 보였습니다.")
    elif result.grade == "B":
        lines.append("👍 **전반적으로 잘 연주했습니다.** 몇 가지 부분을 다듬으면 더욱 완성도가 높아질 것입니다.")
    elif result.grade == "C":
        lines.append("📌 **기본기는 잘 갖춰져 있으나**, 집중적인 연습이 필요한 구간이 있습니다.")
    else:
        lines.append("💪 **더 많은 연습이 필요합니다.** 아래 항목을 중점적으로 연습해 보세요.")

    lines.append("")

    # 템포 피드백
    tempo_diff = result.stu_tempo - result.ref_tempo
    if abs(tempo_diff) < 3:
        lines.append(f"🥁 **템포**: 매우 안정적입니다. (모범: {result.ref_tempo:.1f} BPM ↔ 학생: {result.stu_tempo:.1f} BPM)")
    elif tempo_diff > 0:
        lines.append(f"🥁 **템포**: 모범 연주보다 {tempo_diff:.1f} BPM 빠릅니다. 메트로놈을 활용한 느린 연습을 권장합니다.")
    else:
        lines.append(f"🥁 **템포**: 모범 연주보다 {abs(tempo_diff):.1f} BPM 느립니다. 박자감 유지에 집중하세요.")

    # 피치 피드백
    if result.pitch_score >= 85:
        lines.append(f"🎵 **음정**: 매우 정확합니다. (일치율 {result.pitch_score:.1f}%)")
    elif result.pitch_score >= 65:
        lines.append(f"🎵 **음정**: 대체로 정확하나 일부 구간에서 이탈이 감지됩니다. (일치율 {result.pitch_score:.1f}%)")
    else:
        lines.append(f"🎵 **음정**: 여러 구간에서 음정 이탈이 확인됩니다. (일치율 {result.pitch_score:.1f}%) 개별 음정 연습을 권장합니다.")

    # 다이나믹 피드백
    if result.dynamic_score >= 80:
        lines.append(f"🔊 **다이나믹**: 강약 표현이 모범 연주와 잘 어울립니다. (유사도 {result.dynamic_score:.1f}%)")
    else:
        lines.append(f"🔊 **다이나믹**: 강약 표현을 더 다양하게 살려보세요. (유사도 {result.dynamic_score:.1f}%)")

    # 문제 구간 목록
    if result.problem_segments:
        lines.append("")
        lines.append("### ⚠️ 집중 연습 구간")
        for seg in result.problem_segments[:5]:  # 최대 5개
            m1, s1 = divmod(seg["start"], 60)
            m2, s2 = divmod(seg["end"], 60)
            lines.append(
                f"- `{int(m1)}:{s1:04.1f}` ~ `{int(m2)}:{s2:04.1f}` "
                f"(음정 이탈 약 {seg['avg_diff_cents']} cents, {seg['duration']:.1f}초간 지속)"
            )

    return "\n".join(lines)
