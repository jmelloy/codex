import { defineStore } from 'pinia'
import axios from 'axios'

export const useImagesStore = defineStore('images', {
  state: () => ({
    images: [],
    total: 0,
    page: 1,
    pages: 1,
    loading: false,
    searchQuery: '',
    selectedTags: [],
    showHidden: false,
    dateFrom: '',
    dateTo: '',
    minRating: -999,
    sortBy: 'date_taken',
    sortDir: 'desc',
    selectedImageIds: [],
    allTags: [],
    availableDates: [],
  }),

  actions: {
    async fetchImages(resetPage = false) {
      if (resetPage) this.page = 1
      this.loading = true
      try {
        const params = {
          page: this.page,
          limit: 50,
          sort_by: this.sortBy,
          sort_dir: this.sortDir,
          show_hidden: this.showHidden,
          min_rating: this.minRating,
        }
        if (this.searchQuery) params.q = this.searchQuery
        if (this.selectedTags.length) params.tags = this.selectedTags
        if (this.dateFrom) params.date_from = this.dateFrom
        if (this.dateTo) params.date_to = this.dateTo

        const res = await axios.get('/api/images', { params })
        this.images = res.data.items
        this.total = res.data.total
        this.page = res.data.page
        this.pages = res.data.pages
      } catch (e) {
        console.error('fetchImages failed', e)
      } finally {
        this.loading = false
      }
    },

    async fetchMoreImages() {
      if (this.page >= this.pages) return
      this.loading = true
      try {
        const params = {
          page: this.page + 1,
          limit: 50,
          sort_by: this.sortBy,
          sort_dir: this.sortDir,
          show_hidden: this.showHidden,
          min_rating: this.minRating,
        }
        if (this.searchQuery) params.q = this.searchQuery
        if (this.selectedTags.length) params.tags = this.selectedTags
        if (this.dateFrom) params.date_from = this.dateFrom
        if (this.dateTo) params.date_to = this.dateTo

        const res = await axios.get('/api/images', { params })
        this.images = [...this.images, ...res.data.items]
        this.page = res.data.page
        this.pages = res.data.pages
      } catch (e) {
        console.error('fetchMoreImages failed', e)
      } finally {
        this.loading = false
      }
    },

    async rateImage(imageId, rating) {
      await axios.put(`/api/images/${imageId}/rating`, { rating })
      const img = this.images.find((i) => i.id === imageId)
      if (img) {
        img.rating = rating
        img.hidden = rating === -1
        if (rating === -1 && !this.showHidden) {
          this.images = this.images.filter((i) => i.id !== imageId)
        }
      }
    },

    async addTags(imageId, tagNames) {
      const res = await axios.post(`/api/images/${imageId}/tags`, { tag_names: tagNames })
      const img = this.images.find((i) => i.id === imageId)
      if (img) img.tags = res.data.tags
      await this.fetchAllTags()
      return res.data
    },

    async removeTag(imageId, tagName) {
      const res = await axios.delete(`/api/images/${imageId}/tags/${encodeURIComponent(tagName)}`)
      const img = this.images.find((i) => i.id === imageId)
      if (img) img.tags = res.data.tags
      return res.data
    },

    async bulkTag(tagNames) {
      if (!this.selectedImageIds.length || !tagNames.length) return
      await axios.post('/api/images/bulk-tag', {
        image_ids: this.selectedImageIds,
        tag_names: tagNames,
      })
      await this.fetchImages()
      await this.fetchAllTags()
    },

    async bulkRemoveTag(tagName) {
      if (!this.selectedImageIds.length || !tagName) return
      await axios.post('/api/images/bulk-remove-tag', {
        image_ids: this.selectedImageIds,
        tag_name: tagName,
      })
      await this.fetchImages()
      await this.fetchAllTags()
    },

    async bulkRate(rating) {
      if (!this.selectedImageIds.length) return
      await axios.post('/api/images/bulk-rating', {
        image_ids: this.selectedImageIds,
        rating,
      })
      await this.fetchImages()
    },

    async scanDirectory(directory) {
      const res = await axios.post('/api/images/scan', { directory })
      await this.fetchImages(true)
      await this.fetchAllTags()
      return res.data
    },

    async fetchAllTags() {
      const res = await axios.get('/api/tags')
      this.allTags = res.data
    },

    async fetchDates() {
      const res = await axios.get('/api/images/dates')
      this.availableDates = res.data
    },

    toggleImageSelection(id) {
      const idx = this.selectedImageIds.indexOf(id)
      if (idx === -1) this.selectedImageIds.push(id)
      else this.selectedImageIds.splice(idx, 1)
    },

    clearSelection() {
      this.selectedImageIds = []
    },

    selectAll() {
      this.selectedImageIds = this.images.map((i) => i.id)
    },
  },
})
