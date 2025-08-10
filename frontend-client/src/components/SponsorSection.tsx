// SponsorSection.tsx
import React from "react";
import "./SponsorSection.css";
import GlitchImage from "./GlightImage";
import Wolfram from "../assets/img/wolfram.webp";

const sponsors = [
  { name: "Jane Street", src: "https://opensource.janestreet.com/assets/JS_logo-d7838b558a1de6c51553426ab5a2bba474510c41c6a5e910a9e30524a32dec27.png", link: "https://www.janestreet.com" },
  { name: "QuantConnect", src: "https://www.interactivebrokers.com/images/emailImages/co-logo-quantconnect.png", link: "https://www.quantconnect.com" },
  { name: "Wolfram", src: Wolfram, link: "https://www.wolfram.com" },
  { name: "QuantInsti", src: "https://upload.wikimedia.org/wikipedia/commons/5/5b/Quantinsti-registered-logo.png", link: "https://www.quantinsti.com" },
];

const SponsorSection: React.FC = () => {
  return (
    <section className="sponsor-section">
      <h2 className="sponsor-title">OUR SPONSORS</h2>
      <p className="sponsor-contact">
        Sponsorship inquiries:{" "}
        <a href="mailto:uwfeclub@gmail.com">uwfeclub@gmail.com</a>
      </p>

      <div className="sponsor-grid">
        {sponsors.map((sponsor) => (
          <a
            key={sponsor.name}
            href={sponsor.link}
            target="_blank"
            rel="noopener noreferrer"
            className="sponsor-link"
          >
            <div className="sponsor-card">
              <img src={sponsor.src} alt={sponsor.name} />
            </div>
          </a>
        ))}
      </div>
      <div className="glitch-image-container min-h-[30vh] w-full flex justify-center items-center">
        <GlitchImage imageSrc="https://media.licdn.com/dms/image/v2/C4E0BAQFDyQj1pXubxQ/company-logo_200_200/company-logo_200_200/0/1630586949571?e=1750896000&v=beta&t=HFUrj5-7R8YP_08aSgebs0uVxCkYhXQZ5uhOgmO7DuM" height={300} width={800}/>
      </div>
    </section>
  );
};

export default SponsorSection;