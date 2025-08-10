import React, { useState, useEffect } from "react";
import img1 from "../assets/img/img1.webp";
import img2 from "../assets/img/img2.webp";
import img3 from "../assets/img/img3.webp";

const developers = ["Hoang Nguyen - Lead Dev", "Bhavesh Kumar - Director", "Demirhan", "Elise Poniman", "Derek", "Thakrit", ];
const advisors = ["Tim Leung - Director CFMR Program @UW"];

const GlitchText = ({ children, intensity = "medium" }: { children: React.ReactNode; intensity?: "low" | "medium" | "high" }) => {
  const [isGlitching, setIsGlitching] = useState(false);
  
  useEffect(() => {
    // Random glitch effect
    const glitchInterval = setInterval(() => {
      setIsGlitching(true);
      setTimeout(() => setIsGlitching(false), 200);
    }, Math.random() * 5000 + 3000);
    
    return () => clearInterval(glitchInterval);
  }, []);
  
  const glitchClasses = {
    low: "after:content-[attr(data-text)] after:absolute after:left-[2px] after:text-[#ff00cc] after:top-0 after:w-full after:h-full after:z-[-1]",
    medium: "after:content-[attr(data-text)] after:absolute after:left-[2px] after:text-[#ff00cc] after:top-0 after:w-full after:h-full after:z-[-1] before:content-[attr(data-text)] before:absolute before:left-[-2px] before:text-[#39ff14] before:top-0 before:w-full before:h-full before:z-[-1]",
    high: "after:content-[attr(data-text)] after:absolute after:left-[4px] after:text-[#ff00cc] after:top-0 after:w-full after:h-full after:z-[-1] before:content-[attr(data-text)] before:absolute before:left-[-4px] before:text-[#39ff14] before:top-0 before:w-full before:h-full before:z-[-1]"
  };
  
  return (
    <span 
      className={`relative inline-block ${isGlitching ? glitchClasses[intensity] : ""}`}
      data-text={children}
    >
      {children}
    </span>
  );
};

const InfoCard = ({ title, children }: any) => {
  return (
    <div className="bg-black bg-opacity-70 border border-gray-800 p-6 mb-8 relative overflow-hidden group hover:border-[#39ff14] transition-colors duration-300">
      {/* Corner decorations */}
      <div className="absolute top-0 right-0 w-8 h-8 border-t border-r border-[#ff00cc] opacity-50"></div>
      <div className="absolute bottom-0 left-0 w-8 h-8 border-b border-l border-[#ff00cc] opacity-50"></div>
      
      {/* Scan line effect */}
      <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(57,255,20,0.02)_50%)] bg-[length:100%_4px] pointer-events-none"></div>
      
      <h3 className="text-xl font-mono text-[#39ff14] mb-4 flex items-center">
        <span className="inline-block w-2 h-2 bg-[#39ff14] mr-2"></span>
        <GlitchText intensity="low">{title}</GlitchText>
      </h3>
      
      <div className="font-mono text-gray-300 space-y-4">
        {children}
      </div>
      
      {/* Bottom decoration */}
      <div className="w-full h-0.5 mt-4 bg-gradient-to-r from-transparent via-[#ff00cc] to-transparent opacity-30"></div>
    </div>
  );
};

const TeamMember = ({ name, role }: any) => {
  return (
    <div className="flex items-center mb-3 group">
      <div className="w-2 h-2 bg-[#39ff14] mr-3 group-hover:bg-[#ff00cc] transition-colors duration-300"></div>
      <div>
        <p className="font-mono text-white">{name}</p>
        {role && <p className="font-mono text-xs text-gray-500">{role}</p>}
      </div>
    </div>
  );
};

const AboutPage = () => {
  return (
    <section className="py-16 px-6 max-w-6xl mx-auto text-white relative min-h-screen">
      {/* Background grid */}
      <div className="fixed inset-0 bg-black z-[-2]"></div>
      <div className="fixed inset-0 bg-[linear-gradient(to_right,rgba(0,0,0,0)_0px,rgba(255,0,204,0.05)_1px,rgba(0,0,0,0)_1px)] bg-[size:40px_40px] z-[-1]"></div>
      <div className="fixed inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0)_0px,rgba(57,255,20,0.05)_1px,rgba(0,0,0,0)_1px)] bg-[size:40px_40px] z-[-1]"></div>
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,rgba(57,255,20,0.1)_0%,transparent_70%)] z-[-1]"></div>
      
      {/* Terminal header */}
      <div className="mb-12 border-b border-gray-800 pb-4 flex flex-col md:flex-row md:items-end justify-between">
        <div>
          <p className="font-mono text-xs text-gray-500 mb-1">[SYS::INFO]</p>
          <h1 className="text-5xl font-mono font-bold tracking-tighter mb-2">
            <span className="text-[#ff00cc]"><GlitchText intensity="high">HUSKY</GlitchText></span>
            <span className="text-white">::</span>
            <span className="text-[#39ff14]"><GlitchText intensity="high">HOLD'EM</GlitchText></span>
          </h1>
          <p className="font-mono text-sm text-gray-400">// OFFICIAL POKERBOT TOURNAMENT <span className="text-[#39ff14]">v2.5</span></p>
        </div>
        <div className="mt-4 md:mt-0">
          <p className="font-mono text-xs text-gray-500">
            <span className="text-[#ff00cc]">SYSTEM</span>::<span className="text-[#39ff14]">ABOUT</span>
          </p>
        </div>
      </div>

      {/* Main content */}
      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <InfoCard title="ABOUT THE TOURNAMENT">
            <p>
              Husky Hold'em is the official poker bot tournament hosted by the <span className="text-[#39ff14]"><a style={{color: "#39ff14"}} href="https://atcuw.org/" className="underline">[Algorithmic Trading Club]</a></span> at the University of Washington. Competitors build intelligent agents that play Texas Hold'em and compete in a real-time tournament simulation.
            </p>
            <p className="mt-4">
              This event tests algorithmic reasoning, decision-making under uncertainty, and competitive spirit in a cyberpunk-themed challenge.
            </p>
          </InfoCard>
          
          <InfoCard title="ABOUT THE ALGORITHMIC TRADING CLUB">
            <p>
              Founded in 2019, the <span className="text-[#39ff14]"><a style={{color: "#39ff14"}} href="https://atcuw.org/" className="underline">[Algorithmic Trading Club]</a></span> (formerly the Financial Engineering Club) at the University of Washington guides students through the evolving landscape of quantitative finance and algorithmic systems.
            </p>
            <p className="mt-4">
              From foundational Python to advanced data science and machine learning techniques, ATC equips members with the practical skills needed to thrive in high-stakes environments.
            </p>
            <p className="mt-4">
              Our club hosts hands-on workshops in strategy backtesting, trading engine design, and system deployment — all while fostering a collaborative community. Members benefit from guest talks, real-world projects, and high-impact competitions that sharpen their problem-solving abilities.
            </p>
          </InfoCard>
          
          <InfoCard title="WHY POKERBOTS">
            <p>
              Poker serves as a powerful sandbox for modeling uncertainty, making it a natural fit for exploring algorithmic strategy and game theory. Like traders, poker players make decisions with incomplete information, constantly assessing probability distributions and adapting to new information.
            </p>
            <p className="mt-4">
              In Husky Hold'em, participants build bots that operate under these same conditions — balancing expected value, exploiting opponent patterns, and optimizing behavior under uncertainty. It's more than a game: it's a training ground for building real-world decision-making systems.
            </p>
            <div className="mt-6 p-3 bg-black bg-opacity-50 border-l-2 border-[#39ff14] flex gap-3 items-center group hover:bg-opacity-70 transition-all duration-300">
              <span className="text-2xl">📖</span>
              <a 
                href="https://kipiilier.notion.site/Husky-Hold-em-Wiki-1eb8f86cec5c80b9b5e7cc2963162ca2?pvs=74" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="text-[#39ff14] underline hover:text-[#ff00cc] transition-colors duration-300"
              >
                Explore more in the Husky Hold'em Official Wiki
              </a>
            </div>
          </InfoCard>
        </div>
        
        <div className="md:col-span-1">
          {/* Team section */}
          <div className="bg-black bg-opacity-70 border border-gray-800 p-6 mb-8 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#ff00cc] to-[#39ff14]"></div>
            
            <h3 className="text-xl font-mono text-[#ff00cc] mb-6">
              <GlitchText>TEAM::MEMBERS</GlitchText>
            </h3>
            
            <div className="mb-6">
              <h4 className="font-mono text-sm text-[#39ff14] mb-3 uppercase tracking-wider">Developers</h4>
              {developers.map((dev) => (
                <TeamMember key={dev} name={dev} />
              ))}
            </div>
            
            <div className="mb-6">
              <h4 className="font-mono text-sm text-[#39ff14] mb-3 uppercase tracking-wider">Advisors</h4>
              {advisors.map((adv) => (
                <TeamMember key={adv} name={adv} />
              ))}
            </div>
            
            <div className="w-full border-t border-dashed border-gray-800 pt-4 mt-6">
              <p className="font-mono text-xs text-gray-500">
                <span className="text-[#ff00cc]">[STATUS]</span> Active members: {developers.length + advisors.length}
              </p>
            </div>
          </div>
          
          {/* System status */}
          <div className="bg-black bg-opacity-70 border border-gray-800 p-4 mb-8">
            <h4 className="font-mono text-sm text-[#39ff14] mb-2">SYSTEM::STATUS</h4>
            <div className="space-y-2 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Tournament:</span>
                <span className="text-[#39ff14]">ACTIVE</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Registration:</span>
                <span className="text-[#39ff14]">OPEN</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Next event:</span>
                <span className="text-[#ff00cc]">BOT_SUBMISSION</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Image Grid - Enhanced */}
      <div className="mt-16 relative">
        <h3 className="text-xl font-mono text-[#ff00cc] mb-6 flex items-center">
          <span className="inline-block w-2 h-2 bg-[#ff00cc] mr-2"></span>
          <GlitchText>MEMORY::ARCHIVES</GlitchText>
        </h3>
        
        <div className="grid grid-cols-6 grid-rows-6 gap-4 h-[60vh]">
          <div className="col-span-2 row-span-6 bg-[#0f0f0f] border border-gray-800 flex items-center justify-center relative group overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,0,204,0.15)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-[#ff00cc] to-transparent opacity-50"></div>
            <div className="absolute bottom-0 right-0 w-full h-0.5 bg-gradient-to-l from-[#ff00cc] to-transparent opacity-50"></div>
            <span className="font-mono text-gray-500 group-hover:text-[#ff00cc] transition-colors duration-300">NEURAL::ACCESS</span>
          </div>
          
          <div className="col-span-4 row-span-3 bg-cover bg-center border border-gray-800 relative group" style={{ backgroundImage: `url(${img1})` }}>
            <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
              <span className="font-mono text-[#39ff14]">// TOURNAMENT SESSION 2024</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
              <span className="text-[#ff00cc]">[IMAGE::01]</span> Annual competition
            </div>
          </div>
          
          <div className="col-span-3 row-span-3 bg-cover bg-center border border-gray-800 relative group" style={{ backgroundImage: `url(${img2})` }}>
            <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
              <span className="font-mono text-[#39ff14]">// STRATEGY SESSION</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
              <span className="text-[#ff00cc]">[IMAGE::03]</span> Workshop event
            </div>
          </div>
          
          <div className="col-span-3 row-span-3 bg-[#0f0f0f] border border-gray-800 flex items-center justify-center relative group overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(57,255,20,0.15)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="absolute top-0 right-0 w-full h-0.5 bg-gradient-to-l from-[#39ff14] to-transparent opacity-50"></div>
            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-[#39ff14] to-transparent opacity-50"></div>
            <span className="font-mono text-gray-500 group-hover:text-[#39ff14] transition-colors duration-300">DATA::STREAM</span>
          </div>
          
          <div className="col-span-3 row-span-3 bg-cover bg-center border border-gray-800 relative group" style={{ backgroundImage: `url(${img3})` }}>
            <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
              <span className="font-mono text-[#39ff14]">// CODING INTERFACE</span>
            </div>
            <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
              <span className="text-[#ff00cc]">[IMAGE::02]</span> Bot development
            </div>
          </div>
        </div>
      </div>

{/* <div className="mt-16 relative bg-black text-white p-4">
      <h3 className="text-xl font-mono text-[#ff00cc] mb-6 flex items-center">
        <span className="inline-block w-2 h-2 bg-[#ff00cc] mr-2"></span>
        <GlitchText>MEMORY::ARCHIVES</GlitchText>
      </h3>
      
      <div className="grid grid-cols-12 gap-4 h-[80vh]">
        <div className="col-span-6 row-span-4 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// TOURNAMENT SESSION 2024</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::01]</span> Annual competition finals
          </div>
          <img src="/api/placeholder/600/400" alt="Tournament" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-3 row-span-2 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// STRATEGY SESSION</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::02]</span> Workshop event
          </div>
          <img src="/api/placeholder/300/200" alt="Strategy Session" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-3 row-span-2 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// CODING INTERFACE</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::03]</span> Bot development
          </div>
          <img src="/api/placeholder/300/200" alt="Coding Interface" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-3 row-span-2 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// NEURAL NETWORK</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::04]</span> Training algorithms
          </div>
          <img src="/api/placeholder/300/200" alt="Neural Network" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-3 row-span-2 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// VIRTUAL ARENA</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::05]</span> Simulation system
          <div style={{background: 'url("../assets/img/img1.webp")'}}  className="w-full h-full object-cover" />
          </div>
        </div>
        
        <div className="col-span-3 row-span-3 bg-[#0f0f0f] border border-gray-800 flex items-center justify-center relative group overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(57,255,20,0.15)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <div className="absolute top-0 right-0 w-full h-0.5 bg-gradient-to-l from-[#39ff14] to-transparent opacity-50"></div>
          <div className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-[#39ff14] to-transparent opacity-50"></div>
          <span className="font-mono text-gray-500 group-hover:text-[#39ff14] transition-colors duration-300">DATA::STREAM</span>
        </div>
        
        <div className="col-span-3 row-span-3 bg-[#0f0f0f] border border-gray-800 flex items-center justify-center relative group overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,0,204,0.15)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-[#ff00cc] to-transparent opacity-50"></div>
          <div className="absolute bottom-0 right-0 w-full h-0.5 bg-gradient-to-l from-[#ff00cc] to-transparent opacity-50"></div>
          <span className="font-mono text-gray-500 group-hover:text-[#ff00cc] transition-colors duration-300">NEURAL::ACCESS</span>
        </div>
        
        <div className="col-span-2 row-span-1 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-70 opacity-100 group-hover:opacity-0 transition-opacity duration-500"></div>
          <div className="absolute bottom-0 left-0 w-full p-1 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMG::06]</span>
          </div>
          <img src="/api/placeholder/200/100" alt="Image 6" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-2 row-span-1 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-70 opacity-100 group-hover:opacity-0 transition-opacity duration-500"></div>
          <div className="absolute bottom-0 left-0 w-full p-1 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMG::07]</span>
          </div>
          <img src="/api/placeholder/200/100" alt="Image 7" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-2 row-span-1 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-70 opacity-100 group-hover:opacity-0 transition-opacity duration-500"></div>
          <div className="absolute bottom-0 left-0 w-full p-1 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMG::08]</span>
          </div>
          <img src="/api/placeholder/200/100" alt="Image 8" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-4 row-span-3 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// DEVELOPER TEAM</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::09]</span> Hackathon champions
          </div>
          <img src="/api/placeholder/400/300" alt="Developer Team" className="w-full h-full object-cover" />
        </div>
        
        <div className="col-span-2 row-span-3 bg-cover bg-center border border-gray-800 relative group">
          <div className="absolute inset-0 bg-black bg-opacity-60 opacity-100 group-hover:opacity-0 transition-opacity duration-500 flex items-center justify-center">
            <span className="font-mono text-[#39ff14]">// LAB</span>
          </div>
          <div className="absolute bottom-0 left-0 w-full p-2 bg-black bg-opacity-70 font-mono text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-[#ff00cc]">[IMAGE::10]</span>
          </div>
          <img src="/api/placeholder/200/300" alt="Lab" className="w-full h-full object-cover" />
        </div>
      </div>

      <div className="flex justify-center mt-6 gap-2">
        <div className="w-8 h-1 bg-[#ff00cc]"></div>
        <div className="w-8 h-1 bg-gray-700"></div>
        <div className="w-8 h-1 bg-gray-700"></div>
      </div>
    </div> */}
    </section>
  );
};

export default AboutPage;