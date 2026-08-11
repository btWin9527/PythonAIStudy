<template>
  <a-card :title="item.name" size="small" class="attraction-card">
    <template #extra v-if="editMode">
      <a-space>
        <a-button size="small" @click="$emit('moveUp')" :disabled="index === 0">↑</a-button>
        <a-button size="small" @click="$emit('moveDown')" :disabled="isLast">↓</a-button>
        <a-button size="small" danger @click="$emit('delete')">🗑️</a-button>
      </a-space>
    </template>

    <div class="attraction-image-wrapper">
      <img :src="imageSrc" :alt="item.name" class="attraction-image" @error="onImageError" />
      <div class="attraction-badge"><span class="badge-number">{{ index + 1 }}</span></div>
      <div v-if="item.ticket_price" class="price-tag">¥{{ item.ticket_price }}</div>
    </div>

    <div v-if="editMode">
      <p><strong>地址:</strong></p>
      <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />
      <p><strong>游览时长(分钟):</strong></p>
      <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />
      <p><strong>描述:</strong></p>
      <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
    </div>

    <div v-else>
      <p><strong>地址:</strong> {{ item.address }}</p>
      <p><strong>游览时长:</strong> {{ item.visit_duration }}分钟</p>
      <p><strong>描述:</strong> {{ item.description }}</p>
      <p v-if="item.rating"><strong>评分:</strong> {{ item.rating }}⭐</p>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { handleImageError } from '@/utils/image'

defineProps<{
  item: any
  index: number
  editMode: boolean
  isLast: boolean
  imageSrc: string
}>()

defineEmits<{
  moveUp: []
  moveDown: []
  delete: []
}>()

const onImageError = handleImageError
</script>

<style scoped>
.attraction-image-wrapper { position: relative; margin-bottom: 12px; border-radius: 8px; overflow: hidden; }
.attraction-image { width: 100%; height: 200px; object-fit: cover; transition: transform 0.3s ease; }
.attraction-image-wrapper:hover .attraction-image { transform: scale(1.05); }
.attraction-badge { position: absolute; top: 12px; left: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2); }
.badge-number { font-size: 18px; }
.price-tag { position: absolute; top: 12px; right: 12px; background: rgba(255, 77, 79, 0.9); color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2); }
</style>
