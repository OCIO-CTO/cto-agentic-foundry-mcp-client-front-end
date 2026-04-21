import { useState } from 'react';
import { useSpeechService } from '../hooks/useSpeechService';

export function TextToSpeech({ text, disabled = false }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [localError, setLocalError] = useState(null);

  const { synthesizeSpeech, stopSpeech, isInitialized, error: speechError } = useSpeechService();

  const handleClick = () => {
    if (isPlaying) {
      stopSpeech();
      setIsPlaying(false);
      return;
    }

    if (!text || text.trim().length === 0) {
      setLocalError('No text to speak');
      return;
    }

    setLocalError(null);
    synthesizeSpeech(
      text,
      () => {
        setIsPlaying(true);
      },
      () => {
        setIsPlaying(false);
      },
      (err) => {
        console.error('TTS error:', err);
        setLocalError(err.message || 'Speech synthesis failed');
        setIsPlaying(false);
      }
    );
  };

  const displayError = localError || speechError;
  const canUse = isInitialized && !disabled && text && text.trim().length > 0;

  return (
    <div className="tts-container">
      <button
        onClick={handleClick}
        disabled={!canUse}
        className={`tts-button ${isPlaying ? 'tts-playing' : ''} ${displayError ? 'tts-error' : ''}`}
        title={isPlaying ? 'Stop speaking' : 'Read aloud'}
        aria-label={isPlaying ? 'Stop audio playback' : 'Read message aloud'}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {isPlaying ? (
            <>
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
            </>
          ) : (
            <>
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </>
          )}
        </svg>
      </button>

      {displayError && (
        <div className="tts-error-message">
          {displayError}
        </div>
      )}
    </div>
  );
}
