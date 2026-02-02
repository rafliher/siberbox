<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Deploy New Container</h3>
        <button @click="$emit('close')" class="close-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <form @submit.prevent="submit" class="form">
        <div class="form-group">
          <label for="userId">User ID</label>
          <input 
            id="userId"
            v-model="userId" 
            required 
            placeholder="Enter user UUID"
            type="text"
          />
          <p class="form-hint">The UUID of the user this container will be assigned to</p>
        </div>

        <div class="form-group">
          <label for="zipFile">Docker Compose Package</label>
          <div class="file-upload">
            <input 
              id="zipFile"
              type="file" 
              accept=".zip" 
              @change="handleFileUpload" 
              required 
              ref="fileInput"
              class="file-input"
            />
            <div class="file-upload-area" @click="$refs.fileInput.click()">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <p v-if="!file">Click to upload or drag and drop</p>
              <p v-else class="file-name">{{ file.name }}</p>
              <p class="file-hint">ZIP file containing docker-compose.yml</p>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" @click="$emit('close')" class="btn btn-secondary">
            Cancel
          </button>
          <button type="submit" class="btn btn-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Deploy Container
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      userId: '',
      file: null
    };
  },
  methods: {
    handleFileUpload(event) {
      this.file = event.target.files[0];
    },
    async submit() {
      if (!this.userId || !this.file) {
        alert('Please fill in all required fields');
        return;
      }

      const formData = new FormData();
      formData.append('file', this.file);

      try {
        this.$emit('add-container', this.userId, formData);
        this.$emit('close');
      } catch (error) {
        console.error('Failed to deploy container:', error);
        alert('Failed to deploy container');
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

.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
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

.file-upload {
  position: relative;
}

.file-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.file-upload-area {
  padding: var(--space-2xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  background: var(--color-bg-elevated);
}

.file-upload-area:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-hover);
}

.file-upload-area svg {
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-md);
}

.file-upload-area p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.file-name {
  color: var(--color-primary) !important;
  font-weight: 500;
}

.file-hint {
  margin-top: var(--space-xs) !important;
  font-size: 0.8125rem !important;
  color: var(--color-text-tertiary) !important;
}

.form-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: flex-end;
  margin-top: var(--space-lg);
}

.form-actions button {
  min-width: 120px;
}
</style>
