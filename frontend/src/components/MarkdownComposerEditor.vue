<script setup lang="ts">
import { Editor, defaultValueCtx, rootCtx } from "@milkdown/kit/core";
import { listener, listenerCtx } from "@milkdown/kit/plugin/listener";
import {
  commonmark,
  createCodeBlockCommand,
  insertHrCommand,
  liftListItemCommand,
  sinkListItemCommand,
  toggleEmphasisCommand,
  toggleInlineCodeCommand,
  toggleLinkCommand,
  toggleStrongCommand,
  wrapInBlockquoteCommand,
  wrapInBulletListCommand,
  wrapInHeadingCommand,
  wrapInOrderedListCommand,
} from "@milkdown/kit/preset/commonmark";
import {
  gfm,
  insertTableCommand,
} from "@milkdown/kit/preset/gfm";
import {
  callCommand,
  replaceAll,
  type $Command,
} from "@milkdown/kit/utils";

import { Milkdown, useEditor } from "@milkdown/vue";
import { watch } from "vue";

import "@milkdown/kit/prose/view/style/prosemirror.css";

const props = defineProps<{
  modelValue: string;
  placeholder: string;
  toolbarEnabled: boolean;
  disabled: boolean;
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
    .use(gfm)
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

function runCommand<T>(
  command: $Command<T>,
  payload?: T,
) {
  if (props.disabled) {
    return;
  }
  const editor = get();
  if (!editor) {
    return;
  }

  editor.action(callCommand(command.key, payload));
}

function insertLink() {
  const href = window.prompt("Link-URL:");
  if (!href?.trim()) {
    return;
  }

  runCommand(toggleLinkCommand, {
    href: href.trim(),
  });
}

function handleKeydown(event: KeyboardEvent) {
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  emit("keydown", event);
}
</script>

<template>
  <div
    class="markdown-composer"
    :class="{
      'markdown-composer--toolbar': toolbarEnabled,
      'markdown-composer--disabled': disabled,
    }"
    data-testid="chat-input"
    :data-placeholder="placeholder"
    aria-label="Nachricht"
    :aria-disabled="disabled"
    :tabindex="disabled ? -1 : undefined"
    @keydown="handleKeydown"
  >
    <div
      v-if="toolbarEnabled"
      class="markdown-toolbar"
      data-testid="markdown-toolbar"
      role="toolbar"
      aria-label="Markdown-Formatierung"
      @mousedown.prevent
    >
      <button
        type="button"
        data-testid="format-bold"
        aria-label="Fett"
        title="Fett"
        @click="runCommand(toggleStrongCommand)"
      >
        <strong>B</strong>
      </button>

      <button
        type="button"
        data-testid="format-italic"
        aria-label="Kursiv"
        title="Kursiv"
        @click="runCommand(toggleEmphasisCommand)"
      >
        <em>I</em>
      </button>

      <span class="toolbar-separator" />

      <button
        type="button"
        data-testid="format-heading-1"
        aria-label="Überschrift 1"
        title="Überschrift 1"
        @click="runCommand(wrapInHeadingCommand, 1)"
      >
        H1
      </button>

      <button
        type="button"
        data-testid="format-heading-2"
        aria-label="Überschrift 2"
        title="Überschrift 2"
        @click="runCommand(wrapInHeadingCommand, 2)"
      >
        H2
      </button>

      <button
        type="button"
        data-testid="format-heading-3"
        aria-label="Überschrift 3"
        title="Überschrift 3"
        @click="runCommand(wrapInHeadingCommand, 3)"
      >
        H3
      </button>

      <span class="toolbar-separator" />

      <button
        type="button"
        data-testid="format-bullet-list"
        aria-label="Aufzählung"
        title="Aufzählung"
        @click="runCommand(wrapInBulletListCommand)"
      >
        •
      </button>

      <button
        type="button"
        data-testid="format-ordered-list"
        aria-label="Nummerierte Liste"
        title="Nummerierte Liste"
        @click="runCommand(wrapInOrderedListCommand)"
      >
        1.
      </button>

      <button
        type="button"
        data-testid="format-outdent"
        aria-label="Einzug verringern"
        title="Einzug verringern"
        @click="runCommand(liftListItemCommand)"
      >
        ⇤
      </button>

      <button
        type="button"
        data-testid="format-indent"
        aria-label="Einzug erhöhen"
        title="Einzug erhöhen"
        @click="runCommand(sinkListItemCommand)"
      >
        ⇥
      </button>

      <span class="toolbar-separator" />

      <button
        type="button"
        data-testid="format-link"
        aria-label="Link"
        title="Link"
        @click="insertLink"
      >
        🔗
      </button>

      <button
        type="button"
        data-testid="format-inline-code"
        aria-label="Inline-Code"
        title="Inline-Code"
        @click="runCommand(toggleInlineCodeCommand)"
      >
        `
      </button>

      <button
        type="button"
        data-testid="format-code-block"
        aria-label="Codeblock"
        title="Codeblock"
        @click="runCommand(createCodeBlockCommand)"
      >
        ```
      </button>

      <button
        type="button"
        data-testid="format-quote"
        aria-label="Zitat"
        title="Zitat"
        @click="runCommand(wrapInBlockquoteCommand)"
      >
        ❞
      </button>

      <button
        type="button"
        data-testid="format-horizontal-rule"
        aria-label="Horizontale Linie"
        title="Horizontale Linie"
        @click="runCommand(insertHrCommand)"
      >
        —
      </button>

      <button
        type="button"
        data-testid="format-table"
        aria-label="Tabelle"
        title="Tabelle einfügen"
        @click="runCommand(insertTableCommand)"
      >
        ▦
      </button>
    </div>

    <Milkdown />
  </div>
</template>

<style scoped>
.markdown-composer {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  overflow: hidden;
  color: inherit;
  font-family: system-ui, sans-serif;
  font-size: 0.95rem;
  line-height: 1.45;
}

.markdown-toolbar {
  min-height: 2.6rem;
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 0.2rem;
  padding: 0.3rem 3.25rem 0.3rem 0.45rem;
  box-sizing: border-box;
  overflow-x: auto;
  border-bottom: 1px solid #e2e2e2;
  background: #fafafa;
}

.markdown-toolbar button {
  min-width: 1.9rem;
  height: 1.9rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  padding: 0.2rem 0.4rem;
  border: 1px solid transparent;
  border-radius: 0.3rem;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.markdown-toolbar button:hover {
  border-color: #d8d8d8;
  background: #eeeeee;
}

.toolbar-separator {
  width: 1px;
  height: 1.35rem;
  flex: 0 0 auto;
  margin: 0 0.15rem;
  background: #d8d8d8;
}

.markdown-composer :deep(.milkdown) {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.markdown-composer :deep(.ProseMirror) {
  min-height: 100%;
  padding: 0.75rem 3.5rem 0.75rem 0.85rem;
  box-sizing: border-box;
  outline: none;
  white-space: pre-wrap;
}

.markdown-composer :deep(.ProseMirror code) {
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  background: #eeeeee;
  font-family: ui-monospace, "Consolas", "Liberation Mono", monospace;
  font-size: 0.92em;
}

.markdown-composer :deep(.ProseMirror pre) {
  margin: 0.75rem 0;
  padding: 0.75rem 0.9rem;
  overflow-x: auto;
  border: 1px solid #dddddd;
  border-radius: 0.4rem;
  background: #f5f5f5;
  font-family: ui-monospace, "Consolas", "Liberation Mono", monospace;
}

.markdown-composer :deep(.ProseMirror pre code) {
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  font-size: inherit;
}

.markdown-composer :deep(.ProseMirror table) {
  margin: 0.75rem 0;
  border-collapse: collapse;
}

.markdown-composer :deep(.ProseMirror th),
.markdown-composer :deep(.ProseMirror td) {
  min-width: 4rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid #d8d8d8;
  text-align: left;
  vertical-align: top;
}

.markdown-composer :deep(.ProseMirror th) {
  background: #f2f2f2;
  font-weight: 600;
}

.markdown-composer :deep(.ProseMirror tr:nth-child(even) td) {
  background: #fafafa;
}

.markdown-composer:has(:deep(.ProseMirror p:first-child:last-child:empty))::before {
  content: attr(data-placeholder);
  position: absolute;
  padding: 0.75rem 3.5rem 0.75rem 0.85rem;
  color: #999999;
  pointer-events: none;
}

.markdown-composer--toolbar:has(:deep(.ProseMirror p:first-child:last-child:empty))::before {
  top: 2.6rem;
}

.markdown-composer--disabled {
  opacity: 0.55;
  pointer-events: none;
}
</style>
