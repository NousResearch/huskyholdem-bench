import { useState } from "react";

const timelineItems = [
  { date: "July 12th", label: "Official Competition Start" },
  { date: "July 21st", label: "Final Submission Deadline" },
  { date: "July 22nd", label: "Tournament Begins" },
  { date: "July 25th", label: "Tournament Ends" },
  { date: "July 26th", label: "Showdown Watch Party/Results Announced" },
];

const TimelineSection = () => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  return (
    <section className="py-16 px-4  min-h-screen flex flex-col items-center justify-center ">
      <div className="relative mb-16">
        <h2 className="text-4xl font-bold text-[#39ff14] tracking-widest uppercase relative z-10">
          <span className="text-fuchsia-600">SYS</span>:<span className="text-[#39ff14]">TIMELINE</span>
        </h2>
        <div className="absolute -inset-1 bg-[#39ff14] opacity-20 blur-md"></div>
      </div>
      
      <div className="max-w-3xl mx-auto relative">
        {/* Vertical line with glow */}
        <div className="absolute left-6 top-4 bottom-6 w-1 bg-gradient-to-b from-fuchsia-600 via-[#39ff14] to-fuchsia-600 rounded-full">
          <div className="absolute inset-0 blur-sm bg-gradient-to-b from-fuchsia-600 via-[#39ff14] to-fuchsia-600 opacity-70"></div>
        </div>
        
        <ul className="relative space-y-12">
          {timelineItems.map((item, idx) => (
            <li 
              key={idx} 
              className="relative pl-12 pr-4 py-3 border border-gray-800 bg-gray-900 bg-opacity-80 rounded"
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {/* Node point */}
              <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2 flex items-center justify-center">
                <div className={`w-4 h-4 bg-fuchsia-600 rounded-full z-10 ${hoveredIndex === idx ? 'animate-pulse' : ''}`}></div>
                <div className={`absolute w-6 h-6 bg-[#39ff14] rounded-full blur-md opacity-70 ${hoveredIndex === idx ? 'animate-pulse' : ''}`}></div>
              </div>
              
              {/* Content */}
              <div className={`transition-all duration-300 ${hoveredIndex === idx ? 'translate-x-2' : ''}`}>
                <p className="text-fuchsia-600 text-lg mb-1 flex items-center">
                  <span className="inline-block w-8 text-[#39ff14] mr-2">[</span>
                  {item.date}
                  <span className="inline-block w-8 text-[#39ff14] ml-2">]</span>
                </p>
                <p className="text-[#39ff14] text-xl tracking-wide ml-12">
                  {item.label}
                </p>
                <div className={`absolute inset-0 border border-fuchsia-600 opacity-0 ${hoveredIndex === idx ? 'opacity-20' : ''} transition-opacity duration-300 blur-sm`}></div>
              </div>
              
              {/* Glitchy decoration */}
              <div className="absolute top-0 right-0 h-full w-1 bg-gradient-to-b from-transparent via-[#39ff14] to-transparent opacity-60"></div>
              <div className="absolute bottom-0 left-0 h-1 w-1/3 bg-gradient-to-r from-fuchsia-600 to-transparent opacity-60"></div>
            </li>
          ))}
        </ul>
        
        {/* Background decorative elements */}
        <div className="absolute -top-4 -right-4 w-16 h-16 border-t-2 border-r-2 border-[#39ff14] opacity-50"></div>
        <div className="absolute -bottom-4 -left-4 w-16 h-16 border-b-2 border-l-2 border-fuchsia-600 opacity-50"></div>
      </div>
      
      <div className="mt-12 font-mono text-xs text-gray-500 tracking-wider">
        {/* ACTIVE, ESTIMATED, DONE */}
        <p className="mb-2">[SYS:STATUS] <span className="text-[#39ff14]">TOURNAMENT_PHASE</span>:<span className="text-fuchsia-600">ESTIMATED</span></p>
        <p>INIT::<span className="text-[#39ff14]">PROTOCOL_2025</span></p>
      </div>
    </section>
  );
};

export default TimelineSection;