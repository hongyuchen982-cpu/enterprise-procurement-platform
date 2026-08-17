<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiClient } from '../shared/api/client'

interface DependencyStatus {
  status: 'up' | 'down'
  detail: string | null
}

interface ReadinessData {
  status: 'ready' | 'degraded' | 'not_ready'
  dependencies: Record<string, DependencyStatus>
}

const loading = ref(true)
const error = ref<string | null>(null)
const readiness = ref<ReadinessData | null>(null)

const statusType = computed(() => {
  if (readiness.value?.status === 'ready') return 'success'
  if (readiness.value?.status === 'degraded') return 'warning'
  return 'danger'
})

async function loadHealth(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    await apiClient.get('/health/live')
    const response = await apiClient.get<{ data: ReadinessData }>('/health/ready')
    readiness.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Health check failed'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadHealth()
})
</script>

<template>
  <el-card
    v-loading="loading"
    class="page-card"
  >
    <template #header>
      <div class="card-header">
        <h1>System Health</h1>
        <el-button @click="loadHealth">
          刷新
        </el-button>
      </div>
    </template>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />

    <template v-else-if="readiness">
      <p>
        API readiness:
        <el-tag :type="statusType">
          {{ readiness.status }}
        </el-tag>
      </p>
      <el-table
        :data="Object.entries(readiness.dependencies)"
        stripe
      >
        <el-table-column label="Component">
          <template #default="scope">
            {{ scope.row[0] }}
          </template>
        </el-table-column>
        <el-table-column label="Status">
          <template #default="scope">
            <el-tag :type="scope.row[1].status === 'up' ? 'success' : 'danger'">
              {{ scope.row[1].status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Detail">
          <template #default="scope">
            {{ scope.row[1].detail ?? '-' }}
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>
