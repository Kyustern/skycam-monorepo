// API Service
// One function per API endpoint using fetch

const API_BASE = "/api";

// Response Types
export interface ApiResponse<T = unknown> {
  status: string;
  message?: string;
  error?: string;
  data?: T;
}

// Serial Port Types
export interface SerialPortInfo {
  ports: string[];
  count: number;
  default: string;
  connected: boolean;
}

export interface MovetoCommandParams {
  azimuth: number;
  elevation: number;
}

// Turret Types
export interface TurretStatus {
  azimuth: number;
  elevation: number;
  is_armed: boolean;
  battery_level: number;
}

export interface TurretCommandParams {
  azimuth: number;
  elevation: number;
}

// Aircraft Types
export interface AircraftParams {
  lat_min?: number;
  lat_max?: number;
  lon_min?: number;
  lon_max?: number;
}

export interface AircraftPositionParams {
  lat: number;
  lon: number;
  radius_km?: number;
}

// Error type
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly response?: any
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Helper to handle fetch errors
async function handleFetch<T>(
  response: Response,
  context: string
): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      `${context}: ${response.statusText}`,
      response.status,
      errorData
    );
  }
  return response.json() as Promise<T>;
}

// Serial Endpoints

export async function getSerialPorts(): Promise<SerialPortInfo> {
  const response = await fetch(`${API_BASE}/serial/ports`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<SerialPortInfo>(response, "Failed to fetch serial ports");
}

export async function connectSerial(): Promise<SerialPortInfo> {
  const response = await fetch(`${API_BASE}/serial/connect`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<SerialPortInfo>(response, "Failed to connect serial");
}

export async function sendMovetoCommand(
  params: MovetoCommandParams
): Promise<ApiResponse> {
  const roundedParams = {
    azimuth: parseFloat(params.azimuth.toFixed(2)),
    elevation: parseFloat(params.elevation.toFixed(2)),
  };
  const response = await fetch(`${API_BASE}/serial/moveto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: roundedParams }),
  });
  return handleFetch<ApiResponse>(response, "Failed to send moveto command");
}

export async function getSerialMovetoStatus(): Promise<ApiResponse> {
  const response = await fetch(`${API_BASE}/serial/moveto`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<ApiResponse>(response, "Failed to check serial moveto status");
}

// Turret Endpoints

export async function getTurretStatus(): Promise<TurretStatus> {
  const response = await fetch(`${API_BASE}/turret/status`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<TurretStatus>(response, "Failed to fetch turret status");
}

export async function sendTurretCommand(
  params: TurretCommandParams
): Promise<ApiResponse> {
  const response = await fetch(`${API_BASE}/turret/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return handleFetch<ApiResponse>(response, "Failed to send turret command");
}

// Aircraft Endpoints

export async function getAircraft(
  params: AircraftParams = {}
): Promise<ApiResponse> {
  const query = new URLSearchParams();
  if (params.lat_min !== undefined) query.append("lat_min", String(params.lat_min));
  if (params.lat_max !== undefined) query.append("lat_max", String(params.lat_max));
  if (params.lon_min !== undefined) query.append("lon_min", String(params.lon_min));
  if (params.lon_max !== undefined) query.append("lon_max", String(params.lon_max));

  const response = await fetch(`${API_BASE}/aircraft?${query.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<ApiResponse>(response, "Failed to fetch aircraft");
}

export async function getAircraftByPosition(
  params: AircraftPositionParams
): Promise<ApiResponse> {
  const query = new URLSearchParams();
  query.append("lat", String(params.lat));
  query.append("lon", String(params.lon));
  if (params.radius_km !== undefined) {
    query.append("radius_km", String(params.radius_km));
  }

  const response = await fetch(`${API_BASE}/aircraft/position?${query.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<ApiResponse>(response, "Failed to fetch aircraft by position");
}

// Health Endpoint

export async function healthCheck(): Promise<ApiResponse> {
  const response = await fetch(`${API_BASE}/health`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleFetch<ApiResponse>(response, "Failed to check health");
}
