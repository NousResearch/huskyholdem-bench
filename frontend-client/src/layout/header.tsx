import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./header.css";

const DefaultHeader = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { isAuthenticated, user, logout } = useAuth();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      {/* Header Wrapper */}
      <div
        className={`fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300 ${
          scrolled ? "bg-black/90 shadow-lg" : "bg-black/70"
        } border-b border-[#444]`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Main Row */}
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link
              to="/"
              className="text-[#ff00cc] glitch font-glitch text-xl sm:text-2xl uppercase glitch-move"
            >
              HUSKY HOLDEM <span className="text-[#39ff14]">BENCH</span>
            </Link>

            {/* Desktop Menu */}
            <div className="hidden md:flex gap-8 text-sm font-mono tracking-widest uppercase items-center">
              <Link
                to="/"
                className="hover:text-[#ff00cc] text-white transition-all glitch-hover"
              >
                Home
              </Link>
              <Link
                to="/games"
                className="hover:text-[#39ff14] text-white transition-all glitch-hover"
              >
                Games
              </Link>

              {isAuthenticated && (
                <>
                  <Link
                    to="/submission"
                    className="hover:text-[#39ff14] text-white transition-all glitch-hover"
                  >
                    Submission
                  </Link>
                  <Link
                    to="/dashboard"
                    className="hover:text-[#39ff14] text-white transition-all glitch-hover"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/leaderboard"
                    className="hover:text-[#39ff14] text-white transition-all glitch-hover"
                  >
                    Leaderboard
                  </Link>

                  {user?.admin && (
                    <Link
                      to="/admin"
                      className="hover:text-[#ff6600] text-white transition-all glitch-hover"
                    >
                      /a
                    </Link>
                  )}
                  <Link
                    to="/profile"
                    className="hover:text-[#39ff14] text-white transition-all glitch-hover"
                  >
                    <span className="text-gray-300">
                      Hi,{" "}
                      <span className="text-[#ff00cc]">{user?.username}</span>
                    </span>
                  </Link>

                  <button
                    onClick={logout}
                    className="border border-red-500 px-3 py-1 text-red-500 hover:bg-red-500 hover:text-white transition uppercase"
                  >
                    Logout
                  </button>
                </>
              )}
            </div>

            {/* Mobile Menu Button */}
            <div className="md:hidden flex items-center">
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="text-white focus:outline-none"
              >
                {isMenuOpen ? (
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu Items */}
        {isMenuOpen && (
          <div className="md:hidden bg-black border-t border-[#444] px-6 pb-4 pt-2 text-sm font-mono uppercase space-y-4">
            <Link
              to="/"
              className="block text-white hover:text-[#ff00cc] glitch-hover"
              onClick={() => setIsMenuOpen(false)}
            >
              Home
            </Link>
            <Link
              to="/games"
              className="block text-white hover:text-[#39ff14] glitch-hover"
              onClick={() => setIsMenuOpen(false)}
            >
              Games
            </Link>

            {isAuthenticated && (
              <>
                <Link
                  to="/submission"
                  className="block text-white hover:text-[#39ff14] glitch-hover"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Submission
                </Link>
                <Link
                  to="/dashboard"
                  className="block text-white hover:text-[#39ff14] glitch-hover"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Dashboard
                </Link>
                <Link
                  to="/leaderboard"
                  className="block text-white hover:text-[#39ff14] glitch-hover"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Leaderboard
                </Link>

                {user?.admin && (
                  <Link
                    to="/admin"
                    className="block text-white hover:text-[#ff6600] glitch-hover"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Admin
                  </Link>
                )}

                <span className="block text-gray-300">
                  Hi,{" "}
                  <span className="text-[#ff00cc]">{user?.username}</span>
                </span>
                <button
                  onClick={() => {
                    logout();
                    setIsMenuOpen(false);
                  }}
                  className="block border border-red-500 text-center py-2 text-red-500 hover:bg-red-500 hover:text-white transition"
                >
                  Logout
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Spacer to offset fixed header */}
      <div className="h-16 md:h-20"></div>
    </>
  );
};

export default DefaultHeader;
