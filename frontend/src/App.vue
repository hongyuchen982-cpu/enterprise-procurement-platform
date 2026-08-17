<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function navigate(path: string): void {
  void router.push(path)
}
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div>
        <strong>企业采购与供应链智能协同平台</strong>
        <span class="phase">工程骨架</span>
      </div>
      <el-menu
        :default-active="route.path"
        mode="horizontal"
        :ellipsis="false"
        @select="navigate"
      >
        <el-menu-item index="/">
          首页
        </el-menu-item>
        <el-menu-item index="/health">
          Health
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>
