import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VoiceInput } from './VoiceInput';

vi.mock('../hooks/useSpeechService', () => ({
  useSpeechService: () => ({
    startRecognition: vi.fn((onResult) => {
      setTimeout(() => onResult('Test transcript'), 100);
      return {};
    }),
    stopRecognition: vi.fn(),
    isInitialized: true,
    error: null,
  }),
}));

describe('VoiceInput', () => {
  it('renders microphone button', () => {
    render(<VoiceInput onTranscript={() => {}} />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('calls onTranscript when recording stops', async () => {
    const onTranscript = vi.fn();
    render(<VoiceInput onTranscript={onTranscript} />);

    const button = screen.getByRole('button');

    fireEvent.click(button);
    await waitFor(() => {
      expect(button.className).toContain('voice-input-recording');
    });

    fireEvent.click(button);
    await waitFor(() => {
      expect(onTranscript).toHaveBeenCalled();
    }, { timeout: 500 });
  });

  it('disables button when disabled prop is true', () => {
    render(<VoiceInput onTranscript={() => {}} disabled={true} />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });
});
