import React, { useState } from 'react';
import { Shield, CheckCircle, ExternalLink, Users, Trash2, UserCheck } from 'lucide-react';

interface User {
  username: string;
  email: string;
  admin: boolean;
  is_verified: boolean;
}

interface UserListProps {
  users: User[];
  currentUser?: { username: string } | null;
  onToggleAdmin: (username: string) => void;
  onUserClick: (username: string) => void;
  onToggleVerification: (username: string) => void;
  onDeleteUser: (username: string) => void;
}

const UserList: React.FC<UserListProps> = ({
  users,
  currentUser,
  onToggleAdmin,
  onUserClick,
  onToggleVerification,
  onDeleteUser
}) => {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleDeleteClick = (username: string) => {
    setConfirmDelete(username);
  };

  const handleConfirmDelete = () => {
    if (confirmDelete) {
      onDeleteUser(confirmDelete);
      setConfirmDelete(null);
    }
  };

  const handleCancelDelete = () => {
    setConfirmDelete(null);
  };

  return (
    <div className="bg-black bg-opacity-30 border-l-4 border-[#00ffff] p-6 my-8 rounded-lg">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <Users className="w-6 h-6 text-[#00ffff]" />
          USER MANAGEMENT MATRIX
        </h2>
        <div className="text-sm text-gray-400">
          Total Users: <span className="text-[#00ffff] font-mono">{users.length}</span>
        </div>
      </div>

      <div className="h-96 overflow-y-auto">
        <div className="space-y-2">
          {users.map((u) => (
            <div
              key={u.username}
              className="bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-[#00ffff] transition-colors duration-200 flex items-center justify-between"
            >
              {/* Left side - User Info */}
              <div className="flex items-center gap-4 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-mono text-[#00ffff] font-bold text-lg">{u.username}</h3>
                  <button
                    onClick={() => onUserClick(u.username)}
                    className="text-gray-400 hover:text-[#00ffff] transition-colors"
                    title="View Profile"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="text-gray-400 text-sm">
                  {u.email}
                </div>
                
                {/* Status Tags */}
                <div className="flex gap-2">
                  {u.admin && (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-opacity-20 border border-[#ff00cc] text-[#ff00cc] text-xs rounded font-bold">
                      <Shield className="w-3 h-3" />
                      ADMIN
                    </span>
                  )}
                  {u.is_verified ? (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-opacity-20 border border-[#39ff14] text-[#39ff14] text-xs rounded font-bold">
                      <CheckCircle className="w-3 h-3" />
                      VERIFIED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-3 py-1 bg-opacity-20 border border-red-500 text-red-400 text-xs rounded font-bold">
                      UNVERIFIED
                    </span>
                  )}
                </div>
              </div>

              {/* Right side - Actions */}
              {u.username !== currentUser?.username && (
                <div className="flex gap-2">
                  <button
                    onClick={() => onToggleAdmin(u.username)}
                    className={`px-4 py-2 text-xs rounded border transition-colors duration-200 font-semibold ${
                      u.admin
                        ? 'border-red-500 text-red-400 hover:bg-red-500 hover:text-black'
                        : 'border-[#ffcc00] text-[#ffcc00] hover:bg-[#ffcc00] hover:text-black'
                    }`}
                  >
                    {u.admin ? 'REVOKE ADMIN' : 'GRANT ADMIN'}
                  </button>
                  
                  <button
                    onClick={() => onToggleVerification(u.username)}
                    className={`px-4 py-2 text-xs rounded border transition-colors duration-200 font-semibold flex items-center gap-1 ${
                      u.is_verified
                        ? 'border-orange-500 text-orange-400 hover:bg-orange-500 hover:text-black'
                        : 'border-[#39ff14] text-[#39ff14] hover:bg-[#39ff14] hover:text-black'
                    }`}
                  >
                    <UserCheck className="w-3 h-3" />
                    {u.is_verified ? 'UNVERIFY' : 'VERIFY'}
                  </button>
                  
                  <button
                    onClick={() => onUserClick(u.username)}
                    className="px-4 py-2 text-xs rounded border border-[#00ffff] text-[#00ffff] hover:bg-[#00ffff] hover:text-black transition-colors duration-200 font-semibold"
                  >
                    VIEW
                  </button>
                  
                  <button
                    onClick={() => handleDeleteClick(u.username)}
                    className="px-4 py-2 text-xs rounded border border-red-500 text-red-400 hover:bg-red-500 hover:text-black transition-colors duration-200 font-semibold flex items-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    DELETE
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {users.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No users found</p>
        </div>
      )}

      {/* Confirmation Dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-red-500 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <Trash2 className="w-6 h-6 text-red-500" />
              <h3 className="text-xl font-bold text-white">Confirm User Deletion</h3>
            </div>
            
            <p className="text-gray-300 mb-6">
              Are you sure you want to permanently delete user{' '}
              <span className="font-mono text-[#ff00cc]">{confirmDelete}</span>?
            </p>
            
            <div className="bg-red-900 bg-opacity-20 border border-red-500 rounded-lg p-4 mb-6">
              <p className="text-red-400 text-sm font-semibold">
                ⚠️ WARNING: This action cannot be undone!
              </p>
              <p className="text-red-300 text-sm mt-2">
                This will permanently remove the user and all associated data from the system.
              </p>
            </div>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancelDelete}
                className="px-4 py-2 border border-gray-500 text-gray-400 rounded hover:bg-gray-500 hover:text-black transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors font-semibold"
              >
                Delete User
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserList; 