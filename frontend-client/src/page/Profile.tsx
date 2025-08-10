import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useParams } from "react-router-dom";
import { profileAPI, submissionAPI, adminAPI } from "../api";
import { Trophy, TrendingUp, Clock, User, Award, ChevronDown, ChevronUp, Loader, FileText, Package, Download } from "lucide-react";

interface LeaderboardEntry {
  username: string;
  score: number;
  tag: string;
  time_created: string;
}

interface Profile {
  username: string;
  email?: string | null;
  name?: string | null;
  github?: string | null;
  discord_username?: string | null;
  about?: string | null;
  admin?: boolean;
}

interface ProfileApiResponse {
  profile: Profile;
  leaderboard_entries: LeaderboardEntry[];
}

interface FinalSubmission {
  username: string;
  has_final_submission: boolean;
  submission_id?: string;
  player_file?: string;
  package_file?: string;
  created_at?: string;
  message: string;
}

const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [leaderboardEntries, setLeaderboardEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [finalSubmission, setFinalSubmission] = useState<FinalSubmission | null>(null);
  const [expandedSubmission, setExpandedSubmission] = useState<boolean>(false);
  const [fileContents, setFileContents] = useState({ player: null, requirements: null });
  const [loadingContents, setLoadingContents] = useState(false);

  const { user } = useAuth();
  const { username } = useParams(); 

  const isSelf = !username || username === user?.username;
  console.log(username);
    

  useEffect(() => {
    const fetchData = async () => {
        if (!user) return;
        setLoading(true);

        try {
            if (!username || username === user.username) {
                const data: ProfileApiResponse = await profileAPI.getProfileSelf();
                setProfile(data.profile);
                setLeaderboardEntries(data.leaderboard_entries || []);
            } else {                
                const data: ProfileApiResponse = await profileAPI.getProfilePublic(username);
                setProfile(data.profile);
                setLeaderboardEntries(data.leaderboard_entries || []);
            }

            // Fetch final submission if user is admin and viewing another user's profile
            if (user.admin && username) {
                try {
                    const finalSubData = await adminAPI.getUserFinalSubmission(username);
                    setFinalSubmission(finalSubData);
                } catch (err) {
                    console.error("Error fetching final submission:", err);
                }
            }
        } catch (err) {
            console.error("Error fetching profile data:", err);
        } finally {
            setLoading(false);
        }
    };

    fetchData();
  }, [user, username]);

  useEffect(() => {
    if (profile) {
        setFormData({
            name: profile.name || "",
            github: profile.github || "",
            discord_username: profile.discord_username || "",
            about: profile.about || ""
        });
    }
    }, [profile]);


    const getScoreStats = () => {
    if (leaderboardEntries.length === 0) {
      return {
        totalSubmissions: 0,
        bestScore: 0,
        latestScore: 0,
        latestDate: "N/A",
      };
    }

    const sortedByScore = [...leaderboardEntries].sort((a, b) => b.score - a.score);
    const sortedByDate = [...leaderboardEntries].sort((a, b) => 
      new Date(b.time_created).getTime() - new Date(a.time_created).getTime()
    );

    return {
      totalSubmissions: leaderboardEntries.length,
      bestScore: sortedByScore[0]?.score || 0,
      latestScore: sortedByDate[0]?.score || 0,
      latestDate: sortedByDate[0] ? new Date(sortedByDate[0].time_created).toLocaleString() : "N/A",
    };
  };

  const stats = getScoreStats();

  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: profile?.name || "",
    github: profile?.github || "",
    discord_username: profile?.discord_username || "",
    about: profile?.about || ""
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    try {
        await profileAPI.updateProfile(formData);
        setProfile({ ...profile!, ...formData }); // Update local state
        setEditMode(false);
    } catch (err) {
        console.error("Error updating profile:", err);
    }
  };

  const toggleSubmission = async () => {
    if (expandedSubmission) {
      setExpandedSubmission(false);
      setFileContents({ player: null, requirements: null });
      return;
    }
    
    if (!finalSubmission?.has_final_submission) return;
    
    setExpandedSubmission(true);
    setLoadingContents(true);
    
    try {
      const [playerContent, requirementsContent] = await Promise.all([
        submissionAPI.getContentFile(finalSubmission.player_file!),
        submissionAPI.getContentFile(finalSubmission.package_file!)
      ]);
      
      setFileContents({
        player: playerContent.file_data,
        requirements: requirementsContent.file_data
      });
    } catch (err) {
      console.error("Failed to fetch file contents:", err);
    } finally {
      setLoadingContents(false);
    }
  };


  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-4xl mx-auto">
      <div className="mb-10 border-b border-[#444] pb-6">
        <h1 className="text-3xl font-bold mb-2 font-glitch">
          Profile —{" "}
          <span className="text-[#ff00cc]">
            {isSelf ? "You" : profile?.username}
          </span>
          {profile?.admin && (
            <span className="ml-2 text-sm bg-yellow-500 text-black px-2 py-1 rounded">
              ADMIN
            </span>
          )}
        </h1>
      </div>
  
      {loading ? (
        <p className="text-gray-400">Loading profile...</p>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
            {/* Profile Info */}
            <div className="bg-gray-900 border border-[#ff00cc] rounded-lg p-6">
                <h2 className="text-xl font-bold text-[#ff00cc] flex items-center mb-4">
                    <User className="h-5 w-5 mr-2" />
                    Profile Info
                    {isSelf && (
                        <button
                            className="ml-auto px-3 py-1 border-[#39ff14] border-2 text-[#39ff14] text-sm font-medium rounded hover:bg-[#39ff14] hover:text-black transition-colors duration-200"
                            onClick={() => setEditMode(!editMode)}
                        >
                            {editMode ? "Cancel" : "Edit"}
                        </button>
                    )}
                </h2>

                {editMode ? (
                    <div className="bg-white/5 backdrop-blur-md rounded-xl border border-white/10 shadow-lg p-6 mt-4">
                        <form
                            className="space-y-4"
                            onSubmit={e => { e.preventDefault(); handleSubmit(); }}
                        >
                            <div>
                                <label className="block text-sm font-medium mb-1" htmlFor="name">Name</label>
                                <input
                                    id="name"
                                    name="name"
                                    className="w-full px-4 py-2 bg-white/10 text-white placeholder-gray-400 border border-white/10 focus:outline-none focus:ring-2 focus:ring-[#ff00cc]"
                                    value={formData.name}
                                    onChange={handleChange}
                                    placeholder="Your full name"
                                    autoComplete="off"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1" htmlFor="github">GitHub</label>
                                <input
                                    id="github"
                                    name="github"
                                    className="w-full px-4 py-2 bg-white/10 text-white placeholder-gray-400 border border-white/10 focus:outline-none focus:ring-2 focus:ring-[#ff00cc]"
                                    value={formData.github}
                                    onChange={handleChange}
                                    placeholder="Your GitHub username"
                                    autoComplete="off"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1" htmlFor="discord_username">Discord</label>
                                <input
                                    id="discord_username"
                                    name="discord_username"
                                    className="w-full px-4 py-2 bg-white/10 text-white placeholder-gray-400 border border-white/10 focus:outline-none focus:ring-2 focus:ring-[#ff00cc]"
                                    value={formData.discord_username}
                                    onChange={handleChange}
                                    placeholder="Your Discord username"
                                    autoComplete="off"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1" htmlFor="about">About Me</label>
                                <textarea
                                    id="about"
                                    name="about"
                                    rows={4}
                                    className="w-full px-4 py-2 bg-white/10 text-white placeholder-gray-400 border border-white/10 focus:outline-none focus:ring-2 focus:ring-[#ff00cc] resize-none"
                                    value={formData.about}
                                    onChange={handleChange}
                                    placeholder="Tell us about yourself..."
                                />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button
                                    type="submit"
                                    className="px-6 py-2 border border-[#39ff14] text-[#39ff14] hover:bg-[#39ff14] hover:text-black transition-colors duration-200"
                                >
                                    Save Changes
                                </button>
                                <button
                                    type="button"
                                    className="px-6 py-2 border border-gray-400 text-gray-400 hover:bg-gray-400 hover:text-black transition-colors duration-200"
                                    onClick={() => setEditMode(false)}
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                ) : (
                    <>
                        <p>
                            <span className="text-[#39ff14]">Username:</span>{" "}
                            {profile?.username || "N/A"}
                        </p>
                        <p>
                            <span className="text-[#39ff14]">Name:</span>{" "}
                            {profile?.name || "N/A"}
                        </p>
                        <p>
                            <span className="text-[#39ff14]">GitHub:</span>{" "}
                            {profile?.github || "N/A"}
                        </p>
                        <p>
                            <span className="text-[#39ff14]">Discord:</span>{" "}
                            {profile?.discord_username || "N/A"}
                        </p>
                        <div className="mt-4">
                            <p className="text-[#39ff14] font-semibold">About Me:</p>
                            <p className="text-sm text-gray-300 bg-gray-800 p-3 rounded mt-2">
                                {profile?.about || "This user hasn't written anything yet."}
                            </p>
                        </div>
                    </>
                )}
            </div>

          {/* Score Stats */}
          <div className="bg-gray-900 border border-[#39ff14] rounded-lg p-6">
            <h2 className="text-xl font-bold text-[#39ff14] mb-4 flex items-center">
              <Trophy className="h-5 w-5 mr-2" />
              Performance Stats
            </h2>
            <p className="flex items-center mb-2">
              <Award className="h-5 w-5 mr-2 text-yellow-300" />
              Total submissions:
              <span className="ml-2 font-mono">{stats.totalSubmissions}</span>
            </p>
            <p className="flex items-center mb-2">
              <TrendingUp className="h-5 w-5 mr-2 text-green-400" />
              Best score:
              <span className="ml-2 font-mono">{stats.bestScore}</span>
            </p>
            <p className="flex items-center mb-2">
              <Trophy className="h-5 w-5 mr-2 text-blue-400" />
              Latest score:
              <span className="ml-2 font-mono">{stats.latestScore}</span>
            </p>
            <p className="flex items-center">
              <Clock className="h-5 w-5 mr-2 text-cyan-400" />
              Last submission:
              <span className="ml-2 font-mono text-xs">{stats.latestDate}</span>
            </p>
          </div>

          {/* Recent Scores - Show for both self and public profiles */}
          {leaderboardEntries.length > 0 && (
            <div className="bg-gray-900 border border-[#00ffff] rounded-lg p-6 md:col-span-2">
              <h2 className="text-xl font-bold text-[#00ffff] mb-4 flex items-center">
                <TrendingUp className="h-5 w-5 mr-2" />
                Recent Scores
              </h2>
              <div className="space-y-2 mt-8">
                {leaderboardEntries
                  .sort((a, b) => new Date(b.time_created).getTime() - new Date(a.time_created).getTime())
                  .map((entry, index) => (
                    <div 
                      key={`${entry.time_created}-${index}`}
                      className="flex justify-between items-center bg-gray-800 p-3 rounded border-l-4 border-[#00ffff]"
                    >
                      <div>
                        <span className="font-mono text-lg">
                          Score: {entry.score}
                        </span>
                        <span className="text-xs text-gray-400 ml-2">
                          ({entry.tag})
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {new Date(entry.time_created).toLocaleString()}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Final Submission - Show for admin viewing other users */}
          {user?.admin && finalSubmission && (
            <div className="bg-gray-900 border border-[#ff00cc] rounded-lg p-6 md:col-span-2">
              <div 
                onClick={toggleSubmission}
                className="flex justify-between items-center cursor-pointer hover:bg-gray-800 transition duration-200"
              >
                <h2 className="text-xl font-bold text-[#ff00cc] flex items-center">
                  <Package className="h-5 w-5 mr-2" />
                  Final Submission
                  {finalSubmission.has_final_submission && (
                    <span className="ml-2 text-sm bg-green-500 text-black px-2 py-1 rounded">
                      ✓ Available
                    </span>
                  )}
                </h2>
                {finalSubmission.has_final_submission && (
                  expandedSubmission ? (
                    <ChevronUp className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  )
                )}
              </div>
              
              {!finalSubmission.has_final_submission && (
                <p className="text-gray-400 mt-2">{finalSubmission.message}</p>
              )}

              {finalSubmission.has_final_submission && (
                <div className="mt-4">
                  <p className="text-gray-300 text-sm">
                    Submission ID: <span className="font-mono text-[#39ff14]">{finalSubmission.submission_id}</span>
                  </p>
                  <p className="text-gray-300 text-sm">
                    Created: <span className="font-mono text-[#39ff14]">
                      {finalSubmission.created_at ? new Date(finalSubmission.created_at).toLocaleString() : 'N/A'}
                    </span>
                  </p>
                </div>
              )}
              
              {expandedSubmission && finalSubmission.has_final_submission && (
                <div className="border-t border-gray-700 mt-4 pt-4">
                  {loadingContents ? (
                    <div className="flex justify-center items-center py-8">
                      <Loader className="h-6 w-6 text-[#ff00cc] animate-spin" />
                      <span className="ml-3 text-gray-400">Loading file contents...</span>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <div className="bg-gray-800 rounded border border-[#39ff14] p-4">
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="text-[#39ff14] font-medium flex items-center">
                            <FileText className="h-4 w-4 mr-2" /> player.py
                          </h3>
                          <a
                            href={`https://api.atcuw.org/submission/file/${finalSubmission.player_file}`}
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
                      
                      <div className="bg-gray-800 rounded border border-purple-700 p-4">
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="text-purple-400 font-medium flex items-center">
                            <Package className="h-4 w-4 mr-2" /> requirements.txt
                          </h3>
                          <a
                            href={`https://api.atcuw.org/submission/file/${finalSubmission.package_file}`}
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
          )}
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
