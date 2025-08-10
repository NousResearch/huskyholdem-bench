import { ChevronDown, X, Zap, Users, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { submissionAPI, userAPI, gameAPI, adminAPI } from "../api";
import { useNavigate } from "react-router-dom";
import JobList from "../components/JobList";

const PAGE_SIZE = 10;  

const SimulationPage = () => {
  const navigate = useNavigate();  

  const [usersLoading, setUsersLoading] = useState<boolean>(true);
  const [userFinalMap, setUserFinalMap] = useState({});
  const [page, setPage] = useState(0);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [sortHasFinal, setSortHasFinal] = useState(false);
  const [numRounds, setNumRounds] = useState<number>(6);

  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [job2025Status, setJob2025Status] = useState<Record<string, boolean | undefined>>({});
  const [processing2025, setProcessing2025] = useState<Record<string, boolean>>({});
  const [removing2025, setRemoving2025] = useState<Record<string, boolean>>({});

  const [searchQuery, setSearchQuery] = useState("");

  const [blind, setBlind] = useState<number>(10);
  const [blindMultiplier, setBlindMultiplier] = useState<number>(1.0);
  const [blindIncreaseInterval, setBlindIncreaseInterval] = useState<number>(1);

  const fetchUsersSubStatus = async () => {
    setUsersLoading(true)
    try {
      // Fetch first page to get total pages
      const firstPage = await userAPI.getAllUsers(1, 25);
      let users = firstPage.users;
      const totalPages = firstPage.total_pages || 1;

      if (totalPages > 1) {
        // Fetch all remaining pages in parallel
        const pagePromises = [];
        for (let page = 2; page <= totalPages; page++) {
          pagePromises.push(userAPI.getAllUsers(page, 25));
        }
        const results = await Promise.all(pagePromises);
        for (const res of results) {
          users = users.concat(res.users);
        }
      }

      const finals = await submissionAPI.getUsersWithFinalSubmission();
      const finalsSet = new Set(finals.users_list || []);
      // Store user -> has_final
      const map: { [key: string]: boolean } = {};
      for (const user of users) {
        map[user.username] = finalsSet.has(user.username);
      }
      setUserFinalMap(map);
      setPage(0);
      setSelectedUsers([]);
      setSortHasFinal(false);
    } catch (err) {
      console.error("Error fetching user submission status:", err);
    } finally {
      setUsersLoading(false);
    }
  };

  const fetch2025Statuses = async (jobs: any[]) => {
    const statusMap: Record<string, boolean | undefined> = {};
    await Promise.all(jobs.map(async (job) => {
      try {
        const res = await adminAPI.get2025JobStatus(job.job_id);
        statusMap[job.job_id] = !!res.tournaments_2025_added;
      } catch {
        statusMap[job.job_id] = undefined;
      }
    }));
    setJob2025Status(statusMap);
  };

  const fetchJobs = async () => {
    try {
      const data = await adminAPI.listSimAdminJob();
      const convertedData = data.map((job: any) => ({
        job_id: job.id,
        job_status: job?.status,
        error: job?.error_message,
        result_data: job?.result_data,
        username: job?.username
      }));
      setJobs(convertedData);
      await fetch2025Statuses(convertedData);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setJobsLoading(false); 
    }
  };

  const runSimulation = async () => {
    try {
      await gameAPI.submitSimulationUserJob(
        selectedUsers,
        numRounds,
        blind,
        blindMultiplier,
        blindIncreaseInterval
      );
      setSelectedUsers([]);
      fetchJobs();
    } catch (err: any) {
      console.error(err);
    }
  };

  const deleteJob = async (jobId: string) => {
    try {
      await gameAPI.deleteJob(jobId);
      fetchJobs(); // Refresh the jobs list
    } catch (err: any) {
      console.error("Failed to delete job:", err);
      alert("Failed to delete job: " + (err.message || "Unknown error"));
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

  const process2025Job = async (job_id: string) => {
    setProcessing2025((prev) => ({ ...prev, [job_id]: true }));
    try {
      await adminAPI.processTournament2025Job(job_id);
      await fetch2025Statuses(jobs); // Refresh status
    } catch (err: any) {
      alert(err?.response?.data?.detail || err.message || "Failed to process job for 2025 leaderboard.");
    } finally {
      setProcessing2025((prev) => ({ ...prev, [job_id]: false }));
    }
  };

  const remove2025Job = async (job_id: string) => {
    setRemoving2025((prev) => ({ ...prev, [job_id]: true }));
    try {
      await adminAPI.deleteTournament2025Job(job_id);
      await fetch2025Statuses(jobs); // Refresh status
    } catch (err: any) {
      alert(err?.response?.data?.detail || err.message || "Failed to remove job from 2025 leaderboard.");
    } finally {
      setRemoving2025((prev) => ({ ...prev, [job_id]: false }));
    }
  };

  useEffect(() => {
    fetchUsersSubStatus();
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 15000);
    return () => clearInterval(interval);
  }, []);

  /* ---- pagination helpers ---- */
  const baseEntries = Object.entries(userFinalMap) as [string, boolean][];

  const filteredEntries = baseEntries.filter(([username]) =>
    username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const entries = sortHasFinal
    ? [...filteredEntries].sort((a, b) => (a[1] === b[1] ? 0 : a[1] ? -1 : 1))
    : filteredEntries;

  const pageCount = Math.ceil(entries.length / PAGE_SIZE);

  const pageRows = entries.slice(
    page * PAGE_SIZE,
    page * PAGE_SIZE + PAGE_SIZE
  );

  // Logic for the X button
  const removeUser = (username: string) =>
    setSelectedUsers(prev => prev.filter(u => u !== username));

  const next = () => setPage((p) => Math.min(p + 1, pageCount - 1));
  const prev = () => setPage((p) => Math.max(p - 1, 0));

  const toggle = (username: string, hasFinal: boolean) => {
    /**
     * Checkbox logic
     * - If there is no final sub disable toggle
     * - Only allow max 6 checkbox checked at a time
     */
    if (!hasFinal) return;
    setSelectedUsers(prev => {
      if (prev.includes(username)) return prev.filter(u => u !== username);
      if (prev.length >= 6) return prev;
      return [...prev, username];
    });
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-6xl mx-auto">
      {/* Header Section */}
      <div className="mb-8">
        <button
          onClick={() => navigate("/admin")}
          className="mb-6 text-sm px-4 py-2 border border-[#39ff14] text-[#39ff14] rounded hover:bg-[#39ff14] hover:text-black transition duration-200 flex items-center gap-2"
        >
          ← Back to Admin Dashboard
        </button>
        
        <div className="border-b border-[#444] pb-6">
          <h1 className="text-4xl font-bold mb-3 font-glitch text-[#ff00cc]">
            <Zap className="inline w-8 h-8 mr-3" />
            SIMULATION CONTROL CENTER
          </h1>
          <p className="text-lg text-gray-400">
            Manage tournament simulations and monitor job status in real-time
          </p>
        </div>
      </div>

      {/* Protocol Notice */}
      <div className="bg-black bg-opacity-30 border-l-4 border-[#ff00cc] pl-6 py-4 my-6 rounded-md">
        <p className="text-[#39ff14] font-bold mb-2">⚡ SIMULATION PROTOCOL ⚡</p>
        <p className="text-gray-300 text-sm mb-2">
          Welcome to the <span className="text-[#ff00cc] font-semibold">Tournament Simulation Arena</span>! 
          Select up to 6 users with final submissions to run competitive poker simulations. 
          Monitor job progress below and track results in real-time.
        </p>
        <p className="text-gray-400 text-xs">
          <span className="text-yellow-400">⚠️ SYSTEM REQUIREMENT:</span> Only users with final submissions can participate in simulations.
        </p>
      </div>

      {/* Users Selection Section */}
      <div className="bg-black bg-opacity-30 border-l-4 border-[#39ff14] p-6 my-8 rounded-lg">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Users className="w-6 h-6 text-[#39ff14]" />
            USER SELECTION MATRIX
          </h2>
          <button 
            onClick={fetchUsersSubStatus}
            className="text-sm border border-[#39ff14] text-[#39ff14] px-4 py-2 rounded hover:bg-[#39ff14] hover:text-black transition duration-200"
          >
            SYNC DATA
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left Column - User List */}
          <div className="xl:col-span-2">
            <h3 className="text-[#ff00cc] text-lg mb-4 font-semibold">REGISTERED PARTICIPANTS</h3>
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              {usersLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#39ff14]"></div>
                  <p className="text-gray-400 mt-2">Loading participants...</p>
                </div>
              ) : (
                <div className="text-sm text-white">
                  {/* Search */}
                  <div className="mb-4 flex items-center gap-2">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search by username"
                      className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:border-[#39ff14] focus:outline-none transition-colors"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery("")}
                        className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-500 transition"
                      >
                        Clear
                      </button>
                    )}
                  </div>
              
                  {/* Header */}
                  <div className="grid grid-cols-4 gap-4 font-semibold py-3 border-b-2 border-[#39ff14] text-[#39ff14]">
                    <div>SELECT</div>
                    <div>USERNAME</div>
                    <div className="flex items-center space-x-2">
                      <span>FINAL SUB</span>
                      <button onClick={() => setSortHasFinal(v => !v)}>
                        <ChevronDown
                          className={`w-4 h-4 transition-transform ${
                            sortHasFinal ? "rotate-180" : ""
                          }`}
                        />
                      </button>
                    </div>
                    <div>STATUS</div>
                  </div>
              
                  {/* Data rows */}
                  {entries.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No participants found.</p>
                  ) : (
                    <div className="max-h-96 overflow-y-auto">
                      {pageRows.map(([username, hasFinal]) => (
                        <div
                          key={username}
                          className={`grid grid-cols-4 gap-4 py-3 items-center border-b border-gray-700 hover:bg-gray-800 transition-colors ${
                            selectedUsers.includes(username) ? 'bg-gray-800 border-[#39ff14]' : ''
                          }`}
                        >
                          <div>
                            <input
                              type="checkbox"
                              checked={selectedUsers.includes(username)}
                              disabled={!hasFinal}
                              onChange={() => toggle(username, hasFinal)}
                              className={`w-4 h-4 ${!hasFinal ? "cursor-not-allowed opacity-40" : "cursor-pointer"}`}
                            />
                          </div>
                          <div className="font-mono">{username}</div>
                          <div className={hasFinal ? "text-[#39ff14]" : "text-red-400"}>
                            {hasFinal ? "✓ YES" : "✗ NO"}
                          </div>
                          <div className={selectedUsers.includes(username) ? "text-[#39ff14] font-bold" : "text-gray-400"}>
                            {selectedUsers.includes(username) ? "SELECTED" : "STANDBY"}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Pagination */}
                  {pageCount > 1 && (
                    <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-gray-700">
                      <button
                        onClick={prev}
                        disabled={page === 0}
                        className="px-4 py-2 border border-[#39ff14] text-[#39ff14] rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#39ff14] hover:text-black transition"
                      >
                        PREV
                      </button>
                      <span className="text-[#ff00cc] font-mono">
                        PAGE {page + 1} OF {pageCount}
                      </span>
                      <button
                        onClick={next}
                        disabled={page === pageCount - 1}
                        className="px-4 py-2 border border-[#39ff14] text-[#39ff14] rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#39ff14] hover:text-black transition"
                      >
                        NEXT
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Selected Users & Controls */}
          <div className="xl:col-span-1">
            <h3 className="text-[#ff00cc] text-lg mb-4 font-semibold">SIMULATION ROSTER</h3>
            <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
              <div className="text-center mb-4">
                <div className="text-3xl font-bold text-[#39ff14] mb-2">{selectedUsers.length}/6</div>
                <div className="text-sm text-gray-400">PARTICIPANTS SELECTED</div>
              </div>

              {selectedUsers.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No participants selected</p>
                </div>
              ) : (
                <div className="space-y-3 mb-6">
                  {selectedUsers.map((username, index) => (
                    <div key={username} className="flex items-center justify-between bg-gray-800 p-3 rounded border-l-2 border-[#39ff14]">
                      <div className="flex items-center gap-3">
                        <span className="text-[#39ff14] font-bold text-xs">#{index + 1}</span>
                        <span className="font-mono text-sm">{username}</span>
                      </div>
                      <button
                        onClick={() => removeUser(username)}
                        className="text-red-400 hover:text-red-300 transition"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  
                  <button
                    onClick={() => setSelectedUsers([])}
                    className="w-full text-sm text-red-400 hover:text-red-300 transition mt-4 py-2"
                  >
                    CLEAR ALL
                  </button>
                </div>
              )}

              {/* Number of Rounds Input */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-[#ff00cc] mb-2">
                  NUMBER OF ROUNDS
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={numRounds}
                  onChange={(e) => setNumRounds(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:border-[#39ff14] focus:outline-none transition-colors"
                  placeholder="Enter number of rounds"
                />
                <p className="text-xs text-gray-400 mt-1">Default: 6 rounds</p>
              </div>

              {/* Blind Input */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-[#ff00cc] mb-2">
                  INITIAL BLIND
                </label>
                <input
                  type="number"
                  min="1"
                  value={blind}
                  onChange={(e) => setBlind(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:border-[#39ff14] focus:outline-none transition-colors"
                  placeholder="Enter initial blind"
                />
                <p className="text-xs text-gray-400 mt-1">Default: 10</p>
              </div>

              {/* Blind Multiplier Input */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-[#ff00cc] mb-2">
                  BLIND MULTIPLIER
                </label>
                <input
                  type="number"
                  min="0.1"
                  step="0.01"
                  value={blindMultiplier}
                  onChange={(e) => setBlindMultiplier(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:border-[#39ff14] focus:outline-none transition-colors"
                  placeholder="Enter blind multiplier"
                />
                <p className="text-xs text-gray-400 mt-1">Default: 1.0</p>
              </div>

              {/* Blind Increase Interval Input */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-[#ff00cc] mb-2">
                  BLIND INCREASE INTERVAL
                </label>
                <input
                  type="number"
                  min="1"
                  value={blindIncreaseInterval}
                  onChange={(e) => setBlindIncreaseInterval(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:border-[#39ff14] focus:outline-none transition-colors"
                  placeholder="Enter blind increase interval"
                />
                <p className="text-xs text-gray-400 mt-1">Default: 1</p>
              </div>

              <button
                disabled={selectedUsers.length !== 6}
                className={`w-full py-4 px-6 rounded-lg font-bold text-lg transition-all duration-200 flex items-center justify-center gap-3 ${
                  selectedUsers.length === 6
                    ? "bg-[#39ff14] text-black hover:bg-[#2bff00] hover:shadow-lg hover:shadow-[#39ff14]/50"
                    : "bg-gray-700 text-gray-500 cursor-not-allowed"
                }`}
                onClick={runSimulation}
              >
                <Play className="w-5 h-5" />
                {selectedUsers.length === 6 ? "INITIATE SIMULATION" : "SELECT 6 PARTICIPANTS"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Jobs Status Section */}
      <JobList
        jobs={jobs}
        loading={jobsLoading}
        onRefresh={() => {
          setJobsLoading(true);
          fetchJobs();
        }}
        onDelete={deleteJob}
        onCopy={copyToClipboard}
        title="ACTIVE SIMULATION JOBS"
        showDeleteAction={true}
        job2025Status={job2025Status}
        onProcess2025={process2025Job}
        processing2025={processing2025}
        onRemove2025={remove2025Job}
        removing2025={removing2025}
      />
    </div>
  );
};

export default SimulationPage;