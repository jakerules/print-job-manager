import { io, Socket } from 'socket.io-client'
import { WS_URL } from '../config'

class WebSocketService {
  private socket: Socket | null = null
  private listeners: Map<string, Set<Function>> = new Map()

  connect() {
    if (this.socket?.connected) return

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 5000,
      reconnectionAttempts: 5,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      const user = localStorage.getItem('user')
      if (user) {
        const userData = JSON.parse(user)
        this.socket?.emit('join_notifications', { user_id: userData.id })
      }
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
    })

    // Set up event listeners
    this.socket.on('job:new', (data) => this.emit('job:new', data))
    this.socket.on('job:updated', (data) => this.emit('job:updated', data))
    this.socket.on('stats:update', (data) => this.emit('stats:update', data))
    this.socket.on('notification', (data) => this.emit('notification', data))
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: Function) {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.delete(callback)
    }
  }

  private emit(event: string, data: any) {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach((callback) => callback(data))
    }
  }
}

export const wsService = new WebSocketService()
