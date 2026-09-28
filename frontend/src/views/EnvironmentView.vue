<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { getJson } from '../api'

const loading = ref(false)
const checked = ref(false)
const apiReady = ref(false)
const databaseReady = ref(false)

async function check() {
  loading.value = true
  const results = await Promise.allSettled([
    getJson('/api/v1/status'),
    getJson('/health/ready'),
  ])
  apiReady.value = results[0].status === 'fulfilled'
  databaseReady.value = results[1].status === 'fulfilled'
  checked.value = true
  loading.value = false
}

onMounted(check)
</script>

<template>
  <section class="environment" aria-labelledby="page-title">
    <div class="eyebrow">Этап 2 · Каркас проекта</div>
    <h1 id="page-title">Окружение приложения</h1>
    <p class="intro">Проверка связи между интерфейсом, API и базой данных.</p>

    <dl class="connection-list" aria-live="polite" :aria-busy="loading">
      <div><dt>Интерфейс <span>Vue + PrimeVue</span></dt><dd><Tag value="Работает" severity="success" /></dd></div>
      <div><dt>Backend <span>Python + FastAPI</span></dt><dd><Tag
        :value="loading ? 'Проверка…' : apiReady ? 'Доступен' : 'Недоступен'"
        :severity="loading || !checked ? 'secondary' : apiReady ? 'success' : 'danger'"
      /></dd></div>
      <div><dt>База данных <span>PostgreSQL 18</span></dt><dd><Tag
        :value="loading ? 'Проверка…' : databaseReady ? 'Подключена' : 'Недоступна'"
        :severity="loading || !checked ? 'secondary' : databaseReady ? 'success' : 'danger'"
      /></dd></div>
    </dl>
    <Message v-if="checked && !loading && (!apiReady || !databaseReady)" severity="error" :closable="false">
      Не удалось проверить соединение. Убедитесь, что контейнеры запущены, и повторите проверку.
    </Message>
    <div class="actions">
      <Button label="Проверить соединение" icon="pi pi-refresh" :loading="loading" @click="check" />
      <a class="docs-link" href="/docs" target="_blank" rel="noopener">Документация API <i class="pi pi-arrow-up-right" aria-hidden="true" /></a>
    </div>
    <p class="stage-note">Это техническая страница каркаса. Учёт оборудования будет подключён на следующих этапах.</p>
  </section>
</template>
