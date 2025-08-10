import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./HeroSection.css"; // Assuming you have a CSS file for styles
import CyberPunkButton from "./CyberPunkButton";

// Updated to use Pacific timezone (America/Los_Angeles)
// July dates use PDT (UTC-7) due to daylight saving time
const COMPETITION_START = new Date("2025-07-12T00:00:00-07:00"); 
const FINAL_DEADLINE = new Date("2025-07-21T23:59:59-07:00");

const HeroSection: React.FC = () => {
  const [timeLeft, setTimeLeft] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date().getTime();
      
      // Check if competition hasn't started yet
      if (now < COMPETITION_START.getTime()) {
        setTimeLeft("Huskyholdem will officially start at July 12 2025");
        return;
      }
      
      // Competition has started, count down to final deadline
      const diff = FINAL_DEADLINE.getTime() - now;

      if (diff <= 0) {
        setTimeLeft("Submissions closed.");
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      setTimeLeft(`${days}d ${hours}h ${minutes}m ${seconds}s`);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="text-center bg-black py-16 w-full h-[80vh] flex flex-col items-center justify-center overflow-clip">
    <div className="environment"></div>
    <h1 className="hero glitch layers" data-text="冷血不够，要冷码"><span>HUSKY♠ HOLD'EM</span></h1>
    {timeLeft == "Huskyholdem will officially start at July 12 2025" && <p className="hero-countdown">{timeLeft}</p>}
    {timeLeft != "Huskyholdem will officially start at July 12 2025" && <p className="hero-countdown">Final submission in: {timeLeft}</p>}
    <p>A University of Washington POKERBOTS EXTRAVAGANZA</p>
    <CyberPunkButton text="REGISTER" onClick={() => navigate("/register")} className="mt-4"/>
    </section>
  );
};

export default HeroSection;
