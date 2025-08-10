import { useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stage } from "@react-three/drei";
import { Model } from "./Model";

const RotatingPrizeModel = () => {
  return (
    <Canvas 
      style={{ width: "100%", height: "100%" }} 
      camera={{ position: [0, 0, 40], fov: 75 }}
      shadows
    >
      <color attach="background" args={["#050510"]} />
      <fog attach="fog" args={["#050510", 50, 60]} />
      
      {/* Enhanced lighting for cyberpunk effect */}
      <ambientLight intensity={0.3} />
      <pointLight position={[20, 20, 20]} color="#39ff14" intensity={2} />
      <pointLight position={[-20, -10, -10]} color="#ff00cc" intensity={1.5} />
      
      <Stage 
        intensity={0.5} 
        shadows="contact" 
        environment="city"
      >
        <Model 
          scale={1} 
          position={[0, 0, 0]} 
        />
      </Stage>
      
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={2} />
    </Canvas>
  );
};

const PrizeCard = ({ emoji, title, description, color, highlight }: any) => {
  const [hover, setHover] = useState(false);
  
  return (
    <div 
      className={`relative border border-gray-800 bg-black bg-opacity-70 p-4 transition-all duration-300 ${
        hover ? "translate-x-1 -translate-y-1" : ""
      }`}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Background effects */}
      <div className={`absolute inset-0 bg-gradient-to-r from-transparent to-${color} opacity-10`}></div>
      <div className={`absolute top-0 left-0 w-full h-0.5 bg-${color} opacity-50`}></div>
      <div className={`absolute bottom-0 right-0 w-1/2 h-0.5 bg-${color} opacity-30`}></div>
      
      {/* Highlight indicator */}
      {highlight && (
        <div className="absolute -right-1 top-0 bottom-0 w-1 bg-gradient-to-b from-[#39ff14] via-fuchsia-600 to-[#39ff14]"></div>
      )}
      
      <div className="flex items-center">
        <span className="text-2xl mr-3">{emoji}</span>
        <div>
          <h3 className={`text-${color} text-lg  mb-1`}>{title}</h3>
          <p className="text-gray-300  text-sm tracking-wide">{description}</p>
        </div>
      </div>
    </div>
  );
};

const GlitchText = ({ children }: any) => {
  const [glitchActive, setGlitchActive] = useState(false);
  
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 200);
    }, 3000);
    
    return () => clearInterval(glitchInterval);
  }, []);
  
  return (
    <span className="relative inline-block">
      <span className={`${glitchActive ? "opacity-0" : "opacity-100"} transition-opacity`}>
        {children}
      </span>
      {glitchActive && (
        <>
          <span className="absolute top-0 left-0 text-[#39ff14] translate-x-0.5 translate-y-0.5 opacity-70">
            {children}
          </span>
          <span className="absolute top-0 left-0 text-fuchsia-600 -translate-x-0.5 -translate-y-0.5 opacity-70">
            {children}
          </span>
        </>
      )}
    </span>
  );
};

const PrizeSection = () => {
  return (
    <section className="py-16 px-4 min-h-screen flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(57,255,20,0.03)_0%,_transparent_70%)]"></div>
      {/* <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(0,0,0,0)_0px,rgba(255,0,204,0.1)_1px,rgba(0,0,0,0)_1px)]" style={{ backgroundSize: "40px 40px" }}></div> */}
      {/* <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0)_0px,rgba(255,0,204,0.1)_1px,rgba(0,0,0,0)_1px)]" style={{ backgroundSize: "40px 40px" }}></div> */}
      
      {/* Corner decorations */}
      <div className="absolute top-0 right-0 w-32 h-32 border-t-2 border-r-2 border-[#39ff14] opacity-30"></div>
      <div className="absolute bottom-0 left-0 w-32 h-32 border-b-2 border-l-2 border-fuchsia-600 opacity-30"></div>
      
      <div className="container mx-auto z-10">
        {/* Header */}
        <div className="relative mb-12 text-center">
          <h2 className="text-4xl  text-fuchsia-600 mb-2 tracking-widest uppercase">
            <GlitchText>NEURAL</GlitchText>::<span className="text-[#39ff14]"><GlitchText>REWARDS</GlitchText></span>
          </h2>
          <p className="text-gray-400  text-sm">// TOURNAMENT PRIZES 2.0.2.5</p>
          <div className="w-32 h-1 mx-auto mt-2 bg-gradient-to-r from-fuchsia-600 to-[#39ff14]"></div>
        </div>

        <div className="flex flex-col md:flex-row gap-8 items-center">
          {/* Trophy Visualization */}
          <div className="md:w-1/2">
            <div className="aspect-square max-w-md mx-auto border border-gray-800 bg-black bg-opacity-50 rounded-sm overflow-hidden relative">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,0,204,0.1)_0%,_transparent_70%)]"></div>
              <RotatingPrizeModel />
              <div className="absolute bottom-4 left-0 right-0 text-center">
                <div className="inline-block px-3 py-1 bg-black bg-opacity-70 border-l border-r border-fuchsia-600">
                  <span className="text-[#39ff14]  text-sm tracking-wider">CHAMPIONSHIP TROPHY</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Prize List */}
          <div className="md:w-1/2 space-y-4">
            <PrizeCard 
              emoji="🥇" 
              title="FIRST PRIZE" 
              description="Championship Trophy (FPGA board) + ATC-0 fast track + $150 + Jane Street Owala Water bottles" 
              color="fuchsia-600" 
              highlight={true}
            />
            <PrizeCard 
              emoji="🥈" 
              title="SECOND PRIZE" 
              description="$100 + Jane Street Owala Water bottles + Digital Certificate" 
              color="#39ff14" 
              highlight={false}
            />
            <PrizeCard 
              emoji="🥉" 
              title="THIRD PRIZE" 
              description="$50 + Jane Street Owala Water bottles + Digital Certificate" 
              color="#39ff14" 
              highlight={false}
            />
            <PrizeCard 
              emoji="🏅" 
              title="HONORABLE MENTIONS" 
              description="Digital Certificate" 
              color="#39ff14" 
              highlight={false}
            />
          </div>
        </div>
        
        {/* Additional details */}
        <div className="mt-12 max-w-lg mx-auto text-center">
          <div className="inline-block px-4 py-2 bg-black bg-opacity-70 border-l-2 border-r-2 border-[#39ff14]">
            <p className="text-gray-400  text-sm">
              <span className="text-fuchsia-600">[SYS:INFO]</span> All winners receive exclusive fast-track interview for ATC-0, our newest quant funnel program.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PrizeSection;