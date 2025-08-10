import React, { useState, useEffect } from 'react';
import { dockerAPI } from '../api';
import { FileText, Download, RefreshCw, AlertCircle, CheckCircle, Server } from 'lucide-react';

interface GameLogResponse {
  port: number;
  container_name: string;
  log_content: string;
  success: boolean;
  message: string;
}

interface ContainerInfo {
  port: number;
  container_name: string;
  state: string;
  created_by: string;
}

interface PoolDetailedResponse {
  success: boolean;
  data: {
    pool_summary: {
      pool_size: number;
      active_containers: number;
      total_containers: number;
      target_pool_size: number;
      idle_containers: number;
      acquired_containers: number;
      shared_pool: boolean;
    };
    idle_containers: ContainerInfo[];
    active_containers: ContainerInfo[];
  };
}

interface ContainerLogViewerProps {
  className?: string;
}

const ContainerLogViewer: React.FC<ContainerLogViewerProps> = ({ className = '' }) => {
  const [selectedContainer, setSelectedContainer] = useState<ContainerInfo | null>(null);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [logData, setLogData] = useState<GameLogResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [containersLoading, setContainersLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchContainers = async () => {
    setContainersLoading(true);
    try {
      const response: PoolDetailedResponse = await dockerAPI.getPoolDetailed();
      const allContainers = [
        ...response.data.idle_containers,
        ...response.data.active_containers
      ];
      setContainers(allContainers);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch containers');
    } finally {
      setContainersLoading(false);
    }
  };

  const fetchLog = async () => {
    if (!selectedContainer) {
      setError('Please select a container');
      return;
    }

    setLoading(true);
    setError(null);
    setLogData(null);

    try {
      const data = await dockerAPI.getGameLog(selectedContainer.port);
      setLogData(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch log');
    } finally {
      setLoading(false);
    }
  };

  const downloadLog = () => {
    if (!logData?.log_content || !selectedContainer) return;

    const blob = new Blob([logData.log_content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `game-log-port-${selectedContainer.port}-${logData.container_name}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Fetch containers on component mount
  useEffect(() => {
    fetchContainers();
  }, []);

  const formatLogContent = (content: string) => {
    return content.split('\n').map((line, index) => (
      <div key={index} className="font-mono text-xs">
        {line}
      </div>
    ));
  };

  return (
    <div className={`bg-black/30 border border-[#444] rounded-xl p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-6">
        <FileText className="w-6 h-6 text-[#ff00cc]" />
        <h3 className="text-xl font-bold text-white">CONTAINER LOG VIEWER</h3>
      </div>

      {/* Container Selection and Controls */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <label className="text-gray-300 font-mono text-sm">Container:</label>
          <select
            value={selectedContainer?.port || ''}
            onChange={(e) => {
              const port = parseInt(e.target.value);
              const container = containers.find(c => c.port === port);
              setSelectedContainer(container || null);
            }}
            className="px-3 py-2 bg-black border border-[#444] text-white rounded-lg focus:outline-none focus:border-[#ff00cc] font-mono text-sm min-w-48"
            disabled={containersLoading}
          >
            <option value="">Select a container...</option>
            {containers.map((container) => (
              <option key={container.port} value={container.port}>
                {container.container_name} (Port: {container.port}, State: {container.state})
              </option>
            ))}
          </select>
        </div>
        
        <button
          onClick={fetchContainers}
          disabled={containersLoading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 border border-blue-500 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {containersLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Server className="w-4 h-4" />
          )}
          {containersLoading ? 'Loading...' : 'Refresh Containers'}
        </button>

        <button
          onClick={fetchLog}
          disabled={loading || !selectedContainer}
          className="flex items-center gap-2 px-4 py-2 bg-[#ff00cc]/20 border border-[#ff00cc] text-[#ff00cc] rounded-lg hover:bg-[#ff00cc]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <FileText className="w-4 h-4" />
          )}
          {loading ? 'Loading...' : 'Fetch Log'}
        </button>

        {logData && (
          <button
            onClick={downloadLog}
            className="flex items-center gap-2 px-4 py-2 bg-[#39ff14]/20 border border-[#39ff14] text-[#39ff14] rounded-lg hover:bg-[#39ff14]/30 transition-colors"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-red-900/20 border border-red-500 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
        </div>
      )}

      {/* Success Message */}
      {logData?.success && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-green-900/20 border border-green-500 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="text-green-300 text-sm">{logData.message}</span>
        </div>
      )}

      {/* Log Content */}
      {logData && (
        <div className="bg-black border border-[#444] rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div>
                <span className="text-gray-400 text-sm">Container:</span>
                <span className="text-[#39ff14] font-mono ml-2">{logData.container_name}</span>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Port:</span>
                <span className="text-[#ff00cc] font-mono ml-2">{logData.port}</span>
              </div>
              <div>
                <span className="text-gray-400 text-sm">State:</span>
                <span className={`font-mono ml-2 ${
                  selectedContainer?.state === 'active' ? 'text-green-400' : 
                  selectedContainer?.state === 'idle' ? 'text-yellow-400' : 'text-gray-400'
                }`}>
                  {selectedContainer?.state || 'unknown'}
                </span>
              </div>
            </div>
            <div className="text-gray-400 text-xs">
              {logData.log_content.split('\n').length} lines
            </div>
          </div>
          
          <div className="bg-gray-900 border border-[#333] rounded p-3 max-h-96 overflow-y-auto">
            <div className="space-y-1">
              {formatLogContent(logData.log_content)}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!logData && !loading && !error && (
        <div className="text-center py-12 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm">Select a container from the dropdown and click "Fetch Log" to view container logs</p>
        </div>
      )}
    </div>
  );
};

export default ContainerLogViewer; 