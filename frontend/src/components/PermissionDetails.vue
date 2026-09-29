<script setup lang="ts">
defineProps<{
  context: string;
  permissionKey: string;
  validityType: "permanent" | "duration" | "range";
  granted: boolean;
  readOnly?: boolean;
}>();
</script>

<template>
  <section class="permission-details">
    <h1>Permission</h1>
    <p>{{ context }}.{{ permissionKey }}</p>
    <p class="permission-status">
      {{ granted ? "Bereits erteilt" : "Erteilbar" }}
      <span v-if="readOnly"> · nur lesbar</span>
    </p>
    <slot />
  </section>
</template>

<style scoped>
.permission-details { padding: 1.5rem; }
.permission-status { color: #444; }
</style>
