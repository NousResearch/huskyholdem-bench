import React from 'react';
import { Copy, Trash2, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Job {
  job_id: string;
  job_status: string;
  error?: any;
  result_data?: any;
  username?: string;
}

interface JobListProps {
  jobs: Job[];
  loading: boolean;
  onRefresh: () => void;
  onDelete?: (jobId: string) => void;
  onCopy?: (text: string) => void;
  title?: string;
  showDeleteAction?: boolean;
  job2025Status?: Record<string, boolean | undefined>;
  onProcess2025?: (jobId: string) => void;
  processing2025?: Record<string, boolean>;
  onRemove2025?: (jobId: string) => void;
  removing2025?: Record<string, boolean>;
}

const JobList: React.FC<JobListProps> = ({
  jobs,
  loading,
  onRefresh,
  onDelete,
  onCopy,
  title = "ACTIVE SIMULATION JOBS",
  showDeleteAction = true,
  job2025Status = {},
  onProcess2025,
  processing2025 = {},
  onRemove2025,
  removing2025 = {},
}) => {
  const copyToClipboard = async (text: string) => {
    if (onCopy) {
      onCopy(text);
    } else {
      try {
        await navigator.clipboard.writeText(text);
      } catch (err) {
        console.error("Failed to copy to clipboard:", err);
      }
    }
  };

  const deleteJob = async (jobId: string) => {
    if (!onDelete) return;
    
    if (!confirm(`Are you sure you want to delete job ${jobId}? This action cannot be undone.`)) {
      return;
    }
    
    onDelete(jobId);
  };

  return (
    <div className="bg-black bg-opacity-30 border-l-4 border-[#ff00cc] p-6 my-8 rounded-lg">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <Zap className="w-6 h-6 text-[#ff00cc]" />
          {title}
        </h2>
        <button 
          onClick={onRefresh}
          className="text-sm border border-[#ff00cc] text-[#ff00cc] px-4 py-2 rounded hover:bg-[#ff00cc] hover:text-black transition duration-200"
        >
          REFRESH STATUS
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#ff00cc]"></div>
          <p className="text-gray-400 mt-2">Loading job status...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <Zap className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No simulation jobs found</p>
          <p className="text-gray-600 text-sm">Jobs will appear here when submitted</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full table-fixed border-collapse text-sm">
            <thead>
              <tr className="text-left text-[#ff00cc] border-b border-[#333]">
                <th className="p-2 w-1/4">Job ID</th>
                <th className="p-2 w-1/8">Status</th>
                <th className="p-2 w-1/8">User</th>
                <th className="p-2 w-1/3">Result/Error</th>
                <th className="p-2 w-1/8">2025 Leaderboard</th>
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
                const is2025 = job2025Status[job.job_id];
                const isProcessing = processing2025[job.job_id];
                const isRemoving = removing2025[job.job_id];
                return (
                  <tr key={job.job_id} className="border-b border-[#222]">
                    <td className="p-2 font-mono text-xs text-[#39ff14] break-all w-1/4">
                      <Link
                        to={`/games/${job.job_id}`}
                        className="underline underline-offset-2 hover:text-[#2bff00] transition-colors"
                        title="View game details"
                      >
                        {job.job_id}
                      </Link>
                    </td>
                    <td className="p-2 w-1/8">
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          job.job_status === "Finished" || job.job_status === "Completed"
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
                    <td className="p-2 w-1/8 text-[#39ff14] font-mono text-xs">
                      {job.username || 'N/A'}
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
                    <td className="p-2 w-1/8">
                      {is2025 === undefined ? (
                        <span className="text-gray-400">-</span>
                      ) : is2025 ? (
                        <button
                          className="px-2 py-1 text-xs border border-red-400 text-red-400 rounded hover:bg-red-400 hover:text-black transition disabled:opacity-50"
                          disabled={isRemoving || !onRemove2025}
                          onClick={() => onRemove2025 && onRemove2025(job.job_id)}
                        >
                          {isRemoving ? 'Removing...' : 'Remove from 2025'}
                        </button>
                      ) : (
                        <button
                          className="px-2 py-1 text-xs border border-[#ff00cc] text-[#ff00cc] rounded hover:bg-[#ff00cc] hover:text-black transition disabled:opacity-50"
                          disabled={isProcessing || !onProcess2025}
                          onClick={() => onProcess2025 && onProcess2025(job.job_id)}
                        >
                          {isProcessing ? 'Processing...' : 'Add to 2025'}
                        </button>
                      )}
                    </td>
                    <td className="p-2 w-1/6">
                      <div className="flex gap-2">
                        <button
                          onClick={() => copyToClipboard(contentToShow)}
                          className="text-[#39ff14] hover:text-[#2bff00] transition-colors p-1 rounded hover:bg-gray-700"
                          title="Copy to clipboard"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        {showDeleteAction && onDelete && (
                          <button
                            onClick={() => deleteJob(job.job_id)}
                            className="text-red-400 hover:text-red-300 transition-colors p-1 rounded hover:bg-red-900 hover:bg-opacity-20"
                            title="Delete job"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default JobList; 