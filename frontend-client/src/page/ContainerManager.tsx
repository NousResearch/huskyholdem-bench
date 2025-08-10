import { Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { dockerAPI, adminAPI } from "../api";
import { useEffect, useState } from "react";
import JobList from "../components/JobList";
import ContainerLogViewer from "../components/ContainerLogViewer";

const ContainerManagerPage = () => {
    const navigate = useNavigate();  

    const [poolSize, setPoolSize] = useState<number | null>(null);
    const [activeContainers, setActiveContainers] = useState<number | null>(null);
    const [idleContainers, setIdleContainers] = useState<number | null>(null);
    const [acquiredContainers, setAcquiredContainers] = useState<number | null>(null);

    const [targetSize, setTargetSize] = useState<number>(3);
    const [jobs, setJobs] = useState<any[]>([]);
    const [jobsLoading, setJobsLoading] = useState(true);

    const fetchPoolStatus = async () => {
        try {
            const res = await dockerAPI.getPoolStatus();
            
            const pool_size = res.data.pool_size;
            const active_containers = res.data.active_containers;
            const idle_containers = res.data.idle_containers;
            const acquired_containers = res.data.acquired_containers;

            setPoolSize(pool_size);
            setActiveContainers(active_containers);
            setIdleContainers(idle_containers);
            setAcquiredContainers(acquired_containers);
        } 
        catch (err) {
            console.error("Error fetching pool status:", err);
        }
    }

    const fetchJobs = async () => {
        try {
            const res = await adminAPI.listScalingJob();
            setJobs(res);
        } catch (err) {
            console.error("Error fetching scaling jobs:", err);
        } finally {
            setJobsLoading(false);
        }
    };

    const runScaling = async () => {
        if (targetSize < 3) {
            alert("Target size must be at least 3.");
            return;
        }
    
        try {
            await dockerAPI.submitScalingJob(targetSize);
            fetchPoolStatus();
            fetchJobs();
        } catch (err: any) {
            alert(err.response?.data?.detail || err.message || "Scaling failed.");
        }
    }

    useEffect(() => {
        fetchPoolStatus();
        fetchJobs();
    
        const jobInterval = setInterval(fetchJobs, 15000);
        const poolInterval = setInterval(fetchPoolStatus, 15000);
    
        return () => {
            clearInterval(jobInterval);
            clearInterval(poolInterval);
        };
    }, []);

    return (
        <div className="min-h-screen text-white px-4 py-12 max-w-6xl mx-auto">
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
                    CONTAINER MANAGER CENTER
                </h1>
                <p className="text-lg text-gray-400">
                    Manage game container and monitor scaling job status in real-time
                </p>
                </div>
            </div>

            <div className="bg-black bg-opacity-30 border-l-4 border-[#ff00cc] p-6 my-8 rounded-lg">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Zap className="w-6 h-6 text-[#ff00cc]" />
                    CURRENT POOL STATUS
                    </h2>
                    <button 
                    onClick={fetchPoolStatus}
                    className="text-sm border border-[#ff00cc] text-[#ff00cc] px-4 py-2 rounded hover:bg-[#ff00cc] hover:text-black transition duration-200"
                    >
                    REFRESH POOL STATUS
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="bg-gray-900 border border-[#ff00cc] p-6 rounded-lg">
                    <h2 className="text-xl font-bold text-[#ff00cc] mb-2">Pool Size</h2>
                    <p className="text-3xl font-mono">{poolSize !== null ? poolSize : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-[#39ff14] p-6 rounded-lg">
                    <h2 className="text-xl font-bold text-[#39ff14] mb-2">Active Containers</h2>
                    <p className="text-3xl font-mono">{activeContainers !== null ? activeContainers : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-[#00ffff] p-6 rounded-lg">
                    <h2 className="text-xl font-bold text-[#00ffff] mb-2">Idle Containers</h2>
                    <p className="text-3xl font-mono">{idleContainers !== null ? idleContainers : '...'}</p>
                    </div>

                    <div className="bg-gray-900 border border-yellow-400 p-6 rounded-lg">
                    <h2 className="text-xl font-bold text-yellow-400 mb-2">Acquired Containers</h2>
                    <p className="text-3xl font-mono">{acquiredContainers !== null ? acquiredContainers : '...'}</p>
                    </div>
                </div>
                </div>


            <div className="bg-gray-900 border border-white p-6 rounded-lg max-w-md mt-4">
                <h2 className="text-xl font-bold text-white mb-2">Adjust Pool Size</h2>
                <p className="text-sm text-gray-400 mb-4">
                    Set the target number of containers.
                </p>

                <div className="flex items-center gap-4">
                    <input
                        type="number"
                        min={3}
                        value={targetSize}
                        onChange={(e) => setTargetSize(e.target.valueAsNumber)}
                        className="w-28 px-3 py-2 rounded bg-black border border-white text-white focus:outline-none"
                        placeholder="e.g. 3"
                    />
                    <button
                        onClick={() => {
                            if (targetSize >= 3) runScaling();
                            else alert("Target size must be at least 3.");
                        }}
                        className="px-4 py-2 bg-[#39ff14] text-black font-semibold rounded hover:bg-[#2ecc71] transition-colors"
                    >
                        Scale Now
                    </button>
                </div>
            </div>
            
            <JobList
                jobs={jobs}
                loading={jobsLoading}
                onRefresh={() => {
                    setJobsLoading(true);
                    fetchJobs();
                }}
                title="ACTIVE SCALING JOBS"
                showDeleteAction={false}
            />

            {/* Container Log Viewer */}
            <div className="mt-8">
                <ContainerLogViewer />
            </div>
        </div>
    )
}

export default ContainerManagerPage;