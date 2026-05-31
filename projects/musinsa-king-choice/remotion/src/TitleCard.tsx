import React from "react";
import {
  useCurrentFrame,
  interpolate,
  Easing,
  Audio,
  Img,
  staticFile,
} from "remotion";
import { FPS, TITLE_IMPACT, AUDIO_MIX } from "./generated/manifest";

/**
 * TitleCard — 28~30초 (2초)
 *
 * 구조: KV 로고 히어로(대형) → "왕의 선택" 서브타이틀
 * 타이밍:
 *   0.00s: 검은 화면
 *   0.05s ~ 0.40s: KV 로고 임팩트 등장 (scale 1.12 → 1.0 + 페이드인)
 *   0.35s ~ 0.65s: "왕의 선택" 텍스트 페이드인
 *   0.65s ~ 1.70s: 풀 디스플레이
 *   1.70s ~ 2.00s: 전체 페이드아웃
 */
export const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const sec = frame / FPS;

  // KV 로고: 첫 번째 등장 — 임팩트 스케일 + 페이드인
  const logoOpacity = interpolate(
    sec,
    [0.05, 0.4, 1.7, 2.0],
    [0, 1, 1, 0],
    { easing: Easing.ease, extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const logoScale = interpolate(
    sec,
    [0.05, 0.25, 0.45],
    [1.12, 1.03, 1.0],
    { easing: Easing.out(Easing.cubic), extrapolateRight: "clamp" }
  );

  // "왕의 선택" 타이틀: 로고 이후 서브타이틀로 등장
  const titleOpacity = interpolate(
    sec,
    [0.35, 0.65, 1.7, 2.0],
    [0, 1, 1, 0],
    { easing: Easing.ease, extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#000000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        gap: 40,
      }}
    >
      {/* 쿵 임팩트 SFX — 번들 에셋(public/sfx-bundled/impact.mp3). 파일 추가 전엔 TITLE_IMPACT="" 라 렌더 안 됨. */}
      {TITLE_IMPACT ? (
        <Audio src={staticFile(TITLE_IMPACT)} volume={AUDIO_MIX.impactVolume} />
      ) : null}

      {/* 무신사 무진장 공식 키비주얼 — 히어로 사이즈 */}
      <Img
        src={staticFile("musinsa-logo.png")}
        style={{
          width: "72%",
          maxWidth: 780,
          maxHeight: 860,
          height: "auto",
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
          objectFit: "contain",
          filter: "drop-shadow(0 12px 36px rgba(255, 60, 30, 0.45))",
        }}
      />

      {/* 서브타이틀: 왕의 선택 */}
      <div
        style={{
          fontSize: 88,
          fontWeight: 900,
          color: "#f5e6c8",
          letterSpacing: "10px",
          opacity: titleOpacity,
          fontFamily: "'Noto Serif KR', 'Nanum Myeongjo', serif",
          textAlign: "center",
          lineHeight: 1.2,
          textShadow:
            "0 0 24px rgba(245, 230, 200, 0.2), 0 4px 12px rgba(0,0,0,0.9)",
        }}
      >
        왕의 선택
      </div>

      {/* 가로 라인 장식 */}
      <div
        style={{
          width: 200,
          height: 1,
          background:
            "linear-gradient(90deg, transparent, #f5e6c8, transparent)",
          opacity: titleOpacity * 0.7,
          marginTop: -24,
        }}
      />
    </div>
  );
};
