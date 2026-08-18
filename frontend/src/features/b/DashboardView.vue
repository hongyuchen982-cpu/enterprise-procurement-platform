<script setup lang="ts">
const deliveryItems = [
  'Supplier domain and SupplierSnapshot facade',
  'Sourcing and award contracts',
  'Agent task orchestration',
  'Tool registry with risk levels',
  'Worker, RAG, risk, and reporting extensions',
]
</script>

<template>
  <section class="b-dashboard">
    <div class="b-dashboard__header">
      <p class="eyebrow">
        Member B Workspace
      </p>
      <h1>Suppliers, sourcing, and AI collaboration</h1>
      <p>
        This area is owned by Member B and integrates with Member A only through
        facades, contracts, and domain events.
      </p>
    </div>

    <el-row :gutter="16">
      <el-col
        :xs="24"
        :md="8"
      >
        <el-statistic
          title="Supplier APIs"
          value="2"
        />
      </el-col>
      <el-col
        :xs="24"
        :md="8"
      >
        <el-statistic
          title="Agent APIs"
          value="2"
        />
      </el-col>
      <el-col
        :xs="24"
        :md="8"
      >
        <el-statistic
          title="Registered tools"
          value="2"
        />
      </el-col>
    </el-row>

    <el-card class="b-dashboard__panel">
      <template #header>
        <div class="card-header">
          <span>Delivery sequence</span>
          <el-tag type="success">
            feature/b-supplier-ai
          </el-tag>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="item in deliveryItems"
          :key="item"
          type="primary"
          :hollow="true"
        >
          {{ item }}
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </section>
</template>

<style scoped>
.b-dashboard {
  max-width: 1080px;
  margin: 24px auto;
}

.b-dashboard__header {
  margin-bottom: 20px;
}

.b-dashboard__header h1 {
  margin: 4px 0 8px;
  font-size: 26px;
}

.b-dashboard__header p {
  max-width: 760px;
  color: #475569;
}

.eyebrow {
  margin: 0;
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

.b-dashboard__panel {
  margin-top: 16px;
}
</style>
