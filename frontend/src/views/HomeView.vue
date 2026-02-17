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
        v-if="workspaceStore.currentFile || workspaceStore.currentFolder"
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
                <span class="mr-2 text-sm">{{ getFileIcon(file) }}</span>
                <div class="flex-1 min-w-0">
                  <div class="truncate font-medium" style="color: var(--notebook-text)">
                    {{ file.title || file.filename }}
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
                  @click.stop="startCreateFile(notebook)"
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
                <template v-if="notebookFileTrees.get(notebook.id)?.length">
                  <template v-for="node in notebookFileTrees.get(notebook.id)" :key="node.path">
                    <!-- Render folder or file -->
                    <li v-if="node.type === 'folder'">
                      <!-- Folder -->
                      <div
                        :class="[
                          'folder-item flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] transition',
                          {
                            'bg-primary/20 border-t-2 border-primary':
                              dragOverFolder === `${notebook.id}:${node.path}`,
                          },
                          {
                            'folder-active':
                              workspaceStore.currentFolder?.path === node.path &&
                              workspaceStore.currentFolder?.notebook_id === notebook.id,
                          },
                        ]"
                        @click="handleFolderClick($event, notebook.id, node.path)"
                        @dragover.prevent="handleFolderDragOver($event, notebook.id, node.path)"
                        @dragenter.prevent="handleFolderDragEnter(notebook.id, node.path)"
                        @dragleave="handleFolderDragLeave"
                        @drop.prevent.stop="handleFolderDrop($event, notebook.id, node.path)"
                      >
                        <span class="text-[10px] mr-2 w-3" style="color: var(--pen-gray)">{{
                          isFolderExpanded(notebook.id, node.path) ? "▼" : "▶"
                        }}</span>
                        <span class="mr-2 text-sm">📁</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{
                          node.name
                        }}</span>
                      </div>

                      <!-- Folder contents -->
                      <ul
                        v-if="isFolderExpanded(notebook.id, node.path) && node.children"
                        class="list-none p-0 m-0"
                      >
                        <FileTreeItem
                          v-for="child in node.children"
                          :key="child.path"
                          :node="child"
                          :notebook-id="notebook.id"
                          :depth="1"
                          :expanded-folders="expandedFolders"
                          :current-file-id="workspaceStore.currentFile?.id"
                          :current-folder-path="workspaceStore.currentFolder?.path"
                          :current-folder-notebook-id="workspaceStore.currentFolder?.notebook_id"
                          @toggle-folder="toggleFolder"
                          @select-folder="handleSelectFolder"
                          @select-file="selectFile"
                          @move-file="handleMoveFile"
                        />
                      </ul>
                    </li>

                    <!-- Root level file -->
                    <li v-else>
                      <div
                        :class="[
                          'file-item flex items-center py-2 px-4 pl-8 cursor-grab text-[13px] transition',
                          {
                            'file-active font-medium':
                              workspaceStore.currentFile?.id === node.file?.id,
                          },
                        ]"
                        draggable="true"
                        @click="node.file && selectFile(node.file)"
                        @dragstart="handleFileDragStart($event, node.file!, notebook.id)"
                      >
                        <span class="mr-2 text-sm">{{ getFileIcon(node.file) }}</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{
                          node.file?.title || node.name
                        }}</span>
                      </div>
                    </li>
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
        v-if="workspaceStore.fileLoading"
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

      <!-- Editor Mode -->
      <div
        v-else-if="workspaceStore.isEditing && workspaceStore.currentFile"
        class="flex-1 flex overflow-hidden p-4"
      >
        <div class="flex-1 flex flex-col overflow-hidden">
          <FileHeader
            :file="workspaceStore.currentFile"
            @toggle-properties="toggleProperties"
            @rename="handleRenameFile"
          >
            <template #actions>
              <!-- Markdown files: autosave is on, just show Done + Properties -->
              <template v-if="isMarkdownFile">
                <button
                  @click="handleCancelEdit"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                >
                  Done
                </button>
              </template>
              <!-- Non-markdown files: show explicit Save/Cancel -->
              <template v-else>
                <button
                  @click="handleSaveFile(editContent)"
                  class="notebook-button-primary px-4 py-2 rounded cursor-pointer text-sm transition"
                >
                  Save
                </button>
                <button
                  @click="handleCancelEdit"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                >
                  Cancel
                </button>
              </template>
              <button
                @click="toggleProperties"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
              >
                Properties
              </button>
            </template>
          </FileHeader>
          <MarkdownEditor
            v-model="editContent"
            :frontmatter="workspaceStore.currentFile.properties"
            :autosave="isMarkdownFile"
            :autosave-delay="1500"
            :workspace-id="workspaceStore.currentWorkspace?.id"
            :notebook-id="workspaceStore.currentFile.notebook_id"
            @save="isMarkdownFile ? handleAutoSave($event) : handleSaveFile($event)"
            @cancel="handleCancelEdit"
            class="flex-1"
          />
        </div>
      </div>

      <!-- Viewer Mode -->
      <div v-else-if="workspaceStore.currentFile" class="flex-1 flex overflow-hidden p-4">
        <!-- All file types use a consistent header + content pattern -->
        <div class="flex-1 flex flex-col overflow-hidden">
          <FileHeader
            :file="workspaceStore.currentFile"
            @toggle-properties="toggleProperties"
            @rename="handleRenameFile"
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

              <!-- Editable files (code, markdown, view) get Edit button -->
              <button
                v-else-if="['code', 'markdown', 'view'].includes(displayType)"
                @click="startEdit"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
              >
                Edit
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
          </FileHeader>

          <!-- Image Viewer -->
          <div
            v-if="displayType === 'image'"
            class="flex-1 flex items-center justify-center overflow-auto bg-bg-secondary rounded-lg"
          >
            <img
              :src="currentContentUrl"
              :alt="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
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
              :title="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
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
              :title="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>

          <!-- Dynamic View Renderer for .cdx files -->
          <ViewRenderer
            v-else-if="displayType === 'view'"
            :file-id="workspaceStore.currentFile.id"
            :workspace-id="workspaceStore.currentWorkspace!.id"
            :notebook-id="workspaceStore.currentFile.notebook_id"
            class="flex-1"
            @select-file="selectFile"
          />

          <!-- Code Viewer -->
          <CodeViewer
            v-else-if="displayType === 'code'"
            :content="workspaceStore.currentFile.content"
            :filename="workspaceStore.currentFile.filename"
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
            :content="workspaceStore.currentFile.content"
            :frontmatter="workspaceStore.currentFile.properties"
            :workspace-id="workspaceStore.currentWorkspace?.id"
            :notebook-id="workspaceStore.currentNotebook?.id"
            :current-file-path="workspaceStore.currentFile.path"
            :show-frontmatter="false"
            :show-toolbar="false"
            @edit="startEdit"
            @copy="handleCopy"
            class="flex-1"
          />
        </div>
      </div>

      <!-- Folder View Mode -->
      <div v-else-if="workspaceStore.currentFolder" class="flex-1 flex overflow-hidden p-4">
        <FolderView
          :folder="workspaceStore.currentFolder"
          class="flex-1"
          @select-file="selectFile"
          @select-folder="handleSelectSubfolder"
          @toggle-properties="toggleProperties"
        />
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
      v-if="showPropertiesPanel && (workspaceStore.currentFile || workspaceStore.currentFolder)"
      class="fixed inset-0 bg-black/50 z-40 lg:hidden"
      @click="showPropertiesPanel = false"
    ></div>

    <FilePropertiesPanel
      v-if="showPropertiesPanel && workspaceStore.currentFile && workspaceStore.currentWorkspace"
      :file="workspaceStore.currentFile"
      :workspace-id="workspaceStore.currentWorkspace.id"
      :notebook-id="workspaceStore.currentFile.notebook_id"
      class="w-full lg:w-[300px] lg:min-w-[300px] fixed lg:relative inset-0 lg:inset-auto z-50 lg:z-auto pt-14 lg:pt-0"
      @close="showPropertiesPanel = false"
      @update-properties="handleUpdateProperties"
      @delete="handleDeleteFile"
      @restore="handleRestoreVersion"
    />

    <!-- Folder Properties Panel -->
    <FolderPropertiesPanel
      v-if="showPropertiesPanel && workspaceStore.currentFolder && !workspaceStore.currentFile"
      :folder="workspaceStore.currentFolder"
      class="w-full lg:w-[300px] lg:min-w-[300px] fixed lg:relative inset-0 lg:inset-auto z-50 lg:z-auto pt-14 lg:pt-0"
      @close="showPropertiesPanel = false"
      @update-properties="handleUpdateFolderProperties"
      @delete="handleDeleteFolder"
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
  <Modal v-model="showCreateFile" title="Create File" confirm-text="Create" hide-actions>
    <form @submit.prevent="handleCreateFile">
      <!-- Template Selection -->
      <div class="mb-4">
        <TemplateSelector
          :notebook-id="createFileNotebook?.id"
          :workspace-id="workspaceStore.currentWorkspace?.id"
          v-model="selectedTemplate"
          @select="handleTemplateSelect"
          @update:mode="handleModeChange"
        />
      </div>

      <!-- Input section -->
      <div class="border-t border-border-light pt-4 mt-4">
        <!-- Template filename input -->
        <FormGroup v-if="selectedTemplate" label="Filename" v-slot="{ inputId }">
          <div class="flex items-center gap-2">
            <input
              :id="inputId"
              v-model="customTitle"
              :placeholder="getFilenamePlaceholder()"
              class="flex-1 px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
            />
            <span class="text-text-secondary text-sm">{{ selectedTemplate?.file_extension }}</span>
          </div>
          <p class="text-sm text-text-secondary mt-1">
            Will create: <code class="bg-bg-hover px-1 rounded">{{ getPreviewFilename() }}</code>
          </p>
        </FormGroup>

        <!-- Blank file filename input -->
        <FormGroup v-else label="Filename" v-slot="{ inputId }">
          <input
            :id="inputId"
            v-model="newFileName"
            placeholder="example.md"
            required
            class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
          />
          <p class="text-sm text-text-secondary mt-1">
            Enter any filename with extension (e.g., notes.md, data.json, script.py)
          </p>
        </FormGroup>
      </div>

      <div class="flex gap-2 justify-end mt-6">
        <button
          type="button"
          @click="showCreateFile = false"
          class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer"
        >
          Cancel
        </button>
        <button
          v-if="createMode === 'file' && !selectedTemplate && newFileName.endsWith('.cdx')"
          type="button"
          @click="switchToViewCreator"
          class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition"
        >
          Configure View →
        </button>
        <button
          v-else
          type="submit"
          class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition"
        >
          Create
        </button>
      </div>
    </form>
  </Modal>

  <!-- Create View Modal -->
  <CreateViewModal v-model="showCreateView" @create="handleCreateView" />

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
import type { Workspace, Notebook, FileMetadata, Template } from "../services/codex"
import { templateService, searchService } from "../services/codex"
import { getDisplayType } from "../utils/contentType"
import Modal from "../components/Modal.vue"
import FormGroup from "../components/FormGroup.vue"
import MarkdownViewer from "../components/MarkdownViewer.vue"
import MarkdownEditor from "../components/MarkdownEditor.vue"
import CodeViewer from "../components/CodeViewer.vue"
import ViewRenderer from "../components/views/ViewRenderer.vue"
import FilePropertiesPanel from "../components/FilePropertiesPanel.vue"
import FolderPropertiesPanel from "../components/FolderPropertiesPanel.vue"
import FolderView from "../components/FolderView.vue"
import FileHeader from "../components/FileHeader.vue"
import FileTreeItem from "../components/FileTreeItem.vue"
import CreateViewModal from "../components/CreateViewModal.vue"
import TemplateSelector from "../components/TemplateSelector.vue"
import SettingsDialog from "../components/SettingsDialog.vue"
import AgentChat from "../components/agent/AgentChat.vue"
import { useAgentStore } from "../stores/agent"
import type { Agent } from "../services/agent"
import { showToast } from "../utils/toast"
import type { FileTreeNode } from "../utils/fileTree"

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const agentStore = useAgentStore()

// Modal state
const showCreateWorkspace = ref(false)
const showCreateNotebook = ref(false)
const showCreateFile = ref(false)
const showCreateView = ref(false)
const showSettingsDialog = ref(false)

// Form state
const newWorkspaceName = ref("")
const newNotebookName = ref("")
const newFileName = ref("")
const createFileNotebook = ref<Notebook | null>(null)
const selectedTemplate = ref<Template | null>(null)
const customTitle = ref("")
const createMode = ref<"file" | "template">("file")

// View state
const showPropertiesPanel = ref(false)
const editContent = ref("")

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
const searchResults = ref<FileMetadata[]>([])
const isSearching = ref(false)

// Folder expansion state - tracks which folder paths are expanded
const expandedFolders = ref<Map<number, Set<string>>>(new Map())

// Drag-drop state
const dragOverNotebook = ref<number | null>(null)
const dragOverFolder = ref<string | null>(null)

// Get file trees from the store (now pre-built and maintained)
const notebookFileTrees = computed(() => {
  const trees = new Map<number, FileTreeNode[]>()
  workspaceStore.notebooks.forEach((notebook) => {
    trees.set(notebook.id, workspaceStore.getFileTree(notebook.id))
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

// Build file URL path: /w/{workspace}/{notebook}/{filePath}
function buildFileUrl(file: FileMetadata, notebook?: Notebook | null): string {
  const ws = workspaceStore.currentWorkspace
  const nb = notebook || workspaceStore.notebooks.find((n) => n.id === file.notebook_id)
  if (!ws || !nb) return "/"
  return `/w/${getSlugOrId(ws)}/${getSlugOrId(nb)}/${file.path}`
}

// Build folder URL path: /w/{workspace}/{notebook}/{folderPath}
function buildFolderUrl(folderPath: string, notebookId: number): string {
  const ws = workspaceStore.currentWorkspace
  const nb = workspaceStore.notebooks.find((n) => n.id === notebookId)
  if (!ws || !nb) return "/"
  return `/w/${getSlugOrId(ws)}/${getSlugOrId(nb)}/${folderPath}`
}

// Get content URL for current file (for binary files like images, PDFs, audio, video)
const currentContentUrl = computed(() => {
  if (!workspaceStore.currentFile || !workspaceStore.currentWorkspace) return ""
  const workspaceId = workspaceStore.currentWorkspace.id || workspaceStore.currentWorkspace.slug
  const notebook = workspaceStore.notebooks.find(
    (n: any) => n.id === workspaceStore.currentFile?.notebook_id,
  )
  const notebookId = notebook?.id || notebook?.slug
  return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${workspaceStore.currentFile.id}/content`
})

// Get display type for current file
const displayType = computed(() => {
  if (!workspaceStore.currentFile) return "markdown"
  return getDisplayType(workspaceStore.currentFile.content_type)
})

// Check if the current file is a markdown file (for auto-edit behavior)
const isMarkdownFile = computed(() => displayType.value === "markdown")

// Open file in a new tab
function openInNewTab() {
  if (currentContentUrl.value) {
    window.open(currentContentUrl.value, "_blank")
  }
}

// Sync edit content when file changes
watch(
  () => workspaceStore.currentFile,
  (file) => {
    if (file) {
      editContent.value = file.content
    }
  },
  { immediate: true },
)

// Auto-enter live edit mode for markdown files when they finish loading
watch([() => workspaceStore.currentFile, () => workspaceStore.fileLoading], ([file, loading]) => {
  if (
    file &&
    !loading &&
    file.content !== undefined &&
    getDisplayType(file.content_type) === "markdown" &&
    !workspaceStore.isEditing
  ) {
    startEdit()
  }
})

// Watch for route changes to restore file/folder selection from URL (path-based)
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

        // Make sure files for this notebook are loaded
        const files = workspaceStore.getFilesForNotebook(notebook.id)
        if (files.length === 0) {
          await workspaceStore.fetchFiles(notebook.id)
        }

        // Try to find as file first, then as folder
        const file = workspaceStore
          .getFilesForNotebook(notebook.id)
          .find((f) => f.path === itemPath)
        if (file && workspaceStore.currentFile?.path !== itemPath) {
          await workspaceStore.selectFile(file)
        } else if (!file && workspaceStore.currentFolder?.path !== itemPath) {
          // Not a file, try as folder
          await workspaceStore.selectFolder(itemPath, notebook.id)
        }
      }
    } else if (!workspaceSlug && !notebookSlug && !itemPath && route.name === "home") {
      // Clear file/folder selection if on home route with no path params
      workspaceStore.currentFile = null
      workspaceStore.currentFolder = null
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
      // Fetch files for the notebook (in case toggle didn't complete yet)
      await workspaceStore.fetchFiles(notebook.id)

      // Try to find as file first, then as folder
      const file = workspaceStore.getFilesForNotebook(notebook.id).find((f) => f.path === itemPath)
      if (file) {
        await workspaceStore.selectFile(file)
      } else {
        // Not a file, try as folder
        await workspaceStore.selectFolder(itemPath, notebook.id)
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

// Watch for file/folder selection to update document title
watch(
  () =>
    [workspaceStore.currentFile, workspaceStore.currentFolder, workspaceStore.notebooks] as const,
  () => {
    const file = workspaceStore.currentFile
    const folder = workspaceStore.currentFolder
    const notebooks = workspaceStore.notebooks

    if (file) {
      // File selected: "Codex - Notebook / Title (or Filename)"
      // Look up the notebook by the file's notebook_id for accuracy
      const notebook = notebooks.find((n) => n.id === file.notebook_id)
      const notebookName = notebook?.name || "Notebook"
      const fileTitle = file.title || file.filename
      document.title = `Codex - ${notebookName} / ${fileTitle}`
    } else if (folder) {
      // Folder selected: "Codex - Notebook / Folder"
      // Look up the notebook by the folder's notebook_id for accuracy
      const notebook = notebooks.find((n) => n.id === folder.notebook_id)
      const notebookName = notebook?.name || "Notebook"
      const folderTitle = folder.title || folder.name
      document.title = `Codex - ${notebookName} / ${folderTitle}`
    } else if (workspaceStore.currentNotebook) {
      // Only notebook selected: "Codex - Notebook"
      document.title = `Codex - ${workspaceStore.currentNotebook.name}`
    } else {
      // Nothing selected: just "Codex"
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

function toggleFolder(notebookId: number, folderPath: string) {
  if (!expandedFolders.value.has(notebookId)) {
    expandedFolders.value.set(notebookId, new Set())
  }
  const folders = expandedFolders.value.get(notebookId)!
  if (folders.has(folderPath)) {
    folders.delete(folderPath)
  } else {
    folders.add(folderPath)
  }
}

async function handleFolderClick(event: MouseEvent, notebookId: number, folderPath: string) {
  // If clicking on the expand arrow area, just toggle expansion
  const target = event.target as HTMLElement
  const isArrowClick =
    target.classList.contains("text-[10px]") || target.closest(".text-\\[10px\\]")

  await expandOrCollapseFolder(notebookId, folderPath, !isArrowClick)
}

async function expandOrCollapseFolder(
  notebookId: number,
  folderPath: string,
  closeSidebar: boolean = false,
) {
  const isExpanded = isFolderExpanded(notebookId, folderPath)

  if (isExpanded) {
    // Just collapse
    toggleFolder(notebookId, folderPath)
  } else {
    // Expand and select - fetch contents first
    await workspaceStore.selectFolder(folderPath, notebookId)
    // Only expand in UI after successful fetch
    if (workspaceStore.currentFolder?.path === folderPath) {
      toggleFolder(notebookId, folderPath)
    }
    // Close sidebar on mobile after selection if requested
    if (closeSidebar) {
      closeSidebarOnMobile()
    }
  }
}

async function handleSelectFolder(notebookId: number, folderPath: string) {
  // Select the folder and show folder view - this fetches contents
  await workspaceStore.selectFolder(folderPath, notebookId)
  // Close sidebar on mobile after selection
  closeSidebarOnMobile()

  // Expand the folder in UI only after contents are loaded
  if (workspaceStore.currentFolder?.path === folderPath) {
    if (!expandedFolders.value.has(notebookId)) {
      expandedFolders.value.set(notebookId, new Set())
    }
    const folders = expandedFolders.value.get(notebookId)!
    if (!folders.has(folderPath)) {
      folders.add(folderPath)
    }
  }

  // Update URL with path-based format for browser history navigation
  const newUrl = buildFolderUrl(folderPath, notebookId)
  if (newUrl !== "/" && route.path !== newUrl) {
    router.push(newUrl)
  }
}

async function handleSelectSubfolder(subfolder: { path: string }) {
  // Get the notebook_id from the current folder
  if (workspaceStore.currentFolder) {
    const notebookId = workspaceStore.currentFolder.notebook_id
    await handleSelectFolder(notebookId, subfolder.path)
  }
}

function isFolderExpanded(notebookId: number, folderPath: string): boolean {
  return expandedFolders.value.get(notebookId)?.has(folderPath) || false
}

function getFileIcon(file: FileMetadata | undefined): string {
  if (!file) return "📄"

  const displayType = getDisplayType(file.content_type)

  switch (displayType) {
    case "view":
      return "📊" // Chart/view icon for .cdx files
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

function selectFile(file: FileMetadata) {
  workspaceStore.selectFile(file)
  // Close sidebar on mobile after selection
  closeSidebarOnMobile()
  // Update URL with path-based format for browser history navigation
  const newUrl = buildFileUrl(file)
  if (newUrl !== "/" && route.path !== newUrl) {
    router.push(newUrl)
  }
}

// Drag-drop handlers for files within the sidebar
function handleFileDragStart(event: DragEvent, file: FileMetadata, notebookId: number) {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = "move"
  event.dataTransfer.setData(
    "application/x-codex-file",
    JSON.stringify({
      fileId: file.id,
      notebookId: notebookId,
      filename: file.filename,
      path: file.path,
    }),
  )
}

// Folder drag-over handlers
function handleFolderDragOver(event: DragEvent, _notebookId: number, _folderPath: string) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes("application/x-codex-file")
  const hasExternalFile = event.dataTransfer.types.includes("Files")
  if (hasFile || hasExternalFile) {
    event.dataTransfer.dropEffect = "move"
  }
}

function handleFolderDragEnter(notebookId: number, folderPath: string) {
  dragOverFolder.value = `${notebookId}:${folderPath}`
}

function handleFolderDragLeave() {
  dragOverFolder.value = null
}

async function handleFolderDrop(event: DragEvent, notebookId: number, folderPath: string) {
  dragOverFolder.value = null
  if (!event.dataTransfer) return

  // Handle external file drop (upload)
  if (event.dataTransfer.files.length > 0) {
    await handleFileUpload(event.dataTransfer.files, notebookId, folderPath)
    return
  }

  // Handle internal file move
  const data = event.dataTransfer.getData("application/x-codex-file")
  if (!data) return

  try {
    const { fileId, filename } = JSON.parse(data)
    const newPath = folderPath ? `${folderPath}/${filename}` : filename
    await handleMoveFile(fileId, newPath)
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

// Notebook-level drag handlers (for root-level drops)
function handleNotebookDragOver(event: DragEvent, _notebookId: number) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes("application/x-codex-file")
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
  if (event.dataTransfer.files.length > 0) {
    await handleFileUpload(event.dataTransfer.files, notebookId, "")
    return
  }

  // Handle internal file move to root
  const data = event.dataTransfer.getData("application/x-codex-file")
  if (!data) return

  try {
    const { fileId, filename, path } = JSON.parse(data)
    // Only move if not already at root
    if (path !== filename) {
      await handleMoveFile(fileId, filename)
    }
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

// Handle file upload from drag-drop
async function handleFileUpload(files: FileList, notebookId: number, folderPath: string) {
  for (const file of Array.from(files)) {
    try {
      const targetPath = folderPath ? `${folderPath}/${file.name}` : file.name
      await workspaceStore.uploadFile(notebookId, file, targetPath)
      showToast({ message: `Uploaded ${file.name}` })
    } catch (e) {
      console.error(`Failed to upload ${file.name}:`, e)
      showToast({ message: `Failed to upload ${file.name}`, type: "error" })
    }
  }
}

// Handle moving a file to a new path
async function handleMoveFile(fileId: number, newPath: string) {
  const file = findFileById(fileId)
  if (!file) return

  try {
    await workspaceStore.moveFile(fileId, file.notebook_id, newPath)
    showToast({ message: "File moved successfully" })
  } catch (e) {
    console.error("Failed to move file:", e)
    showToast({ message: "Failed to move file", type: "error" })
  }
}

// Helper to find a file by ID across all notebooks
function findFileById(fileId: number): FileMetadata | undefined {
  for (const files of workspaceStore.files.values()) {
    const file = files.find((f) => f.id === fileId)
    if (file) return file
  }
  return undefined
}

function startEdit() {
  if (workspaceStore.currentFile) {
    editContent.value = workspaceStore.currentFile.content
    workspaceStore.setEditing(true)
  }
}

function handleCancelEdit() {
  workspaceStore.setEditing(false)
  if (workspaceStore.currentFile) {
    editContent.value = workspaceStore.currentFile.content
  }
}

async function handleSaveFile(content: string) {
  try {
    await workspaceStore.saveFile(content)
    showToast({ message: "File saved successfully" })
  } catch {
    // Error handled in store
  }
}

async function handleAutoSave(content: string) {
  try {
    await workspaceStore.saveFile(content, undefined, true)
  } catch {
    // Error handled in store
  }
}

function handleCopy() {
  showToast({ message: "Content copied to clipboard!" })
}

function toggleProperties() {
  showPropertiesPanel.value = !showPropertiesPanel.value
}

async function handleUpdateProperties(properties: Record<string, any>) {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.saveFile(workspaceStore.currentFile.content, properties)
    } catch {
      // Error handled in store
    }
  }
}

async function handleRestoreVersion(content: string) {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.saveFile(content)
      editContent.value = content
      showToast({ message: "File restored to previous version" })
    } catch {
      showToast({ message: "Failed to restore file", type: "error" })
    }
  }
}

async function handleDeleteFile() {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.deleteFile(workspaceStore.currentFile.id)
      showPropertiesPanel.value = false
      showToast({ message: "File deleted" })
    } catch {
      // Error handled in store
    }
  }
}

// Handle renaming a file by changing its filename while keeping the same directory
async function handleRenameFile(newFilename: string) {
  if (!workspaceStore.currentFile) return

  const currentFile = workspaceStore.currentFile
  const currentPath = currentFile.path

  // Get the directory part of the current path
  const lastSlashIndex = currentPath.lastIndexOf("/")
  const directory = lastSlashIndex >= 0 ? currentPath.substring(0, lastSlashIndex + 1) : ""

  // Construct the new path with the same directory but new filename
  const newPath = directory + newFilename

  // Don't do anything if the path hasn't changed
  if (newPath === currentPath) return

  try {
    await workspaceStore.moveFile(currentFile.id, currentFile.notebook_id, newPath)
    showToast({ message: "File renamed successfully" })
  } catch (e) {
    console.error("Failed to rename file:", e)
    showToast({ message: "Failed to rename file", type: "error" })
  }
}

async function handleUpdateFolderProperties(properties: Record<string, any>) {
  if (workspaceStore.currentFolder) {
    try {
      await workspaceStore.saveFolderProperties(properties)
      showToast({ message: "Folder properties updated" })
    } catch {
      // Error handled in store
    }
  }
}

async function handleDeleteFolder() {
  if (workspaceStore.currentFolder) {
    try {
      await workspaceStore.deleteFolder()
      showPropertiesPanel.value = false
      showToast({ message: "Folder deleted" })
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

async function handleCreateFile() {
  if (!createFileNotebook.value || !workspaceStore.currentWorkspace) return

  try {
    // If a template is selected, use the template service
    if (selectedTemplate.value) {
      const filename = customTitle.value
        ? customTitle.value + selectedTemplate.value.file_extension
        : undefined

      const newFile = await templateService.createFromTemplate(
        createFileNotebook.value.id,
        workspaceStore.currentWorkspace.id,
        selectedTemplate.value.id,
        filename,
      )

      // Refresh file list and select the new file
      await workspaceStore.fetchFiles(createFileNotebook.value.id)
      await workspaceStore.selectFile(newFile)

      showCreateFile.value = false
      newFileName.value = ""
      customTitle.value = ""
      selectedTemplate.value = null
      createFileNotebook.value = null
      showToast({ message: "File created from template!" })
      return
    }

    // Otherwise, create a blank file with custom content
    const path = newFileName.value
    const baseName = path.replace(/\.[^/.]+$/, "") || path

    // Generate default content based on file extension
    let content: string
    if (path.endsWith(".cdx")) {
      // Create basic view template
      content = `---
type: view
view_type: kanban
title: ${baseName}
description: Dynamic view
query:
  tags: []
config: {}
---

# ${baseName}

Edit the frontmatter above to configure this view.
`
    } else if (path.endsWith(".md")) {
      content = `# ${baseName}\n\nStart writing here...`
    } else if (path.endsWith(".json")) {
      content = "{\n  \n}"
    } else {
      // Default: empty file for other types
      content = ""
    }

    await workspaceStore.createFile(createFileNotebook.value.id, path, content)
    showCreateFile.value = false
    newFileName.value = ""
    customTitle.value = ""
    selectedTemplate.value = null
    createFileNotebook.value = null
  } catch {
    // Error handled in store
  }
}

function switchToViewCreator() {
  showCreateFile.value = false
  showCreateView.value = true
}

async function handleCreateView(data: { filename: string; content: string }) {
  if (!createFileNotebook.value) return

  try {
    await workspaceStore.createFile(createFileNotebook.value.id, data.filename, data.content)
    showCreateView.value = false
    createFileNotebook.value = null
    showToast({ message: "View created successfully!" })
  } catch {
    // Error handled in store
  }
}

function startCreateFile(notebook: Notebook) {
  createFileNotebook.value = notebook
  newFileName.value = ""
  selectedTemplate.value = null
  customTitle.value = ""
  createMode.value = "file"
  showCreateFile.value = true
}

function handleTemplateSelect(template: Template | null) {
  selectedTemplate.value = template
  if (template) {
    createMode.value = "template"
    // Clear custom filename when a template is selected
    customTitle.value = ""
  }
}

function handleModeChange(mode: "file" | "template") {
  createMode.value = mode
}

function getFilenamePlaceholder(): string {
  if (!selectedTemplate.value) return "filename"
  // Extract placeholder from default_name pattern
  const pattern = selectedTemplate.value.default_name
  if (pattern.includes("{title}")) {
    return "Enter title (optional)"
  }
  // For date-based patterns, show what the filename will be
  return templateService.expandPattern(pattern).replace(selectedTemplate.value.file_extension, "")
}

function getPreviewFilename(): string {
  if (!selectedTemplate.value) return newFileName.value || "filename.md"

  const pattern = selectedTemplate.value.default_name
  const title = customTitle.value || "untitled"

  return templateService.expandPattern(pattern, title)
}

// Search functionality
async function handleSearch() {
  if (!searchQuery.value.trim() || !workspaceStore.currentWorkspace) {
    searchResults.value = []
    return
  }

  isSearching.value = true
  try {
    // First, do a local search through all loaded files
    const query = searchQuery.value.toLowerCase()
    const localResults: FileMetadata[] = []

    for (const [_notebookId, files] of workspaceStore.files) {
      for (const file of files) {
        // Search in filename, title, and path
        if (
          file.filename.toLowerCase().includes(query) ||
          file.title?.toLowerCase().includes(query) ||
          file.path.toLowerCase().includes(query)
        ) {
          localResults.push(file)
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
            localResults.push(result)
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

function selectSearchResult(file: FileMetadata) {
  // Switch back to files tab and select the file
  sidebarTab.value = "files"
  selectFile(file)

  // Expand the notebook containing the file
  const notebook = workspaceStore.notebooks.find((n) => n.id === file.notebook_id)
  if (notebook && !workspaceStore.expandedNotebooks.has(notebook.id)) {
    workspaceStore.toggleNotebookExpansion(notebook)
  }

  // Expand parent folders if the file is in a folder
  if (file.path.includes("/")) {
    const pathParts = file.path.split("/")
    pathParts.pop() // Remove filename

    if (!expandedFolders.value.has(file.notebook_id)) {
      expandedFolders.value.set(file.notebook_id, new Set())
    }

    // Expand each parent folder
    let currentPath = ""
    for (const part of pathParts) {
      currentPath = currentPath ? `${currentPath}/${part}` : part
      expandedFolders.value.get(file.notebook_id)!.add(currentPath)
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

/* Folder items */
.folder-item {
  color: var(--pen-gray);
}

.folder-item:hover:not(.folder-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.folder-active {
  background: color-mix(in srgb, var(--notebook-accent) var(--selected-opacity), transparent);
  color: var(--notebook-accent);
}

/* File items */
.file-item {
  color: var(--pen-gray);
}

.file-item:hover:not(.file-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.file-active {
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
