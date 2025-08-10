import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { adminAPI, gameAPI } from '../api';
import JobList from '../components/JobList';
import UserList from '../components/UserList';

const Admin: React.FC = () => {
    const {user} = useAuth();
    const navigate = useNavigate();

    const [userCount, setUserCount] = useState<number | null>(null);
    const [jobCount, setJobCount] = useState<number | null>(null);
    const [submissionCount, setSubmissionCount] = useState<number | null>(null);
    const [verifiedUserCount, setVerifiedUserCount] = useState<number | null>(null);
    const [users, setUsers] = useState<any[]>([]);
    const [jobs, setJobs] = useState<any[]>([]);
    const [jobsLoading, setJobsLoading] = useState(true);

    const fetchJobs = async () => {
        try {
            const data = await adminAPI.listJobs();
            const convertedData = data.map((job: any) => ({
                job_id: job.id,
                job_status: job?.status,
                error: job?.error_message,
                result_data: job?.result_data,
                username: job?.username
            }));
            setJobs(convertedData);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        } finally {
            setJobsLoading(false);
        }
    };

    const handleDeleteJob = async (jobId: string) => {
        try {
            await gameAPI.deleteJob(jobId);
            fetchJobs(); // Refresh the jobs list
        } catch (err: any) {
            console.error("Failed to delete job:", err);
            alert("Failed to delete job: " + (err.message || "Unknown error"));
        }
    };

    const handleCopyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            // You could add a toast notification here if desired
        } catch (err) {
            console.error("Failed to copy to clipboard:", err);
        }
    };

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const [usersCount, jobsCount, submissionsCount, userList] = await Promise.all([
                    adminAPI.getUserCount(),
                    adminAPI.getJobCount(),
                    adminAPI.getSubmissionCount(),
                    adminAPI.listUsers()
                ]);
                setUserCount(usersCount);
                setJobCount(jobsCount);
                setSubmissionCount(submissionsCount);
                setUsers(userList);
                
                // Calculate verified users count
                const verifiedCount = userList.filter((u: any) => u.is_verified).length;
                setVerifiedUserCount(verifiedCount);
            } catch (err) {
                console.error('Failed to load admin stats', err);
            }
        };
        fetchStats();
    }, []);

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const handleToggleAdmin = async (username: string) => {
        try {
            const updated = await adminAPI.toggleAdmin(username);
            setUsers(prev => prev.map(u => u.username === username ? {...u, admin: updated.admin} : u));
        } catch (err) {
            console.error('Failed to toggle admin status', err);
        }
    };

    const handleToggleVerification = async (username: string) => {
        try {
            const updated = await adminAPI.verifyUser(username);
            setUsers(prev => {
                const updatedUsers = prev.map(u => u.username === username ? {...u, is_verified: updated.is_verified} : u);
                // Update verified user count
                const verifiedCount = updatedUsers.filter(u => u.is_verified).length;
                setVerifiedUserCount(verifiedCount);
                return updatedUsers;
            });
        } catch (err) {
            console.error('Failed to toggle verification status', err);
            alert('Failed to update verification status: ' + (err as Error).message);
        }
    };

    const handleDeleteUser = async (username: string) => {
        try {
            await adminAPI.deleteUser(username);
            setUsers(prev => {
                const updatedUsers = prev.filter(u => u.username !== username);
                // Update verified user count
                const verifiedCount = updatedUsers.filter(u => u.is_verified).length;
                setVerifiedUserCount(verifiedCount);
                return updatedUsers;
            });
            
            // Update total user count
            setUserCount(prev => prev !== null ? prev - 1 : null);
        } catch (err) {
            console.error('Failed to delete user', err);
            alert('Failed to delete user: ' + (err as Error).message);
        }
    };

    const handleUserClick = (username: string) => {
        navigate(`/profile/${username}`);
    };

    return (
        <div className="text-white p-8">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
                    <p className="text-gray-400">Welcome back, {user?.username}!</p>
                </div>

                <div className="flex flex-row space-x-4 mb-8">
                    <button
                        onClick={() => navigate('/simulation')}
                        className="w-fit px-6 py-2 bg-[#39ff14] text-black rounded hover:bg-[#2ecc71] transition-colors"
                    >
                        Go to Simulation Page
                    </button>
                    <button
                        onClick={() => navigate('/container-manager')}
                        className="w-fit px-6 py-2 bg-[#39ff14] text-black rounded hover:bg-[#2ecc71] transition-colors"
                    >
                        Go to Container Manager
                    </button>
                    <button
                        onClick={() => navigate('/admin/games')}
                        className="w-fit px-6 py-2 bg-[#39ff14] text-black rounded hover:bg-[#2ecc71] transition-colors"
                    >
                        Go to Admin Game Page
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div className="bg-gray-900 border border-[#ff00cc] p-6 rounded-lg">
                        <h2 className="text-xl font-bold text-[#ff00cc] mb-2">Total Users</h2>
                        <p className="text-3xl font-mono">{userCount !== null ? userCount : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-[#39ff14] p-6 rounded-lg">
                        <h2 className="text-xl font-bold text-[#39ff14] mb-2">Verified Users</h2>
                        <p className="text-3xl font-mono">{verifiedUserCount !== null ? verifiedUserCount : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-[#ffcc00] p-6 rounded-lg">
                        <h2 className="text-xl font-bold text-[#ffcc00] mb-2">Jobs</h2>
                        <p className="text-3xl font-mono">{jobCount !== null ? jobCount : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-[#00ffff] p-6 rounded-lg">
                        <h2 className="text-xl font-bold text-[#00ffff] mb-2">Submissions</h2>
                        <p className="text-3xl font-mono">{submissionCount !== null ? submissionCount : '...'}</p>
                    </div>
                </div>

                {/* User Management Section */}
                <UserList
                    users={users}
                    currentUser={user}
                    onToggleAdmin={handleToggleAdmin}
                    onUserClick={handleUserClick}
                    onToggleVerification={handleToggleVerification}
                    onDeleteUser={handleDeleteUser}
                />

                <JobList
                    jobs={jobs}
                    loading={jobsLoading}
                    onRefresh={() => {
                        setJobsLoading(true);
                        fetchJobs();
                    }}
                    onDelete={handleDeleteJob}
                    onCopy={handleCopyToClipboard}
                    title="ALL SYSTEM JOBS"
                    showDeleteAction={true}
                />
            </div>
        </div>
    );
};

export default Admin;