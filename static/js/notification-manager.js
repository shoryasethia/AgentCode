/**
 * NotificationManager - Handles toast notifications
 */
class NotificationManager {
    constructor() {
        this.container = document.getElementById('notificationContainer');
        this.notifications = new Map();
        this.idCounter = 0;
    }

    /**
     * Show notification
     */
    show(title, message, type = 'info', duration = 5000, closable = true) {
        const id = ++this.idCounter;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.dataset.id = id;
        
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">${title}</span>
                ${closable ? '<span class="notification-close">&times;</span>' : ''}
            </div>
            <div class="notification-body">${message}</div>
        `;

        // Add close handler
        if (closable) {
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => this.remove(id));
        }

        this.container.appendChild(notification);
        this.notifications.set(id, notification);

        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }

        return id;
    }

    /**
     * Remove notification
     */
    remove(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }

    /**
     * Show success notification
     */
    success(title, message, duration = 3000) {
        return this.show(title, message, 'success', duration);
    }

    /**
     * Show error notification
     */
    error(title, message, duration = 8000) {
        return this.show(title, message, 'error', duration);
    }

    /**
     * Show warning notification
     */
    warning(title, message, duration = 5000) {
        return this.show(title, message, 'warning', duration);
    }

    /**
     * Show info notification
     */
    info(title, message, duration = 5000) {
        return this.show(title, message, 'info', duration);
    }

    /**
     * Show persistent notification (doesn't auto-close)
     */
    persistent(title, message, type = 'info') {
        return this.show(title, message, type, 0);
    }

    /**
     * Clear all notifications
     */
    clearAll() {
        this.notifications.forEach((notification, id) => {
            this.remove(id);
        });
    }
}