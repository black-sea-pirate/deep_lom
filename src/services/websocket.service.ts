/**
 * WebSocket Service for Lobby
 *
 * Provides real-time communication for test lobbies.
 * Handles connection management, reconnection, and message handling.
 */

import { ref, reactive, computed } from "vue";

/**
 * Lobby student data
 */
export interface LobbyStudent {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  status: "waiting" | "ready";
  joined_at: string;
}

/**
 * Lobby state
 */
export interface LobbyState {
  project_id: string;
  status: "waiting" | "active" | "completed";
  students: LobbyStudent[];
  student_count: number;
  max_students: number;
}

/**
 * WebSocket message from server
 */
export interface LobbyMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

/**
 * Connection status
 */
export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

/**
 * Lobby WebSocket service class
 */
export class LobbyWebSocket {
  private ws: WebSocket | null = null;
  private projectId: string = "";
  private role: "teacher" | "student" = "teacher";
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  // Reactive state
  public connectionStatus = ref<ConnectionStatus>("disconnected");
  public lobbyState = reactive<LobbyState>({
    project_id: "",
    status: "waiting",
    students: [],
    student_count: 0,
    max_students: 30,
  });
  public error = ref<string | null>(null);
  public lastMessage = ref<LobbyMessage | null>(null);

  // Event callbacks
  private onStudentJoined?: (student: LobbyStudent) => void;
  private onStudentLeft?: (userId: string, name: string) => void;
  private onStudentReady?: (userId: string, status: string) => void;
  private onTestStarted?: (data: {
    project_id: string;
    started_at: string;
  }) => void;
  private onTestCompleted?: (projectId: string) => void;
  private onLobbyClosed?: (reason: string) => void;
  private onError?: (message: string) => void;

  /**
   * Get WebSocket URL based on current environment
   */
  private getWsUrl(): string {
    const apiUrl =
      import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
    // Convert http(s) to ws(s)
    const wsProtocol = apiUrl.startsWith("https") ? "wss" : "ws";
    const baseUrl = apiUrl.replace(/^https?/, wsProtocol);
    return baseUrl;
  }

  /**
   * Connect to lobby as teacher
   */
  async connectAsTeacher(projectId: string): Promise<boolean> {
    this.projectId = projectId;
    this.role = "teacher";
    return this.connect();
  }

  /**
   * Connect to lobby as student
   */
  async connectAsStudent(projectId: string): Promise<boolean> {
    this.projectId = projectId;
    this.role = "student";
    return this.connect();
  }

  /**
   * Establish WebSocket connection
   */
  private async connect(): Promise<boolean> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return true;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      this.error.value = "No authentication token";
      this.connectionStatus.value = "error";
      return false;
    }

    this.connectionStatus.value = "connecting";
    this.error.value = null;

    return new Promise((resolve) => {
      const wsUrl = `${this.getWsUrl()}/ws/lobby/${this.projectId}/${
        this.role
      }?token=${token}`;

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log("🔌 WebSocket connected");
          this.connectionStatus.value = "connected";
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (event) => {
          console.error("❌ WebSocket error:", event);
          this.error.value = "Connection error";
          this.connectionStatus.value = "error";
          this.onError?.("Connection error");
        };

        this.ws.onclose = (event) => {
          console.log("🔌 WebSocket closed:", event.code, event.reason);
          this.connectionStatus.value = "disconnected";
          this.stopPingInterval();

          // Attempt reconnection if not intentional close
          if (
            event.code !== 1000 &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.scheduleReconnect();
          }

          resolve(false);
        };
      } catch (err) {
        console.error("❌ WebSocket connection failed:", err);
        this.error.value = "Failed to connect";
        this.connectionStatus.value = "error";
        resolve(false);
      }
    });
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(data: string): void {
    try {
      const message: LobbyMessage = JSON.parse(data);
      this.lastMessage.value = message;

      console.log("📩 WebSocket message:", message.type, message.data);

      switch (message.type) {
        case "lobby_update":
          this.updateLobbyState(message.data as LobbyState);
          break;

        case "student_joined":
          const student = message.data as LobbyStudent;
          this.lobbyState.students.push(student);
          this.lobbyState.student_count = this.lobbyState.students.length;
          this.onStudentJoined?.(student);
          break;

        case "student_left":
          const leftData = message.data as { user_id: string; name: string };
          this.lobbyState.students = this.lobbyState.students.filter(
            (s) => s.user_id !== leftData.user_id
          );
          this.lobbyState.student_count = this.lobbyState.students.length;
          this.onStudentLeft?.(leftData.user_id, leftData.name);
          break;

        case "student_ready":
          const readyData = message.data as {
            user_id: string;
            status: "waiting" | "ready";
          };
          const foundStudent = this.lobbyState.students.find(
            (s) => s.user_id === readyData.user_id
          );
          if (foundStudent) {
            foundStudent.status = readyData.status;
          }
          this.onStudentReady?.(readyData.user_id, readyData.status);
          break;

        case "test_started":
          this.lobbyState.status = "active";
          this.onTestStarted?.(
            message.data as { project_id: string; started_at: string }
          );
          break;

        case "test_completed":
          this.lobbyState.status = "completed";
          this.onTestCompleted?.(
            (message.data as { project_id: string }).project_id
          );
          break;

        case "lobby_closed":
          this.onLobbyClosed?.(
            (message.data as { reason?: string }).reason || "Lobby closed"
          );
          this.disconnect();
          break;

        case "error":
          this.error.value = (message.data as { message: string }).message;
          this.onError?.((message.data as { message: string }).message);
          break;

        case "pong":
          // Ping response received
          break;

        default:
          console.warn("Unknown message type:", message.type);
      }
    } catch (err) {
      console.error("Failed to parse WebSocket message:", err);
    }
  }

  /**
   * Update lobby state from server
   */
  private updateLobbyState(state: LobbyState): void {
    this.lobbyState.project_id = state.project_id;
    this.lobbyState.status = state.status;
    this.lobbyState.students = state.students;
    this.lobbyState.student_count = state.student_count;
    this.lobbyState.max_students = state.max_students;
  }

  /**
   * Send message to server
   */
  private send(action: string, data: Record<string, any> = {}): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not connected");
      return false;
    }

    try {
      this.ws.send(JSON.stringify({ action, ...data }));
      return true;
    } catch (err) {
      console.error("Failed to send message:", err);
      return false;
    }
  }

  /**
   * Start test (teacher only)
   */
  startTest(): boolean {
    if (this.role !== "teacher") {
      console.error("Only teacher can start test");
      return false;
    }
    return this.send("start_test");
  }

  /**
   * Kick student from lobby (teacher only)
   */
  kickStudent(userId: string): boolean {
    if (this.role !== "teacher") {
      console.error("Only teacher can kick students");
      return false;
    }
    return this.send("kick_student", { user_id: userId });
  }

  /**
   * Close lobby (teacher only)
   */
  closeLobby(): boolean {
    if (this.role !== "teacher") {
      console.error("Only teacher can close lobby");
      return false;
    }
    return this.send("close_lobby");
  }

  /**
   * Set ready status (student only)
   */
  setReady(isReady: boolean = true): boolean {
    if (this.role !== "student") {
      console.error("Only student can set ready status");
      return false;
    }
    return this.send(isReady ? "ready" : "not_ready");
  }

  /**
   * Leave lobby (student only)
   */
  leaveLobby(): boolean {
    if (this.role !== "student") {
      console.error("Only student can leave lobby");
      return false;
    }
    return this.send("leave");
  }

  /**
   * Disconnect from lobby
   */
  disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
    this.connectionStatus.value = "disconnected";
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      this.send("ping");
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Set event callbacks
   */
  setCallbacks(callbacks: {
    onStudentJoined?: (student: LobbyStudent) => void;
    onStudentLeft?: (userId: string, name: string) => void;
    onStudentReady?: (userId: string, status: string) => void;
    onTestStarted?: (data: { project_id: string; started_at: string }) => void;
    onTestCompleted?: (projectId: string) => void;
    onLobbyClosed?: (reason: string) => void;
    onError?: (message: string) => void;
  }): void {
    this.onStudentJoined = callbacks.onStudentJoined;
    this.onStudentLeft = callbacks.onStudentLeft;
    this.onStudentReady = callbacks.onStudentReady;
    this.onTestStarted = callbacks.onTestStarted;
    this.onTestCompleted = callbacks.onTestCompleted;
    this.onLobbyClosed = callbacks.onLobbyClosed;
    this.onError = callbacks.onError;
  }

  /**
   * Computed properties
   */
  get isConnected(): boolean {
    return this.connectionStatus.value === "connected";
  }

  get studentCount(): number {
    return this.lobbyState.student_count;
  }

  get students(): LobbyStudent[] {
    return this.lobbyState.students;
  }

  get readyCount(): number {
    return this.lobbyState.students.filter((s) => s.status === "ready").length;
  }

  get allReady(): boolean {
    return (
      this.lobbyState.students.length > 0 &&
      this.lobbyState.students.every((s) => s.status === "ready")
    );
  }
}

/**
 * Create a new lobby WebSocket instance
 */
export function useLobbyWebSocket(): LobbyWebSocket {
  return new LobbyWebSocket();
}

export default LobbyWebSocket;
