import { useEffect, useId, useRef, useState } from "react";

const INTERACTIVE_SELECTOR =
  'a, button, [role="button"], input, select, textarea, label, .button, .arrow-link';

const BLOB_POINTS = 14;
const CENTER = 100;
const BASE_RADIUS = 30;

interface BlobPoint {
  x: number;
  y: number;
}

function buildBlobPath(points: BlobPoint[]) {
  if (!points.length) return "";

  const firstMidX = (points[0].x + points[1].x) / 2;
  const firstMidY = (points[0].y + points[1].y) / 2;

  let path = `M ${firstMidX.toFixed(2)} ${firstMidY.toFixed(2)}`;

  for (let index = 1; index < points.length; index += 1) {
    const point = points[index];
    const next = points[(index + 1) % points.length];
    const midX = (point.x + next.x) / 2;
    const midY = (point.y + next.y) / 2;
    path += ` Q ${point.x.toFixed(2)} ${point.y.toFixed(2)} ${midX.toFixed(2)} ${midY.toFixed(2)}`;
  }

  const closingPoint = points[0];
  path += ` Q ${closingPoint.x.toFixed(2)} ${closingPoint.y.toFixed(2)} ${firstMidX.toFixed(2)} ${firstMidY.toFixed(2)} Z`;
  return path;
}

function createBlobPath(time: number, hoverMix: number) {
  const points: BlobPoint[] = [];
  const amplitude = 9 + hoverMix * 5;
  const speed = 0.00105 + hoverMix * 0.00065;

  for (let index = 0; index < BLOB_POINTS; index += 1) {
    const angle = (Math.PI * 2 * index) / BLOB_POINTS;
    const wobbleA = Math.sin(time * speed + index * 0.83) * amplitude;
    const wobbleB = Math.cos(time * speed * 1.51 + index * 1.17) * amplitude * 0.54;
    const wobbleC = Math.sin(time * speed * 0.73 + index * 2.21) * amplitude * 0.28;
    const wobbleD = Math.cos(time * speed * 2.12 + index * 0.49) * amplitude * 0.18;
    const radius = BASE_RADIUS + wobbleA + wobbleB + wobbleC + wobbleD;

    points.push({
      x: CENTER + Math.cos(angle) * radius,
      y: CENTER + Math.sin(angle) * radius,
    });
  }

  return buildBlobPath(points);
}

export function OceanCursor() {
  const cursorRef = useRef<HTMLDivElement | null>(null);
  const maskPathRef = useRef<SVGPathElement | null>(null);
  const shadowPathRef = useRef<SVGPathElement | null>(null);
  const outlinePathRef = useRef<SVGPathElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const maskId = useId().replace(/[^a-zA-Z0-9_-]/g, "");

  useEffect(() => {
    const mediaQuery = window.matchMedia("(hover: hover) and (pointer: fine)");
    const syncEnabled = () => setEnabled(mediaQuery.matches);

    syncEnabled();
    mediaQuery.addEventListener("change", syncEnabled);

    return () => mediaQuery.removeEventListener("change", syncEnabled);
  }, []);

  useEffect(() => {
    if (!enabled || !cursorRef.current || !maskPathRef.current || !shadowPathRef.current || !outlinePathRef.current) {
      return;
    }

    const cursor = cursorRef.current;
    const maskPath = maskPathRef.current;
    const shadowPath = shadowPathRef.current;
    const outlinePath = outlinePathRef.current;

    let currentX = window.innerWidth / 2;
    let currentY = window.innerHeight / 2;
    let targetX = currentX;
    let targetY = currentY;
    let hoverMix = 0;
    let isActive = false;

    const setVisible = (visible: boolean) => {
      cursor.dataset.visible = visible ? "true" : "false";
    };

    const setActive = (active: boolean) => {
      isActive = active;
      cursor.dataset.active = active ? "true" : "false";
    };

    const render = (time: number) => {
      currentX += (targetX - currentX) * 0.18;
      currentY += (targetY - currentY) * 0.18;

      const hoveredTarget = document.elementFromPoint(targetX, targetY);
      const hoveredInteractive =
        hoveredTarget instanceof Element ? hoveredTarget.closest(INTERACTIVE_SELECTOR) : null;

      if (Boolean(hoveredInteractive) !== isActive) {
        setActive(Boolean(hoveredInteractive));
      }

      hoverMix += ((isActive ? 1 : 0) - hoverMix) * 0.02;

      cursor.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;

      const blobPath = createBlobPath(time, hoverMix);
      maskPath.setAttribute("d", blobPath);
      shadowPath.setAttribute("d", blobPath);
      outlinePath.setAttribute("d", blobPath);

      frameRef.current = window.requestAnimationFrame(render);
    };

    const handleMove = (event: MouseEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
      setVisible(true);
    };

    const handleLeaveWindow = () => {
      setVisible(false);
      setActive(false);
    };

    frameRef.current = window.requestAnimationFrame(render);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("blur", handleLeaveWindow);
    document.addEventListener("mouseleave", handleLeaveWindow);

    return () => {
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("blur", handleLeaveWindow);
      document.removeEventListener("mouseleave", handleLeaveWindow);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div
      aria-hidden="true"
      className="remindr-ocean-cursor"
      data-active="false"
      data-visible="false"
      ref={cursorRef}
    >
      <div className="remindr-ocean-cursor-core" />
      <div className="remindr-ocean-cursor-drop">
        <svg className="remindr-ocean-cursor-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id={`remindr-ocean-cursor-gradient-${maskId}`} cx="38%" cy="30%" r="70%">
              <stop offset="0%" stopColor="rgba(255,255,255,0.95)" />
              <stop offset="36%" stopColor="rgba(182,238,255,0.88)" />
              <stop offset="72%" stopColor="rgba(67,184,222,0.48)" />
              <stop offset="100%" stopColor="rgba(14,79,117,0.16)" />
            </radialGradient>
            <mask id={`remindr-ocean-cursor-mask-${maskId}`}>
              <g className="remindr-ocean-cursor-blob-mask">
                <path fill="white" ref={maskPathRef} />
              </g>
            </mask>
          </defs>

          <path className="remindr-ocean-cursor-shadow" ref={shadowPathRef} />
          <rect
            fill={`url(#remindr-ocean-cursor-gradient-${maskId})`}
            height="200"
            mask={`url(#remindr-ocean-cursor-mask-${maskId})`}
            width="200"
            x="0"
            y="0"
          />
          <path className="remindr-ocean-cursor-outline" ref={outlinePathRef} />
        </svg>
      </div>
    </div>
  );
}
