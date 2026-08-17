<template>
  <el-card class="page-card">
    <template #header>
      <h1>工程骨架已启动</h1>
    </template>
    <p>当前仅包含工程基础设施、健康检查、公共 Contract 和协作边界。</p>
    <el-alert
      title="尚未实现采购、供应商、RFQ、订单、发票、RAG 或 Agent 业务功能。"
      type="info"
      :closable="false"
      show-icon
    />
  </el-card>
</template>
