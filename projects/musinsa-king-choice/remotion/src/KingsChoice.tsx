import React from "react";
import {
  Composition,
  Series,
  Video,
  Audio,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { FPS, WIDTH, HEIGHT, TOTAL_FRAMES, TITLE_CARD_FRAMES, CUTS, AVAILABLE_CLIPS } from "./generated/manifest";
import { Subtitle } from "./Subtitle";
import { TitleCard } from "./TitleCard";

// 클립 파일이 아직 없을 때 표시할 자리표시자 — 컷 라벨을 보여줌
const ClipPlaceholder: React.FC<{ label: string; clipId: string }> = ({ label, clipId }) => (
  <div
    style={{
      width: "100%",
      height: "100%",
      background: "linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      color: "#888",
      fontFamily: "sans-serif",
      gap: 24,
      padding: 60,
      textAlign: "center",
    }}
  >
    <div style={{ fontSize: 36, opacity: 0.5 }}>[ 클립 미생성 ]</div>
    <div style={{ fontSize: 72, fontWeight: 700, color: "#ddd" }}>{label}</div>
    <div style={{ fontSize: 28, opacity: 0.4, fontFamily: "monospace" }}>public/clips/{clipId}.mp4</div>
  </div>
);

// 개별 컷: 영상 클립(있으면) + 자막 오버레이
const ClipScene: React.FC<{ clipId: string; label: string }> = ({ clipId, label }) => {
  const hasClip = AVAILABLE_CLIPS.has(clipId);
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {hasClip ? (
        <Video
          src={staticFile(`clips/${clipId}.mp4`)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <ClipPlaceholder label={label} clipId={clipId} />
      )}
      <Subtitle />
    </div>
  );
};

// 전환 효과 래퍼 (크로스페이드용 — Series와 함께 사용 시 각 씬에 적용)
const FadeScene: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
  fadeDuration?: number;
}> = ({ children, durationInFrames, fadeDuration = 8 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, fadeDuration, durationInFrames - fadeDuration, durationInFrames],
    [0, 1, 1, 0],
    { easing: Easing.ease, extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return <div style={{ opacity, width: "100%", height: "100%" }}>{children}</div>;
};

// 메인 시퀀스
const MainSequence: React.FC = () => {
  return (
    <div style={{ width: WIDTH, height: HEIGHT, background: "#000", overflow: "hidden" }}>
      <Series>
        {CUTS.filter((c) => c.duration > 0).map((cut) => (
          <Series.Sequence
            key={cut.id}
            durationInFrames={cut.duration * FPS}
            name={cut.label}
          >
            <FadeScene durationInFrames={cut.duration * FPS}>
              <ClipScene clipId={cut.id} label={cut.label} />
            </FadeScene>
          </Series.Sequence>
        ))}
        {/* 마지막: 타이틀 카드 2초 (28~30s) — 검은 화면 + "왕의 선택" + "무진장 무신사" + 쿵 임팩트 */}
        <Series.Sequence durationInFrames={TITLE_CARD_FRAMES} name="타이틀 카드">
          <TitleCard />
        </Series.Sequence>
      </Series>

      {/* BGM — public/music/bgm.mp3 배치 후 활성화 */}
      {/* <Audio src={staticFile("music/bgm.mp3")} volume={0.7} /> */}
    </div>
  );
};

// Composition 등록 (renderMedia 시 id="KingsChoice" 지정)
export const KingsChoiceComposition: React.FC = () => {
  return (
    <Composition
      id="KingsChoice"
      component={MainSequence}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
