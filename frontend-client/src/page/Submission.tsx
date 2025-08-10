import { useEffect, useState } from "react";
import { submissionAPI } from "../api";
import { useAuth } from "../context/AuthContext";
import FileUploadPanel from "../components/FileUploadPanel";
import { ChevronDown, ChevronUp, Loader, FileText, Package, Star, XCircle, Download } from "lucide-react";

interface Submission {
  id: string;
  player_file: string;
  package_file: string;
  final: boolean;
  created_at: string;
}

const SubmissionPage = () => {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [playerFile, setPlayerFile] = useState<File | null>(null);
  const [requirementsFile, setRequirementsFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);
  const [expandedSubmission, setExpandedSubmission] = useState<string | null>(null);
  const [fileContents, setFileContents] = useState({ player: null, requirements: null });
  const [loadingContents, setLoadingContents] = useState(false);

  const { user } = useAuth();

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const data = await submissionAPI.listSubmissions();
      setSubmissions(data.files);
    } catch (err) {
      console.error("Failed to fetch submissions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
    setCooldownRemaining(0); // Reset cooldown on mount
  }, []);

  const handleSubmit = async () => {
    if (!playerFile || !requirementsFile) {
      setError("Both player.py and requirements.txt must be selected.");
      return;
    }

    const formData = new FormData();
    formData.append("python_file", playerFile);
    formData.append("packages_file", requirementsFile);

    try {
      setStatus("submitting");
      await submissionAPI.uploadSubmission(formData);
      setStatus("success");
      setPlayerFile(null);
      setRequirementsFile(null);
      setError(null);
      fetchSubmissions();
    } catch (err) {
      console.error(err);
      setStatus("error");
      setError("Failed to upload submission. Error: " + (err as Error).message);
    }
  };

  const handleMarkFinal = async (id: string) => {
    try {
      const res = await submissionAPI.mark_submission(id);
      if (res.status_code !== 200) {
        console.error("Failed to mark as final:", res);
      }
      fetchSubmissions();
    } catch (err) {
      console.error("Error marking submission as final:", err);
    }
  };

  const handleUnmarkFinal = async (id: string) => {
    try {
      await submissionAPI.unmark_submission(id);
      fetchSubmissions();
    } catch (err) {
      console.error("Error unmarking submission as final:", err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await submissionAPI.delete_submission(id);
      if (expandedSubmission === id) {
        setExpandedSubmission(null);
        setFileContents({ player: null, requirements: null });
      }
      fetchSubmissions();
    } catch (err) {
      console.error("Error deleting submission:", err);
    }
  };

  const toggleSubmission = async (id: string) => {
    if (expandedSubmission === id) {
      setExpandedSubmission(null);
      setFileContents({ player: null, requirements: null });
      return;
    }
    
    setExpandedSubmission(id);
    setLoadingContents(true);
    
    try {
      const submission = await submissionAPI.getSubmission(id);
      
      const [playerContent, requirementsContent] = await Promise.all([
        submissionAPI.getContentFile(submission.player_file),
        submissionAPI.getContentFile(submission.package_file)
      ]);
      
      setFileContents({
        player: playerContent.file_data,
        requirements: requirementsContent.file_data
      });
    } catch (err) {
      console.error("Failed to fetch file contents:", err);
      setError("Failed to fetch file contents");
    } finally {
      setLoadingContents(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-3xl mx-auto">
      <div className="mb-10 border-b border-[#444] pb-6">
        <h1 className="text-3xl font-bold mb-2 font-glitch">
          Submissions — <span className="text-[#ff00cc]">{user?.username}</span>
        </h1>
      </div>

      <div className="bg-black bg-opacity-30 border-l-4 border-[#ff00cc] pl-4 py-3 my-4">
        <p className="text-[#39ff14] font-bold mb-1">🃏 TOURNAMENT PROTOCOL 🃏</p>
        <p className="text-gray-300 text-sm mb-2">
            Your submissions will be used by <span className="text-[#ff00cc]">HuskyHoldem Admin</span> to determine your fate in the final tournament. 
            Remember to <span className="text-[#39ff14] font-semibold">mark your best submission as final</span> before the deadline!
        </p>
        <p className="text-gray-400 text-xs">
            <span className="text-yellow-400">⚠️ HOUSE RULES:</span> Maximum of 5 submissions allowed in your hand. To upload more, fold (delete) the ones you don't need.
        </p>
      </div>

      <FileUploadPanel
        playerFile={playerFile}
        requirementsFile={requirementsFile}
        setPlayerFile={setPlayerFile}
        setRequirementsFile={setRequirementsFile}
        error={error}
        status={status}
        setError={setError}
        setStatus={setStatus}
        onSubmit={handleSubmit}
        cooldownRemaining={cooldownRemaining}
      />

      {/* Submission List */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold mb-4 border-b border-gray-700 pb-3 flex items-center">
          <Package className="mr-2 text-[#39ff14]" />
          Your Submissions
        </h2>
        </div>
        
        {loading ? (
          <p className="text-gray-400">Loading submissions...</p>
        ) : submissions.length === 0 ? (
          <p className="text-gray-500">No submissions yet. Upload your first submission above.</p>
        ) : (
          <div className="space-y-2">
            {submissions.map((sub: Submission) => (
              <div key={sub.id} className="border-b border-[#222] overflow-hidden">
                <div 
                  onClick={() => toggleSubmission(sub.id)}
                  className="p-3 flex justify-between items-center cursor-pointer hover:bg-gray-900 transition duration-200"
                >
                  <div className="flex items-center space-x-3">
                    {sub.final && (
                      <span className="px-2 py-1 rounded text-xs font-semibold text-green-400">
                        <Star className="h-4 w-4 inline mr-1" /> Final
                      </span>
                    )}
                    <div className="font-mono text-xs text-[#39ff14] break-all">{sub.id}</div>
                    <div className="text-gray-400 text-sm">{formatDate(sub.created_at || new Date().toISOString())}</div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="flex space-x-2">
                      {sub.final ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleUnmarkFinal(sub.id); }}
                          className="text-yellow-400 hover:underline flex items-center text-sm"
                        >
                          <XCircle className="h-4 w-4 mr-1" /> Unmark
                        </button>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleMarkFinal(sub.id); }}
                          className="text-cyan-400 hover:underline flex items-center text-sm"
                        >
                        <Star className="h-4 w-4 mr-1" /> Mark Final
                        </button>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(sub.id); }}
                        className="text-red-500 hover:underline flex items-center text-sm"
                      >
                        Delete
                      </button>
                    </div>
                    {expandedSubmission === sub.id ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </div>
                </div>
                
                {expandedSubmission === sub.id && (
                  <div className="border-t border-gray-700 p-4">
                    {loadingContents ? (
                      <div className="flex justify-center items-center py-8">
                        <Loader className="h-6 w-6 text-[#ff00cc] animate-spin" />
                        <span className="ml-3 text-gray-400">Loading file contents...</span>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="bg-gray-900 rounded border border-[#39ff14] p-4">
                          <div className="flex justify-between items-center mb-2">
                            <h3 className="text-[#39ff14] font-medium flex items-center">
                              <FileText className="h-4 w-4 mr-2" /> player.py
                            </h3>
                            <a
                              href={`https://api.atcuw.org/submission/file/${sub.player_file}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-cyan-300 hover:text-cyan-500 transition"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Download className="h-4 w-4" />
                            </a>
                          </div>
                          <pre className="bg-gray-950 p-3 rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto">
                            {fileContents.player}
                          </pre>
                        </div>
                        
                        <div className="bg-gray-900 rounded border border-purple-700 p-4">
                          <div className="flex justify-between items-center mb-2">
                            <h3 className="text-purple-400 font-medium flex items-center">
                              <Package className="h-4 w-4 mr-2" /> requirements.txt
                            </h3>
                            <a
                              href={`https://api.atcuw.org/submission/file/${sub.package_file}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-purple-300 hover:text-purple-500 transition"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Download className="h-4 w-4" />
                            </a>
                          </div>
                          <pre className="bg-gray-950 p-3 rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto">
                            {fileContents.requirements}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SubmissionPage;