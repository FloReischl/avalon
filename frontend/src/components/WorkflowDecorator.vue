<script setup lang="ts">
import { computed } from "vue";
import type { WorkflowExecution } from "../services/backend";

const props = defineProps<{ execution: WorkflowExecution; messages: string[] }>();

const fallback = computed(() => {
  const prefix = `Workflow ${props.execution.workflow_key}`;
  if (props.execution.state === "running") return `${prefix} läuft …`;
  if (props.execution.state === "completed") return `${prefix} abgeschlossen`;
  if (props.execution.state === "failed") return `${prefix} fehlgeschlagen`;
  return `${prefix}: ${props.execution.state}`;
});
</script>

<template>
  <section class="workflow-decorator" :data-testid="`workflow-${execution.state}`">
    <strong>{{ fallback }}</strong>
    <ul v-if="messages.length">
      <li v-for="entry in messages" :key="entry">{{ entry }}</li>
    </ul>
  </section>
</template>
