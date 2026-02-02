<template>
  <div class="app-layout">
    <Navbar />
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script>
import Navbar from '../components/NavigationBar.vue';
export default {
  components: { Navbar }
};
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.main-content {
  flex: 1;
  width: 100%;
}
</style>