"""
analyzer.py — 음원 분석 핵심 로직 (librosa 기반)
모범 연주와 학생 연주를 비교 분석합니다.
"""

import numpy as np
import librosa
import soundfile as sf
import io
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnalysisResult:
    """분석 결과를 담는 데이터 클래스"""
    # 피치 데이터
    ref_pitches: np.ndarray
    ref_pitch_times: np.ndarray
    stu_pitches: np.ndarray
    stu_pitch_times: np.ndarray

    # 템포 데이터
    ref_tempo: float
    stu_tempo: float
    ref_beat_times: np.ndarray
    stu_beat_times: np.ndarray

    # 음량(RMS) 데이터
    ref_rms: np.ndarray
    ref_rms_times: np.ndarray
    stu_rms: np.ndarray
    stu_rms_times: np.ndarray

    # 점수
    pitch_score: float    # 0~100
    tempo_score: float    # 0~100
    dynamic_score: float  # 0~100
    total_score: float    # 0~100
    grade: str            # A ~ D

    # 구간별 이탈 목록
    problem_segments: list

    # 오디오 길이
    ref_duration: float
    stu_duration: float


def load_audio(file_bytes: bytes, filename: str) -> tuple[np.ndarray, int]:
    """바이트 데이터에서 오디오 로드"""
    buf = io.BytesIO(file_bytes)
    try:
        y, sr = librosa.load(buf, sr=None, mono=True)
    except Exception:
        buf.seek(0)
        data, sr = sf.read(buf)
        if data.ndim > 1:
            data = data.mean(axis=1)
        y = data.astype(np.float32)
    return y, sr


def extract_pitch(y: np.ndarray, sr: int, frame_length=2048, hop_length=512):
    """피치(기본 주파수) 추출 — librosa.yin 사용"""
    f0 = librosa.yin(
        y,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7'),
        frame_length=frame_length,
        hop_length=hop_length,
    )
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)
    # 0Hz(무음) 구간은 NaN 처리
    f0 = np.where(f0 < 50, np.nan, f0)
    return f0, times


def extract_tempo_and_beats(y: np.ndarray, sr: int):
    """템포 및 비트 추출"""
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return float(tempo), beat_times


def extract_rms(y: np.ndarray, sr: int, frame_length=2048, hop_length=512):
    """음량(RMS) 추출"""
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    # dB 변환
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    return rms_db, times


def _align_arrays(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """두 배열을 같은 길이로 맞춤 (짧은 쪽 기준)"""
    min_len = min(len(a), len(b))
    return a[:min_len], b[:min_len]


def compute_pitch_score(ref_f0: np.ndarray, stu_f0: np.ndarray) -> float:
    """피치 일치율 점수 (0~100)"""
    r, s = _align_arrays(ref_f0, stu_f0)
    valid = ~np.isnan(r) & ~np.isnan(s)
    if valid.sum() == 0:
        return 0.0
    # 반음 단위로 비교
    r_cents = 1200 * np.log2(np.clip(r[valid], 1e-6, None))
    s_cents = 1200 * np.log2(np.clip(s[valid], 1e-6, None))
    diff = np.abs(r_cents - s_cents)
    # 50센트(반음의 절반) 이내면 정확
    accuracy = np.mean(diff < 50)
    return round(float(accuracy) * 100, 1)


def compute_tempo_score(ref_tempo: float, stu_tempo: float) -> float:
    """템포 일치율 점수 (0~100)"""
    diff_ratio = abs(ref_tempo - stu_tempo) / max(ref_tempo, 1)
    score = max(0, 100 - diff_ratio * 200)
    return round(score, 1)


def compute_dynamic_score(ref_rms: np.ndarray, stu_rms: np.ndarray) -> float:
    """음량 곡선 유사도 점수 — 피어슨 상관계수 기반 (0~100)"""
    r, s = _align_arrays(ref_rms, stu_rms)
    if len(r) < 2:
        return 0.0
    corr = np.corrcoef(r, s)[0, 1]
    corr = np.nan_to_num(corr, nan=0.0)
    score = (corr + 1) / 2 * 100  # -1~1 → 0~100
    return round(float(score), 1)


def detect_problem_segments(
    ref_f0: np.ndarray,
    stu_f0: np.ndarray,
    ref_times: np.ndarray,
    sr: int,
    threshold_cents: float = 100.0,
    min_duration: float = 0.5,
):
    """피치 이탈 구간 감지"""
    r, s = _align_arrays(ref_f0, stu_f0)
    t, _ = _align_arrays(ref_times, np.zeros(len(s)))

    valid = ~np.isnan(r) & ~np.isnan(s)
    r_cents = np.where(valid, 1200 * np.log2(np.clip(r, 1e-6, None)), np.nan)
    s_cents = np.where(valid, 1200 * np.log2(np.clip(s, 1e-6, None)), np.nan)
    diff = np.abs(r_cents - s_cents)

    problem_mask = diff > threshold_cents
    segments = []
    in_seg = False
    seg_start = 0.0

    for i, is_prob in enumerate(problem_mask):
        if is_prob and not in_seg:
            in_seg = True
            seg_start = t[i]
        elif not is_prob and in_seg:
            in_seg = False
            duration = t[i] - seg_start
            if duration >= min_duration:
                segments.append({
                    "start": round(seg_start, 2),
                    "end": round(t[i], 2),
                    "duration": round(duration, 2),
                    "avg_diff_cents": round(float(np.nanmean(diff[max(0,i-10):i])), 1),
                })

    if in_seg:
        duration = t[-1] - seg_start
        if duration >= min_duration:
            segments.append({
                "start": round(seg_start, 2),
                "end": round(t[-1], 2),
                "duration": round(duration, 2),
                "avg_diff_cents": round(float(np.nanmean(diff[-10:])), 1),
            })

    return segments


def grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


def analyze(ref_bytes: bytes, ref_name: str, stu_bytes: bytes, stu_name: str) -> AnalysisResult:
    """전체 분석 파이프라인 실행"""
    ref_y, ref_sr = load_audio(ref_bytes, ref_name)
    stu_y, stu_sr = load_audio(stu_bytes, stu_name)

    # 피치 추출
    ref_f0, ref_pt = extract_pitch(ref_y, ref_sr)
    stu_f0, stu_pt = extract_pitch(stu_y, stu_sr)

    # 템포 추출
    ref_tempo, ref_beats = extract_tempo_and_beats(ref_y, ref_sr)
    stu_tempo, stu_beats = extract_tempo_and_beats(stu_y, stu_sr)

    # 음량 추출
    ref_rms, ref_rt = extract_rms(ref_y, ref_sr)
    stu_rms, stu_rt = extract_rms(stu_y, stu_sr)

    # 점수 계산
    pitch_score = compute_pitch_score(ref_f0, stu_f0)
    tempo_score = compute_tempo_score(ref_tempo, stu_tempo)
    dynamic_score = compute_dynamic_score(ref_rms, stu_rms)
    total = round(pitch_score * 0.5 + tempo_score * 0.3 + dynamic_score * 0.2, 1)

    # 문제 구간 감지
    problems = detect_problem_segments(ref_f0, stu_f0, ref_pt, ref_sr)

    return AnalysisResult(
        ref_pitches=ref_f0,
        ref_pitch_times=ref_pt,
        stu_pitches=stu_f0,
        stu_pitch_times=stu_pt,
        ref_tempo=ref_tempo,
        stu_tempo=stu_tempo,
        ref_beat_times=ref_beats,
        stu_beat_times=stu_beats,
        ref_rms=ref_rms,
        ref_rms_times=ref_rt,
        stu_rms=stu_rms,
        stu_rms_times=stu_rt,
        pitch_score=pitch_score,
        tempo_score=tempo_score,
        dynamic_score=dynamic_score,
        total_score=total,
        grade=grade_from_score(total),
        problem_segments=problems,
        ref_duration=librosa.get_duration(y=ref_y, sr=ref_sr),
        stu_duration=librosa.get_duration(y=stu_y, sr=stu_sr),
    )
