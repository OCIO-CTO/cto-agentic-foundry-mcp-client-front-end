import { useState, useEffect } from 'react';
import { TYPEWRITER_CONFIG } from '../config/constants';

/**
 * Custom hook for typewriter animation effect
 * @param {Array<string>} texts - Array of texts to cycle through
 * @param {boolean} isActive - Whether the typewriter should be active
 * @returns {string} - Current typed text
 */
export function useTypewriter(texts, isActive = true) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [typedText, setTypedText] = useState('');

  useEffect(() => {
    if (!isActive || texts.length === 0) {
      setTypedText('');
      return;
    }

    const currentText = texts[currentIndex];
    let timeout;

    if (typedText.length < currentText.length) {
      // Typing
      timeout = setTimeout(() => {
        setTypedText(currentText.slice(0, typedText.length + 1));
      }, TYPEWRITER_CONFIG.TYPING_SPEED);
    } else if (typedText.length === currentText.length) {
      // Pause after typing complete, then clear and move to next
      timeout = setTimeout(() => {
        setTypedText('');
        setCurrentIndex((prev) => (prev + 1) % texts.length);
      }, TYPEWRITER_CONFIG.PAUSE_AFTER_TYPING);
    }

    return () => clearTimeout(timeout);
  }, [typedText, currentIndex, texts, isActive]);

  return typedText;
}
