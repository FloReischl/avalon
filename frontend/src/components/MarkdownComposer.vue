<script setup lang="ts">
import { MilkdownProvider } from "@milkdown/vue";

import MarkdownComposerEditor from "./MarkdownComposerEditor.vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder: string;
    toolbarEnabled?: boolean;
    disabled?: boolean;
  }>(),
  {
    toolbarEnabled: false,
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
  keydown: [event: KeyboardEvent];
}>();
</script>

<template>
  <MilkdownProvider>
    <MarkdownComposerEditor
      :model-value="props.modelValue"
      :placeholder="props.placeholder"
      :toolbar-enabled="props.toolbarEnabled"
      :disabled="props.disabled"
      @update:model-value="emit('update:modelValue', $event)"
      @keydown="emit('keydown', $event)"
    />
  </MilkdownProvider>
</template>
