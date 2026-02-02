<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Container Details</h3>
        <button @click="$emit('close')" class="close-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">Container ID</span>
          <code class="detail-value">{{ detail.id }}</code>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">Name</span>
          <span class="detail-value">{{ detail.name }}</span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">Status</span>
          <span 
            :class="['status', detail.status === 'running' ? 'status-success' : 'status-error']"
          >
            {{ detail.status }}
          </span>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">IP Address</span>
          <code class="detail-value ip-address">{{ detail.ip_address }}</code>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">User ID</span>
          <code class="detail-value">{{ detail.user_id }}</code>
        </div>
        
        <div class="detail-item">
          <span class="detail-label">Host ID</span>
          <code class="detail-value">{{ detail.host_id }}</code>
        </div>
      </div>

      <div class="vpn-section">
        <h4>VPN Configuration</h4>
        <p class="vpn-hint">Manage VPN profile for this user's container access</p>
        
        <div class="vpn-actions">
          <button 
            @click="downloadVpn()" 
            :disabled="downloading" 
            class="btn btn-secondary"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {{ downloading ? 'Downloading...' : 'Download VPN Profile' }}
          </button>
          
          <button 
            @click="rotateVpn()" 
            :disabled="rotating" 
            class="btn btn-secondary"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            {{ rotating ? 'Rotating...' : 'Rotate VPN Profile' }}
          </button>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="$emit('close')" class="btn btn-primary">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
import { saveAs } from 'file-saver';
import { getVpnProfile, rotateVpnProfile } from '../services/apiUserService';
import { useToast } from 'vue-toastification';

export default {
  props: {
    detail: {
      type: Object,
      required: true
    }
  },
  setup() {
    const toast = useToast();
    return { toast };
  },
  data() {
    return {
      downloading: false,
      rotating: false
    };
  },
  methods: {
    async downloadVpn() {
      this.downloading = true;
      try {
        const resp = await getVpnProfile(this.detail.user_id);
        const blob = new Blob([resp.data], {
          type: 'application/x-openvpn-profile'
        });
        saveAs(blob, `${this.detail.user_id}.ovpn`);
        this.toast.success('VPN profile downloaded successfully');
      } catch (e) {
        console.error('Failed to download VPN profile', e);
        this.toast.error('Failed to download VPN profile');
      } finally {
        this.downloading = false;
      }
    },
    async rotateVpn() {
      this.rotating = true;
      try {
        const resp = await rotateVpnProfile(this.detail.user_id);
        const blob = new Blob([resp.data], {
          type: 'application/x-openvpn-profile'
        });
        saveAs(blob, `${this.detail.user_id}.ovpn`);
        this.toast.success('VPN profile rotated and downloaded successfully');
      } catch (e) {
        console.error('Failed to rotate VPN profile', e);
        this.toast.error('Failed to rotate VPN profile');
      } finally {
        this.rotating = false;
      }
    }
  }
};
</script>

<style scoped>
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2xl);
}

.modal-header h3 {
  font-size: 1.5rem;
  color: var(--color-text-primary);
}

.close-btn {
  width: 2rem;
  height: 2rem;
  padding: 0;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.close-btn:hover {
  background: var(--color-error);
  border-color: var(--color-error);
  color: white;
}

.detail-grid {
  display: grid;
  gap: var(--space-lg);
  margin-bottom: var(--space-2xl);
  padding-bottom: var(--space-2xl);
  border-bottom: 1px solid var(--color-border);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.detail-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.detail-value code,
code.detail-value {
  font-family: var(--font-mono);
  padding: 0.5rem;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  display: block;
  word-break: break-all;
}

.ip-address {
  color: var(--color-primary) !important;
}

.vpn-section {
  margin-bottom: var(--space-2xl);
}

.vpn-section h4 {
  font-size: 1.125rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.vpn-hint {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
}

.vpn-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.vpn-actions button {
  flex: 1;
  min-width: 200px;
}

.vpn-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
}

.modal-footer button {
  min-width: 120px;
}

@media (max-width: 768px) {
  .vpn-actions button {
    min-width: 100%;
  }
}
</style>
