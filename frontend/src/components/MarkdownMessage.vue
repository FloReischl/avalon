<script setup lang="ts">
import { ref } from "vue";

import MarkdownIt from "markdown-it";

import hljs from "highlight.js";
import "highlight.js/styles/github.css";

import { openExternalLink } from "../services/externalLinks";

defineProps<{
  content: string;
}>();

const rootElement = ref<HTMLElement>();

function getRenderedHtml(): string {
  return rootElement.value?.innerHTML ?? "";
}

function getPlainText(): string {
  const root = rootElement.value;
  if (!root) {
    return "";
  }

  const clone = root.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("[data-copy-code]").forEach((element) => {
    element.remove();
  });

  return (
    clone.innerText
    || clone.textContent
    || ""
  ).trim();
}

defineExpose({
  getRenderedHtml,
  getPlainText,
});


function highlightCode(code: string, language: string): string {
  if (language && hljs.getLanguage(language)) {
    return hljs.highlight(code, {
      language,
      ignoreIllegals: true,
    }).value;
  }

  return MarkdownIt().utils.escapeHtml(code);
}

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: false,
  highlight: highlightCode,
});

markdown.renderer.rules.fence = (tokens, index): string => {
  const token = tokens[index];
  const language = token.info.trim().split(/\s+/)[0];
  const highlighted = highlightCode(token.content, language);
  const languageClass = language
    ? ` class="hljs language-${markdown.utils.escapeHtml(language)}"`
    : ' class="hljs"';

  return [
    '<div class="code-block">',
    '<button type="button" class="copy-code-button" data-copy-code>Copy</button>',
    `<pre><code${languageClass}>${highlighted}</code></pre>`,
    "</div>",
  ].join("");
};

async function handleClick(event: MouseEvent) {
  const target = event.target;

  if (!(target instanceof Element)) {
    return;
  }

  const copyButton = target.closest<HTMLElement>("[data-copy-code]");
  if (copyButton) {
    const code = copyButton
      .closest(".code-block")
      ?.querySelector("code")
      ?.textContent;

    if (code !== undefined) {
      await navigator.clipboard.writeText(code);
    }

    return;
  }

  const link = target.closest<HTMLAnchorElement>("a[href]");
  if (!link) {
    return;
  }

  event.preventDefault();

  try {
    await openExternalLink(link.href);
  } catch (error) {
    console.error("[external-link] failed to open link", error);
  }
}
</script>

<template>
  <div
    ref="rootElement"
    class="markdown-message"
    data-testid="markdown-message"
    @click="handleClick"
    v-html="markdown.render(content)"
  />
</template>

<style scoped>
.markdown-message {
  overflow-wrap: anywhere;
}

.markdown-message :deep(> :first-child) {
  margin-top: 0;
}

.markdown-message :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-message :deep(pre) {
  overflow-x: auto;
  margin: 0;
  padding: 1rem;
}

.markdown-message :deep(.code-block) {
  position: relative;
  margin: 0.75rem 0;
  overflow: hidden;
  border: 1px solid #d8d8d8;
  border-radius: 0.4rem;
}

.markdown-message :deep(.copy-code-button) {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  z-index: 1;
}

.markdown-message :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-message :deep(th),
.markdown-message :deep(td) {
  padding: 0.4rem 0.65rem;
  border: 1px solid #d8d8d8;
}

.markdown-message :deep(blockquote) {
  margin-left: 0;
  padding-left: 1rem;
  border-left: 3px solid #c0c0c0;
}

.markdown-message :deep(a) {
  text-decoration: underline;
  cursor: pointer;
}
</style>
