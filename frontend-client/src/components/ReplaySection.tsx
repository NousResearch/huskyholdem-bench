import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { liveAPI } from "../api";
import { SkipBack, SkipForward, Users, TrendingUp, DollarSign,  Eye, EyeOff, ArrowLeft } from "lucide-react";
import './ReplaySection.css';

interface GameRound {
  pot: number;
  bets: { [playerId: string]: number };
  actions: { [playerId: string]: string };
  actionTimes: { [playerId: string]: number };
  action_sequence?: ActionSequence[];
}

interface ActionSequence {
  action: string;
  amount: number;
  player: string | number;
  timestamp: number;
  pot_after_action: number;
  side_pots_after_action?: any[];
  total_pot_after_action?: number;
  total_side_pots_after_action?: any[];
}

interface GameData {
  rounds: { [roundId: string]: GameRound };
  playerNames: { [playerId: string]: string };
  playerHands: { [playerId: string]: string[] };
  finalBoard: string[];
  blinds: { small: number; big: number };
  playerIdToUsername?: { [playerId: string]: string };
  usernameMapping?: { [username: string]: string | number };
  playerMoney?: {
    initialAmount: number;
    startingMoney: { [playerId: string]: number };
    finalMoney: { [playerId: string]: number };
    thisGameDelta: { [playerId: string]: number };
  };
}

interface PlayerSeatProps {
  playerId: string;
  style: React.CSSProperties;
  playerStacks: { [playerId: string]: number };
  playerIdToUsername?: { [playerId: string]: string };
  playerHands?: { [playerId: string]: string[] };
  isCurrentPlayer?: boolean;
  showCards?: boolean;
}

interface Position {
  top?: string;
  bottom?: string;
  left?: string;
  right?: string;
  transform?: string;
}

interface ReplaySectionProps {
  gameId?: string;
  uploadedGameData?: any; // Optional uploaded game data
}

const ReplaySection: React.FC<ReplaySectionProps> = ({ gameId, uploadedGameData }) => {
  const navigate = useNavigate();
  const [gameData, setGameData] = useState<GameData | null>(null);
  const [actionList, setActionList] = useState<ActionSequence[]>([]);
  const [currentActionIdx, setCurrentActionIdx] = useState<number>(0);
  const [currentRoundIdx, setCurrentRoundIdx] = useState<number>(0);
  const [playerStacks, setPlayerStacks] = useState<{ [playerId: string]: number }>({});
  const [playerDeltas, setPlayerDeltas] = useState<{ [playerId: string]: number }>({});
  const [viewMode, setViewMode] = useState<'action' | 'round'>('action');
  const [showPlayerCards, setShowPlayerCards] = useState<boolean>(false);
  const [showPots, setShowPots] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch game data or use uploaded data
  useEffect(() => {
    const fetchData = async () => {
      try {
        if (uploadedGameData) {
          // Use uploaded game data directly
          setGameData(uploadedGameData);
        } else if (gameId) {
          // Fetch from API
          const data = await liveAPI.get_game_data(gameId);
          setGameData(data.game_data);
        } else {
          setGameData(null);
        }
      } catch (err: any) {
        if (err.response?.status === 403) {
          setError("This game is private and cannot be accessed.");
        } else if (err.response?.status === 404) {
          setError("Game not found.");
        } else {
          setError("Failed to load game data.");
        }
      }
    };
    fetchData();
  }, [gameId, uploadedGameData]);

  // Build a flat action list from all rounds
  useEffect(() => {
    if (!gameData) return;
    const actions: ActionSequence[] = [];
    Object.values(gameData.rounds).forEach((round) => {
      if (round.action_sequence) {
        actions.push(...round.action_sequence);
      }
    });
    setActionList(actions);
    setCurrentActionIdx(0);
    setCurrentRoundIdx(0);
  }, [gameData]);

  // Helper function to get username from player ID
  const getPlayerUsername = (playerId: string | number) => {
    const numericId = typeof playerId === 'string' ? parseInt(playerId) : playerId;
    // some how the playerId is 1 less than the actual playerId
    return gameData?.playerIdToUsername?.[numericId + 1] || String(playerId);
  };

  // Helper function to truncate long usernames
  const truncateUsername = (username: string, maxLength: number = 20) => {
    if (username.length <= maxLength) return username;
    return username.substring(0, maxLength - 3) + '...';
  };

  // Get player order based on first round action sequence
  const getPlayerOrder = () => {
    if (!gameData) return [];
    
    const firstRoundKey = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b))[0];
    const firstRound = gameData.rounds[firstRoundKey];
    
    if (firstRound?.action_sequence) {
      // Extract unique player order from action sequence
      const playerOrder: string[] = [];
      const seen = new Set<string>();
      
      for (const action of firstRound.action_sequence) {
        const playerId = String(action.player);
        if (!seen.has(playerId)) {
          playerOrder.push(playerId);
          seen.add(playerId);
        }
      }
      
      return playerOrder;
    }
    
    // Fallback to playerNames keys if no action sequence
    return Object.keys(gameData.playerNames);
  };

  // Calculate player stacks and deltas based on view mode
  useEffect(() => {
    if (!gameData) return;
    
    const stacks: { [playerId: string]: number } = {};
    const deltas: { [playerId: string]: number } = {};
    
    // Initialize stacks and deltas for all players using their actual starting money
    Object.keys(gameData.playerNames).forEach(pid => { 
      const numericPid = parseInt(pid) + 1; // Convert to actual player ID
      const startingMoney = gameData.playerMoney?.startingMoney?.[numericPid] || 10000;
      stacks[pid] = startingMoney; 
      deltas[pid] = 0;
    });
    
    if (viewMode === 'round') {
      // Calculate stacks up to current round
      const roundKeys = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b));
      for (let i = 0; i <= currentRoundIdx && i < roundKeys.length; i++) {
        const round = gameData.rounds[roundKeys[i]];
        Object.entries(round.bets).forEach(([playerId, betAmount]) => {
          const numericPid = parseInt(playerId) + 1;
          const startingMoney = gameData.playerMoney?.startingMoney?.[numericPid] || 10000;
          stacks[playerId] = (stacks[playerId] || startingMoney) - betAmount;
          deltas[playerId] = (deltas[playerId] || 0) - betAmount;
        });
      }
    } else {
      // Calculate stacks up to current action
      if (actionList.length > 0) {
        for (let i = 0; i <= currentActionIdx && i < actionList.length; i++) {
          const action = actionList[i];
          const pid = String(action.player);
          const numericPid = parseInt(pid) + 1;
          const startingMoney = gameData.playerMoney?.startingMoney?.[numericPid] || 10000;
          if (action.action === 'CALL' || action.action === 'RAISE' || action.action === 'BET') {
            stacks[pid] = (stacks[pid] || startingMoney) - action.amount;
            deltas[pid] = (deltas[pid] || 0) - action.amount;
          }
        }
      }
    }
    
    setPlayerStacks(stacks);
    setPlayerDeltas(deltas);
  }, [gameData, actionList, currentActionIdx, currentRoundIdx, viewMode]);

  // Show error banner if error exists
  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center">
        {/* Error box at top center */}
        <div className="mt-6 bg-red-900/20 border border-red-500 text-red-400 font-mono font-bold text-lg text-center px-6 py-4 rounded-lg shadow-md">
          {error}
        </div>
      </div>
    );
  }
  

  if (!gameData) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#ff00cc] mb-4"></div>
        <p className="text-gray-400">Loading game replay...</p>
      </div>
    </div>
  );

  const maxActionIdx = actionList.length - 1;
  const roundKeys = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b));
  const maxRoundIdx = roundKeys.length - 1;
  const currentAction = actionList[currentActionIdx];
  const currentRound = gameData.rounds[roundKeys[currentRoundIdx]];

  // Get which round's actions the current action belongs to
  const getCurrentActionRound = () => {
    if (!gameData || actionList.length === 0) return 0;
    
    const currentAction = actionList[currentActionIdx];
    if (!currentAction) return 0;
    
    // Find which round this action belongs to by checking timestamps
    const roundKeys = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b));
    
    for (const roundKey of roundKeys) {
      const round = gameData.rounds[roundKey];
      if (round.action_sequence) {
        // Check if current action is in this round's sequence
        const actionFound = round.action_sequence.some(action => 
          action.timestamp === currentAction.timestamp && 
          action.player === currentAction.player &&
          action.action === currentAction.action
        );
        if (actionFound) {
          return parseInt(roundKey);
        }
      }
    }
    
    return 0; // Fallback to pre-flop
  };

  // Get board cards based on completed rounds only
  const getBoardCards = () => {
    if (!gameData.finalBoard) return [];
    
    let completedRounds = 0;
    
    if (viewMode === 'action') {
       // In action mode, show cards based on which round the current action belongs to
       // Cards are visible during the entire round (revealed at start of round)
       completedRounds = getCurrentActionRound();
         } else {
       // In round mode, show cards based on current round
       // Cards are revealed at the START of each round (after previous round ends)
       completedRounds = currentRoundIdx;
     }
     
     // Return appropriate number of cards based on current round
     switch (completedRounds) {
       case 0: return []; // Pre-flop: no cards revealed yet
       case 1: return gameData.finalBoard.slice(0, 3); // Flop: show 3 cards (revealed after pre-flop ended)
       case 2: return gameData.finalBoard.slice(0, 4); // Turn: show 4 cards (revealed after flop ended)
       case 3: return gameData.finalBoard.slice(0, 5); // River: show 5 cards (revealed after turn ended)
       default: return gameData.finalBoard; // All cards revealed
    }
  };

  // Convert card string to display format with suit symbols
  const formatCard = (cardString: string): { rank: string; suitSymbol: string; suitColor: string } => {
    if (!cardString || cardString.length < 2) {
      return { rank: cardString, suitSymbol: '', suitColor: 'text-black' };
    }
    
    let rank = cardString[0];
    const suit = cardString[1];
    
    // Convert T to 10 for better readability
    if (rank === 'T') {
      rank = '10';
    }
    
    let suitSymbol = '';
    let suitColor = '';
    
    switch (suit) {
      case 'h':
      case 'H':
        suitSymbol = '♥️';
        suitColor = 'text-red-600';
        break;
      case 'd':
      case 'D':
        suitSymbol = '♦️';
        suitColor = 'text-red-600';
        break;
      case 'c':
      case 'C':
        suitSymbol = '♣️';
        suitColor = 'text-black';
        break;
      case 's':
      case 'S':
        suitSymbol = '♠️';
        suitColor = 'text-black';
        break;
      default:
        return { rank: cardString, suitSymbol: '', suitColor: 'text-black' };
    }
    
    return { rank, suitSymbol, suitColor };
  };

  const PlayerSeat: React.FC<PlayerSeatProps> = ({ playerId, style, playerStacks, playerHands, isCurrentPlayer, showCards }) => {
    const username = getPlayerUsername(playerId);
    const truncatedUsername = truncateUsername(username);
    const stack = playerStacks[playerId] || 0;
    const cards = playerHands?.[playerId] || [];
    const hasFolded = hasPlayerFolded(playerId);
    const isAllIn = isPlayerAllIn(playerId);
    
    // Determine border color based on player state
    let borderColor = 'border-[#444]';
    if (hasFolded) {
      borderColor = 'border-red-500';
    } else if (isAllIn) {
      borderColor = 'border-yellow-500';
    } else if (isCurrentPlayer) {
      borderColor = 'border-[#ff00cc]';
    }
    
    return (
      <div 
        className={`absolute bg-black/30 border rounded-lg p-2 min-w-[140px] ${borderColor} ${
          isCurrentPlayer ? 'shadow-lg shadow-[#ff00cc]/25' : ''
        } ${hasFolded ? 'opacity-60' : ''}`}
        style={style}
        title={username !== truncatedUsername ? username : undefined} // Show full username on hover if truncated
      >
        <div className="text-center">
          <div className={`font-mono text-sm font-bold ${isCurrentPlayer ? 'text-[#ff00cc]' : 'text-white'}`}>
            {truncatedUsername}
          </div>
          <div className="text-[#39ff14] font-mono text-xs mt-1">
            ${stack}
          </div>
          {/* Status indicators */}
          <div className="flex justify-center gap-1 mt-1">
            {hasFolded && (
              <span className="text-red-500 text-xs font-bold">FOLDED</span>
            )}
            {isAllIn && !hasFolded && (
              <span className="text-yellow-500 text-xs font-bold">ALL-IN</span>
            )}
          </div>
          {/* Player Cards */}
          <div className="flex justify-center gap-1 mt-2">
            {cards.map((card, index) => {
              if (showCards) {
                const formattedCard = formatCard(card);
                return (
                  <div
                    key={index}
                    className="w-6 h-8 rounded border bg-white border-gray-300 text-xs flex flex-col items-center justify-center font-mono"
                  >
                    <div className="text-black font-bold">{formattedCard.rank}</div>
                    <div className={`text-xs ${formattedCard.suitColor}`}>{formattedCard.suitSymbol}</div>
                  </div>
                );
              } else {
                return (
              <div
                key={index}
                    className="w-6 h-8 rounded border bg-blue-900 text-blue-300 border-blue-700 text-xs flex items-center justify-center font-mono"
              >
                    🂠
              </div>
                );
              }
            })}
          </div>
        </div>
      </div>
    );
  };

  const getActionColor = (action: string) => {
    switch (action.toUpperCase()) {
      case 'CALL': return 'text-[#39ff14]';
      case 'RAISE': return 'text-[#ff00cc]';
      case 'BET': return 'text-[#ff00cc]';
      case 'FOLD': return 'text-red-500';
      case 'CHECK': return 'text-gray-400';
      default: return 'text-white';
    }
  };

  const getRoundName = (roundIdx: number) => {
    switch (roundIdx) {
      case 0: return 'Pre-flop';
      case 1: return 'Flop';
      case 2: return 'Turn';
      case 3: return 'River';
      default: return `Round ${roundIdx + 1}`;
    }
  };

  // Determine small and big blind positions based on first round action sequence
  const getBlindPositions = () => {
    if (!gameData) return { smallBlind: '', bigBlind: '' };
    
    const firstRoundKey = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b))[0];
    const firstRound = gameData.rounds[firstRoundKey];
    
    if (firstRound?.action_sequence && firstRound.action_sequence.length >= 2) {
      // 5th play is small blind, 6th play is big blind (0-based index)
      const smallBlindPlayer = String(firstRound.action_sequence[0].player);
      const bigBlindPlayer = String(firstRound.action_sequence[1].player);
      
      return {
        smallBlind: getPlayerUsername(smallBlindPlayer),
        bigBlind: getPlayerUsername(bigBlindPlayer)
      };
    }
    
    return { smallBlind: '', bigBlind: '' };
  };

  // Get winner information
  const getWinnerInfo = () => {
    if (!gameData?.playerMoney) return null;
    
    const winners: { username: string; amount: number; delta: number }[] = [];
    const losers: { username: string; amount: number; delta: number }[] = [];
    
    Object.keys(gameData.playerNames).forEach(pid => {
      const numericPid = parseInt(pid) + 1;
      const username = getPlayerUsername(pid);
      const finalMoney = gameData.playerMoney!.finalMoney[numericPid] || 0;
      const startingMoney = gameData.playerMoney!.startingMoney[numericPid] || 0;
      const delta = finalMoney - startingMoney;
      
      if (delta > 0) {
        winners.push({ username, amount: finalMoney, delta });
      } else if (delta < 0) {
        losers.push({ username, amount: finalMoney, delta });
      }
    });
    
    return { winners, losers };
  };

  // Check if a player has folded up to the current point
  const hasPlayerFolded = (playerId: string) => {
    if (!gameData || !actionList.length) return false;
    
    const maxActionIndex = viewMode === 'action' ? currentActionIdx : actionList.length - 1;
    
    for (let i = 0; i <= maxActionIndex && i < actionList.length; i++) {
      const action = actionList[i];
      if (String(action.player) === playerId && action.action === 'FOLD') {
        return true;
      }
    }
    return false;
  };

  // Check if a player is all-in (stack is 0 or very close to 0)
  const isPlayerAllIn = (playerId: string) => {
    if (!gameData || !actionList.length) return false;
    
    const maxActionIndex = viewMode === 'action' ? currentActionIdx : actionList.length - 1;
    
    for (let i = 0; i <= maxActionIndex && i < actionList.length; i++) {
      const action = actionList[i];
      if (String(action.player) === playerId && action.action === 'ALL IN') {
        return true;
      }
    }
    return false;
  };

  // Check if we're at the end of the game
  const isGameEnd = () => {
    if (viewMode === 'action') {
      return currentActionIdx === actionList.length - 1;
    } else {
      return currentRoundIdx === roundKeys.length - 1;
    }
  };

  // Get current pots and eligible players
  const getCurrentPots = () => {
    if (!gameData || !currentAction) return [];
    
    if (viewMode === 'action') {
      return currentAction.total_side_pots_after_action || [];
    } else {
      // For round mode, get pots from the last action of current round
      const roundKeys = Object.keys(gameData.rounds).sort((a, b) => parseInt(a) - parseInt(b));
      const currentRound = gameData.rounds[roundKeys[currentRoundIdx]];
      if (currentRound?.action_sequence && currentRound.action_sequence.length > 0) {
        const lastAction = currentRound.action_sequence[currentRound.action_sequence.length - 1];
        return lastAction.total_side_pots_after_action || [];
      }
    }
    
    return [];
  };

  // Player positions
  const playerPositions: Position[] = [
    { top: '10px', left: '50%', transform: 'translateX(-50%)' },
    { top: '25%', right: '10px', transform: 'translateY(-50%)' },
    { top: '75%', right: '10px', transform: 'translateY(-50%)' },
    { bottom: '10px', left: '50%', transform: 'translateX(-50%)' },
    { top: '75%', left: '10px', transform: 'translateY(-50%)' },
    { top: '25%', left: '10px', transform: 'translateY(-50%)' },
  ];

  const boardCards = getBoardCards();
  const playerOrder = getPlayerOrder();

  return (
    <div className="min-h-screen text-white p-6">
      <div className="max-w-6xl mx-auto">
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
          <h1 className="text-3xl font-bold font-mono text-[#ff00cc] mb-2">POKER REPLAY</h1>
          <p className="text-gray-400">Step-by-step game analysis</p>
            </div>
            <div className="w-20"></div> {/* Spacer to center the title */}
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex justify-center mb-6">
          <div className="bg-black border border-[#444] rounded-xl p-2 flex items-center gap-2">
            <button
              onClick={() => setViewMode('action')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'action' 
                  ? 'bg-[#ff00cc] text-black' 
                  : 'text-[#ff00cc] hover:bg-[#ff00cc]/20'
              }`}
            >
              Action by Action
            </button>
            <button
              onClick={() => setViewMode('round')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'round' 
                  ? 'bg-[#39ff14] text-black' 
                  : 'text-[#39ff14] hover:bg-[#39ff14]/20'
              }`}
            >
              Round by Round
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-black/40 border border-[#444] rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              {viewMode === 'action' ? (
                <>
                  <button
                    onClick={() => setCurrentActionIdx(Math.max(0, currentActionIdx - 1))}
                    disabled={currentActionIdx === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-[#ff00cc]/20 border border-[#ff00cc] text-[#ff00cc] rounded-lg hover:bg-[#ff00cc]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <SkipBack className="w-4 h-4" />
                    Previous
                  </button>
                  <span className="font-mono text-lg">
                    Action <span className="text-[#ff00cc]">{currentActionIdx + 1}</span> of <span className="text-[#39ff14]">{actionList.length}</span>
                  </span>
                  <button
                    onClick={() => setCurrentActionIdx(Math.min(maxActionIdx, currentActionIdx + 1))}
                    disabled={currentActionIdx === maxActionIdx}
                    className="flex items-center gap-2 px-4 py-2 bg-[#ff00cc]/20 border border-[#ff00cc] text-[#ff00cc] rounded-lg hover:bg-[#ff00cc]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <SkipForward className="w-4 h-4" />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setCurrentRoundIdx(Math.max(0, currentRoundIdx - 1))}
                    disabled={currentRoundIdx === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-[#39ff14]/20 border border-[#39ff14] text-[#39ff14] rounded-lg hover:bg-[#39ff14]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <SkipBack className="w-4 h-4" />
                    Previous
                  </button>
                  <span className="font-mono text-lg">
                    <span className="text-[#39ff14]">{getRoundName(currentRoundIdx)}</span> ({currentRoundIdx + 1} of {roundKeys.length})
                  </span>
                  <button
                    onClick={() => setCurrentRoundIdx(Math.min(maxRoundIdx, currentRoundIdx + 1))}
                    disabled={currentRoundIdx === maxRoundIdx}
                    className="flex items-center gap-2 px-4 py-2 bg-[#39ff14]/20 border border-[#39ff14] text-[#39ff14] rounded-lg hover:bg-[#39ff14]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <SkipForward className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowPlayerCards(!showPlayerCards)}
                className="flex items-center gap-2 px-3 py-1 bg-yellow-500/20 border border-yellow-500 text-yellow-500 rounded-lg hover:bg-yellow-500/30 transition-colors text-sm"
              >
                {showPlayerCards ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showPlayerCards ? 'Hide' : 'Show'} Cards
              </button>
              <button
                onClick={() => setShowPots(!showPots)}
                className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 border border-blue-500 text-blue-500 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
              >
                {showPots ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showPots ? 'Hide' : 'Show'} Pots
              </button>
              <div className="flex items-center gap-4 text-sm text-gray-400">
                <span>SB: ${gameData.blinds.small}</span>
                <span>BB: ${gameData.blinds.big}</span>
              </div>
            </div>
          </div>

          {/* Current Info */}
          {viewMode === 'action' && currentAction && (
            <div className="bg-black border border-[#444] rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#39ff14]" />
                    <span className="font-mono text-[#39ff14]" title={getPlayerUsername(String(currentAction.player))}>
                      {truncateUsername(getPlayerUsername(String(currentAction.player)))}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-mono font-bold ${getActionColor(currentAction.action)}`}>
                      {currentAction.action}
                    </span>
                    {currentAction.amount > 0 && (
                      <span className="text-white font-mono">${currentAction.amount}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-sm">Round:</span>
                    <span className="font-mono font-bold text-[#ff00cc]">
                      {getRoundName(getCurrentActionRound())}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-[#39ff14]">
                  <DollarSign className="w-4 h-4" />
                  <span className="font-mono">Pot: ${currentAction.pot_after_action}</span>
                </div>
              </div>
            </div>
          )}

          {viewMode === 'round' && currentRound && (
            <div className="bg-black border border-[#444] rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-[#39ff14]" />
                    <span className="font-mono text-[#39ff14] font-bold">
                      {getRoundName(currentRoundIdx)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-[#39ff14]">
                  <DollarSign className="w-4 h-4" />
                  <span className="font-mono">Pot: ${currentRound.pot}</span>
                </div>
              </div>
            </div>
          )}

          {/* Pots and Eligible Players Display */}
          {showPots && (
            <div className="bg-black border border-[#444] rounded-lg p-3 mb-3">
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="w-4 h-4 text-blue-400" />
                <h3 className="font-mono font-bold text-blue-400 text-sm">POTS & ELIGIBLE PLAYERS</h3>
              </div>
              
              {(() => {
                const pots = getCurrentPots();
                if (pots.length === 0) {
                  return (
                    <p className="text-gray-400 text-xs">No pots available at this point in the game.</p>
                  );
                }
                
                return (
                  <div className="overflow-x-auto">
                    <table className="w-full table-fixed border-collapse text-xs">
                      <thead>
                        <tr className="text-left text-blue-400 border-b border-[#333]">
                          <th className="p-2 w-1/6">Pot ID</th>
                          <th className="p-2 w-1/6">Amount</th>
                          <th className="p-2 w-2/3">Eligible Players</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pots.map((pot, index) => (
                          <tr key={index} className="border-b border-[#222]">
                            <td className="p-2 font-mono text-blue-300">
                              {pot.id !== undefined ? pot.id + 1 : index + 1}
                            </td>
                            <td className="p-2 font-bold text-blue-400">
                              ${pot.amount}
                            </td>
                            <td className="p-2">
                              {pot.eligible_players && pot.eligible_players.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {pot.eligible_players.map((playerId: number, playerIndex: number) => {
                                    const username = getPlayerUsername(playerId);
                                    const truncatedUsername = truncateUsername(username, 12); // Shorter for pots display
                                    return (
                                      <span
                                        key={playerIndex}
                                        className="px-1.5 py-0.5 bg-blue-900/30 border border-blue-500 text-blue-300 rounded text-xs font-mono"
                                        title={username !== truncatedUsername ? username : undefined} // Show full username on hover if truncated
                                      >
                                        {truncatedUsername}
                                      </span>
                                    );
                                  })}
                                </div>
                              ) : (
                                <span className="text-gray-500 text-xs">None</span>
                              )}
                            </td>
                          </tr>
                        ))}
                        {/* Total Row */}
                        <tr className="border-t-2 border-blue-400 bg-blue-900/20">
                          <td className="p-2 font-mono text-blue-300 font-bold">
                            TOTAL
                          </td>
                          <td className="p-2 font-bold text-blue-400 text-sm">
                            ${pots.reduce((sum, pot) => sum + pot.amount, 0)}
                          </td>
                          <td className="p-2 text-gray-400 text-xs">
                            All pots combined
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Poker Table */}
          <div className="lg:col-span-2">
            <div className="bg-black border border-[#444] rounded-xl p-6 relative h-96">
              <div className="absolute inset-4 bg-green-900/20 rounded-full border-2 border-[#39ff14]/30"></div>
              
              {/* Center area with pot and board */}
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-[#39ff14] font-mono text-2xl font-bold mb-2">
                  ${viewMode === 'action' ? (currentAction?.pot_after_action || 0) : (currentRound?.pot || 0)}
                </div>
                <div className="text-gray-400 text-sm mb-1">POT</div>
                {(() => {
                  const pots = getCurrentPots();
                  const totalPots = pots.reduce((sum, pot) => sum + pot.amount, 0);
                  return (
                    <div className="text-blue-400 font-mono text-sm mb-3">
                      TOTAL: ${totalPots}
                    </div>
                  );
                })()}
                
                {/* Board Cards */}
                <div className="flex justify-center gap-1">
                  {boardCards.length > 0 ? (
                    boardCards.map((card, index) => {
                      const formattedCard = formatCard(card);
                      return (
                      <div
                        key={index}
                          className="w-8 h-11 bg-white border border-gray-300 rounded text-xs flex flex-col items-center justify-center font-mono"
                      >
                          <div className="text-black font-bold">{formattedCard.rank}</div>
                          <div className={`text-xs ${formattedCard.suitColor}`}>{formattedCard.suitSymbol}</div>
                      </div>
                      );
                    })
                  ) : (
                    <div className="text-gray-500 text-sm">No community cards</div>
                  )}
                </div>
              </div>
              
              {/* Player seats */}
              {playerOrder.map((playerId: string, index: number) => (
                <PlayerSeat
                  key={playerId}
                  playerId={playerId}
                  style={playerPositions[index]}
                  playerStacks={playerStacks}
                  playerHands={gameData.playerHands}
                  showCards={showPlayerCards}
                  isCurrentPlayer={
                    viewMode === 'action' 
                      ? currentAction && String(currentAction.player) === playerId
                      : false
                  }
                />
              ))}
            </div>
          </div>

          {/* Player Stacks */}
          <div className="bg-black border border-[#444] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-[#39ff14]" />
              <h3 className="font-mono font-bold text-[#39ff14]">PLAYER STACKS</h3>
            </div>
            <div className="space-y-2">
              {playerOrder.map(pid => {
                const stack = playerStacks[pid] || 0;
                const delta = playerDeltas[pid] || 0;
                const username = getPlayerUsername(pid);
                const truncatedUsername = truncateUsername(username);
                const isCurrentPlayer = viewMode === 'action' && currentAction && String(currentAction.player) === pid;
                const { smallBlind, bigBlind } = getBlindPositions();
                const isSmallBlind = username === smallBlind;
                const isBigBlind = username === bigBlind;
                
                return (
                  <div
                    key={pid}
                    className={`flex justify-between items-center p-2 rounded border font-mono text-sm ${
                      isCurrentPlayer 
                        ? 'border-[#ff00cc] bg-[#ff00cc]/10' 
                        : 'border-[#444] bg-black/30'
                    }`}
                    title={username !== truncatedUsername ? username : undefined} // Show full username on hover if truncated
                  >
                    <div className="flex items-center gap-2">
                    <span className={isCurrentPlayer ? 'text-[#ff00cc]' : 'text-white'}>
                        {truncatedUsername}
                    </span>
                      {isSmallBlind && (
                        <span className="text-xs bg-yellow-500 text-black px-1 rounded">SB</span>
                      )}
                      {isBigBlind && (
                        <span className="text-xs bg-orange-500 text-black px-1 rounded">BB</span>
                      )}
                    </div>
                    <div className="flex flex-col items-end">
                    <span className={`font-bold ${stack >= 0 ? 'text-[#39ff14]' : 'text-red-500'}`}>
                      ${stack}
                    </span>
                      <span className={`text-xs ${delta >= 0 ? 'text-[#39ff14]' : 'text-red-500'}`}>
                        {delta >= 0 ? '+' : ''}{delta}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
        </div>
                 {/* Game Results Display */}
         {isGameEnd() && (
           <div className="bg-black border-l-4 border-[#ff00cc] pl-4 py-3 my-4">
             <p className="text-[#39ff14] font-bold mb-1 text-lg">🎉 GAME RESULTS 🎉</p>
             <p className="text-gray-300 text-base mb-3">
               Final standings and updated balances for this hand. Winners are highlighted in green, losers in red.
             </p>
             
             {(() => {
               const winnerInfo = getWinnerInfo();
               if (!winnerInfo) return null;
               
               return (
                 <div className="space-y-4">
                   {/* Winners */}
                   {winnerInfo.winners.length > 0 && (
                     <div>
                       <p className="text-green-400 text-sm mb-2">
                         <span className="text-yellow-400">🏆 WINNERS:</span> Players who gained money this hand
                       </p>
                       <div className="space-y-2">
                         {winnerInfo.winners.map((winner, index) => (
                           <div key={index} className="flex justify-between items-center text-base">
                             <span className="font-mono text-green-300 font-semibold" title={winner.username}>
                               {truncateUsername(winner.username)}
                             </span>
                             <div className="text-right">
                               <span className="text-green-400 font-bold text-lg">${winner.amount}</span>
                               <span className="text-green-300 ml-3 text-sm">(+${winner.delta})</span>
                             </div>
                           </div>
                         ))}
                       </div>
                     </div>
                   )}

                   {/* Losers */}
                   {winnerInfo.losers.length > 0 && (
                     <div>
                       <p className="text-red-400 text-sm mb-2">
                         <span className="text-yellow-400">📉 LOSERS:</span> Players who lost money this hand
                       </p>
                       <div className="space-y-2">
                         {winnerInfo.losers.map((loser, index) => (
                           <div key={index} className="flex justify-between items-center text-base">
                             <span className="font-mono text-red-300 font-semibold" title={loser.username}>
                               {truncateUsername(loser.username)}
                             </span>
                             <div className="text-right">
                               <span className="text-red-400 font-bold text-lg">${loser.amount}</span>
                               <span className="text-red-300 ml-3 text-sm">({loser.delta})</span>
                             </div>
                           </div>
                         ))}
                       </div>
                     </div>
                   )}

                   {winnerInfo.winners.length === 0 && winnerInfo.losers.length === 0 && (
                     <p className="text-gray-400 text-sm">
                       <span className="text-yellow-400">⚖️ BALANCED:</span> No money exchanged this hand
                     </p>
                   )}
                 </div>
               );
             })()}
           </div>
         )}
      </div>
    </div>
  );
};

export default ReplaySection;