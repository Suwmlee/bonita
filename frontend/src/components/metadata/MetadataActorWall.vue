<script setup lang="ts">
import type { ActorSummary } from "@/client"
import { actorGradient, actorInitial } from "@/utils/actorVisual"
import { resourceImageUrl } from "@/utils/resourceImage"
import { ref } from "vue"
import { useI18n } from "vue-i18n"

defineProps<{
  actors: ActorSummary[]
}>()

const emit = defineEmits<{
  select: [actor: ActorSummary]
}>()

const { t } = useI18n()
const broken = ref<Record<string, boolean>>({})
const loaded = ref<Record<string, boolean>>({})

function markBroken(key: string) {
  broken.value = { ...broken.value, [key]: true }
}

function markLoaded(key: string) {
  loaded.value = { ...loaded.value, [key]: true }
}

function coversOf(actor: ActorSummary) {
  return (actor.covers ?? [])
    .filter((cover) => cover.path && !broken.value[`cover:${actor.name}:${cover.path}`])
    .slice(0, 4)
}

function showPhoto(actor: ActorSummary) {
  return Boolean(actor.photo) && !broken.value[`photo:${actor.name}`]
}
</script>

<template>
  <VRow>
    <VCol
      v-for="actor in actors"
      :key="actor.name"
      cols="6"
      sm="4"
      md="4"
      lg="3"
      xl="2"
      class="d-flex"
    >
      <article
        class="actor-card"
        role="button"
        tabindex="0"
        :title="actor.name"
        @click="emit('select', actor)"
        @keydown.enter="emit('select', actor)"
      >
        <div class="actor-stage" :style="{ background: actorGradient(actor.name) }">
          <div
            v-if="coversOf(actor).length"
            class="mosaic"
            :class="`mosaic-${coversOf(actor).length}`"
          >
            <div
              v-for="cover in coversOf(actor)"
              :key="cover.path"
              class="mosaic-cell"
              :class="{ 'show-full': cover.crop === false }"
            >
              <img
                v-if="cover.crop === false"
                class="mosaic-fill"
                :src="resourceImageUrl(cover.path)"
                alt=""
              />
              <img
                class="mosaic-image"
                :src="resourceImageUrl(cover.path)"
                alt=""
                @error="markBroken(`cover:${actor.name}:${cover.path}`)"
              />
            </div>
          </div>
          <div class="stage-shade" />
          <div class="actor-copy">
            <div class="avatar" :style="{ background: actorGradient(actor.name) }">
              <img
                v-if="showPhoto(actor)"
                v-show="loaded[`photo:${actor.name}`]"
                :src="resourceImageUrl(actor.photo || '')"
                :alt="actor.name"
                @load="markLoaded(`photo:${actor.name}`)"
                @error="markBroken(`photo:${actor.name}`)"
              />
              <span v-if="!loaded[`photo:${actor.name}`] || !showPhoto(actor)">{{ actorInitial(actor.name) }}</span>
            </div>
            <p class="actor-name">{{ actor.name }}</p>
            <p class="actor-count">{{ t('pages.metadata.workCount', { count: actor.count }) }}</p>
          </div>
        </div>
      </article>
    </VCol>
  </VRow>
</template>

<style scoped>
.actor-card {
  width: 100%;
  border-radius: 18px;
  overflow: hidden;
  cursor: pointer;
  background: #141414;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.actor-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.22);
}

.actor-card:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 3px;
}

.actor-stage {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
}

.mosaic {
  position: absolute;
  inset: 0;
  display: grid;
  gap: 2px;
}

.mosaic-cell {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #1a1a1a;
}

.mosaic-fill,
.mosaic-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.mosaic-fill {
  object-fit: cover;
  object-position: center;
  filter: blur(14px) saturate(1.1) brightness(0.65);
  transform: scale(1.15);
}

.mosaic-image {
  object-fit: cover;
  object-position: right center;
}

.mosaic-cell.show-full .mosaic-image {
  object-fit: contain;
  object-position: center;
  z-index: 1;
}

.mosaic-1 {
  grid-template-columns: 1fr;
}

.mosaic-2 {
  grid-template-columns: 1fr 1fr;
}

.mosaic-3 {
  grid-template-columns: 1.35fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.mosaic-3 .mosaic-cell:first-child {
  grid-row: 1 / span 2;
}

.mosaic-4 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.stage-shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to top, rgba(0, 0, 0, 0.82) 0%, rgba(0, 0, 0, 0.28) 42%, rgba(0, 0, 0, 0.12) 100%);
}

.actor-copy {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 12px 16px;
  color: #fff;
}

.avatar {
  position: relative;
  width: 84px;
  height: 84px;
  margin-bottom: 10px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
  line-height: 1;
  color: #fff;
}

.avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.actor-name {
  width: 100%;
  margin: 0;
  font-size: 1.02rem;
  font-weight: 650;
  line-height: 1.3;
  text-align: center;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.45);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.actor-count {
  margin: 8px 0 0;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(8px);
}
</style>
