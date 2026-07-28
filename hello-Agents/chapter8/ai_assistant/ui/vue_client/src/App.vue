<script setup lang="ts">
import { ref, provide } from 'vue'
import TokenBar from './components/TokenBar.vue'
import Sidebar from './components/Sidebar.vue'
import HomeView from './components/HomeView.vue'
import ChatView from './components/ChatView.vue'
import NotesView from './components/NotesView.vue'
import StatsView from './components/StatsView.vue'

const activeTab = ref('chat')

function navigate(tab: string) {
  activeTab.value = tab
}

// TokenBar 刷新信号：对话完成后 +1，TokenBar watch 到后自动刷新
const refreshTokenSignal = ref(0)
provide('refreshToken', () => { refreshTokenSignal.value++ })
provide('refreshTokenSignal', refreshTokenSignal)
</script>

<template>
  <div class="app-layout">
    <Sidebar :active-tab="activeTab" @navigate="navigate" />
    <div class="main-area">
      <TokenBar />
      <div class="content-area">
        <HomeView     v-if="activeTab === 'home'" />
        <ChatView     v-if="activeTab === 'chat'" />
        <NotesView    v-if="activeTab === 'notes'" />
        <StatsView    v-if="activeTab === 'stats'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.content-area {
  flex: 1;
  overflow: hidden;
}
</style>
