import '@testing-library/jest-dom';
import { vi } from 'vitest';

global.MediaRecorder = vi.fn().mockImplementation(() => ({
  start: vi.fn(),
  stop: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
  state: 'inactive',
  stream: {},
  ondataavailable: null,
  onerror: null,
  onpause: null,
  onresume: null,
  onstart: null,
  onstop: null,
}));

global.AudioContext = vi.fn().mockImplementation(() => ({
  createMediaStreamSource: vi.fn(),
  createGain: vi.fn(() => ({
    connect: vi.fn(),
    gain: { value: 1 },
  })),
  createAnalyser: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    fftSize: 2048,
    frequencyBinCount: 1024,
    getByteTimeDomainData: vi.fn(),
  })),
  destination: {},
  close: vi.fn(),
  resume: vi.fn(),
  suspend: vi.fn(),
}));

global.navigator.mediaDevices = {
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: () => [
      {
        stop: vi.fn(),
        kind: 'audio',
        enabled: true,
      },
    ],
  }),
  enumerateDevices: vi.fn().mockResolvedValue([]),
};

const mockSpeechSDK = {
  SpeechConfig: {
    fromAuthorizationToken: vi.fn((token, region) => ({
      authorizationToken: token,
      region: region,
      speechRecognitionLanguage: 'en-US',
    })),
    fromSubscription: vi.fn((key, region) => ({
      subscriptionKey: key,
      region: region,
      speechRecognitionLanguage: 'en-US',
    })),
  },
  AudioConfig: {
    fromDefaultMicrophoneInput: vi.fn(() => ({})),
    fromStreamInput: vi.fn(() => ({})),
  },
  SpeechRecognizer: vi.fn().mockImplementation(() => ({
    recognizeOnceAsync: vi.fn((successCb, errorCb) => {
      successCb({
        reason: 3,
        text: 'Test recognition result',
      });
    }),
    startContinuousRecognitionAsync: vi.fn((successCb) => successCb && successCb()),
    stopContinuousRecognitionAsync: vi.fn((successCb) => successCb && successCb()),
    close: vi.fn(),
    recognized: null,
    recognizing: null,
    canceled: null,
  })),
  SpeechSynthesizer: vi.fn().mockImplementation(() => ({
    speakTextAsync: vi.fn((text, successCb, errorCb) => {
      successCb({
        reason: 3,
        audioData: new ArrayBuffer(8),
      });
    }),
    close: vi.fn(),
  })),
  ResultReason: {
    RecognizedSpeech: 3,
    Canceled: 0,
    NoMatch: 1,
    SynthesizingAudioCompleted: 3,
  },
  CancellationReason: {
    Error: 1,
    EndOfStream: 2,
  },
  PropertyId: {
    SpeechServiceConnection_InitialSilenceTimeoutMs: 0,
    SpeechServiceConnection_EndSilenceTimeoutMs: 1,
  },
};

vi.mock('microsoft-cognitiveservices-speech-sdk', () => mockSpeechSDK);

global.Audio = vi.fn().mockImplementation(function() {
  return {
    play: vi.fn().mockResolvedValue(undefined),
    pause: vi.fn(),
    load: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    currentTime: 0,
    duration: 0,
    paused: true,
    ended: false,
    volume: 1,
  };
});
