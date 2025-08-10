import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { userAPI } from "../api";
import { Search, User, Github, MessageCircle, Clock, ChevronLeft, ChevronRight } from "lucide-react";

interface UserSearchResult {
  username: string;
  name?: string | null;
  github?: string | null;
  discord_username?: string | null;
  about?: string | null;
}

interface PaginatedUsersResponse {
  message: string;
  users: UserSearchResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  status_code: number;
}

const DirectoryPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [allUsers, setAllUsers] = useState<UserSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const navigate = useNavigate();

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [pageSize] = useState(25);

  // Load all users with pagination
  const loadAllUsers = async (page: number = 1) => {
    setLoading(true);
    try {
      const response: PaginatedUsersResponse = await userAPI.getAllUsers(page, pageSize);
      setAllUsers(response.users);
      setCurrentPage(response.page);
      setTotalPages(response.total_pages);
      setTotalUsers(response.total);
    } catch (error) {
      console.error("Error loading users:", error);
      setAllUsers([]);
    } finally {
      setLoading(false);
    }
  };

  // Load initial users on component mount
  useEffect(() => {
    loadAllUsers(1);
  }, []);

  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setHasSearched(false);
      // Load all users when search is cleared
      loadAllUsers(1);
      return;
    }

    setLoading(true);
    try {
      const results = await userAPI.searchUsers(query);
      setSearchResults(results);
      setHasSearched(true);
    } catch (error) {
      console.error("Error searching users:", error);
      setSearchResults([]);
      setHasSearched(true);
    } finally {
      setLoading(false);
    }
  };

  // Debounced search effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      handleSearch(searchQuery);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
  };

  const handleUserClick = (username: string) => {
    navigate(`/profile/${username}`);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      loadAllUsers(newPage);
    }
  };

  const renderPaginationControls = () => {
    if (hasSearched || totalPages <= 1) return null;

    const pageNumbers = [];
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    // Adjust start page if we're near the end
    if (endPage - startPage < maxVisiblePages - 1) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pageNumbers.push(i);
    }

    return (
      <div className="flex items-center justify-center space-x-2 mt-6">
        <button
          onClick={() => handlePageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="flex items-center px-3 py-2 text-sm border border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:border-[#39ff14] hover:text-[#39ff14] transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Previous
        </button>

        {startPage > 1 && (
          <>
            <button
              onClick={() => handlePageChange(1)}
              className="px-3 py-2 text-sm border border-gray-600 rounded-lg hover:border-[#39ff14] hover:text-[#39ff14] transition-colors"
            >
              1
            </button>
            {startPage > 2 && <span className="text-gray-400">...</span>}
          </>
        )}

        {pageNumbers.map((pageNum) => (
          <button
            key={pageNum}
            onClick={() => handlePageChange(pageNum)}
            className={`px-3 py-2 text-sm border rounded-lg transition-colors ${
              pageNum === currentPage
                ? "border-[#ff00cc] bg-[#ff00cc] text-black font-semibold"
                : "border-gray-600 hover:border-[#39ff14] hover:text-[#39ff14]"
            }`}
          >
            {pageNum}
          </button>
        ))}

        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && <span className="text-gray-400">...</span>}
            <button
              onClick={() => handlePageChange(totalPages)}
              className="px-3 py-2 text-sm border border-gray-600 rounded-lg hover:border-[#39ff14] hover:text-[#39ff14] transition-colors"
            >
              {totalPages}
            </button>
          </>
        )}

        <button
          onClick={() => handlePageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="flex items-center px-3 py-2 text-sm border border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:border-[#39ff14] hover:text-[#39ff14] transition-colors"
        >
          Next
          <ChevronRight className="h-4 w-4 ml-1" />
        </button>
      </div>
    );
  };

  const renderUserList = (users: UserSearchResult[], isSearchResults: boolean = false) => {
    if (users.length === 0) {
      return (
        <div className="text-center text-gray-400 py-8">
          <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">{isSearchResults ? "No users found" : "No users available"}</p>
          <p className="text-sm">{isSearchResults ? "Try searching with different keywords" : "Check back later"}</p>
        </div>
      );
    }

    return (
      <div className="space-y-4 mt-4">
        {users.map((user) => (
          <div
            key={user.username}
            onClick={() => handleUserClick(user.username)}
            className="bg-white/5 border border-gray-700 rounded-lg p-4 cursor-pointer hover:border-[#ff00cc] hover:bg-white/10 transition-all duration-200 group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <h3 className="text-lg font-semibold text-white group-hover:text-[#ff00cc] transition-colors">
                    {user.name || user.username}
                  </h3>
                  {user.name && (
                    <span className="ml-2 text-sm text-gray-400">
                      @{user.username}
                    </span>
                  )}
                </div>
                
                {user.about && (
                  <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                    {user.about}
                  </p>
                )}
                
                <div className="flex items-center space-x-4 text-sm text-gray-400">
                  {user.github && (
                    <div className="flex items-center">
                      <Github className="h-4 w-4 mr-1" />
                      <span>{user.github}</span>
                    </div>
                  )}
                  {user.discord_username && (
                    <div className="flex items-center">
                      <MessageCircle className="h-4 w-4 mr-1" />
                      <span>{user.discord_username}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="text-[#ff00cc] text-sm font-medium">
                  View Profile →
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen text-white px-4 py-12 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10 border-b border-[#444] pb-6">
        <h1 className="text-3xl font-bold mb-2 font-glitch">
          User Directory —{" "}
          <span className="text-[#ff00cc]">Find Participants</span>
        </h1>
        <p className="text-gray-400">
          {hasSearched 
            ? "Search results for participants"
            : `Browse all ${totalUsers} registered participants`
          }
        </p>
      </div>

      {/* Search Input */}
      <div className="bg-white/5 backdrop-blur-sm border border-[#00ffff] rounded-lg p-6 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            placeholder="Search by name or username..."
            value={searchQuery}
            onChange={handleInputChange}
            className="w-full pl-10 pr-4 py-3 bg-white/10 text-white placeholder-gray-400 border border-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#00ffff] focus:border-transparent transition-all duration-200"
          />
        </div>
        {loading && (
          <div className="mt-4 text-center text-gray-400">
            <div className="inline-flex items-center">
              <Clock className="animate-spin h-4 w-4 mr-2" />
              {hasSearched ? "Searching..." : "Loading users..."}
            </div>
          </div>
        )}
      </div>

      {/* User List */}
      <div className="bg-white/5 backdrop-blur-sm border border-[#39ff14] rounded-lg p-6">
        <h2 className="text-xl font-bold text-[#39ff14] mb-4 flex items-center">
          <User className="h-5 w-5 mr-2" />
          {hasSearched ? "Search Results" : "All Users"}
          {(hasSearched ? searchResults : allUsers).length > 0 && (
            <span className="ml-2 text-sm bg-[#39ff14] text-black px-2 py-1 rounded">
              {hasSearched 
                ? `${searchResults.length} found`
                : `${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, totalUsers)} of ${totalUsers}`
              }
            </span>
          )}
        </h2>

        {renderUserList(hasSearched ? searchResults : allUsers, hasSearched)}
        {renderPaginationControls()}
      </div>

      {/* Instructions */}
      {!hasSearched && !loading && allUsers.length > 0 && (
        <div className="bg-white/5 backdrop-blur-sm border border-gray-600 rounded-lg p-6 mt-6">
          <h2 className="text-xl font-bold text-gray-300 mb-4">
            How to Use
          </h2>
          <div className="space-y-2 text-gray-400">
            <p>• Browse all users using pagination controls below</p>
            <p>• Use the search box to find specific users by name or username</p>
            <p>• Click on any user to view their profile</p>
            <p>• Clear the search to return to browsing all users</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default DirectoryPage; 