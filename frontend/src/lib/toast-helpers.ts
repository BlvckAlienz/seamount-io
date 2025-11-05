import toast from 'react-hot-toast';

export const toastInfo = (message: string) => {
  toast(message, { 
    icon: 'ℹ️',
    duration: 3000,
    style: {
      background: '#3b82f6',
      color: '#fff',
    },
  });
};

export const toastWarning = (message: string) => {
  toast(message, { 
    icon: '⚠️',
    duration: 4000,
    style: {
      background: '#f59e0b',
      color: '#fff',
    },
  });
};