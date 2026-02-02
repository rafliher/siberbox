<template>
  <MainLayout>
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
    
    <div class="dashboard">
      <div class="dashboard-header">
        <div>
          <h1>Container Management</h1>
          <p>Monitor and manage active container instances</p>
        </div>
        <button @click="showAddContainerForm = true" class="btn btn-primary">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Deploy Container
        </button>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon running">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Running</p>
            <p class="stat-value">{{ runningCount }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon stopped">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Stopped</p>
            <p class="stat-value">{{ stoppedCount }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon total">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </div>
          <div class="stat-content">
            <p class="stat-label">Total Containers</p>
            <p class="stat-value">{{ containers.length }}</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Active Containers</h3>
          <div class="search-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input 
              v-model="searchQuery" 
              placeholder="Search by name, status, user..." 
              class="search-input"
            />
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Container ID</th>
                <th>Status</th>
                <th>User ID</th>
                <th>Host ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="container in filteredContainers" :key="container.id">
                <td>
                  <code class="container-id">{{ container.id.substring(0, 12) }}</code>
                </td>
                <td>
                  <span 
                    :class="['status', container.status === 'running' ? 'status-success' : 'status-error']"
                  >
                    {{ container.status }}
                  </span>
                </td>
                <td>
                  <code class="user-id">{{ container.user_id.substring(0, 8) }}</code>
                </td>
                <td>
                  <code class="host-id">{{ container.host_id.substring(0, 8) }}</code>
                </td>
                <td>
                  <div class="action-buttons">
                    <button @click="viewDetail(container.id)" class="btn-icon btn-ghost" title="View Details">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                    <button @click="restart(container.id)" class="btn-icon btn-ghost" title="Restart">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                      </svg>
                    </button>
                    <button @click="remove(container.id)" class="btn-icon btn-ghost" title="Delete">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredContainers.length === 0">
                <td colspan="5" class="empty-state">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="7" height="7" rx="1"/>
                    <rect x="14" y="3" width="7" height="7" rx="1"/>
                    <rect x="3" y="14" width="7" height="7" rx="1"/>
                    <rect x="14" y="14" width="7" height="7" rx="1"/>
                  </svg>
                  <p>No containers found</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <ContainerForm
        v-if="showAddContainerForm"
        @add-container="handleAddContainer"
        @close="showAddContainerForm = false"
      />
      
      <ContainerDetail
        v-if="showDetailModal"
        :detail="detailData"
        @close="showDetailModal = false"
      />
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '../layouts/MainLayout.vue';
import ContainerForm from '../components/ContainerForm.vue';
import ContainerDetail from '../components/ContainerDetail.vue';
import { listContainer, deleteContainer, restartContainer, getContainerData, addContainer } from '../services/apiContainerService';
import { useToast } from 'vue-toastification';

export default {
  components: { MainLayout, ContainerForm, ContainerDetail },
  data() {
    return {
      searchQuery: '',
      showAddContainerForm: false,
      containers: [],
      isLoading: false,
      showDetailModal: false,
      detailData: {},
    };
  },
  setup() {
    const toast = useToast();
    return { toast };
  },
  computed: {
    filteredContainers() {
      const q = this.searchQuery.toLowerCase();
      return this.containers.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.host_id.toLowerCase().includes(q) ||
        c.user_id.toLowerCase().includes(q) ||
        c.status.toLowerCase().includes(q)
      );
    },
    runningCount() {
      return this.containers.filter(c => c.status === 'running').length;
    },
    stoppedCount() {
      return this.containers.filter(c => c.status === 'stopped').length;
    }
  },
  methods: {
    async handleAddContainer(user_id, data) {
      if (this.isLoading) return;
      if (!data) return;
      this.isLoading = true;
      try {
        await addContainer(user_id, data);
        this.fetchContainers();
        this.toast.success('Container deployed successfully');
        this.showAddContainerForm = false;
      } catch (error) {
        console.error('Failed to deploy container:', error);
        this.toast.error('Failed to deploy container');
      } finally {
        this.isLoading = false;
      }
    },
    async viewDetail(id) {
      this.isLoading = true;
      try {
        const res = await getContainerData(id);
        this.detailData = res.data;
        this.showDetailModal = true;
      } catch (err) {
        console.error('Failed to fetch details:', err);
        this.toast.error('Failed to fetch container details');
      } finally {
        this.isLoading = false;
      }
    },
    async fetchContainers() {
      this.isLoading = true;
      try {
        const res = await listContainer();
        this.containers = res.data;
      } catch (error) {
        console.error(error);
        this.toast.error('Failed to load containers');
      } finally {
        this.isLoading = false;
      }
    },
    async restart(id) {
      this.isLoading = true;
      try {
        await restartContainer(id);
        this.fetchContainers();
        this.toast.success('Container restarted successfully');
      } catch (error) {
        console.error(error);
        this.toast.error('Failed to restart container');
      } finally {
        this.isLoading = false;
      }
    },
    async remove(id) {
      if (!confirm('Are you sure you want to delete this container?')) return;
      this.isLoading = true;
      try {
        await deleteContainer(id);
        this.toast.success('Container deleted');
        this.fetchContainers();
      } catch (error) {
        console.error(error);
        this.toast.error('Failed to delete container');
      } finally {
        this.isLoading = false;
      }
    }
  },
  mounted() {
    this.fetchContainers();
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

.stat-icon.running {
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.stat-icon.stopped {
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

.container-id,
.user-id,
.host-id {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
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
}
</style>
