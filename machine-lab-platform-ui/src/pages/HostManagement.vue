<template>
  <MainLayout>
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
    
    <div class="dashboard">
      <div class="dashboard-header">
        <div>
          <h1>Host Management</h1>
          <p>Monitor and manage container host machines</p>
        </div>
        <button @click="showAddHostModal = true" class="btn btn-primary">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Add Host
        </button>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon healthy">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Healthy Hosts</p>
            <p class="stat-value">{{ healthyCount }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon offline">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Offline Hosts</p>
            <p class="stat-value">{{ offlineCount }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon total">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Total Hosts</p>
            <p class="stat-value">{{ hosts.length }}</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Registered Hosts</h3>
          <div class="search-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input 
              v-model="searchQuery" 
              placeholder="Search hosts..." 
              class="search-input"
            />
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Hostname</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Resource Usage</th>
                <th>Last Seen</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="host in filteredHosts" :key="host.id">
                <td>
                  <div class="hostname-cell">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="2" y="3" width="20" height="14" rx="2"/>
                      <line x1="8" y1="21" x2="16" y2="21"/>
                      <line x1="12" y1="17" x2="12" y2="21"/>
                    </svg>
                    <span>{{ host.hostname }}</span>
                  </div>
                </td>
                <td>
                  <code class="ip-address">{{ host.ip }}</code>
                </td>
                <td>
                  <span 
                    :class="['status', host.status === 'healthy' ? 'status-success' : 'status-error']"
                  >
                    {{ host.status }}
                  </span>
                </td>
                <td>
                  <div class="resource-usage">
                    <div class="resource-item">
                      <span class="resource-label">CPU</span>
                      <div class="progress-bar">
                        <div 
                          class="progress-fill" 
                          :style="{ width: host.cpu_percent + '%', background: getResourceColor(host.cpu_percent) }"
                        ></div>
                      </div>
                      <span class="resource-value">{{ host.cpu_percent }}%</span>
                    </div>
                    <div class="resource-item">
                      <span class="resource-label">MEM</span>
                      <div class="progress-bar">
                        <div 
                          class="progress-fill" 
                          :style="{ width: host.mem_percent + '%', background: getResourceColor(host.mem_percent) }"
                        ></div>
                      </div>
                      <span class="resource-value">{{ host.mem_percent }}%</span>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="timestamp">{{ formatTime(host.last_seen) }}</span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button @click="editHost(host)" class="btn-icon btn-ghost" title="Edit">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button @click="deleteHost(host.id)" class="btn-icon btn-ghost" title="Delete">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredHosts.length === 0">
                <td colspan="6" class="empty-state">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2"/>
                    <line x1="8" y1="21" x2="16" y2="21"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                  <p>No hosts found</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <HostForm
        v-if="showAddHostModal"
        :key="'add-host-form'"
        @add-host="handleAddHost"
        @close="showAddHostModal = false"
      />
      
      <HostForm
        v-if="showEditHostModal"
        :key="'edit-host-form'"
        :host="selectedHost"
        :isEdit="true"
        @edit-host="handleEditHost"
        @close="showEditHostModal = false"
      />
      
      <div v-if="showCredentialModal" class="modal-overlay">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Host Registered Successfully</h3>
            <p>Save these credentials securely. They won't be shown again.</p>
          </div>
          
          <div class="credential-section">
            <label>Host ID</label>
            <div class="credential-box">
              <code>{{ newHostCredentials.host_id }}</code>
              <button @click="copyToClipboard(newHostCredentials.host_id)" class="copy-btn" title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="credential-section">
            <label>Server Key</label>
            <div class="credential-box">
              <code class="credential-key">{{ newHostCredentials.server_key }}</code>
              <button @click="copyToClipboard(newHostCredentials.server_key)" class="copy-btn" title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </button>
            </div>
          </div>
          
          <button @click="showCredentialModal = false" class="btn btn-primary" style="width: 100%">
            Done
          </button>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import { listHost, deleteHost, registerHost, updateHost } from '../services/apiHostService';
import HostForm from '../components/HostForm.vue';
import { useToast } from 'vue-toastification';
import MainLayout from '../layouts/MainLayout.vue';
import dayjs from 'dayjs';

export default {
  name: 'HostManagement',
  components: { MainLayout, HostForm },
  data() {
    return {
      hosts: [],
      showEditHostModal: false,
      selectedHost: null,
      showAddHostModal: false,
      isLoading: false,
      showCredentialModal: false,
      searchQuery: '',
      newHostCredentials: {
        host_id: '',
        server_key: ''
      },
    };
  },
  setup() {
    const toast = useToast();
    return { toast };
  },
  computed: {
    filteredHosts() {
      const q = this.searchQuery.toLowerCase();
      return this.hosts.filter(h =>
        h.hostname.toLowerCase().includes(q) ||
        h.ip.toLowerCase().includes(q) ||
        h.status.toLowerCase().includes(q)
      );
    },
    healthyCount() {
      return this.hosts.filter(h => h.status === 'healthy').length;
    },
    offlineCount() {
      return this.hosts.filter(h => h.status === 'offline').length;
    }
  },
  methods: {
    async fetchHosts() {
      try {
        const response = await listHost();
        this.hosts = response.data;
      } catch (error) {
        console.error('Failed to fetch hosts:', error);
        this.toast.error('Failed to load hosts');
      }
    },
    formatTime(timeString) {
      if (!timeString) return 'Never';
      return dayjs(timeString).format('MMM D, YYYY HH:mm');
    },
    getResourceColor(percent) {
      if (percent >= 90) return 'var(--color-error)';
      if (percent >= 75) return 'var(--color-warning)';
      return 'var(--color-success)';
    },
    async handleAddHost(data) {
      if (this.loading) return;
      if (!data) return;
      this.isLoading = true;
      try {
        const response = await registerHost(data);
        this.newHostCredentials = {
          host_id: response.data.host_id,
          server_key: response.data.server_key
        };
        this.showCredentialModal = true;
        this.fetchHosts();
        this.toast.success('Host registered successfully');
        this.showAddHostModal = false;
      } catch (error) {
        console.error('Failed to add host:', error);
        this.toast.error('Failed to register host');
      } finally {
        this.isLoading = false;
      }
    },
    async handleEditHost(data) {
      if (this.loading) return;
      this.isLoading = true;
      try {
        await updateHost(this.selectedHost.id, data);
        this.fetchHosts();
        this.toast.success('Host updated successfully');
        this.showEditHostModal = false;
        this.selectedHost = null;
      } catch (error) {
        console.error('Failed to edit host:', error);
        this.toast.error('Failed to update host');
      } finally {
        this.isLoading = false;
      }
    },
    editHost(host) {
      this.selectedHost = host;
      this.showEditHostModal = true;
    },
    async deleteHost(id) {
      if (!confirm('Are you sure you want to delete this host?')) return;
      this.isLoading = true;
      try {
        await deleteHost(id);
        this.fetchHosts();
        this.toast.success('Host deleted successfully');
      } catch (error) {
        console.error('Failed to delete host:', error);
        this.toast.error('Failed to delete host');
      } finally {
        this.isLoading = false;
      }
    },
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        this.toast.success('Copied to clipboard');
      } catch (err) {
        this.toast.error('Failed to copy');
      }
    }
  },
  mounted() {
    this.fetchHosts();
  }
};
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-2xl) var(--space-lg);
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2xl);
}

.dashboard-header h1 {
  font-size: 2rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.dashboard-header p {
  color: var(--color-text-secondary);
  font-size: 0.9375rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-2xl);
}

.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  transition: border-color var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--color-border-hover);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.healthy {
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.stat-icon.offline {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}

.stat-icon.total {
  background: rgba(220, 38, 38, 0.1);
  color: var(--color-primary);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-lg);
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-lg);
}

.card-header h3 {
  font-size: 1.25rem;
  color: var(--color-text-primary);
}

.search-box {
  position: relative;
  width: 100%;
  max-width: 320px;
}

.search-box svg {
  position: absolute;
  left: 0.875rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.625rem 0.875rem 0.625rem 2.5rem;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-text-primary);
  transition: all var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}

.hostname-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-text-primary);
  font-weight: 500;
}

.hostname-cell svg {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.ip-address {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.resource-usage {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 180px;
}

.resource-item {
  display: grid;
  grid-template-columns: 32px 1fr 45px;
  align-items: center;
  gap: 0.5rem;
}

.resource-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.progress-bar {
  height: 6px;
  background: var(--color-bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width var(--transition-normal);
  border-radius: 3px;
}

.resource-value {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-align: right;
}

.timestamp {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.empty-state {
  text-align: center;
  padding: var(--space-2xl) var(--space-lg);
  color: var(--color-text-tertiary);
}

.empty-state svg {
  margin-bottom: var(--space-md);
  opacity: 0.5;
}

.empty-state p {
  font-size: 0.9375rem;
}

.modal-header {
  margin-bottom: var(--space-2xl);
}

.modal-header h3 {
  font-size: 1.5rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.modal-header p {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.credential-section {
  margin-bottom: var(--space-lg);
}

.credential-section label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-sm);
}

.credential-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.credential-box code {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  word-break: break-all;
}

.credential-key {
  color: var(--color-success) !important;
}

.copy-btn {
  padding: 0.5rem;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.copy-btn:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-lg);
  }
  
  .dashboard-header button {
    width: 100%;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .search-box {
    max-width: 100%;
  }
  
  .resource-usage {
    min-width: auto;
  }
}
</style>
