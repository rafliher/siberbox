<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ isEdit ? 'Edit Host' : 'Register New Host' }}</h3>
        <button @click="$emit('close')" class="close-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="form">
        <div v-if="!isEdit" class="form-section">
          <h4>Host Information</h4>
          
          <div class="form-group">
            <label for="hostname">Hostname</label>
            <input 
              id="hostname"
              v-model="form.hostname" 
              required 
              placeholder="docker-host-01"
              type="text"
            />
            <p class="form-hint">A friendly name to identify this host</p>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="ssh_port">SSH Port</label>
              <input 
                id="ssh_port"
                type="number" 
                v-model.number="form.ssh_port" 
                min="1" 
                max="65535"
                required 
              />
            </div>

            <div class="form-group">
              <label for="api_port">API Port</label>
              <input 
                id="api_port"
                type="number" 
                v-model.number="form.api_port" 
                min="1" 
                max="65535"
                required 
              />
            </div>
          </div>
        </div>

        <div class="form-section">
          <h4 v-if="!isEdit">Network Configuration</h4>
          
          <div class="form-group">
            <label for="ip">IP Address</label>
            <input 
              id="ip"
              v-model="form.ip" 
              required 
              placeholder="192.168.1.100"
              type="text"
              pattern="^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
            />
            <p class="form-hint">The IPv4 address where this host can be reached</p>
          </div>

          <div class="form-group">
            <label for="max_containers">Maximum Containers</label>
            <input 
              id="max_containers"
              type="number" 
              v-model.number="form.max_containers" 
              min="1" 
              max="1000"
              required 
            />
            <p class="form-hint">Maximum number of containers this host can run simultaneously</p>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" @click="$emit('close')" class="btn btn-secondary">
            Cancel
          </button>
          <button type="submit" class="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            {{ isEdit ? 'Save Changes' : 'Register Host' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    host: {
      type: Object,
      default: () => ({})
    },
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      form: {
        hostname: '',
        ip: '',
        ssh_port: 22,
        api_port: 8003,
        max_containers: 10
      }
    };
  },
  watch: {
    host: {
      immediate: true,
      handler(newHost) {
        if (this.isEdit) {
          this.form.ip = newHost.ip || '';
          this.form.max_containers = newHost.max_containers || 10;
        } else {
          this.form = { ...this.form, ...newHost };
        }
      }
    }
  },
  methods: {
    handleSubmit() {
      if (this.isEdit) {
        const data = {
          ip: this.form.ip,
          max_containers: this.form.max_containers,
        };
        this.$emit('edit-host', data);
      } else {
        const data = {
          hostname: this.form.hostname,
          ip: this.form.ip,
          ssh_port: this.form.ssh_port,
          api_port: this.form.api_port,
          max_containers: this.form.max_containers,
        };
        this.$emit('add-host', data);
      }
    },
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

.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.form-section h4 {
  font-size: 1rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.form-hint {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
  margin: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
}

.form-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: flex-end;
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border);
}

.form-actions button {
  min-width: 120px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column-reverse;
  }
  
  .form-actions button {
    width: 100%;
  }
}
</style>
