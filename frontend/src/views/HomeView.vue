<template>
  <div class="h-screen flex w-full relative">
    <!-- Mobile Sidebar Overlay/Backdrop -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/50 z-40 lg:hidden"
      @click="sidebarOpen = false"
    ></div>

    <!-- Mobile Header with Hamburger Menu -->
    <div
      class="fixed top-0 left-0 right-0 h-14 notebook-sidebar flex items-center px-4 z-30 lg:hidden"
      style="border-bottom: 1px solid var(--page-border)"
    >
      <button
        @click="sidebarOpen = !sidebarOpen"
        class="sidebar-icon-button mr-3"
        :title="sidebarOpen ? 'Close menu' : 'Open menu'"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
      <h1 class="m-0 text-xl font-semibold" style="color: var(--notebook-text)">Codex</h1>
      <!-- Mobile Properties Toggle -->
      <button
        v-if="workspaceStore.currentBlock"
        @click="toggleProperties"
        class="sidebar-icon-button ml-auto"
        title="Properties"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="1"></circle>
          <circle cx="12" cy="5" r="1"></circle>
          <circle cx="12" cy="19" r="1"></circle>
        </svg>
      </button>
    </div>

    <!-- Left: File Browser Sidebar (280px) -->
    <aside
      :class="[
        'w-[280px] min-w-[280px] notebook-sidebar flex flex-col overflow-hidden',
        'fixed lg:relative inset-y-0 left-0 z-50',
        'transform transition-transform duration-300 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      ]"
    >
      <!-- Codex Header -->
      <div
        class="flex items-center justify-between px-4 py-4"
        style="border-bottom: 1px solid var(--page-border)"
      >
        <h1 class="m-0 text-xl font-semibold" style="color: var(--notebook-text)">Codex</h1>
        <!-- Close button for mobile -->
        <button
          @click="sidebarOpen = false"
          class="sidebar-icon-button lg:hidden"
          title="Close menu"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <!-- Sidebar Tabs -->
      <div class="sidebar-tabs flex" style="border-bottom: 1px solid var(--page-border)">
        <button
          class="sidebar-tab flex-1 py-2 px-4 text-sm font-medium transition"
          :class="{ 'sidebar-tab-active': sidebarTab === 'files' }"
          @click="sidebarTab = 'files'"
        >
          Files
        </button>
        <button
          class="sidebar-tab flex-1 py-2 px-4 text-sm font-medium transition"
          :class="{ 'sidebar-tab-active': sidebarTab === 'search' }"
          @click="sidebarTab = 'search'"
        >
          Search
        </button>
      </div>

      <!-- Search Panel -->
      <div v-if="sidebarTab === 'search'" class="flex-1 flex flex-col overflow-hidden">
        <!-- Search Input -->
        <div class="p-3" style="border-bottom: 1px solid var(--page-border)">
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search files..."
              class="search-input w-full px-3 py-2 pr-8 text-sm rounded"
              @keyup.enter="handleSearch"
            />
            <button
              v-if="searchQuery"
              @click="clearSearch"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              title="Clear search"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <button
            @click="handleSearch"
            :disabled="!searchQuery.trim() || isSearching"
            class="notebook-button w-full mt-2 py-2 text-sm text-white rounded cursor-pointer transition"
          >
            {{ isSearching ? "Searching..." : "Search" }}
          </button>
        </div>

        <!-- Search Results -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="isSearching" class="p-4 text-center text-sm" style="color: var(--pen-gray)">
            Searching...
          </div>
          <div
            v-else-if="searchResults.length === 0 && searchQuery"
            class="p-4 text-center text-sm"
            style="color: var(--pen-gray)"
          >
            No files found matching "{{ searchQuery }}"
          </div>
          <div
            v-else-if="searchResults.length === 0"
            class="p-4 text-center text-sm"
            style="color: var(--pen-gray)"
          >
            Enter a search term to find files
          </div>
          <ul v-else class="list-none p-0 m-0">
            <li
              v-for="file in searchResults"
              :key="file.id"
              class="search-result-item py-2 px-4 cursor-pointer text-sm transition"
              @click="selectSearchResult(file)"
            >
              <div class="flex items-center">
                <span class="mr-2 text-sm">{{ getBlockIcon(file) }}</span>
                <div class="flex-1 min-w-0">
                  <div class="truncate font-medium" style="color: var(--notebook-text)">
                    {{ file.title || file.filename || file.path.split('/').pop() }}
                  </div>
                  <div class="truncate text-xs" style="color: var(--pen-gray)">
                    {{ file.path }}
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Files Panel (existing content) -->
      <div v-else class="flex-1 flex flex-col overflow-hidden">
        <div
          class="flex justify-between items-center px-4 py-4"
          style="border-bottom: 1px solid var(--page-border)"
        >
          <h2
            class="m-0 text-sm font-semibold uppercase tracking-wide"
            style="color: var(--pen-gray)"
          >
            Workspaces
          </h2>
          <button
            @click="showCreateWorkspace = true"
            title="Create Workspace"
            class="notebook-button text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center transition"
          >
            +
          </button>
        </div>
        <ul class="list-none p-0 m-0 max-h-[150px] overflow-y-auto">
          <li
            v-for="workspace in workspaceStore.workspaces"
            :key="workspace.id"
            :class="[
              'workspace-item py-2.5 px-4 cursor-pointer text-sm transition',
              {
                'workspace-active font-semibold':
                  workspaceStore.currentWorkspace?.id === workspace.id,
              },
            ]"
            @click="selectWorkspace(workspace)"
          >
            {{ workspace.name }}
          </li>
        </ul>

        <div
          v-if="workspaceStore.currentWorkspace"
          class="flex-1 flex flex-col overflow-hidden"
          style="border-top: 1px solid var(--page-border)"
        >
          <div
            class="flex justify-between items-center px-4 py-4"
            style="border-bottom: 1px solid var(--page-border)"
          >
            <h3
              class="m-0 text-sm font-semibold uppercase tracking-wide"
              style="color: var(--pen-gray)"
            >
              Notebooks
            </h3>
            <button
              @click="showCreateNotebook = true"
              title="Create Notebook"
              class="notebook-button text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center transition"
            >
              +
            </button>
          </div>

          <!-- Notebook Tree with Files -->
          <ul class="list-none p-0 m-0 overflow-y-auto flex-1">
            <li
              v-for="notebook in workspaceStore.notebooks"
              :key="notebook.id"
              style="border-bottom: 1px solid var(--page-border)"
            >
              <div
                :class="[
                  'notebook-item flex items-center py-2 px-4 cursor-pointer text-sm transition',
                  { 'notebook-active': workspaceStore.currentNotebook?.id === notebook.id },
                ]"
                @click="toggleNotebook(notebook)"
              >
                <span class="text-[10px] mr-2 w-3" style="color: var(--pen-gray)">{{
                  workspaceStore.expandedNotebooks.has(notebook.id) ? "▼" : "▶"
                }}</span>
                <span class="flex-1 font-medium">{{ notebook.name }}</span>
                <button
                  v-if="workspaceStore.expandedNotebooks.has(notebook.id)"
                  @click.stop="startCreatePage(notebook)"
                  class="notebook-button w-5 h-5 text-sm ml-auto opacity-0 hover:opacity-100 transition text-white border-none rounded-full cursor-pointer flex items-center justify-center"
                  title="New File"
                >
                  +
                </button>
              </div>

              <!-- File Tree with drop zone -->
              <ul
                v-if="workspaceStore.expandedNotebooks.has(notebook.id)"
                class="list-none p-0 m-0"
                :class="{ 'bg-primary/10': dragOverNotebook === notebook.id }"
                @dragover.prevent="handleNotebookDragOver($event, notebook.id)"
                @dragenter.prevent="handleNotebookDragEnter(notebook.id)"
                @dragleave="handleNotebookDragLeave"
                @drop.prevent="handleNotebookDrop($event, notebook.id)"
              >
                <template v-if="notebookBlockTrees.get(notebook.id)?.length">
                  <template v-for="node in notebookBlockTrees.get(notebook.id)" :key="node.path">
                    <!-- Only render pages in the sidebar, not leaf blocks -->
                    <li v-if="node.type === 'page'">
                      <!-- Folder -->
                      <div
                        :class="[
                          'page-item flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] transition',
                          {
                            'bg-primary/20 border-t-2 border-primary':
                              dragOverPage === `${notebook.id}:${node.path}`,
                          },
                          {
                            'page-active':
                              workspaceStore.currentPageBlock?.path === node.path &&
                              workspaceStore.currentPageBlock?.notebook_id === notebook.id,
                          },
                        ]"
                        @click="handlePageClick($event, notebook.id, node.path, node)"
                        @dragover.prevent="handlePageDragOver($event, notebook.id, node.path)"
                        @dragenter.prevent="handlePageDragEnter(notebook.id, node.path)"
                        @dragleave="handlePageDragLeave"
                        @drop.prevent.stop="handlePageDrop($event, notebook.id, node.path)"
                      >
                        <span
                          v-if="!node.isPage || hasSubpages(node)"
                          class="text-[10px] mr-2 w-3"
                          style="color: var(--pen-gray)"
                        >{{
                          isPageExpanded(notebook.id, node.path) ? "▼" : "▶"
                        }}</span>
                        <span v-else class="mr-2 w-3"></span>
                        <span class="mr-2 text-sm">{{ node.pageMeta?.properties?.icon || (node.isPage ? '📄' : '📁') }}</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{
                          node.pageMeta?.title || node.name
                        }}</span>
                      </div>

                      <!-- Folder contents -->
                      <ul
                        v-if="isPageExpanded(notebook.id, node.path) && node.children"
                        class="list-none p-0 m-0"
                      >
                        <BlockTreeItem
                          v-for="child in node.children"
                          :key="child.path"
                          :node="child"
                          :notebook-id="notebook.id"
                          :depth="1"
                          :expanded-pages="expandedPages"
                          :current-block-id="workspaceStore.currentLeafBlock?.id"
                          :current-page-path="workspaceStore.currentPageBlock?.path"
                          :current-page-notebook-id="workspaceStore.currentPageBlock?.notebook_id"
                          @toggle-page="togglePage"
                          @select-page="handleSelectPage"
                          @select-block="selectLeafBlock"
                          @move-block="handleMoveBlock"
                        />
                      </ul>
                    </li>

                    <!-- Root level blocks are hidden from sidebar -->
                  </template>
                </template>
                <li
                  v-else
                  class="py-2 px-4 pl-8 text-xs italic"
                  style="color: var(--pen-gray); opacity: 0.6"
                >
                  {{
                    dragOverNotebook === notebook.id ? "Drop files here to upload" : "No files yet"
                  }}
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </div>

      <!-- User Section at Bottom -->
      <div class="user-section mt-auto px-4 py-3" style="border-top: 1px solid var(--page-border)">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2 min-w-0">
            <div
              class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"
            >
              <span class="text-sm font-medium" style="color: var(--notebook-accent)">
                {{ authStore.user?.username?.charAt(0)?.toUpperCase() }}
              </span>
            </div>
            <span class="text-sm truncate" style="color: var(--notebook-text)">{{
              authStore.user?.username
            }}</span>
          </div>
          <div class="flex items-center gap-1">
            <button
              v-if="workspaceStore.currentWorkspace"
              @click="agentStore.openChat()"
              class="sidebar-icon-button"
              title="AI Agent"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M12 8V4H8"></path>
                <rect width="16" height="12" x="4" y="8" rx="2"></rect>
                <path d="M2 14h2"></path>
                <path d="M20 14h2"></path>
                <path d="M15 13v2"></path>
                <path d="M9 13v2"></path>
              </svg>
            </button>
            <button @click="goToSettings" class="sidebar-icon-button" title="Settings">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="12" cy="12" r="3"></circle>
                <path
                  d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
                ></path>
              </svg>
            </button>
            <button @click="handleLogout" class="sidebar-icon-button" title="Logout">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Center: Content Pane (flex: 1) -->
    <main class="flex-1 flex flex-col overflow-hidden pt-14 lg:pt-0">
      <!-- Loading State -->
      <div
        v-if="workspaceStore.blockLoading"
        class="flex flex-col items-center justify-center h-full text-text-tertiary"
      >
        <span>Loading...</span>
      </div>

      <!-- Error State -->
      <div
        v-else-if="workspaceStore.error"
        class="flex flex-col items-center justify-center h-full text-error"
      >
        <p>{{ workspaceStore.error }}</p>
        <button
          @click="workspaceStore.error = null"
          class="mt-4 px-4 py-2 bg-error text-text-inverse border-none rounded cursor-pointer font-medium"
        >
          Dismiss
        </button>
      </div>

      <!-- Viewer Mode -->
      <div v-else-if="workspaceStore.currentLeafBlock" class="flex-1 flex overflow-hidden p-4">
        <!-- All file types use a consistent header + content pattern -->
        <div class="flex-1 flex flex-col overflow-hidden">
          <BlockHeader
            :block="workspaceStore.currentLeafBlock"
            @toggle-properties="toggleProperties"
            @rename="handleRenameBlock"
          >
            <template #actions>
              <!-- Media files (image, pdf, audio, video, html) get Open button -->
              <button
                v-if="['image', 'pdf', 'audio', 'video', 'html'].includes(displayType)"
                @click="openInNewTab"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                title="Open in new tab"
              >
                Open
              </button>

              <!-- Binary files get Download link -->
              <a
                v-else-if="displayType === 'binary'"
                :href="currentContentUrl"
                download
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition no-underline"
              >
                Download
              </a>

              <!-- All files get Properties button -->
              <button
                @click="toggleProperties"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
              >
                Properties
              </button>
            </template>
          </BlockHeader>

          <!-- Image Viewer -->
          <div
            v-if="displayType === 'image'"
            class="flex-1 flex items-center justify-center overflow-auto bg-bg-secondary rounded-lg"
          >
            <img
              :src="currentContentUrl"
              :alt="workspaceStore.currentLeafBlock.title || workspaceStore.currentLeafBlock.filename"
              class="max-w-full max-h-full object-contain"
            />
          </div>

          <!-- PDF Viewer -->
          <div
            v-else-if="displayType === 'pdf'"
            class="flex-1 overflow-hidden bg-bg-secondary rounded-lg"
          >
            <iframe
              :src="currentContentUrl"
              class="w-full h-full border-0"
              :title="workspaceStore.currentLeafBlock.title || workspaceStore.currentLeafBlock.filename"
            />
          </div>

          <!-- Audio Player -->
          <div
            v-else-if="displayType === 'audio'"
            class="flex-1 flex items-center justify-center bg-bg-secondary rounded-lg"
          >
            <div class="text-center">
              <audio :src="currentContentUrl" controls class="w-full max-w-md">
                Your browser does not support the audio element.
              </audio>
            </div>
          </div>

          <!-- Video Player -->
          <div
            v-else-if="displayType === 'video'"
            class="flex-1 flex items-center justify-center overflow-auto bg-bg-secondary rounded-lg"
          >
            <video :src="currentContentUrl" controls class="max-w-full max-h-full">
              Your browser does not support the video element.
            </video>
          </div>

          <!-- HTML Viewer -->
          <div
            v-else-if="displayType === 'html'"
            class="flex-1 overflow-hidden bg-bg-secondary rounded-lg"
          >
            <iframe
              :src="currentContentUrl"
              class="w-full h-full border-0"
              :title="workspaceStore.currentLeafBlock.title || workspaceStore.currentLeafBlock.filename"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>

          <!-- Code Viewer -->
          <CodeViewer
            v-else-if="displayType === 'code'"
            :content="workspaceStore.currentLeafBlock.content"
            :filename="workspaceStore.currentLeafBlock.filename"
            :show-line-numbers="true"
            :show-toolbar="false"
            class="flex-1"
          />

          <!-- Binary file placeholder -->
          <div
            v-else-if="displayType === 'binary'"
            class="flex-1 flex items-center justify-center bg-bg-secondary rounded-lg"
          >
            <div class="text-center text-text-tertiary">
              <p>This is a binary file.</p>
              <p class="text-sm">Click "Download" to save it to your device.</p>
            </div>
          </div>

          <!-- Markdown Viewer (default) -->
          <MarkdownViewer
            v-else
            :content="workspaceStore.currentLeafBlock.content"
            :frontmatter="workspaceStore.currentLeafBlock.properties"
            :workspace-id="workspaceStore.currentWorkspace?.id"
            :notebook-id="workspaceStore.currentNotebook?.id"
            :current-file-path="workspaceStore.currentLeafBlock.path"
            :show-frontmatter="false"
            :show-toolbar="false"
            @copy="handleCopy"
            class="flex-1"
          />
        </div>
      </div>

      <!-- Block/Page View Mode -->
      <div
        v-else-if="workspaceStore.currentPageBlock"
        class="flex-1 flex overflow-hidden p-4"
      >
        <div class="flex-1 flex flex-col overflow-hidden">
          <!-- Cover image -->
          <div
            v-if="workspaceStore.currentPageBlock?.properties?.cover_image"
            class="page-cover-image"
          >
            <img
              :src="workspaceStore.currentPageBlock.properties.cover_image"
              alt="Cover"
              class="page-cover-img"
            />
          </div>

          <!-- Page header bar -->
          <div class="page-header-bar flex items-center justify-between px-4 py-2" style="border-bottom: 1px solid var(--page-border)">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-sm">{{ workspaceStore.currentPageBlock?.properties?.icon || '📄' }}</span>
              <span class="font-medium truncate" style="color: var(--notebook-text)">
                {{ workspaceStore.currentPageBlock.title || workspaceStore.currentPageBlock.name }}
              </span>
            </div>
            <button
              @click="toggleProperties"
              class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
            >
              Properties
            </button>
          </div>

          <BlockView
            :blocks="workspaceStore.currentPageBlocks"
            :page-title="workspaceStore.currentPageBlock.title"
            :page-description="workspaceStore.currentPageBlock.description"
            :page-icon="workspaceStore.currentPageBlock.properties?.icon"
            :page-cover-image="workspaceStore.currentPageBlock.properties?.cover_image"
            :workspace-id="workspaceStore.currentWorkspace?.id"
            :notebook-id="workspaceStore.currentPageBlock.notebook_id"
            class="flex-1 overflow-y-auto"
            @navigate-page="handleNavigatePageBlock"
            @delete-block="handleDeleteBlock"
            @add-block="handleAddBlock"
            @reorder="handleReorderBlocks"
            @update-block="handleUpdateBlock"
            @create-subpage="handleCreateSubpage"
            @upload-file="handleUploadFile"
          />
        </div>
      </div>

      <!-- Welcome State -->
      <div
        v-else
        class="flex flex-col items-center justify-center h-full text-center"
        style="color: var(--pen-gray)"
      >
        <h2 class="mb-2" style="color: var(--notebook-text)">Welcome to Codex</h2>
        <p v-if="!workspaceStore.currentWorkspace">Select a workspace to get started</p>
        <p v-else-if="!workspaceStore.notebooks || workspaceStore.notebooks.length === 0">
          Create a notebook to start adding files
        </p>
        <p v-else>Select a notebook and file to view its content</p>
      </div>
    </main>

    <!-- Right: Properties Panel (300px on desktop, full-screen overlay on mobile) -->
    <!-- Mobile Properties Backdrop -->
    <div
      v-if="showPropertiesPanel && workspaceStore.currentBlock"
      class="fixed inset-0 bg-black/50 z-40 lg:hidden"
      @click="showPropertiesPanel = false"
    ></div>

    <BlockPropertiesPanel
      v-if="showPropertiesPanel && workspaceStore.currentLeafBlock && workspaceStore.currentWorkspace"
      :block="workspaceStore.currentLeafBlock"
      :workspace-id="workspaceStore.currentWorkspace.id"
      :notebook-id="workspaceStore.currentLeafBlock.notebook_id"
      class="w-full lg:w-[300px] lg:min-w-[300px] fixed lg:relative inset-0 lg:inset-auto z-50 lg:z-auto pt-14 lg:pt-0"
      @close="showPropertiesPanel = false"
      @update-properties="handleUpdateProperties"
      @delete="handleDeleteLeafBlock"
      @restore="handleRestoreVersion"
    />

    <!-- Page Properties Panel -->
    <BlockPropertiesPanel
      v-if="showPropertiesPanel && workspaceStore.currentPageBlock && !workspaceStore.currentLeafBlock"
      :block="workspaceStore.currentBlock"
      :workspace-id="workspaceStore.currentWorkspace?.id ?? 0"
      :notebook-id="workspaceStore.currentBlock?.notebook_id ?? 0"
      class="w-full lg:w-[300px] lg:min-w-[300px] fixed lg:relative inset-0 lg:inset-auto z-50 lg:z-auto pt-14 lg:pt-0"
      @close="showPropertiesPanel = false"
      @update-properties="handleUpdateProperties"
      @delete="handleDeletePageBlock"
    />
  </div>

  <!-- Create Workspace Modal -->
  <Modal v-model="showCreateWorkspace" title="Create Workspace" confirm-text="Create" hide-actions>
    <form @submit.prevent="handleCreateWorkspace">
      <FormGroup label="Name" v-slot="{ inputId }">
        <input :id="inputId" v-model="newWorkspaceName" required />
      </FormGroup>
      <div class="flex gap-2 justify-end mt-6">
        <button
          type="button"
          @click="showCreateWorkspace = false"
          class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition"
        >
          Create
        </button>
      </div>
    </form>
  </Modal>

  <!-- Create Notebook Modal -->
  <Modal v-model="showCreateNotebook" title="Create Notebook" confirm-text="Create" hide-actions>
    <form @submit.prevent="handleCreateNotebook">
      <FormGroup label="Name" v-slot="{ inputId }">
        <input :id="inputId" v-model="newNotebookName" required />
      </FormGroup>
      <div class="flex gap-2 justify-end mt-6">
        <button
          type="button"
          @click="showCreateNotebook = false"
          class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition"
        >
          Create
        </button>
      </div>
    </form>
  </Modal>

  <!-- Create File Modal -->
  <Modal v-model="showCreatePage" title="New Page" confirm-text="Create" hide-actions>
    <form @submit.prevent="handleCreatePage">
      <FormGroup label="Name" v-slot="{ inputId }">
        <input
          :id="inputId"
          v-model="newPageName"
          placeholder="My Page"
          required
          class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
        />
        <p class="text-sm text-text-secondary mt-1">
          Enter a name for the page, or a filename with extension for other file types (e.g., data.json, script.py)
        </p>
      </FormGroup>

      <div class="flex gap-2 justify-end mt-6">
        <button
          type="button"
          @click="showCreatePage = false"
          class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition"
        >
          Create
        </button>
      </div>
    </form>
  </Modal>

  <!-- Settings Dialog -->
  <SettingsDialog v-model="showSettingsDialog" @open-agent-chat="handleOpenAgentChat" />

  <!-- Agent Chat Panel (floating) -->
  <Teleport to="body">
    <div v-if="agentStore.chatOpen" class="agent-chat-overlay">
      <div class="agent-chat-panel">
        <AgentChat
          v-if="workspaceStore.currentWorkspace"
          :workspace-id="workspaceStore.currentWorkspace.id"
          :initial-notebook-path="currentNotebookPath"
          @close="agentStore.closeChat()"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue"
import { useRouter, useRoute } from "vue-router"
import { useAuthStore } from "../stores/auth"
import { useWorkspaceStore } from "../stores/workspace"
import type { Workspace, Notebook, Block } from "../services/codex"
import { blockService, searchService } from "../services/codex"
import { getDisplayType } from "../utils/contentType"
import Modal from "../components/Modal.vue"
import FormGroup from "../components/FormGroup.vue"
import MarkdownViewer from "../components/MarkdownViewer.vue"
import CodeViewer from "../components/CodeViewer.vue"
import BlockPropertiesPanel from "../components/BlockPropertiesPanel.vue"
import BlockView from "../components/BlockView.vue"
import BlockHeader from "../components/BlockHeader.vue"
import BlockTreeItem from "../components/BlockTreeItem.vue"
import SettingsDialog from "../components/SettingsDialog.vue"
import AgentChat from "../components/agent/AgentChat.vue"
import { useAgentStore } from "../stores/agent"
import type { Agent } from "../services/agent"
import { showToast } from "../utils/toast"
import type { BlockTreeNode } from "../utils/blockTree"

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const agentStore = useAgentStore()

// Modal state
const showCreateWorkspace = ref(false)
const showCreateNotebook = ref(false)
const showCreatePage = ref(false)
const showSettingsDialog = ref(false)

// Form state
const newWorkspaceName = ref("")
const newNotebookName = ref("")
const newPageName = ref("")
const createPageNotebook = ref<Notebook | null>(null)

// View state
const showPropertiesPanel = ref(false)
// Mobile sidebar state
const sidebarOpen = ref(false)

// Helper to close sidebar on mobile (under lg breakpoint: 1024px)
function closeSidebarOnMobile() {
  if (window.innerWidth < 1024) {
    sidebarOpen.value = false
  }
}

// Sidebar tab state
const sidebarTab = ref<"files" | "search">("files")
const searchQuery = ref("")
const searchResults = ref<Block[]>([])
const isSearching = ref(false)

// Page expansion state - tracks which page paths are expanded
const expandedPages = ref<Map<number, Set<string>>>(new Map())

// Drag-drop state
const dragOverNotebook = ref<number | null>(null)
const dragOverPage = ref<string | null>(null)

// Get block trees from the store (pre-built and maintained)
const notebookBlockTrees = computed(() => {
  const trees = new Map<number, BlockTreeNode[]>()
  workspaceStore.notebooks.forEach((notebook) => {
    trees.set(notebook.id, workspaceStore.getBlockTree(notebook.id))
  })
  return trees
})

// Helper to get slug or fallback to id for URL building
function getSlugOrId(entity: { slug?: string; id: number } | null | undefined): string {
  if (!entity) return ""
  return entity.slug || String(entity.id)
}

// Helper to find workspace by slug or id
function findWorkspaceBySlugOrId(identifier: string): Workspace | undefined {
  return workspaceStore.workspaces.find((w) => w.slug === identifier || String(w.id) === identifier)
}

// Helper to find notebook by slug or id
function findNotebookBySlugOrId(identifier: string): Notebook | undefined {
  return workspaceStore.notebooks.find((n) => n.slug === identifier || String(n.id) === identifier)
}

// Build URL path: /w/{workspace}/{notebook}/{path}
function buildBlockUrl(pathOrBlock: string | Block, notebookId?: number): string {
  const ws = workspaceStore.currentWorkspace
  let path: string
  let nbId: number | undefined
  if (typeof pathOrBlock === "string") {
    path = pathOrBlock
    nbId = notebookId
  } else {
    path = pathOrBlock.path
    nbId = pathOrBlock.notebook_id
  }
  const nb = workspaceStore.notebooks.find((n) => n.id === nbId)
  if (!ws || !nb) return "/"
  return `/w/${getSlugOrId(ws)}/${getSlugOrId(nb)}/${path}`
}

// Get content URL for current block (for binary content like images, PDFs, audio, video)
const currentContentUrl = computed(() => {
  if (!workspaceStore.currentLeafBlock || !workspaceStore.currentWorkspace) return ""
  const workspaceId = workspaceStore.currentWorkspace.id || workspaceStore.currentWorkspace.slug
  const notebook = workspaceStore.notebooks.find(
    (n: any) => n.id === workspaceStore.currentLeafBlock?.notebook_id,
  )
  const notebookId = notebook?.id || notebook?.slug
  return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${workspaceStore.currentLeafBlock.block_id}/content`
})

// Get display type for current block
const displayType = computed(() => {
  if (!workspaceStore.currentLeafBlock) return "markdown"
  return getDisplayType(workspaceStore.currentLeafBlock.content_type || "")
})

// Open file in a new tab
function openInNewTab() {
  if (currentContentUrl.value) {
    window.open(currentContentUrl.value, "_blank")
  }
}


// Watch for route changes to restore block selection from URL (path-based)
watch(
  () => route.params,
  async (params) => {
    const workspaceSlug = params.workspaceSlug as string | undefined
    const notebookSlug = params.notebookSlug as string | undefined
    const itemPath = Array.isArray(params.filePath)
      ? params.filePath.join("/")
      : (params.filePath as string | undefined)

    if (workspaceSlug && notebookSlug && itemPath) {
      // Find workspace and set it if different
      const workspace = findWorkspaceBySlugOrId(workspaceSlug)
      if (workspace && workspaceStore.currentWorkspace?.id !== workspace.id) {
        workspaceStore.setCurrentWorkspace(workspace)
        await workspaceStore.fetchNotebooks(workspace.id)
      }

      // Find notebook
      const notebook = findNotebookBySlugOrId(notebookSlug)
      if (notebook) {
        // Expand notebook if not already expanded
        if (!workspaceStore.expandedNotebooks.has(notebook.id)) {
          workspaceStore.toggleNotebookExpansion(notebook)
        }

        // Resolve path via API
        if (workspaceStore.currentBlock?.path !== itemPath) {
          try {
            const block = await blockService.resolveLink(itemPath, notebook.id, workspace!.id)
            await workspaceStore.selectBlock(block)
          } catch {
            await workspaceStore.selectBlockByPath(itemPath, notebook.id)
          }
        }
      }
    } else if (!workspaceSlug && !notebookSlug && !itemPath && route.name === "home") {
      // Clear block selection if on home route with no path params
      workspaceStore.currentBlock = null
    }
  },
  { immediate: false },
)

onMounted(async () => {
  await workspaceStore.fetchWorkspaces()

  // Check for path-based URL parameters: /w/{workspace}/{notebook}/{path}
  const workspaceSlug = route.params.workspaceSlug as string | undefined
  const notebookSlug = route.params.notebookSlug as string | undefined
  const itemPath = Array.isArray(route.params.filePath)
    ? route.params.filePath.join("/")
    : (route.params.filePath as string | undefined)

  // If we have URL params, find and set the workspace
  if (workspaceSlug) {
    const workspace = findWorkspaceBySlugOrId(workspaceSlug)
    if (workspace) {
      workspaceStore.setCurrentWorkspace(workspace)
    }
  }

  // Auto-select first workspace if none is currently selected
  // This must happen BEFORE trying to restore file from URL
  if (!workspaceStore.currentWorkspace && workspaceStore.workspaces.length > 0) {
    const firstWorkspace = workspaceStore.workspaces[0]!
    workspaceStore.setCurrentWorkspace(firstWorkspace)
  }

  // Restore file/folder selection from URL after workspaces are loaded
  if (notebookSlug && itemPath && workspaceStore.currentWorkspace) {
    // Ensure notebooks are loaded for the current workspace
    if (workspaceStore.notebooks.length === 0) {
      await workspaceStore.fetchNotebooks(workspaceStore.currentWorkspace.id)
    }

    // Find and expand the notebook in the sidebar
    const notebook = findNotebookBySlugOrId(notebookSlug)
    if (notebook && !workspaceStore.expandedNotebooks.has(notebook.id)) {
      workspaceStore.toggleNotebookExpansion(notebook)
    }

    if (notebook) {
      try {
        const block = await blockService.resolveLink(itemPath, notebook.id, workspaceStore.currentWorkspace!.id)
        await workspaceStore.selectBlock(block)
      } catch {
        await workspaceStore.selectBlockByPath(itemPath, notebook.id)
      }
    }
  }
})

// Watch for notebooks to be loaded after workspace selection, then auto-select first notebook
const hasAutoSelectedNotebook = ref(false)
watch(
  () => workspaceStore.notebooks,
  (notebooks) => {
    if (
      !hasAutoSelectedNotebook.value &&
      notebooks &&
      notebooks.length > 0 &&
      !workspaceStore.currentNotebook &&
      workspaceStore.expandedNotebooks.size === 0
    ) {
      hasAutoSelectedNotebook.value = true
      const firstNotebook = notebooks[0]
      if (firstNotebook) {
        workspaceStore.toggleNotebookExpansion(firstNotebook)
      }
    }
  },
  { deep: true },
)

// Watch for block selection to update document title
watch(
  () => [workspaceStore.currentBlock, workspaceStore.notebooks] as const,
  () => {
    const block = workspaceStore.currentBlock
    const notebooks = workspaceStore.notebooks

    if (block) {
      const notebook = notebooks.find((n) => n.id === block.notebook_id)
      const notebookName = notebook?.name || "Notebook"
      const blockTitle = block.title || block.filename || block.path.split("/").pop()
      document.title = `Codex - ${notebookName} / ${blockTitle}`
    } else if (workspaceStore.currentNotebook) {
      document.title = `Codex - ${workspaceStore.currentNotebook.name}`
    } else {
      document.title = "Codex"
    }
  },
  { immediate: true },
)

function handleLogout() {
  authStore.logout()
  router.push("/login")
}

function goToSettings() {
  showSettingsDialog.value = true
}

function selectWorkspace(workspace: Workspace) {
  workspaceStore.setCurrentWorkspace(workspace)
  showPropertiesPanel.value = false
}

function toggleNotebook(notebook: Notebook) {
  workspaceStore.toggleNotebookExpansion(notebook)
}

function togglePage(notebookId: number, pagePath: string) {
  if (!expandedPages.value.has(notebookId)) {
    expandedPages.value.set(notebookId, new Set())
  }
  const folders = expandedPages.value.get(notebookId)!
  if (folders.has(pagePath)) {
    folders.delete(pagePath)
  } else {
    folders.add(pagePath)
  }
}

async function handlePageClick(event: MouseEvent, notebookId: number, pagePath: string, node?: BlockTreeNode) {
  const target = event.target as HTMLElement
  const isArrowClick =
    target.classList.contains("text-[10px]") || target.closest(".text-\\[10px\\]")

  // Pages without subpages: always just select (no disclosure)
  if (node?.isPage && !node?.hasSubpages && !isArrowClick) {
    await workspaceStore.selectBlockByPath(pagePath, notebookId)
    closeSidebarOnMobile()
    const newUrl = buildBlockUrl(pagePath, notebookId)
    if (newUrl !== "/" && route.path !== newUrl) {
      router.push(newUrl)
    }
    return
  }

  await expandOrCollapsePage(notebookId, pagePath, !isArrowClick)
}

async function expandOrCollapsePage(
  notebookId: number,
  pagePath: string,
  closeSidebar: boolean = false,
) {
  const isExpanded = isPageExpanded(notebookId, pagePath)

  if (isExpanded) {
    togglePage(notebookId, pagePath)
  } else {
    await workspaceStore.selectBlockByPath(pagePath, notebookId)
    if (workspaceStore.currentBlock?.path === pagePath) {
      togglePage(notebookId, pagePath)
    }
    if (closeSidebar) {
      closeSidebarOnMobile()
    }
  }
}

async function handleSelectPage(notebookId: number, pagePath: string) {
  await workspaceStore.selectBlockByPath(pagePath, notebookId)
  closeSidebarOnMobile()

  if (workspaceStore.currentBlock?.path === pagePath) {
    if (!expandedPages.value.has(notebookId)) {
      expandedPages.value.set(notebookId, new Set())
    }
    const folders = expandedPages.value.get(notebookId)!
    if (!folders.has(pagePath)) {
      folders.add(pagePath)
    }
  }

  const newUrl = buildBlockUrl(pagePath, notebookId)
  if (newUrl !== "/" && route.path !== newUrl) {
    router.push(newUrl)
  }
}

// handleSelectSubpage removed — pages are now navigated via block tree

// Block/page event handlers
async function handleNavigatePageBlock(block: any) {
  if (workspaceStore.currentBlock) {
    const notebookId = workspaceStore.currentBlock.notebook_id
    await handleSelectPage(notebookId, block.path)
  }
}

async function handleDeleteBlock(blockId: string) {
  const pageBlockId = workspaceStore.currentPageBlockId
  const notebookId = workspaceStore.currentBlock?.notebook_id
  if (pageBlockId && notebookId) {
    try {
      await workspaceStore.deleteBlock(notebookId, blockId, pageBlockId)
      showToast({ message: "Block deleted" })
    } catch {
      showToast({ message: "Failed to delete block", type: "error" })
    }
  }
}

async function handleAddBlock(blockType: string = "text", content: string = "", position?: number) {
  const pageBlockId = workspaceStore.currentPageBlockId
  const notebookId = workspaceStore.currentBlock?.notebook_id
  if (pageBlockId && notebookId) {
    try {
      return await workspaceStore.createBlock(notebookId, pageBlockId, blockType, content, position)
    } catch {
      showToast({ message: "Failed to add block", type: "error" })
    }
  }
}

async function handleReorderBlocks(blockIds: string[]) {
  const pageBlockId = workspaceStore.currentPageBlockId
  const notebookId = workspaceStore.currentBlock?.notebook_id
  if (pageBlockId && notebookId) {
    try {
      await workspaceStore.reorderBlocks(notebookId, pageBlockId, blockIds)
    } catch {
      showToast({ message: "Failed to reorder blocks", type: "error" })
    }
  }
}

async function handleUpdateBlock(block: { block_id: string; content: string; block_type?: string }) {
  const notebookId = workspaceStore.currentBlock?.notebook_id
  if (!notebookId) return
  try {
    const result = await blockService.updateBlock(
      block.block_id,
      notebookId,
      workspaceStore.currentWorkspace!.id,
      block.content,
      block.block_type,
    )
    if (result.blocks) {
      workspaceStore.currentPageBlocks = result.blocks
    }
  } catch {
    showToast({ message: "Failed to save block", type: "error" })
  }
}

async function handleUploadFile(file: File, parentBlockId?: string, _position?: number) {
  const notebookId = workspaceStore.currentBlock?.notebook_id
  if (!notebookId || !workspaceStore.currentWorkspace) return
  try {
    await blockService.upload(notebookId, workspaceStore.currentWorkspace.id, file, parentBlockId)
    // Refresh page blocks to show the new file
    const pageBlockId = workspaceStore.currentPageBlockId
    if (pageBlockId) {
      await workspaceStore.fetchPageBlocks(pageBlockId, notebookId)
    }
    showToast({ message: "File uploaded" })
  } catch {
    showToast({ message: "Failed to upload file", type: "error" })
  }
}

async function handleCreateSubpage() {
  const notebookId = workspaceStore.currentBlock?.notebook_id
  const parentPath = workspaceStore.currentBlock?.path
  if (!notebookId || !parentPath) return
  const title = prompt("Page name")
  if (!title) return
  try {
    await workspaceStore.createPage(notebookId, title, parentPath)
    showToast({ message: "Subpage created!" })
    await workspaceStore.selectBlockByPath(parentPath, notebookId)
  } catch {
    showToast({ message: "Failed to create subpage", type: "error" })
  }
}

function hasSubpages(node: BlockTreeNode): boolean {
  if (node.hasSubpages !== undefined) return node.hasSubpages
  if (!node.children) return false
  return node.children.some((c) => c.type === "page" && c.isPage)
}

function isPageExpanded(notebookId: number, pagePath: string): boolean {
  return expandedPages.value.get(notebookId)?.has(pagePath) || false
}

function getBlockIcon(file: Block | undefined): string {
  if (!file) return "📄"
  if (file.properties?.icon) return file.properties.icon

  const displayType = getDisplayType(file.content_type || "")

  switch (displayType) {
    case "markdown":
      return "📝" // Memo for markdown
    case "json":
      return "📋" // Clipboard for JSON
    case "xml":
      return "🏷️" // Tag for XML
    case "code":
      return "💻" // Computer for code files
    case "image":
      return "🖼️" // Picture for images
    case "pdf":
      return "📕" // Book for PDF
    case "audio":
      return "🎵" // Music note for audio
    case "video":
      return "🎬" // Film for video
    case "html":
      return "🌐" // Globe for HTML
    case "text":
      return "📄" // Document for text
    case "binary":
      return "📦" // Package for binary
    default:
      return "📄" // Default file icon
  }
}

function selectLeafBlock(block: Block) {
  workspaceStore.selectBlock(block)
  closeSidebarOnMobile()
  const newUrl = buildBlockUrl(block)
  if (newUrl !== "/" && route.path !== newUrl) {
    router.push(newUrl)
  }
}

// Folder drag-over handlers
function handlePageDragOver(event: DragEvent, _notebookId: number, _pagePath: string) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes("application/x-codex-block")
  const hasExternalFile = event.dataTransfer.types.includes("Files")
  if (hasFile || hasExternalFile) {
    event.dataTransfer.dropEffect = "move"
  }
}

function handlePageDragEnter(notebookId: number, pagePath: string) {
  dragOverPage.value = `${notebookId}:${pagePath}`
}

function handlePageDragLeave() {
  dragOverPage.value = null
}

async function handlePageDrop(event: DragEvent, notebookId: number, pagePath: string) {
  dragOverPage.value = null
  if (!event.dataTransfer) return

  // Handle external file drop (upload)
  if (event.dataTransfer.types.includes("Files") && !event.dataTransfer.types.includes("application/x-codex-block")) {
    await handleBlockUpload(event.dataTransfer, notebookId, pagePath)
    return
  }

  // Handle internal file move
  const data = event.dataTransfer.getData("application/x-codex-block")
  if (!data) return

  try {
    const { blockId, filename } = JSON.parse(data)
    const newPath = pagePath ? `${pagePath}/${filename}` : filename
    await handleMoveBlock(blockId, newPath)
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

// Notebook-level drag handlers (for root-level drops)
function handleNotebookDragOver(event: DragEvent, _notebookId: number) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes("application/x-codex-block")
  const hasExternalFile = event.dataTransfer.types.includes("Files")
  if (hasFile || hasExternalFile) {
    event.dataTransfer.dropEffect = "move"
  }
}

function handleNotebookDragEnter(notebookId: number) {
  dragOverNotebook.value = notebookId
}

function handleNotebookDragLeave() {
  dragOverNotebook.value = null
}

async function handleNotebookDrop(event: DragEvent, notebookId: number) {
  dragOverNotebook.value = null
  if (!event.dataTransfer) return

  // Handle external file drop (upload)
  if (event.dataTransfer.types.includes("Files") && !event.dataTransfer.types.includes("application/x-codex-block")) {
    await handleBlockUpload(event.dataTransfer, notebookId, "")
    return
  }

  // Handle internal file move to root
  const data = event.dataTransfer.getData("application/x-codex-block")
  if (!data) return

  try {
    const { blockId, filename, path } = JSON.parse(data)
    if (path !== filename) {
      await handleMoveBlock(blockId, filename)
    }
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

// Recursively read all files from a dropped directory entry
function readEntriesRecursively(
  entry: FileSystemDirectoryEntry
): Promise<{ file: File; relativePath: string }[]> {
  return new Promise((resolve) => {
    const reader = entry.createReader()
    const results: Promise<{ file: File; relativePath: string }[]>[] = []

    function readBatch() {
      reader.readEntries((entries) => {
        if (entries.length === 0) {
          Promise.all(results).then((arrays) => resolve(arrays.flat()))
          return
        }
        for (const child of entries) {
          if (child.isFile) {
            results.push(
              new Promise((res) => {
                ;(child as FileSystemFileEntry).file((f) => {
                  res([{ file: f, relativePath: child.fullPath.replace(/^\//, "") }])
                })
              })
            )
          } else if (child.isDirectory) {
            results.push(readEntriesRecursively(child as FileSystemDirectoryEntry))
          }
        }
        // readEntries may not return all entries at once; keep reading
        readBatch()
      })
    }
    readBatch()
  })
}

// Collect files from DataTransfer, recursing into directories
async function collectDroppedFiles(
  dataTransfer: DataTransfer
): Promise<{ file: File; relativePath: string }[]> {
  const items = dataTransfer.items
  const fileEntries: Promise<{ file: File; relativePath: string }[]>[] = []
  let hasDirectories = false

  if (items) {
    for (const item of Array.from(items)) {
      if (item.kind !== "file") continue
      const entry = item.webkitGetAsEntry?.()
      if (entry?.isDirectory) {
        hasDirectories = true
        fileEntries.push(readEntriesRecursively(entry as FileSystemDirectoryEntry))
      } else if (entry?.isFile) {
        fileEntries.push(
          new Promise((resolve) => {
            ;(entry as FileSystemFileEntry).file((f) => {
              resolve([{ file: f, relativePath: f.name }])
            })
          })
        )
      }
    }
  }

  if (hasDirectories || fileEntries.length > 0) {
    const arrays = await Promise.all(fileEntries)
    return arrays.flat()
  }

  // Fallback for browsers that don't support webkitGetAsEntry
  return Array.from(dataTransfer.files).map((f) => ({ file: f, relativePath: f.name }))
}

// Handle file upload from drag-drop
async function handleBlockUpload(dataTransfer: DataTransfer, notebookId: number, pagePath: string) {
  // Check if any dropped items are directories
  const items = dataTransfer.items
  let hasDirectories = false
  if (items) {
    for (const item of Array.from(items)) {
      if (item.kind !== "file") continue
      const entry = item.webkitGetAsEntry?.()
      if (entry?.isDirectory) {
        hasDirectories = true
        break
      }
    }
  }

  if (hasDirectories) {
    // Folder drop: collect all files, zip them, and upload as a single zip
    const droppedFiles = await collectDroppedFiles(dataTransfer)
    if (droppedFiles.length === 0) return

    try {
      const JSZip = (await import("jszip")).default
      const zip = new JSZip()
      for (const { file, relativePath } of droppedFiles) {
        zip.file(relativePath, file)
      }
      const blob = await zip.generateAsync({ type: "blob" })
      const zipFile = new File([blob], "folder-upload.zip", { type: "application/zip" })

      if (!workspaceStore.currentWorkspace) return
      await blockService.uploadFolderZip(notebookId, workspaceStore.currentWorkspace.id, zipFile, pagePath)
      await workspaceStore.fetchBlockTree(notebookId)
      showToast({ message: `Uploaded folder (${droppedFiles.length} files)` })
    } catch (e) {
      console.error("Failed to upload folder:", e)
      showToast({ message: "Failed to upload folder", type: "error" })
    }
  } else {
    // Individual file drops
    const droppedFiles = await collectDroppedFiles(dataTransfer)
    for (const { file, relativePath } of droppedFiles) {
      try {
        await workspaceStore.uploadBlock(notebookId, file, relativePath)
        showToast({ message: `Uploaded ${relativePath}` })
      } catch (e) {
        console.error(`Failed to upload ${relativePath}:`, e)
        showToast({ message: `Failed to upload ${relativePath}`, type: "error" })
      }
    }
  }
}

// Handle moving a file to a new path
async function handleMoveBlock(blockId: string, newPath: string) {
  const block = findBlockById(blockId)
  if (!block) return

  try {
    await workspaceStore.moveBlock(blockId, block.notebook_id, newPath)
    showToast({ message: "Block moved successfully" })
  } catch (e) {
    console.error("Failed to move file:", e)
    showToast({ message: "Failed to move block", type: "error" })
  }
}

function findBlockById(blockId: string): Block | undefined {
  for (const blocks of workspaceStore.allBlocks.values()) {
    const block = blocks.find((b) => b.block_id === blockId)
    if (block) return block
  }
  return undefined
}

function handleCopy() {
  showToast({ message: "Content copied to clipboard!" })
}

function toggleProperties() {
  showPropertiesPanel.value = !showPropertiesPanel.value
}

async function handleUpdateProperties(properties: Record<string, any>) {
  if (!workspaceStore.currentBlock || !workspaceStore.currentWorkspace) return

  try {
    if (workspaceStore.currentBlock.block_type === "page") {
      await blockService.updateProperties(
        workspaceStore.currentBlock.block_id,
        workspaceStore.currentBlock.notebook_id,
        workspaceStore.currentWorkspace.id,
        properties,
      )
    } else {
      await workspaceStore.saveBlock(
        (workspaceStore.currentBlock as any).content || "",
        properties,
      )
    }
  } catch {
    // Error handled in store
  }
}

async function handleRestoreVersion(content: string) {
  if (workspaceStore.currentLeafBlock) {
    try {
      await workspaceStore.saveBlock(content)
      showToast({ message: "Block restored to previous version" })
    } catch {
      showToast({ message: "Failed to restore file", type: "error" })
    }
  }
}

async function handleDeleteLeafBlock() {
  if (workspaceStore.currentBlock) {
    try {
      await workspaceStore.deleteBlock(workspaceStore.currentBlock.notebook_id, workspaceStore.currentBlock.block_id)
      showPropertiesPanel.value = false
      showToast({ message: "Block deleted" })
    } catch {
      // Error handled in store
    }
  }
}

async function handleRenameBlock(newName: string) {
  if (!workspaceStore.currentBlock) return

  const block = workspaceStore.currentBlock
  const currentPath = block.path

  // Get the parent path
  const lastSlashIndex = currentPath.lastIndexOf("/")
  const directory = lastSlashIndex >= 0 ? currentPath.substring(0, lastSlashIndex + 1) : ""

  const newPath = directory + newName

  if (newPath === currentPath) return

  try {
    await workspaceStore.moveBlock(block.block_id, block.notebook_id, newPath)
    showToast({ message: "Block renamed successfully" })
  } catch (e) {
    console.error("Failed to rename block:", e)
    showToast({ message: "Failed to rename block", type: "error" })
  }
}

async function handleDeletePageBlock() {
  if (workspaceStore.currentBlock) {
    try {
      await workspaceStore.deleteBlock(workspaceStore.currentBlock.notebook_id, workspaceStore.currentBlock.block_id)
      showPropertiesPanel.value = false
      showToast({ message: "Page deleted" })
    } catch {
      // Error handled in store
    }
  }
}

async function handleCreateWorkspace() {
  try {
    await workspaceStore.createWorkspace(newWorkspaceName.value)
    showCreateWorkspace.value = false
    newWorkspaceName.value = ""
  } catch {
    // Error handled in store
  }
}

async function handleCreateNotebook() {
  if (!workspaceStore.currentWorkspace) return

  try {
    await workspaceStore.createNotebook(workspaceStore.currentWorkspace.id, newNotebookName.value)
    showCreateNotebook.value = false
    newNotebookName.value = ""
  } catch {
    // Error handled in store
  }
}

async function handleCreatePage() {
  if (!createPageNotebook.value || !workspaceStore.currentWorkspace) return

  try {
    const path = newPageName.value
    const hasExtension = /\.[^/.]+$/.test(path)
    const isSpecialFile = hasExtension && !path.endsWith(".md")

    const title = isSpecialFile ? path : path.replace(/\.md$/, "")

    // Support slash-separated paths to create nested pages
    // e.g. "2026/03/2026-03-25" creates 2026 -> 03 -> 2026-03-25
    const segments = title.split("/").filter((s: string) => s.trim())
    if (segments.length > 1) {
      let parentPath: string | undefined = undefined
      for (const segment of segments) {
        const result = await workspaceStore.createPage(
          createPageNotebook.value!.id,
          segment.trim(),
          parentPath,
        )
        if (result?.path) {
          parentPath = result.path
        }
      }
    } else {
      await workspaceStore.createPage(createPageNotebook.value.id, title)
    }
    showToast({ message: "Page created!" })

    showCreatePage.value = false
    newPageName.value = ""
    createPageNotebook.value = null
  } catch {
    // Error handled in store
  }
}


function startCreatePage(notebook: Notebook) {
  createPageNotebook.value = notebook
  newPageName.value = ""
  showCreatePage.value = true
}

// Search functionality
async function handleSearch() {
  if (!searchQuery.value.trim() || !workspaceStore.currentWorkspace) {
    searchResults.value = []
    return
  }

  isSearching.value = true
  try {
    // First, do a local search through all loaded blocks
    const query = searchQuery.value.toLowerCase()
    const localResults: Block[] = []

    for (const [_notebookId, blocks] of workspaceStore.allBlocks) {
      for (const block of blocks) {
        const fname = block.filename || block.path.split("/").pop() || ""
        if (
          fname.toLowerCase().includes(query) ||
          block.title?.toLowerCase().includes(query) ||
          block.path.toLowerCase().includes(query)
        ) {
          localResults.push(block)
        }
      }
    }

    // Also try API search (may return additional results from content search)
    try {
      const apiResults = await searchService.search(
        workspaceStore.currentWorkspace.id,
        searchQuery.value,
      )
      // Merge API results if they contain file data
      if (apiResults.results && apiResults.results.length > 0) {
        // Add any API results that aren't already in local results
        for (const result of apiResults.results) {
          if (!localResults.find((f) => f.id === result.id)) {
            localResults.push(result as unknown as Block)
          }
        }
      }
    } catch {
      // API search may not be fully implemented, continue with local results
    }

    searchResults.value = localResults
  } finally {
    isSearching.value = false
  }
}

function selectSearchResult(block: Block) {
  // Switch back to browse tab and select the block
  sidebarTab.value = "files"
  selectLeafBlock(block)

  // Expand the notebook containing the block
  const notebook = workspaceStore.notebooks.find((n) => n.id === block.notebook_id)
  if (notebook && !workspaceStore.expandedNotebooks.has(notebook.id)) {
    workspaceStore.toggleNotebookExpansion(notebook)
  }

  // Expand parent pages if the block is nested
  if (block.path.includes("/")) {
    const pathParts = block.path.split("/")
    pathParts.pop() // Remove leaf name

    if (!expandedPages.value.has(block.notebook_id)) {
      expandedPages.value.set(block.notebook_id, new Set())
    }

    // Expand each parent page
    let currentPath = ""
    for (const part of pathParts) {
      currentPath = currentPath ? `${currentPath}/${part}` : part
      expandedPages.value.get(block.notebook_id)!.add(currentPath)
    }
  }
}

function clearSearch() {
  searchQuery.value = ""
  searchResults.value = []
}

// Agent chat
const currentNotebookPath = computed(() => {
  const notebook = workspaceStore.currentNotebook
  if (!notebook) return ""
  return notebook.path || notebook.name || ""
})

function handleOpenAgentChat(agent: Agent) {
  agentStore.openChat(agent)
}
</script>

<style scoped>
/* Add hover effect for notebook header buttons */
.flex.items-center.py-2:hover button {
  opacity: 1;
}

/* Workspace items */
.workspace-item {
  color: var(--notebook-text);
  border-bottom: 1px solid var(--page-border);
}

.workspace-item:hover:not(.workspace-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--hover-opacity), transparent);
}

.workspace-active {
  background: var(--notebook-accent);
  color: white;
  border-bottom: 1px solid color-mix(in srgb, var(--notebook-accent) 80%, black);
}

/* Notebook items */
.notebook-item {
  color: var(--notebook-text);
}

.notebook-item:hover:not(.notebook-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--hover-opacity), transparent);
}

.notebook-active {
  background: color-mix(in srgb, var(--notebook-text) var(--active-opacity), transparent);
}

/* Page items */
.page-item {
  color: var(--pen-gray);
}

.page-item:hover:not(.page-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.page-active {
  background: color-mix(in srgb, var(--notebook-accent) var(--selected-opacity), transparent);
  color: var(--notebook-accent);
}

/* Leaf block items */
.leaf-item {
  color: var(--pen-gray);
}

.leaf-item:hover:not(.leaf-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.leaf-active {
  background: color-mix(in srgb, var(--notebook-accent) var(--selected-opacity), transparent);
  color: var(--notebook-accent);
}

/* User section at bottom of sidebar */
.user-section {
  background: color-mix(in srgb, var(--notebook-bg) 90%, var(--notebook-text) 10%);
}

.sidebar-icon-button {
  background: transparent;
  border: none;
  padding: 0.375rem;
  border-radius: 0.25rem;
  cursor: pointer;
  color: var(--pen-gray);
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background-color 0.2s,
    color 0.2s;
}

.sidebar-icon-button:hover {
  background: color-mix(in srgb, var(--notebook-text) 10%, transparent);
  color: var(--notebook-text);
}

/* Sidebar Tabs */
.sidebar-tab {
  background: transparent;
  border: none;
  color: var(--pen-gray);
  cursor: pointer;
  position: relative;
}

.sidebar-tab:hover {
  color: var(--notebook-text);
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.sidebar-tab-active {
  color: var(--notebook-accent);
  font-weight: 600;
}

.sidebar-tab-active::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--notebook-accent);
}

/* Search Input */
.search-input {
  background: color-mix(in srgb, var(--notebook-text) 5%, var(--notebook-bg));
  border: 1px solid var(--page-border);
  color: var(--notebook-text);
}

.search-input::placeholder {
  color: var(--pen-gray);
}

.search-input:focus {
  outline: none;
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--notebook-accent) 20%, transparent);
}

/* Search Results */
.search-result-item {
  border-bottom: 1px solid var(--page-border);
}

.search-result-item:hover {
  background: color-mix(in srgb, var(--notebook-text) var(--hover-opacity), transparent);
}

/* Page cover image */
.page-cover-image {
  width: 100%;
  height: 200px;
  overflow: hidden;
  position: relative;
}

.page-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>

<style>
/* Agent chat overlay - unscoped so Teleport works */
.agent-chat-overlay {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 9998;
}

.agent-chat-panel {
  width: 420px;
  height: 600px;
  max-height: calc(100vh - 2rem);
  max-width: calc(100vw - 2rem);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid var(--color-border-medium);
}

@media (max-width: 768px) {
  .agent-chat-overlay {
    inset: 0;
    bottom: 0;
    right: 0;
  }

  .agent-chat-panel {
    width: 100%;
    height: 100%;
    max-height: 100vh;
    max-width: 100vw;
    border-radius: 0;
  }
}
</style>
