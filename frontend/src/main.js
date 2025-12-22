import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

import { config } from 'md-editor-v3'

import router from './router'

// 让“预览”和“发布后展示”一致：
// - 单换行：渲染为 <br/>
// - 连续多个空行：尽可能按输入数量保留（Markdown 默认会折叠多余空行）
// 说明：为避免破坏代码块，fence (```/~~~) 内不会改写。
config({
	markdownItConfig(md) {
		md.set({ breaks: true })

		md.core.ruler.before('normalize', 'preserve-blank-lines', (state) => {
			const src = String(state.src || '').replace(/\r\n/g, '\n')
			const lines = src.split('\n')

			const out = []
			let inFence = false
			let fenceChar = ''
			let blankStreak = 0

			for (const line of lines) {
				const fence = line.match(/^\s*(```+|~~~+)/)
				if (fence) {
					const ch = fence[1][0]
					if (!inFence) {
						inFence = true
						fenceChar = ch
					} else if (ch === fenceChar) {
						inFence = false
						fenceChar = ''
					}
					blankStreak = 0
					out.push(line)
					continue
				}

				if (inFence) {
					out.push(line)
					continue
				}

				if (line.trim() === '') {
					blankStreak += 1
					out.push(blankStreak === 1 ? '' : '<br/>')
				} else {
					blankStreak = 0
					out.push(line)
				}
			}

			state.src = out.join('\n')
			return true
		})
	},
})

createApp(App).use(router).mount('#app')
