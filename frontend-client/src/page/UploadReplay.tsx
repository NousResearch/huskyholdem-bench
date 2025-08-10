import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReplaySection from '../components/ReplaySection';
import { Upload, AlertCircle, ArrowLeft, FileText, X } from 'lucide-react';

const UploadReplay: React.FC = () => {
  const navigate = useNavigate();
  const [gameData, setGameData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState(false);

  const validateGameData = (data: any): boolean => {
    // Basic validation for game data structure
    if (!data) return false;
    if (!data.rounds || typeof data.rounds !== 'object') return false;
    if (!data.playerNames || typeof data.playerNames !== 'object') return false;
    if (!data.finalBoard || !Array.isArray(data.finalBoard)) return false;
    
    // Check player count (2-6 players)
    const playerCount = Object.keys(data.playerNames).length;
    if (playerCount < 2 || playerCount > 6) {
      setError(`Invalid number of players: ${playerCount}. Must be between 2-6 players.`);
      return false;
    }
    
    return true;
  };

  const handleFileUpload = (file: File) => {
    if (!file) return;
    
    if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
      setError('Please upload a valid JSON file.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const jsonData = JSON.parse(e.target?.result as string);
        
        // Handle both direct game_data and wrapped response format
        const extractedGameData = jsonData.game_data || jsonData;
        
        if (validateGameData(extractedGameData)) {
          setGameData(extractedGameData);
          setFileName(file.name);
          setError(null);
        } else {
          setError('Invalid game data format. Please check the JSON structure.');
        }
      } catch (err) {
        setError('Invalid JSON file. Please check the file format.');
      }
    };
    reader.readAsText(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const clearData = () => {
    setGameData(null);
    setFileName('');
    setError(null);
  };

  // If game data is loaded, show the replay with upload button
  if (gameData) {
    return (
      <div className="relative">
        <ReplaySection uploadedGameData={gameData} />
        {/* Upload Another Button */}
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={clearData}
            className="flex items-center gap-2 px-4 py-3 bg-[#ff00cc] text-black font-bold rounded-lg hover:bg-[#ff00cc]/80 transition-colors shadow-lg"
            title="Upload another replay file"
          >
            <Upload className="w-5 h-5" />
            Upload Another
          </button>
        </div>
      </div>
    );
  }

  // Show upload interface
  return (
    <div className="min-h-screen text-white p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 px-4 py-2 bg-black border border-[#444] text-[#39ff14] rounded-lg hover:bg-[#39ff14]/20 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <div className="text-center flex-1">
              <h1 className="text-3xl font-bold font-mono text-[#ff00cc] mb-2">UPLOAD REPLAY</h1>
              <p className="text-gray-400">Upload a game JSON file to analyze</p>
            </div>
            <div className="w-20"></div>
          </div>
        </div>

        {/* Upload Area */}
        <div className="max-w-2xl mx-auto">
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              isDragOver
                ? 'border-[#ff00cc] bg-[#ff00cc]/10'
                : 'border-[#444] bg-black/30'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="w-16 h-16 text-[#39ff14] mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              Upload Game Data
            </h3>
            <p className="text-gray-400 mb-4">
              Drag and drop a JSON file here, or click to browse
            </p>
            
            <input
              type="file"
              accept=".json,application/json"
              onChange={handleFileInputChange}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#39ff14] text-black font-bold rounded-lg hover:bg-[#39ff14]/80 transition-colors cursor-pointer"
            >
              <FileText className="w-4 h-4" />
              Choose File
            </label>
          </div>

          {/* Requirements */}
          <div className="bg-black/30 border-l-4 border-[#39ff14] pl-4 py-3 my-6">
            <p className="text-[#39ff14] font-bold mb-1">📋 FILE REQUIREMENTS</p>
            <p className="text-gray-300 text-sm mb-2">
              Upload a valid poker game JSON file with the following requirements:
            </p>
            <ul className="text-gray-400 text-xs space-y-1">
              <li>• <span className="text-yellow-400">File Format:</span> Must be a valid JSON file (.json)</li>
              <li>• <span className="text-yellow-400">Player Count:</span> 2-6 players supported</li>
              <li>• <span className="text-yellow-400">Structure:</span> Must contain rounds, playerNames, and finalBoard</li>
              <li>• <span className="text-yellow-400">Compatibility:</span> Same format as exported game logs</li>
            </ul>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <p className="text-red-300">{error}</p>
              </div>
            </div>
          )}

          {/* Current File Display */}
          {fileName && (
            <div className="bg-green-900/30 border border-green-500 rounded-lg p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-green-400" />
                <span className="text-green-300 font-mono">{fileName}</span>
              </div>
              <button
                onClick={clearData}
                className="text-red-400 hover:text-red-300 p-1 rounded hover:bg-red-900/20 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UploadReplay; 