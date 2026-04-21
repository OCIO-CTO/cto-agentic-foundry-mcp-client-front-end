import { useState, useRef, useEffect } from 'react';
import { useSpeechService } from '../hooks/useSpeechService';

export function VoiceInput({ onTranscript, disabled = false }) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [localError, setLocalError] = useState(null);

  const { startRecognition, stopRecognition, isInitialized, error: speechError } = useSpeechService();
  const recognizerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (recognizerRef.current) {
        stopRecognition();
      }
    };
  }, [stopRecognition]);

  const handleMicClick = async () => {
    if (isListening) {
      stopRecognition();
      setIsListening(false);

      if (transcript && onTranscript) {
        onTranscript(transcript);
      }
      setTranscript('');
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());

        setLocalError(null);
        setTranscript('');

        recognizerRef.current = startRecognition(
          (text) => {
            setTranscript(prev => {
              const newTranscript = prev ? `${prev} ${text}` : text;
              return newTranscript;
            });
          },
          (err) => {
            console.error('Recognition error:', err);
            setLocalError(err.message || 'Recognition failed');
            setIsListening(false);
          }
        );

        if (recognizerRef.current) {
          setIsListening(true);
        }
      } catch (err) {
        console.error('Microphone permission error:', err);
        setLocalError('Microphone permission denied. Please allow microphone access.');
      }
    }
  };

  const displayError = localError || speechError;
  const canUse = isInitialized && !disabled;

  return (
    <div className="voice-input-container">
      <button
        onClick={handleMicClick}
        disabled={!canUse}
        className={`voice-input-button ${isListening ? 'voice-input-recording' : ''} ${displayError ? 'voice-input-error' : ''}`}
        title={isListening ? 'Stop recording' : 'Start voice input'}
        aria-label={isListening ? 'Stop recording' : 'Start voice input'}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {isListening ? (
            <rect x="6" y="4" width="12" height="16" rx="2" />
          ) : (
            <>
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </>
          )}
        </svg>
      </button>

      {isListening && transcript && (
        <div className="voice-input-transcript">
          {transcript}
        </div>
      )}

      {displayError && (
        <div className="voice-input-error-message">
          {displayError}
        </div>
      )}
    </div>
  );
}
