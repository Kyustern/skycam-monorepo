import { useEffect } from 'react';
import { useSerialPortStore, SerialPortStore, SerialPortState, SerialPortActions } from '@/store/useSerialPortStore';

// Custom hook that provides the same interface as the original useSerialPort
// and handles auto-refresh setup
export const useSerialPort = (autoRefreshInterval?: number): SerialPortStore => {
  const store = useSerialPortStore();

  // Setup auto-refresh if interval is provided
  useEffect(() => {
    if (autoRefreshInterval && autoRefreshInterval > 0) {
      const cleanup = store.setupAutoRefresh(autoRefreshInterval);
      
      // Initial fetch
      store.refreshPorts();
      
      return cleanup;
    } else {
      // Initial fetch without auto-refresh
      store.refreshPorts();
    }
  }, [autoRefreshInterval, store]);

  return store;
};

// Export types for convenience
export type { SerialPortState, SerialPortActions, SerialPortStore };
