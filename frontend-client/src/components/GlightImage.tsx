import React, { useRef } from "react";
import Sketch from "react-p5";
import p5Types from "p5";
import { Glitch } from "./Glight";

interface GlitchSketchProps {
  imageSrc: string;
  width: number;
  height: number;
}

const GlitchImage: React.FC<GlitchSketchProps> = ({ imageSrc, width, height }) => {
  const glitchRef = useRef<Glitch | null>(null);
  const imgRef = useRef<p5Types.Image | null>(null);
  const readyRef = useRef(false);

  // Only load image once
  const preload = (p5: p5Types) => {
    if (imgRef.current) return; // don't load again on reload
    p5.loadImage(imageSrc, (img) => {
      // img.resize(width, height);
      imgRef.current = img;
      readyRef.current = true;
    });
  };

  const setup = (p5: p5Types, canvasParentRef: Element) => {
    // Remove old canvas if hot reload left it behind
    const oldCanvas = canvasParentRef.querySelector("canvas");
    if (oldCanvas) oldCanvas.remove();

    const canvas = p5.createCanvas(width, height);
    canvas.parent(canvasParentRef);
    p5.pixelDensity(1);
    p5.background(0);

    if (imgRef.current) {
      glitchRef.current = new Glitch(imgRef.current, p5);
    }
  };

  const draw = (p5: p5Types) => {
    p5.clear(0,0,0,0);
    p5.background(0);
    if (readyRef.current && glitchRef.current) {
      glitchRef.current.show();
    }
  };

  return <Sketch preload={preload} setup={setup} draw={draw} />;
};

export default GlitchImage;
