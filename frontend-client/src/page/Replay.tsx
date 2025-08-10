import React from 'react';
import { useParams } from 'react-router-dom';
import ReplaySection from '../components/ReplaySection';

const Replay: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  return (
    <div>
      <ReplaySection gameId={gameId} />
    </div>
  );
}

export default Replay;