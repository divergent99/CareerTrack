import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import RippleGrid from "./components/RippleGrid";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import Dashboard from "./pages/Dashboard";
import Applications from "./pages/Applications";
import Roadmap from "./pages/Roadmap";
import ResumeReview from "./pages/ResumeReview";
import GithubAnalysis from "./pages/GithubAnalysis";

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [githubResult, setGithubResult] = useState(null);
  const [sessionRevision, setSessionRevision] = useState(0);

  return (
    <BrowserRouter>
      <div className="h-screen w-screen flex bg-black">
        <Sidebar
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onNewChat={() => setActiveSessionId(null)}
          sessionRevision={sessionRevision}
        />

        <div className="relative flex-1 h-full">
          <div className="absolute inset-0 z-0">
            <RippleGrid
              enableRainbow={false}
              gridColor="#5227FF"
              rippleIntensity={0.03}
              gridSize={10}
              gridThickness={15}
              mouseInteraction
              mouseInteractionRadius={0.8}
              opacity={1}
              fadeDistance={1.5}
              vignetteStrength={2}
              glowIntensity={0.1}
              gridRotation={0}
            />
          </div>

          <div className="relative z-10 h-full">
            <Routes>
              <Route
                path="/"
                element={
                  <ChatWindow
                    sessionId={activeSessionId}
                    onSessionCreated={setActiveSessionId}
                    onSessionRenamed={() => setSessionRevision((value) => value + 1)}
                  />
                }
              />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/roadmap" element={<Roadmap />} />
              <Route path="/resume" element={<ResumeReview />} />
              <Route
                path="/github"
                element={<GithubAnalysis result={githubResult} setResult={setGithubResult} />}
              />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}
