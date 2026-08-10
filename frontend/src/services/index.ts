// Services barrel export
export {
  getSerialPorts,
  sendSerialMessage,
  getSerialStatus,
  sendTurretCommand,
  sendSerialMessages,
  createSerialServiceClient,
  serialService,
  SerialServiceError,
} from './serialService';

export type {
  SerialPortInfo,
  SerialResponse,
  SerialSendResponse,
  SerialPortsResponse,
  SerialMessageResponse,
  SerialServiceConfig,
} from './serialService';
