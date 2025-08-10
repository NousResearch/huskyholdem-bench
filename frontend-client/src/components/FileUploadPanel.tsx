import React, { useEffect, useState } from "react";

type Props = {
  onSubmit: (formData: FormData) => Promise<void>;
  error: string | null;
  setError: (error: string | null) => void;
  status: "idle" | "submitting" | "success" | "error";
  setStatus: (status: "idle" | "submitting" | "success" | "error") => void;
  playerFile: File | null;
  setPlayerFile: (file: File | null) => void;
  requirementsFile: File | null;
  setRequirementsFile: (file: File | null) => void;
  cooldownRemaining: number;
};

const FileUploadPanel: React.FC<Props> = ({ playerFile, setPlayerFile, requirementsFile, setRequirementsFile, status, error, onSubmit, cooldownRemaining }) => {
  const [playerFileContent, setPlayerFileContent] = useState("");
  const [requirementsFileContent, setRequirementsFileContent] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState<"player" | "requirements">("player");

  useEffect(() => {
    if (playerFile) {
      const reader = new FileReader();
      reader.onload = (e) => setPlayerFileContent(e.target?.result as string);
      reader.readAsText(playerFile);
    } else setPlayerFileContent("");
  }, [playerFile]);

  useEffect(() => {
    if (requirementsFile) {
      const reader = new FileReader();
      reader.onload = (e) => setRequirementsFileContent(e.target?.result as string);
      reader.readAsText(requirementsFile);
    } else setRequirementsFileContent("");
  }, [requirementsFile]);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    processFiles(Array.from(e.dataTransfer.files));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(Array.from(e.target.files ?? []));
  };

  const processFiles = (files: File[]) => {
    for (const file of files) {
      if (file.name === "player.py") {
        setPlayerFile(file);
        setShowPreview(true);
        setActiveTab("player");
      } else if (file.name === "requirements.txt") {
        setRequirementsFile(file);
        if (!playerFile) {
          setShowPreview(true);
          setActiveTab("requirements");
        }
      }
    }
  };

  return (
    <>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-[#ff00cc] bg-black/30 p-6 rounded-lg text-center cursor-pointer hover:bg-white/5 transition"
      >
        <p className="text-lg mb-2">Drag & drop <code>player.py</code> and <code>requirements.txt</code></p>
        <p className="text-sm text-gray-400">Or select files manually below</p>
        <input
          type="file"
          accept=".py,.txt"
          multiple
          onChange={handleFileInput}
          className="mt-4 text-sm text-white file:hidden"
        />
      </div>

      <div className="mt-4 space-y-2 text-sm">
        <p><span className="font-mono text-green-400">player.py</span>: {playerFile?.name || "Not selected"}</p>
        <p><span className="font-mono text-purple-400">requirements.txt</span>: {requirementsFile?.name || "Not selected"}</p>
      </div>

      {showPreview && (
        <div className="mt-6 border border-[#333] rounded-lg overflow-hidden">
          <div className="flex border-b border-[#333]">
            {playerFile && (
              <button
                className={`px-4 py-2 ${activeTab === "player" ? "bg-[#222] text-[#39ff14]" : "text-gray-400"}`}
                onClick={() => setActiveTab("player")}
              >
                player.py
              </button>
            )}
            {requirementsFile && (
              <button
                className={`px-4 py-2 ${activeTab === "requirements" ? "bg-[#222] text-[#ff00cc]" : "text-gray-400"}`}
                onClick={() => setActiveTab("requirements")}
              >
                requirements.txt
              </button>
            )}
          </div>
          <div className="bg-[#111] p-4 max-h-96 overflow-y-auto">
            <pre className="font-mono text-sm whitespace-pre-wrap break-words">
              {activeTab === "player" ? playerFileContent : requirementsFileContent}
            </pre>
          </div>
        </div>
      )}

      {error && <p className="text-red-500 mt-2 text-sm">{error}</p>}
      {status === "success" && <p className="text-green-400 mt-2 text-sm">Submitted successfully ✅</p>}

      <button
        onClick={() => {
          const formData = new FormData();
          if (playerFile) formData.append("playerFile", playerFile);
          if (requirementsFile) formData.append("requirementsFile", requirementsFile);
          onSubmit(formData);
        }}
        disabled={status === "submitting" || cooldownRemaining > 0}
        className={`mt-6 w-full py-2 border border-[#ff00cc] text-[#ff00cc] hover:bg-[#ff00cc] hover:text-black transition-all ${
          status === "submitting" || cooldownRemaining > 0 ? "opacity-50 cursor-not-allowed" : ""
        }`}
      >
        {status === "submitting"
          ? "Submitting..."
          : cooldownRemaining > 0
          ? `Wait ${cooldownRemaining}s`
          : "Submit Bot"}
      </button>
    </>
  );
};

export default FileUploadPanel;
