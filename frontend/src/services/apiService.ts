// Minimal API service to resolve build errors
export const apiClient = {
  get: (url: string) => fetch(url).then(res => res.json()),
  post: (url: string, data: any) => fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(res => res.json()),
};

export const logger = {
  error: (message: string, error?: any) => console.error(message, error),
  info: (message: string) => console.log(message),
  warn: (message: string) => console.warn(message),
};