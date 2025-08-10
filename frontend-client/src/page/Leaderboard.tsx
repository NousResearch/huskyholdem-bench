import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { leaderboardAPI } from "../api";
import { Trophy, Filter, Trash2, Crown, Calendar, Tag, User } from "lucide-react";

interface LeaderboardEntry {
  id: string;
  username: string;
  score: number;
  tag: string | null;
  time_created: string;
}

interface ConfirmDeleteModal {
  isOpen: boolean;
  entry: LeaderboardEntry | null;
}

const LeaderboardPage: React.FC = () => {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModal, setDeleteModal] = useState<ConfirmDeleteModal>({ isOpen: false, entry: null });
  const [deleting, setDeleting] = useState(false);

  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, [selectedTag]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch top entries and tags in parallel
      const [entriesData, tagsData] = await Promise.all([
        leaderboardAPI.getTopN(100, selectedTag || undefined),
        leaderboardAPI.getAllTags()
      ]);

      setEntries(entriesData.top_entries || []);
      setTags(tagsData.tags || []);
    } catch (err) {
      console.error("Error fetching leaderboard data:", err);
      setError("Failed to load leaderboard data");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEntry = async () => {
    if (!deleteModal.entry) return;
    
    setDeleting(true);
    try {
      await leaderboardAPI.removeEntry(deleteModal.entry.id);
      setEntries(prev => prev.filter(entry => entry.id !== deleteModal.entry!.id));
      setDeleteModal({ isOpen: false, entry: null });
    } catch (err) {
      console.error("Error deleting entry:", err);
      setError("Failed to delete entry");
    } finally {
      setDeleting(false);
    }
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Crown className="h-6 w-6 text-yellow-400" />;
    if (rank === 2) return <Trophy className="h-6 w-6 text-gray-300" />;
    if (rank === 3) return <Trophy className="h-6 w-6 text-orange-400" />;
    return <span className="text-lg font-bold text-gray-400">#{rank}</span>;
  };

  const getScoreColor = (score: number) => {
    if (score > 0) return "text-green-400";
    if (score < 0) return "text-red-400";
    return "text-gray-300";
  };

  const handleUserClick = (username: string) => {
    navigate(`/profile/${username}`);
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-10 border-b border-[#444] pb-6">
        <h1 className="text-4xl font-bold mb-4 font-glitch flex items-center">
          <Trophy className="h-8 w-8 mr-3 text-[#ff00cc]" />
          Leaderboard
        </h1>
        <p className="text-gray-400">Compete for the top scores and climb the rankings</p>
      </div>

      {/* Tag Filter */}
      <div className="mb-8 bg-gray-900 border border-[#333] rounded-lg p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-[#39ff14]" />
            <span className="text-[#39ff14] font-semibold">Filter by Tag:</span>
          </div>
          <button
            onClick={() => setSelectedTag(null)}
            className={`px-3 py-1 rounded border transition-colors ${
              selectedTag === null
                ? "bg-[#ff00cc] text-black border-[#ff00cc]"
                : "border-[#444] text-gray-300 hover:border-[#ff00cc]"
            }`}
          >
            All
          </button>
          {tags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag)}
              className={`px-3 py-1 rounded border transition-colors ${
                selectedTag === tag
                  ? "bg-[#ff00cc] text-black border-[#ff00cc]"
                  : "border-[#444] text-gray-300 hover:border-[#ff00cc]"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-900/30 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">Loading leaderboard...</p>
        </div>
      ) : (
        /* Leaderboard Entries */
        <div className="space-y-4">
          {entries.length === 0 ? (
            <div className="text-center py-12 bg-gray-900 border border-[#333] rounded-lg">
              <Trophy className="h-16 w-16 mx-auto mb-4 text-gray-600" />
              <p className="text-gray-400 text-lg">No entries found</p>
              <p className="text-gray-500">
                {selectedTag ? `No entries found for tag "${selectedTag}"` : "Be the first to appear on the leaderboard!"}
              </p>
            </div>
          ) : (
            entries.map((entry, index) => {
              const rank = index + 1;
              const isCurrentUser = entry.username === user?.username;
              
              return (
                <div
                  key={entry.id}
                  className={`bg-gray-900 border rounded-lg p-4 transition-all hover:bg-gray-800 ${
                    isCurrentUser 
                      ? "border-[#ff00cc] bg-gray-900/80" 
                      : rank <= 3 
                        ? "border-[#39ff14]" 
                        : "border-[#333]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Rank */}
                      <div className="flex items-center justify-center w-12 h-12 bg-gray-800 rounded-full">
                        {getRankIcon(rank)}
                      </div>
                      
                      {/* User Info */}
                      <div>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-[#39ff14]" />
                          <button
                            onClick={() => handleUserClick(entry.username)}
                            className={`font-semibold cursor-pointer hover:underline transition-colors ${
                              isCurrentUser 
                                ? "text-[#ff00cc] hover:text-[#ff44cc]" 
                                : "text-white hover:text-[#39ff14]"
                            }`}
                          >
                            {entry.username}
                            {isCurrentUser && <span className="ml-2 text-xs">(You)</span>}
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-400">
                          {entry.tag && (
                            <div className="flex items-center gap-1">
                              <Tag className="h-3 w-3" />
                              <span>{entry.tag}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{new Date(entry.time_created).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Score and Actions */}
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className={`text-2xl font-bold font-mono ${getScoreColor(entry.score)}`}>
                          {entry.score}
                        </div>
                        <div className="text-xs text-gray-500">points</div>
                      </div>
                      
                      {/* Admin Delete Button */}
                      {user?.admin && (
                        <button
                          onClick={() => setDeleteModal({ isOpen: true, entry })}
                          className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded transition-colors"
                          title="Delete entry (Admin)"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModal.isOpen && deleteModal.entry && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-red-500 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-red-400 mb-4">Confirm Delete</h3>
            <p className="text-gray-300 mb-6">
              Are you sure you want to delete this leaderboard entry?
            </p>
            <div className="bg-gray-800 border border-[#333] rounded p-3 mb-6">
              <p><span className="text-[#39ff14]">User:</span> {deleteModal.entry.username}</p>
              <p><span className="text-[#39ff14]">Score:</span> {deleteModal.entry.score}</p>
              {deleteModal.entry.tag && (
                <p><span className="text-[#39ff14]">Tag:</span> {deleteModal.entry.tag}</p>
              )}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteModal({ isOpen: false, entry: null })}
                disabled={deleting}
                className="flex-1 py-2 border border-[#444] text-gray-300 hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteEntry}
                disabled={deleting}
                className="flex-1 py-2 bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeaderboardPage; 