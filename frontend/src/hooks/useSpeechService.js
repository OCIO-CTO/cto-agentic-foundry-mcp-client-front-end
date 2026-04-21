import { useState, useEffect, useRef, useCallback } from 'react';
import * as SpeechSDK from 'microsoft-cognitiveservices-speech-sdk';

const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';

export function useSpeechService() {
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState(null);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speechConfigRef = useRef(null);
  const recognizerRef = useRef(null);
  const synthesizerRef = useRef(null);

  const fetchToken = useCallback(async () => {
    try {
      const response = await fetch(`${MCP_BASE_URL}/api/speech/token`);
      if (!response.ok) {
        throw new Error(`Failed to fetch token: ${response.statusText}`);
      }
      const data = await response.json();
      return data;
    } catch (err) {
      console.error('Error fetching speech token:', err);
      throw err;
    }
  }, []);

  const initializeSpeech = useCallback(async () => {
    try {
      const { token, region } = await fetchToken();

      speechConfigRef.current = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
      // Language will be automatically detected at start using AutoDetectSourceLanguageConfig
      // Supporting en-US and es-US as candidate languages

      setIsInitialized(true);
      setError(null);
    } catch (err) {
      console.error('Failed to initialize speech service:', err);
      setError(err.message);
      setIsInitialized(false);
    }
  }, [fetchToken]);

  useEffect(() => {
    initializeSpeech();

    return () => {
      if (recognizerRef.current) {
        recognizerRef.current.close();
      }
      if (synthesizerRef.current) {
        synthesizerRef.current.close();
      }
    };
  }, [initializeSpeech]);

  const startRecognition = useCallback(async (onResult, onError) => {
    if (!isInitialized || !speechConfigRef.current) {
      const err = new Error('Speech service not initialized');
      setError(err.message);
      if (onError) onError(err);
      return null;
    }

    try {
      // Configure automatic language detection at start
      // Supports en-US and es-US detection within first 5 seconds of speech
      const autoDetectSourceLanguageConfig = SpeechSDK.AutoDetectSourceLanguageConfig.fromLanguages([
        'en-US',
        'es-US'
      ]);
      console.log('Starting recognition with automatic language detection (en-US, es-US)');

      // Get the actual microphone device - this is crucial for browser environments
      console.log('Enumerating audio devices...');
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputDevices = devices.filter(device => device.kind === 'audioinput');

      console.log('Found audio input devices:', audioInputDevices.map(d => d.label));

      // Use the default device (first one) or a specific device
      let audioConfig;
      if (audioInputDevices.length > 0) {
        const deviceId = audioInputDevices[0].deviceId;
        console.log('Using microphone device:', audioInputDevices[0].label, 'ID:', deviceId);
        audioConfig = SpeechSDK.AudioConfig.fromMicrophoneInput(deviceId);
      } else {
        console.log('No specific device found, using default');
        audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      }

      const recognizer = SpeechSDK.SpeechRecognizer.FromConfig(
        speechConfigRef.current,
        autoDetectSourceLanguageConfig,
        audioConfig
      );

      recognizer.recognizing = (s, e) => {
        console.log('Recognizing (interim):', e.result.text);
        // Log detected language during recognition
        if (e.result.language) {
          console.log('Detected language:', e.result.language);
        }
      };

      recognizer.recognized = (s, e) => {
        console.log('Recognition event fired, reason:', e.result.reason);

        // Log the detected language for debugging
        if (e.result.language) {
          console.log('Final detected language:', e.result.language);
        }

        if (e.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
          console.log('Recognized speech:', e.result.text);
          if (onResult) {
            console.log('Calling onResult callback with:', e.result.text);
            onResult(e.result.text);
          } else {
            console.warn('No onResult callback provided');
          }
        } else if (e.result.reason === SpeechSDK.ResultReason.NoMatch) {
          console.log('No speech could be recognized');
        }
      };

      recognizer.canceled = (s, e) => {
        console.error('Recognition canceled, reason:', e.reason);
        if (e.reason === SpeechSDK.CancellationReason.Error) {
          console.error('Recognition error details:', e.errorDetails);

          // Check if error is related to language detection
          if (e.errorDetails && e.errorDetails.includes('language')) {
            console.error('Language detection error - verify candidate languages are supported');
          }
        }
        setIsRecognizing(false);
        if (e.reason === SpeechSDK.CancellationReason.Error) {
          const err = new Error(`Recognition error: ${e.errorDetails}`);
          setError(err.message);
          if (onError) onError(err);
        }
      };

      recognizer.sessionStopped = () => {
        console.log('Recognition session stopped');
        setIsRecognizing(false);
      };

      recognizer.startContinuousRecognitionAsync(
        () => {
          console.log('Recognition started');
          setIsRecognizing(true);
          setError(null);
        },
        (err) => {
          console.error('Failed to start recognition:', err);
          setError(err);
          setIsRecognizing(false);
          if (onError) onError(err);
        }
      );

      recognizerRef.current = recognizer;
      return recognizer;
    } catch (err) {
      console.error('Error starting recognition:', err);
      setError(err.message);
      setIsRecognizing(false);
      if (onError) onError(err);
      return null;
    }
  }, [isInitialized]);

  const stopRecognition = useCallback(() => {
    if (recognizerRef.current) {
      recognizerRef.current.stopContinuousRecognitionAsync(
        () => {
          console.log('Recognition stopped');
          setIsRecognizing(false);
          recognizerRef.current.close();
          recognizerRef.current = null;
        },
        (err) => {
          console.error('Failed to stop recognition:', err);
          setError(err);
          setIsRecognizing(false);
        }
      );
    }
  }, []);

  const synthesizeSpeech = useCallback(async (text, onStart, onComplete, onError) => {
    if (!isInitialized || !speechConfigRef.current) {
      const err = new Error('Speech service not initialized');
      setError(err.message);
      if (onError) onError(err);
      return;
    }

    try {
      if (onStart) onStart();
      setIsSpeaking(true);

      const synthesizer = new SpeechSDK.SpeechSynthesizer(speechConfigRef.current, null);

      synthesizer.speakTextAsync(
        text,
        (result) => {
          if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
            console.log('Speech synthesis completed');

            const audioBlob = new Blob([result.audioData], { type: 'audio/mpeg' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            audio.onended = () => {
              setIsSpeaking(false);
              URL.revokeObjectURL(audioUrl);
              if (onComplete) onComplete();
            };

            audio.onerror = (err) => {
              console.error('Audio playback error:', err);
              setIsSpeaking(false);
              setError('Audio playback failed');
              URL.revokeObjectURL(audioUrl);
              if (onError) onError(err);
            };

            audio.play();
          } else {
            const err = new Error(`Speech synthesis failed: ${result.reason}`);
            setIsSpeaking(false);
            setError(err.message);
            if (onError) onError(err);
          }

          synthesizer.close();
        },
        (err) => {
          console.error('Speech synthesis error:', err);
          setIsSpeaking(false);
          setError(err);
          if (onError) onError(err);
          synthesizer.close();
        }
      );

      synthesizerRef.current = synthesizer;
    } catch (err) {
      console.error('Error in speech synthesis:', err);
      setIsSpeaking(false);
      setError(err.message);
      if (onError) onError(err);
    }
  }, [isInitialized]);

  return {
    isInitialized,
    error,
    isRecognizing,
    isSpeaking,
    startRecognition,
    stopRecognition,
    synthesizeSpeech,
    reinitialize: initializeSpeech,
  };
}
