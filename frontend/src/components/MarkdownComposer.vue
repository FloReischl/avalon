<script setup lang="ts">
import { MilkdownProvider } from "@milkdown/vue";

import MarkdownComposerEditor from "./MarkdownComposerEditor.vue";

defineProps<{
  modelValue: string;
  placeholder: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  keydown: [event: KeyboardEvent];
}>();
</script>

<template>
  <MilkdownProvider>
    <MarkdownComposerEditor
      :model-value="modelValue"
      :placeholder="placeholder"
      @update:model-value="emit('update:modelValue', $event)"
      @keydown="emit('keydown', $event)"
    />
  </MilkdownProvider>
</template>

