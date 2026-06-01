import React from "react";
import {
  Composition,
  Series,
  Sequence,
  OffthreadVideo,
  Audio,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import {
  FPS,
  WIDTH,
  HEIGHT,
  TOTAL_FRAMES,
  TITLE_CARD_FRAMES,
  CUTS,
  CLIP_SRCS,
  VOICES,
  MUSIC,
  AUDIO_MIX,
} from "./generated/manifest";
import { Subtitle } from "./Subtitle";
import { TitleCard } from "./TitleCard";

// Cuts that have a TTS voice clip linked — their Veo clip audio ducks beneath the voice.
const VOICE_CUT_IDS = new Set(VOICES.map((v) => v.id));

// Global-frame dialogue windows, used to duck the music beds under speech.
const DIALOGUE_WINDOWS: [number, number][] = VOICES.map((v) => [
  Math.round(v.start * FPS),
  Math.round(v.end * FPS),
]);
const isDialogueFrame = (globalFrame: number): boolean =>
  DIALOGUE_WINDOWS.some(([a, b]) => globalFrame >= a && globalFrame < b);

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

// 개별 컷: 영상 클립(있으면) + 자막 오버레이.
// Veo 네이티브 오디오(현장 효과음/앰비언스)는 낮게 깔고, 대사가 있는 컷은 더 낮춰 TTS 음성이 위에 앉도록 함.
const ClipScene: React.FC<{ clipId: string; label: string; hasVoice: boolean }> = ({
  clipId,
  label,
  hasVoice,
}) => {
  const src = CLIP_SRCS[clipId];
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {src ? (
        <OffthreadVideo
          src={staticFile(src)}
          volume={hasVoice ? AUDIO_MIX.clipNativeDuckedVolume : AUDIO_MIX.clipNativeVolume}
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
              <ClipScene clipId={cut.id} label={cut.label} hasVoice={VOICE_CUT_IDS.has(cut.id)} />
            </FadeScene>
          </Series.Sequence>
        ))}
        {/* 마지막: 타이틀 카드 2초 (28~30s) — 검은 화면 + "왕의 선택" + "무진장 무신사" + 쿵 임팩트 */}
        <Series.Sequence durationInFrames={TITLE_CARD_FRAMES} name="타이틀 카드">
          <TitleCard />
        </Series.Sequence>
      </Series>

      {/* 대사 TTS 음성 — storyboard 타이밍에 배치. 음성 파일이 public/voice/에 링크돼야 VOICES에 들어옴. */}
      {VOICES.map((v) => {
        const fromFrame = Math.round(v.start * FPS);
        const durFrames = Math.round((v.end - v.start) * FPS);
        return (
          <Sequence key={`voice-${v.id}`} from={fromFrame} durationInFrames={durFrames} name={`voice-${v.id}`}>
            <Audio src={staticFile(v.src)} volume={AUDIO_MIX.voiceVolume} />
          </Sequence>
        );
      })}

      {/* 배경 음악 베드 — Pixabay 자동 / YT Audio Library 수동. 대사 구간에선 살짝 덕킹. */}
      {MUSIC.map((m, i) => {
        const fromFrame = Math.round(m.start * FPS);
        const durFrames = Math.round((m.end - m.start) * FPS);
        return (
          <Sequence key={`music-${i}`} from={fromFrame} durationInFrames={durFrames} name={`music-${i}`}>
            <Audio
              src={staticFile(m.src)}
              volume={(rel) =>
                isDialogueFrame(fromFrame + rel) ? m.volume * AUDIO_MIX.musicDuckFactor : m.volume
              }
            />
          </Sequence>
        );
      })}
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
