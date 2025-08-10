import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { gameAPI } from "../api";
import FileUploadPanel from "../components/FileUploadPanel";
import { Copy } from "lucide-react";

// Updated to use Pacific timezone (America/Los_Angeles)
// July dates use PDT (UTC-7) due to daylight saving time
const COMPETITION_START = new Date("2025-07-12T00:00:00-07:00");
const FINAL_DEADLINE = new Date("2025-07-21T23:59:59-07:00");

const Dashboard: React.FC = () => {
    // job
    const [jobs, setJobs] = useState<any[]>([]);
    const [jobsLoading, setJobsLoading] = useState(true);

    // cool down
    const [lastSubmittedAt, setLastSubmittedAt] = useState<number | null>(null);
    const [cooldownRemaining, setCooldownRemaining] = useState(0);

    useEffect(() => {
    const interval = setInterval(() => {
        if (lastSubmittedAt) {
        const now = Date.now();
        const secondsElapsed = Math.floor((now - lastSubmittedAt) / 1000);
        const remaining = Math.max(0, 30 - secondsElapsed);
        setCooldownRemaining(remaining);
        }
    }, 1000);

    return () => clearInterval(interval);
    }, [lastSubmittedAt]);

    const fetchJobs = async () => {
    try {
    const data = await gameAPI.get_jobs(); // ✅ use your API
    setJobs(data);
    } catch (err) {
    console.error("Failed to fetch jobs:", err);
    } finally {
    setJobsLoading(false);
    }
    };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here if desired
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
    }
  };

    useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 15000); // Refresh every 15s
    return () => clearInterval(interval);
    }, []);

  const { user } = useAuth();

  const [timeLeft, setTimeLeft] = useState<string>("");
  const [playerFile, setPlayerFile] = useState<File | null>(null);
  const [requirementsFile, setRequirementsFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date().getTime();
      
      // Check if competition hasn't started yet
      if (now < COMPETITION_START.getTime()) {
        setTimeLeft("Huskyholdem will officially start at July 12 2025");
        return;
      }
      
      // Competition has started, count down to final deadline
      const diff = FINAL_DEADLINE.getTime() - now;

      if (diff <= 0) {
        setTimeLeft("Submission closed.");
        clearInterval(interval);
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      setTimeLeft(`${days}d ${hours}h ${minutes}m ${seconds}s`);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const submitBot = async () => {
    if (cooldownRemaining > 0) {
        setError(`Please wait ${cooldownRemaining}s before submitting again.`);
        return;
    }

    if (!playerFile || !requirementsFile) {
        setError("Both player.py and requirements.txt must be provided.");
        return;
    }

    const formData = new FormData();
    formData.append("python_file", playerFile);
    formData.append("packages_file", requirementsFile);

    try {
        setStatus("submitting");
        setError(null);
        await gameAPI.submitSimulationJob(formData);
        setStatus("success");
        setPlayerFile(null);
        setRequirementsFile(null);
        setLastSubmittedAt(Date.now()); // 🆕 Start cooldown timer
        fetchJobs(); // 🆕 Refresh jobs after submit
    } catch (err) {
        console.error(err);
        setStatus("error");
        setError("Failed to upload submission. Error: " + (err as Error).message);
    }
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-3xl mx-auto">
      {/* Top: User & Countdown */}
      <div className="mb-10 border-b border-[#444] pb-6">
        <h1 className="text-3xl font-bold mb-2 font-glitch">
          Welcome, <span className="text-[#ff00cc]">{user?.username}</span>
        </h1>
        <p className="text-md text-gray-400">
          {timeLeft != "Huskyholdem will officially start at July 12 2025" && "Time left until final submission:"}
          <span className="text-[#39ff14] font-mono">{timeLeft}</span>
        </p>
      </div>

      <div className="bg-black bg-opacity-30 border-l-4 border-[#ff00cc] pl-4 py-3 my-4">
        <p className="text-[#39ff14] font-bold mb-1">🃏 TOURNAMENT PROTOCOL 🃏</p>
        <p className="text-gray-300 text-sm mb-2">
        ♠️ Welcome to the <span className="text-[#ff00cc] font-semibold">HuskyHoldem Tournament</span> Arena! Upload your poker bot below to face off in simulated games at our virtual table. 
        This phase (our first phase or the tournament - development) allows you to challenge the <span className="text-[#39ff14] font-mono">House Bot</span> to test your strategy before the main competition.
        Upon submission, you'll receive a unique <span className="text-yellow-300">Job ID</span> to track your bot's performance in real-time under the <strong>My Jobs</strong> section.
        </p>
        <p className="text-gray-400 text-xs mb-2">
            <span className="text-yellow-400">⚠️ HOUSE RULE #1:</span> Make sure your bot behaves! Submissions that crash, stall, or break the rules may be disqualified.
        </p>
        <p className="text-gray-400 text-xs">
        <span className="text-yellow-400">⚠️ HOUSE RULE #2:</span> This upload portal is for <span className="text-[#ffcc00] font-semibold">test runs only</span>. 
            For official entry into the tournament, submit your final bot through the dedicated submission page in the main menu. Stay tuned on the tournament dashboard for updates and deadlines.
        </p>
      </div>

      <FileUploadPanel
        playerFile={playerFile}
        setPlayerFile={setPlayerFile}
        requirementsFile={requirementsFile}
        setRequirementsFile={setRequirementsFile}
        error={error}
        status={status}
        setError={setError}
        setStatus={setStatus}
        onSubmit={submitBot}
        cooldownRemaining={cooldownRemaining}/>

{/* --- My Jobs --- */}
<div className="mt-12">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-xl font-bold border-b border-[#444] pb-2">My Jobs</h2>
    <button
      onClick={() => {
        setJobsLoading(true);
        fetchJobs();
      }}
      className="text-sm border border-[#39ff14] text-[#39ff14] hover:bg-[#39ff14] hover:text-black px-3 py-1 transition"
    >
      Refresh Jobs
    </button>
  </div>


  {jobsLoading ? (
    <p className="text-gray-400">Loading jobs...</p>
  ) : jobs.length === 0 ? (
    <p className="text-gray-500">No jobs submitted yet.</p>
  ) : (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed border-collapse text-sm">
        <thead>
          <tr className="text-left text-[#ff00cc] border-b border-[#333]">
            <th className="p-2 w-1/3">Job ID</th>
            <th className="p-2 w-1/6">Status</th>
            <th className="p-2 w-1/3">Result/Error</th>
            <th className="p-2 w-1/6">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const contentToShow = job.job_status === "Failed" 
              ? (job.error 
                  ? typeof job.error === 'object' 
                    ? JSON.stringify(job.error, null, 2) 
                    : job.error 
                  : "Unknown error")
              : (job.result_data 
                  ? typeof job.result_data === 'object' 
                    ? JSON.stringify(job.result_data, null, 2) 
                    : job.result_data 
                  : "-");
            
            return (
              <tr key={job.job_id} className="border-b border-[#222]">
                <td className="p-2 font-mono text-xs text-[#39ff14] break-all w-1/3">{job.job_id}</td>
                <td className="p-2 w-1/6">
                  <span
                    className={`px-2 py-1 rounded text-xs font-semibold ${
                      job.job_status === "Completed"
                        ? "text-green-400"
                        : job.job_status === "Pending"
                        ? "text-yellow-400"
                        : job.job_status === "Failed"
                        ? "text-red-500"
                        : "text-white"
                    }`}
                  >
                    {job.job_status}
                  </span>
                </td>
                <td className="p-2 w-1/3">
                  <div className="max-h-20 overflow-y-auto text-xs">
                    <pre className={`whitespace-pre-wrap font-mono ${
                      job.job_status === "Failed" ? "text-red-400" : "text-white"
                    }`}>
                      {contentToShow}
                    </pre>
                  </div>
                </td>
                <td className="p-2 w-1/6">
                  <button
                    onClick={() => copyToClipboard(contentToShow)}
                    className="text-[#39ff14] hover:text-[#2bff00] transition-colors p-1 rounded hover:bg-gray-700"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  )}
</div>

    </div>
  );
};

export default Dashboard;