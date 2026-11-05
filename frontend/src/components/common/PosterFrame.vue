<script setup lang="ts">
import { computed, useSlots } from "vue"

const props = withDefaults(
  defineProps<{
    src?: string
    alt?: string
    crop?: boolean | null
    broken?: boolean
    tag?: "div" | "button"
    disabled?: boolean
    title?: string
  }>(),
  {
    src: "",
    alt: "",
    crop: true,
    broken: false,
    tag: "div",
    disabled: false,
  },
)

const emit = defineEmits<{
  error: [event: Event]
}>()

const slots = useSlots()
const showImage = computed(() => Boolean(props.src) && !props.broken)
const showEmpty = computed(() => !showImage.value && Boolean(slots.empty))
</script>

<template>
  <component
    :is="tag"
    class="poster-frame"
    :class="{ 'show-full': crop === false }"
    :type="tag === 'button' ? 'button' : undefined"
    :disabled="tag === 'button' ? disabled : undefined"
    :title="title"
  >
    <img
      v-if="showImage && crop === false"
      class="poster-frame-fill"
      :src="src"
      alt=""
      aria-hidden="true"
      loading="lazy"
      decoding="async"
      referrerpolicy="no-referrer"
    />
    <img
      v-if="showImage"
      class="poster-frame-image"
      :src="src"
      :alt="alt"
      loading="lazy"
      decoding="async"
      referrerpolicy="no-referrer"
      @error="emit('error', $event)"
    />
    <div v-if="showEmpty" class="poster-frame-empty">
      <slot name="empty" />
    </div>
    <slot />
  </component>
</template>

<style scoped>
.poster-frame {
  position: relative;
  display: block;
  width: var(--poster-width, 100%);
  aspect-ratio: 2 / 3;
  overflow: hidden;
  padding: 0;
  border: 0;
  background-color: #1a1a1a;
  color: inherit;
  font: inherit;
  text-align: left;
}

.poster-frame-fill,
.poster-frame-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  user-select: none;
}

.poster-frame-fill {
  object-fit: cover;
  object-position: center;
  filter: blur(20px) saturate(1.1) brightness(0.65);
  transform: scale(1.2);
}

.poster-frame-image {
  object-fit: cover;
  object-position: right center;
  z-index: 1;
}

.poster-frame.show-full .poster-frame-image {
  object-fit: contain;
  object-position: center;
}

.poster-frame-empty {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

button.poster-frame:disabled {
  cursor: default;
  opacity: 1;
}
</style>
