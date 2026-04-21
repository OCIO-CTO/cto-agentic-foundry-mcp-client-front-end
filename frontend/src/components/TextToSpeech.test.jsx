import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TextToSpeech } from './TextToSpeech';

vi.mock('../hooks/useSpeechService', () => ({
  useSpeechService: () => ({
    synthesizeSpeech: vi.fn((text, onStart, onComplete) => {
      onStart();
      setTimeout(onComplete, 100);
    }),
    isInitialized: true,
    error: null,
  }),
}));

describe('TextToSpeech', () => {
  it('renders speaker button', () => {
    render(<TextToSpeech text="Hello world" />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('disables button when no text provided', () => {
    render(<TextToSpeech text="" />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('calls synthesizeSpeech on button click', () => {
    const text = 'Hello world';
    render(<TextToSpeech text={text} />);
    const button = screen.getByRole('button');

    fireEvent.click(button);
    expect(button.className).toContain('tts-playing');
  });

  it('disables button when disabled prop is true', () => {
    render(<TextToSpeech text="Hello" disabled={true} />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });
});
