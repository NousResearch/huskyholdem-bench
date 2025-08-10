import { ReactElement } from "react";
import DefaultFooter from "./footer";
import DefaultHeader from "./header";
import "./layout.css";

const DefaultLayout = ({ children }: { children: ReactElement }) => {
  return (
    <div className="relative min-h-screen bg-black text-white">
      {/* Moving Grid Background */}
      <div className="fixed top-0 left-0 w-full h-full z-0 pointer-events-none overflow-hidden">
        <div className="moving-grid" />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <DefaultHeader />
              <main className="flex-grow">
                  {children}
              </main>
        <DefaultFooter />
      </div>
    </div>
  );
};

export default DefaultLayout;
