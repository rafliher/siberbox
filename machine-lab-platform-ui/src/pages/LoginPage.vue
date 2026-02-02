<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
        </svg>
        <h1>SiberBox</h1>
        <p>Container Orchestration Platform</p>
      </div>
      
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">Email or Username</label>
          <input 
            id="username"
            v-model="username" 
            type="text" 
            placeholder="Enter your email" 
            required 
            autocomplete="username"
          />
        </div>
        
        <div class="form-group">
          <label for="password">Password</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="Enter your password" 
            required 
            autocomplete="current-password"
          />
        </div>
        
        <p v-if="error" class="error-message">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {{ error }}
        </p>
        
        <button type="submit" class="login-btn">
          <span>Sign In</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </form>
      
      <div class="login-footer">
        <p>Secure access to containerized training environments</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import Cookies from 'vue-cookies';
import { login } from '../services/authService';

export default {
  name: 'LoginPage',
  setup() {
    const username = ref('');
    const password = ref('');
    const error = ref('');
    const router = useRouter();
    const store = useStore();
    
    const handleLogin = async () => {
      error.value = '';
      try {
        const response = await login(username.value, password.value);
        Cookies.set("token", response.data.admin_key);
        await store.dispatch("auth/setUser", response.data.user);
        router.push("/dashboard");
      } catch (err) {
        error.value = "Invalid credentials. Please try again.";
      }
    };
    
    return { username, password, error, handleLogin };
  },
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
  position: relative;
}

.login-container {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-2xl);
  box-shadow: var(--shadow-lg);
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-2xl);
}

.logo {
  color: var(--color-primary);
  margin-bottom: var(--space-md);
}

.login-header h1 {
  font-size: 1.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.login-header p {
  font-size: 0.875rem;
  color: var(--color-text-tertiary);
}

.login-form {
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

.error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: 0.875rem;
  margin: 0;
}

.error-message svg {
  flex-shrink: 0;
}

.login-btn {
  width: 100%;
  padding: 0.875rem 1.5rem;
  background: var(--color-primary);
  color: white;
  font-size: 0.9375rem;
  font-weight: 500;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: var(--space-sm);
}

.login-btn:hover {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-glow);
}

.login-btn:active {
  transform: scale(0.98);
}

.login-footer {
  margin-top: var(--space-2xl);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.login-footer p {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
}

@media (max-width: 480px) {
  .login-container {
    padding: var(--space-xl);
  }
}
</style>
