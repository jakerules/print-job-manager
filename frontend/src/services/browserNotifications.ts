/**
 * Browser push notification service.
 * Requests permission and shows native desktop notifications.
 */

class BrowserNotificationService {
  private permission: NotificationPermission = 'default'

  async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) return false

    if (Notification.permission === 'granted') {
      this.permission = 'granted'
      return true
    }

    if (Notification.permission !== 'denied') {
      const result = await Notification.requestPermission()
      this.permission = result
      return result === 'granted'
    }

    return false
  }

  isEnabled(): boolean {
    return 'Notification' in window && Notification.permission === 'granted'
  }

  show(title: string, options?: { body?: string; icon?: string; tag?: string; onClick?: () => void }) {
    if (!this.isEnabled()) return

    const notif = new Notification(title, {
      body: options?.body,
      icon: options?.icon || '/favicon.ico',
      tag: options?.tag,
      badge: '/favicon.ico',
    })

    if (options?.onClick) {
      notif.onclick = () => {
        window.focus()
        options.onClick!()
        notif.close()
      }
    }

    // Auto-close after 8 seconds
    setTimeout(() => notif.close(), 8000)
  }

  notifyNewJob(jobId: string, email: string) {
    this.show('New Print Job', {
      body: `Job ${jobId} from ${email}`,
      tag: `job-${jobId}`,
    })
  }

  notifyJobCompleted(jobId: string) {
    this.show('Job Completed', {
      body: `Job ${jobId} has been marked as completed`,
      tag: `job-${jobId}-done`,
    })
  }

  notifyJobAcknowledged(jobId: string) {
    this.show('Job Acknowledged', {
      body: `Job ${jobId} is now in progress`,
      tag: `job-${jobId}-ack`,
    })
  }
}

export const browserNotifications = new BrowserNotificationService()
