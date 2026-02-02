<template>
  <MainLayout>
    <div class="settings-page">
      <div class="settings-header">
        <div>
          <h1>Settings</h1>
          <p>Manage your authentication and security settings</p>
        </div>
      </div>

      <div class="settings-grid">
        <!-- Admin Token Section -->
        <div class="card">
          <div class="card-header">
            <div class="section-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <div>
              <h3>Admin API Key</h3>
              <p class="section-description">JWT token for API authentication</p>
            </div>
          </div>

          <div class="token-display-wrapper">
            <div class="token-display">
              <code>{{ adminToken || 'Loading...' }}</code>
            </div>
            <button @click="copyToken" class="copy-btn" title="Copy to clipboard">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>

          <button @click="rotateToken" :disabled="rotating" class="btn btn-secondary" style="width: 100%; margin-top: 1rem;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            {{ rotating ? 'Rotating Key...' : 'Rotate API Key' }}
          </button>

          <div class="info-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <p>Rotating the key will invalidate the current token. Make sure to update any external integrations.</p>
          </div>
        </div>

        <!-- Change Password Section -->
        <div class="card">
          <div class="card-header">
            <div class="section-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
            <div>
              <h3>Change Password</h3>
              <p class="section-description">Update your account password</p>
            </div>
          </div>

          <form @submit.prevent="resetPassword" class="password-form">
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <input 
                id="currentPassword"
                v-model="currentPassword" 
                type="password" 
                placeholder="Enter your current password" 
                required 
                autocomplete="current-password"
              />
            </div>

            <div class="form-group">
              <label for="newPassword">New Password</label>
              <input 
                id="newPassword"
                v-model="newPassword" 
                type="password" 
                placeholder="Enter your new password" 
                required 
                autocomplete="new-password"
                minlength="8"
              />
              <p class="form-hint">Minimum 8 characters</p>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm New Password</label>
              <input 
                id="confirmPassword"
                v-model="confirmPassword" 
                type="password" 
                placeholder="Confirm your new password" 
                required 
                autocomplete="new-password"
              />
            </div>

            <button type="submit" :disabled="resetting" class="btn btn-primary" style="width: 100%;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ resetting ? 'Updating Password...' : 'Update Password' }}
            </button>
          </form>

          <div v-if="passwordError" class="error-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <p>{{ passwordError }}</p>
          </div>
        </div>
      </div>

      <!-- Success/Error Messages -->
      <div v-if="message && !passwordError" class="success-message">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <p>{{ message }}</p>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '../layouts/MainLayout.vue';
import { getAdminToken, rotateKey, changePassword } from '../services/authService';
import { useToast } from 'vue-toastification';

export default {
  components: { MainLayout },
  setup() {
    const toast = useToast();
    return { toast };
  },
  data() {
    return {
      adminToken: '',
      message: '',
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
      rotating: false,
      resetting: false,
      passwordError: ''
    };
  },
  async mounted() {
    try {
      const token = await getAdminToken();
      this.adminToken = token;
    } catch (err) {
      this.toast.error('Failed to load admin key');
    }
  },
  methods: {
    async copyToken() {
      try {
        await navigator.clipboard.writeText(this.adminToken);
        this.toast.success('API key copied to clipboard');
      } catch (err) {
        this.toast.error('Failed to copy to clipboard');
      }
    },
    async rotateToken() {
      if (!confirm('Are you sure you want to rotate the API key? This will invalidate the current token.')) {
        return;
      }
      
      this.rotating = true;
      try {
        const newToken = await rotateKey();
        this.adminToken = newToken.data.admin_key;
        this.message = 'API key rotated successfully';
        this.toast.success('API key rotated successfully');
        
        // Clear message after 5 seconds
        setTimeout(() => {
          this.message = '';
        }, 5000);
      } catch (err) {
        console.error(err);
        this.toast.error('Failed to rotate API key');
      } finally {
        this.rotating = false;
      }
    },
    async resetPassword() {
      this.passwordError = '';
      
      // Validation
      if (this.newPassword !== this.confirmPassword) {
        this.passwordError = 'New passwords do not match';
        return;
      }
      
      if (this.newPassword.length < 8) {
        this.passwordError = 'Password must be at least 8 characters long';
        return;
      }
      
      if (this.currentPassword === this.newPassword) {
        this.passwordError = 'New password must be different from current password';
        return;
      }
      
      this.resetting = true;
      try {
        await changePassword(this.currentPassword, this.newPassword);
        this.message = 'Password updated successfully';
        this.toast.success('Password updated successfully');
        
        // Clear form
        this.currentPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
        
        // Clear message after 5 seconds
        setTimeout(() => {
          this.message = '';
        }, 5000);
      } catch (err) {
        console.error(err);
        this.passwordError = 'Failed to update password. Please check your current password.';
        this.toast.error('Failed to update password');
      } finally {
        this.resetting = false;
      }
    }
  }
};
</script>

<style scoped>
.settings-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-2xl) var(--space-lg);
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2xl);
}

.settings-header h1 {
  font-size: 2rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.settings-header p {
  color: var(--color-text-secondary);
  font-size: 0.9375rem;
}

.settings-grid {
  display: grid;
  gap: var(--space-2xl);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-lg);
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-lg);
}

.section-icon {
  width: 48px;
  height: 48px;
  background: var(--color-primary-glow);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}

.card-header h3 {
  font-size: 1.25rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.section-description {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.token-display-wrapper {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.token-display {
  flex: 1;
  padding: var(--space-lg);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.token-display code {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-success);
  word-break: break-all;
  display: block;
  line-height: 1.6;
}

.copy-btn {
  width: 2.75rem;
  height: 2.75rem;
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
  flex-shrink: 0;
}

.copy-btn:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.info-box {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
  margin-top: var(--space-lg);
}

.info-box svg {
  color: var(--color-info);
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.info-box p {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.password-form {
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

.error-box {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  margin-top: var(--space-lg);
}

.error-box svg {
  color: var(--color-error);
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.error-box p {
  font-size: 0.875rem;
  color: var(--color-error);
  margin: 0;
  line-height: 1.6;
}

.success-message {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  margin-top: var(--space-2xl);
}

.success-message svg {
  color: var(--color-success);
  flex-shrink: 0;
}

.success-message p {
  font-size: 0.9375rem;
  color: var(--color-success);
  margin: 0;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .token-display-wrapper {
    flex-direction: column;
  }
  
  .copy-btn {
    width: 100%;
  }
}
</style>
