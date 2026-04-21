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
      console.log('Stopping recognition, transcript:', transcript);
      stopRecognition();
      setIsListening(false);

      if (transcript && onTranscript) {
        console.log('Calling onTranscript with:', transcript);
        onTranscript(transcript);
        setTranscript('');
      } else {
        console.log('No transcript to submit');
      }
    } else {
      try {
        console.log('Checking microphone access...');

        // Check if getUserMedia is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Microphone not supported in this browser. Try Chrome or Edge.');
        }

        // Request microphone permission first
        console.log('Requesting microphone permission...');
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        console.log('Microphone permission granted, active tracks:', stream.getAudioTracks().length);

        // Stop the permission check stream - Azure SDK will create its own
        stream.getTracks().forEach(track => {
          console.log('Stopping permission check track:', track.label);
          track.stop();
        });

        setLocalError(null);
        setTranscript('');

        console.log('Starting speech recognition with Azure SDK using automatic language detection');
        recognizerRef.current = startRecognition(
          (text) => {
            console.log('Recognition result received:', text);
            setTranscript(prev => {
              const newTranscript = prev ? `${prev} ${text}` : text;
              console.log('Updated transcript:', newTranscript);

              // Update parent component in real-time
              if (onTranscript) {
                console.log('Calling onTranscript in real-time with:', newTranscript);
                onTranscript(newTranscript);
              }

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
          console.log('Recognition started successfully');
          setIsListening(true);
        } else {
          console.error('Failed to start recognizer');
          setLocalError('Failed to start speech recognition');
        }
      } catch (err) {
        console.error('Microphone error:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setLocalError('Microphone permission denied. Please allow microphone access in your browser settings.');
        } else if (err.name === 'NotFoundError') {
          setLocalError('No microphone found. Please connect a microphone.');
        } else if (err.name === 'NotSupportedError') {
          setLocalError('HTTPS required. Microphone only works on secure connections.');
        } else {
          setLocalError(err.message || 'Failed to access microphone');
        }
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

      {displayError && (
        <div className="voice-input-error-message">
          {displayError}
        </div>
      )}
    </div>
  );
}
