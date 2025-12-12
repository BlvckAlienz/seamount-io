// File: frontend/src/utils/stringUtils.ts
export const safeSlice = (str: string | undefined | null, start: number, end?: number): string => {
  if (!str || typeof str !== 'string') return '';
  return str.slice(start, end);
};

export const safeTruncate = (str: string | undefined | null, firstChars: number = 6, lastChars: number = 4): string => {
  if (!str || typeof str !== 'string') return '';
  if (str.length <= firstChars + lastChars) return str;
  return `${str.slice(0, firstChars)}...${str.slice(-lastChars)}`;
};

export const safeAddress = (address: string | undefined | null): string => {
  if (!address || typeof address !== 'string') return '';
  // Ensure it's a valid Ethereum-like address
  if (!address.startsWith('0x') || address.length !== 42) return '';
  return address;
};