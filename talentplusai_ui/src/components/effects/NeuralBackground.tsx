"use client";

import { useEffect, useRef } from "react";

/** Matches `talentplus-landing/js/main.js` neural canvas — sparse nodes, thin lines, no bright halos. */
const NODE_COUNT = 80;
const MAX_DIST = 160;
const TEAL = "0,230,200";
const INDIGO = "129,140,248";

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  color: string;
  opacity: number;
};

export default function NeuralBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const cnv = canvas;
    const c = ctx;

    let W = 0;
    let H = 0;
    let raf = 0;
    let mouseX = -999;
    let mouseY = -999;
    const nodes: Node[] = [];

    function createNodes() {
      nodes.length = 0;
      for (let i = 0; i < NODE_COUNT; i++) {
        nodes.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 1.8 + 0.6,
          color: Math.random() > 0.6 ? INDIGO : TEAL,
          opacity: Math.random() * 0.5 + 0.3,
        });
      }
    }

    function resize() {
      W = window.innerWidth;
      H = window.innerHeight;
      cnv.width = W;
      cnv.height = H;
      createNodes();
    }

    function onMove(e: MouseEvent) {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }

    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("mousemove", onMove);

    function draw() {
      c.fillStyle = "#060d14";
      c.fillRect(0, 0, W, H);

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0) n.x = W;
        if (n.x > W) n.x = 0;
        if (n.y < 0) n.y = H;
        if (n.y > H) n.y = 0;

        const dx = mouseX - n.x;
        const dy = mouseY - n.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 200 && dist > 0) {
          n.vx += (dx / dist) * 0.008;
          n.vy += (dy / dist) * 0.008;
        }
        const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
        if (speed > 0.9) {
          n.vx *= 0.95;
          n.vy *= 0.95;
        }
      }

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < MAX_DIST) {
            const alpha = (1 - d / MAX_DIST) * 0.3;
            c.beginPath();
            c.moveTo(a.x, a.y);
            c.lineTo(b.x, b.y);
            c.strokeStyle = `rgba(${a.color},${alpha})`;
            c.lineWidth = 0.7;
            c.stroke();
          }
        }
      }

      for (const n of nodes) {
        c.beginPath();
        c.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        c.fillStyle = `rgba(${n.color},${n.opacity})`;
        c.fill();
      }

      raf = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      window.removeEventListener("resize", resize);
      document.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-[2]" />;
}
