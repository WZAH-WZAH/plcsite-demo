import { reactive } from 'vue'

export const ui = reactive({
  modalOpen: false,
  modalTitle: '提示',
  modalMessage: '',
  openModal(message, { title = '提示' } = {}) {
    this.modalTitle = String(title || '提示')
    this.modalMessage = String(message || '')
    this.modalOpen = true
  },
  closeModal() {
    this.modalOpen = false
    this.modalMessage = ''
  },
})
