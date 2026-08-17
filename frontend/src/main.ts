import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createApp } from 'vue'

import App from './App.vue'
import { pinia } from './app/pinia'
import { router } from './app/router'
import './styles.css'

createApp(App).use(pinia).use(router).use(ElementPlus).mount('#app')
