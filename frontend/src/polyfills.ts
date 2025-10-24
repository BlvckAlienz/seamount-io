// File: src/polyfills.ts
import { Buffer } from 'buffer';

// Polyfill Buffer for browser
(window as any).Buffer = Buffer;
(window as any).global = window;
(window as any).process = {
  env: {},
  version: '',
  nextTick: (callback: () => void) => setTimeout(callback, 0),
};

export {};