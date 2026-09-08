<script setup lang="ts">
import { Editor, defaultValueCtx, rootCtx } from "@milkdown/kit/core";
import { listener, listenerCtx } from "@milkdown/kit/plugin/listener";
import { commonmark } from "@milkdown/kit/preset/commonmark";
import { replaceAll } from "@milkdown/kit/utils";
import { Milkdown, useEditor } from "@milkdown/vue";
import { watch } from "vue";

import "@milkdown/kit/prose/view/style/prosemirror.css";

const props = defineProps<{
  modelValue: string;
  placeholder: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  keydown: [event: KeyboardEvent];
}>();

let editorValue = props.modelValue;
let applyingExternalValue = false;

const { get } = useEditor((root) =>
  Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, root);
      ctx.set(defaultValueCtx, props.modelValue);

      ctx.get(listenerCtx).markdownUpdated(
        (_ctx, markdown) => {
          editorValue = markdown;

          if (!applyingExternalValue) {
            emit("update:modelValue", markdown);
          }
        },
      );
    })
    .use(commonmark)
    .use(listener),
);

watch(
  () => props.modelValue,
  (value) => {
    if (value === editorValue) {
      return;
    }

    const editor = get();
    if (!editor) {
      return;
    }

    applyingExternalValue = true;

    try {
      editor.action(replaceAll(value));
      editorValue = value;
    } finally {
      applyingExternalValue = false;
    }
  },
);

function handleKeydown(event: KeyboardEvent) {
  emit("keydown", event);
}
</script>

<template>
  <div
    class="markdown-composer"
    data-testid="chat-input"
    :data-placeholder="placeholder"
    aria-label="Nachricht"
    @keydown="handleKeydown"
  >
    <Milkdown />
  </div>
</template>

<style scoped>
.markdown-composer {
  position: relative;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  color: inherit;
  font-family: ui-monospace, "Consolas", "Liberation Mono", monospace;
  font-size: 0.95rem;
  line-height: 1.45;
}

.markdown-composer :deep(.milkdown) {
  min-height: 100%;
}

.markdown-composer :deep(.ProseMirror) {
  min-height: 100%;
  padding: 0.75rem 3.5rem 0.75rem 0.85rem;
  box-sizing: border-box;
  outline: none;
  white-space: pre-wrap;
}

.markdown-composer:has(:deep(.ProseMirror p:first-child:last-child:empty))::before {
  content: attr(data-placeholder);
  position: absolute;
  padding: 0.75rem 3.5rem 0.75rem 0.85rem;
  color: #999999;
  pointer-events: none;
}
</style>
