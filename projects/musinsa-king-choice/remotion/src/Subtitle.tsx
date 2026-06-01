import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { FPS, SUBTITLES } from "./generated/manifest";

export const Subtitle: React.FC = () => {
  const frame = useCurrentFrame();
  const currentSec = frame / FPS;

  const active = SUBTITLES.find(
    (s) => currentSec >= s.start && currentSec < s.end
  );

  if (!active) return null;

  const elapsed = currentSec - active.start;
  const remaining = active.end - currentSec;
  const opacity = Math.min(
    interpolate(elapsed, [0, 0.2], [0, 1], { easing: Easing.ease }),
    interpolate(remaining, [0, 0.3], [0, 1], { easing: Easing.ease })
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        padding: "0 40px",
        opacity,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.65)",
          borderRadius: 12,
          padding: "14px 24px",
          textAlign: "center",
          whiteSpace: "pre-line",
          fontSize: 36,
          fontWeight: 700,
          color: "#fff",
          lineHeight: 1.5,
          letterSpacing: "-0.3px",
          textShadow: "0 2px 8px rgba(0,0,0,0.8)",
          fontFamily: "'Noto Serif KR', serif",
        }}
      >
        {active.text}
      </div>
    </div>
  );
};
