import { create } from 'zustand';
import {
  getSerialPorts,
  sendSerialMessage,
  getSerialStatus,
  sendTurretCommand,
  SerialPortInfo,
  SerialResponse,
  SerialSendResponse,
  SerialServiceError,
} from '@/services/serialService';

// Types for store state
export interface SerialPortState {
  // Port information
  ports: string[];
  count: number;
  defaultPort: string;
  isConnected: boolean;
  
  // Status
  isLoading: boolean;
  error: string | null;
  lastResponse: SerialResponse | null;
  
  // Message history
  messageHistory: Array<{
    message: string;
    response: SerialSendResponse | null;
    timestamp: Date;
  }>;
}

// Store actions type
export interface SerialPortActions {
  // Actions
  refreshPorts: () => Promise<void>;
  sendMessage: (message: string) => Promise<SerialSendResponse | null>;
  sendTurretCommand: (azimuth: number, elevation: number) => Promise<SerialSendResponse | null>;
  checkStatus: () => Promise<SerialResponse | null>;
  clearError: () => void;
  clearMessageHistory: () => void;
  
  // Auto-refresh setup
  setupAutoRefresh: (intervalMs: number) => () => void;
}

// Combined store type
export interface SerialPortStore extends SerialPortState, SerialPortActions {}

// Initial state
const initialState: SerialPortState = {
  ports: [],
  count: 0,
  defaultPort: "/dev/ttyUSB0",
  isConnected: false,
  isLoading: true,
  error: null,
  lastResponse: null,
  messageHistory: [],
};

// Helper function to fetch ports
const fetchPortsHelper = async (set: any): Promise<SerialPortInfo | null> => {
  try {
    const portsInfo = await getSerialPorts();
    return portsInfo;
  } catch (error) {
    const message = error instanceof SerialServiceError ? error.message :
      error instanceof Error ? error.message : "Failed to fetch serial ports";
    set({ error: message, isLoading: false });
    return null;
  }
};

// Helper function to fetch status
const fetchStatusHelper = async (set: any): Promise<SerialResponse | null> => {
  try {
    const status = await getSerialStatus();
    return status;
  } catch (error) {
    const message = error instanceof SerialServiceError ? error.message :
      error instanceof Error ? error.message : "Failed to check serial status";
    set({ error: message });
    return null;
  }
};

export const useSerialPortStore = create<SerialPortStore>((set, get) => ({
  // Initial state
  ...initialState,

  // Clear error
  clearError: () => {
    set({ error: null });
  },

  // Clear message history
  clearMessageHistory: () => {
    set({ messageHistory: [] });
  },

  // Refresh ports and status
  refreshPorts: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const portsInfo = await fetchPortsHelper(set);
      const status = await fetchStatusHelper(set);
      
      if (portsInfo) {
        set({
          ports: portsInfo.ports,
          count: portsInfo.count,
          defaultPort: portsInfo.default,
          isConnected: portsInfo.connected,
          isLoading: false,
          lastResponse: status || null,
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to refresh serial ports";
      set({ error: message, isLoading: false });
    }
  },

  // Send a message to serial port
  sendMessage: async (message: string): Promise<SerialSendResponse | null> => {
    if (!message || message.trim().length === 0) {
      set({ error: "Message cannot be empty" });
      return null;
    }

    set({ error: null, isLoading: true });
    
    try {
      const response = await sendSerialMessage(message);
      
      // Add to message history
      set((state) => ({
        lastResponse: response,
        messageHistory: [
          ...state.messageHistory,
          {
            message,
            response,
            timestamp: new Date(),
          },
        ],
        isLoading: false,
      }));
      
      return response;
    } catch (error) {
      const message = error instanceof SerialServiceError ? error.message :
        error instanceof Error ? error.message : "Failed to send message";
      
      // Add failed message to history
      set((state) => ({
        error: message,
        isLoading: false,
        messageHistory: [
          ...state.messageHistory,
          {
            message,
            response: { status: "error", error: message },
            timestamp: new Date(),
          },
        ],
      }));
      
      return null;
    }
  },

  // Send turret command (azimuth, elevation)
  sendTurretCommand: async (azimuth: number, elevation: number): Promise<SerialSendResponse | null> => {
    set({ error: null, isLoading: true });
    
    try {
      const response = await sendTurretCommand(azimuth, elevation);
      
      const command = `moveto ${azimuth} ${elevation}`;
      set((state) => ({
        lastResponse: response,
        messageHistory: [
          ...state.messageHistory,
          {
            message: command,
            response,
            timestamp: new Date(),
          },
        ],
        isLoading: false,
      }));
      
      return response;
    } catch (error) {
      const message = error instanceof SerialServiceError ? error.message :
        error instanceof Error ? error.message : "Failed to send turret command";
      
      set({
        error: message,
        isLoading: false,
      });
      
      return null;
    }
  },

  // Check serial status
  checkStatus: async (): Promise<SerialResponse | null> => {
    set({ error: null, isLoading: true });
    
    try {
      const status = await getSerialStatus();
      set({
        lastResponse: status,
        isLoading: false,
      });
      return status;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to check status";
      set({
        error: message,
        isLoading: false,
      });
      return null;
    }
  },

  // Setup auto-refresh with interval
  setupAutoRefresh: (intervalMs: number) => {
    if (intervalMs <= 0) return () => {};
    
    const interval = setInterval(() => {
      get().refreshPorts();
    }, intervalMs);
    
    // Return cleanup function
    return () => clearInterval(interval);
  },
}));
