<template>
  <nav class="navbar">
    <div class="navbar-container">
      <div class="brand">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
        </svg>
        <span>SiberBox</span>
      </div>
      <div class="nav-links">
        <router-link to="/dashboard" class="nav-link">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
          Dashboard
        </router-link>
        <router-link to="/hosts" class="nav-link">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          Hosts
        </router-link>
        <router-link to="/settings" class="nav-link">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"/>
          </svg>
          Settings
        </router-link>
        <button @click="logout" class="logout-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          Logout
        </button>
      </div>
    </div>
  </nav>
</template>

<script>
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
export default {
  name: 'NavigationBar',
  setup() {
    const store = useStore();
    const router = useRouter();
    const logout = () => {
      store.dispatch('auth/logout');
      router.push('/');
    };
    return { logout };
  }
};
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: blur(8px);
}

.navbar-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: color var(--transition-fast);
}

.brand svg {
  color: var(--color-primary);
}

.brand:hover {
  color: var(--color-primary-light);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  position: relative;
}

.nav-link svg {
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.nav-link:hover svg {
  opacity: 1;
}

.nav-link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-glow);
}

.nav-link.router-link-active svg {
  opacity: 1;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  margin-left: 0.5rem;
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.logout-btn svg {
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.logout-btn:hover svg {
  opacity: 1;
}

@media (max-width: 768px) {
  .nav-link span {
    display: none;
  }
  
  .brand span {
    display: none;
  }
}
</style>
