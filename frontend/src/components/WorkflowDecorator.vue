<script setup lang="ts">
import { computed } from "vue";
import type { WorkflowExecution } from "../services/backend";

const props = defineProps<{ execution: WorkflowExecution }>();

const fallback = computed(() => {
  if (props.execution.state === "running") return "Workflow läuft …";
  if (props.execution.state === "completed") return "Workflow abgeschlossen";
  if (props.execution.state === "failed") return "Workflow fehlgeschlagen";
  return `Workflow: ${props.execution.state}`;
});
</script>

<template>
  <section class="workflow-decorator" :data-testid="`workflow-${execution.state}`">
    <strong>{{ fallback }}</strong>
    <ul v-if="execution.progress_content">
      <li v-for="entry in execution.progress_content" :key="entry">{{ entry }}</li>
    </ul>
  </section>
</template>
