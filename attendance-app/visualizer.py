"""
visualizer.py — Plotly 기반 시각화 컴포넌트
분석 결과를 인터랙티브 그래프로 렌더링합니다.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analyzer import AnalysisResult


# === 색상 팔레트 ===
COLOR_REF = "#00C9A7"   # 모범 연주 — 에메랄드 그린
COLOR_STU = "#FF6B6B"   # 학생 연주 — 코랄 레드
COLOR_BG  = "#0E1117"   # 배경
COLOR_GRID = "#2A2D3E"  # 그리드
FONT_COLOR = "#E8E8E8"

PLOT_LAYOUT = dict(
    paper_bgcolor=COLOR_BG,
    plot_bgcolor=COLOR_BG,
    font=dict(color=FONT_COLOR, family="Noto Sans KR, Arial"),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(
        bgcolor="rgba(255,255,255,0.05)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
    xaxis=dict(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID),
    yaxis=dict(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID),
)


def pitch_comparison_chart(result: AnalysisResult) -> go.Figure:
    """피치 비교 꺾은선 그래프"""
    fig = go.Figure()

    # 모범 연주
    fig.add_trace(go.Scatter(
        x=result.ref_pitch_times,
        y=result.ref_pitches,
        mode="lines",
        name="모범 연주",
        line=dict(color=COLOR_REF, width=1.5),
        connectgaps=False,
    ))

    # 학생 연주
    fig.add_trace(go.Scatter(
        x=result.stu_pitch_times,
        y=result.stu_pitches,
        mode="lines",
        name="학생 연주",
        line=dict(color=COLOR_STU, width=1.5, dash="dot"),
        connectgaps=False,
    ))

    # 문제 구간 음영
    for seg in result.problem_segments:
        fig.add_vrect(
            x0=seg["start"], x1=seg["end"],
            fillcolor="rgba(255, 100, 100, 0.12)",
            line_width=0,
            annotation_text="⚠",
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color="#FF6B6B",
        )

    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="🎵 피치(Pitch) 비교", font=dict(size=15)),
        xaxis_title="시간 (초)",
        yaxis_title="주파수 (Hz)",
        yaxis_type="log",
        height=300,
    )
    return fig


def tempo_comparison_chart(result: AnalysisResult) -> go.Figure:
    """템포 비트 비교 차트"""
    fig = go.Figure()

    ref_bpm = result.ref_tempo
    stu_bpm = result.stu_tempo

    categories = ["모범 연주", "학생 연주"]
    values = [ref_bpm, stu_bpm]
    colors = [COLOR_REF, COLOR_STU]

    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f} BPM" for v in values],
        textposition="outside",
        width=0.4,
    ))

    # 차이 표시
    diff = abs(ref_bpm - stu_bpm)
    fig.add_annotation(
        x=0.5, y=max(values) * 1.15,
        xref="paper",
        text=f"차이: {diff:.1f} BPM",
        showarrow=False,
        font=dict(size=13, color="#FFD93D"),
    )

    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="🥁 템포(Tempo) 비교", font=dict(size=15)),
        yaxis_title="BPM",
        height=300,
        showlegend=False,
    )
    return fig


def dynamic_comparison_chart(result: AnalysisResult) -> go.Figure:
    """음량(다이나믹) 비교 그래프"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=result.ref_rms_times,
        y=result.ref_rms,
        mode="lines",
        name="모범 연주",
        line=dict(color=COLOR_REF, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba(0, 201, 167, 0.08)",
    ))

    fig.add_trace(go.Scatter(
        x=result.stu_rms_times,
        y=result.stu_rms,
        mode="lines",
        name="학생 연주",
        line=dict(color=COLOR_STU, width=1.5, dash="dot"),
        fill="tozeroy",
        fillcolor=f"rgba(255, 107, 107, 0.08)",
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="🔊 음량(Dynamic) 비교", font=dict(size=15)),
        xaxis_title="시간 (초)",
        yaxis_title="음량 (dB)",
        height=300,
    )
    return fig


def score_gauge(score: float, label: str, color: str) -> go.Figure:
    """점수 게이지 차트"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="%", font=dict(size=28, color=FONT_COLOR)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=FONT_COLOR, tickfont=dict(color=FONT_COLOR)),
            bar=dict(color=color),
            bgcolor=COLOR_GRID,
            steps=[
                dict(range=[0, 60], color="rgba(255,100,100,0.1)"),
                dict(range=[60, 75], color="rgba(255,211,61,0.1)"),
                dict(range=[75, 100], color="rgba(0,201,167,0.1)"),
            ],
            threshold=dict(
                line=dict(color="white", width=2),
                thickness=0.75,
                value=score,
            ),
        ),
        title=dict(text=label, font=dict(size=12, color="#AAAAAA")),
    ))
    fig.update_layout(
        paper_bgcolor=COLOR_BG,
        font=dict(color=FONT_COLOR),
        height=200,
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


def total_score_ring(score: float, grade: str) -> go.Figure:
    """총점 도넛 차트"""
    grade_colors = {"A": "#00C9A7", "B": "#4FC3F7", "C": "#FFD93D", "D": "#FF6B6B"}
    color = grade_colors.get(grade, "#AAAAAA")

    fig = go.Figure(go.Pie(
        values=[score, 100 - score],
        hole=0.72,
        marker_colors=[color, COLOR_GRID],
        textinfo="none",
        hoverinfo="skip",
        sort=False,
    ))
    fig.add_annotation(
        text=f"<b>{grade}</b><br>{score}%",
        x=0.5, y=0.5,
        font=dict(size=28, color=color),
        showarrow=False,
    )
    fig.update_layout(
        paper_bgcolor=COLOR_BG,
        showlegend=False,
        height=220,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig
