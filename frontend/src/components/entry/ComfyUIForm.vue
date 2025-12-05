<script setup lang="ts">
import { ref, computed, defineEmits, defineProps } from "vue";

const props = defineProps<{
  modelValue?: {
    workflow?: string;
    server_url?: string;
    timeout?: number;
    poll_interval?: number;
  };
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: Record<string, unknown>): void;
}>();

const workflowJson = ref(
  props.modelValue?.workflow
    ? typeof props.modelValue.workflow === "string"
      ? props.modelValue.workflow
      : JSON.stringify(props.modelValue.workflow, null, 2)
    : "",
);
const serverUrl = ref(props.modelValue?.server_url || "http://127.0.0.1:8188");
const timeout = ref(props.modelValue?.timeout || 300);
const pollInterval = ref(props.modelValue?.poll_interval || 1.0);

const workflowError = ref("");

const inputs = computed(() => {
  const result: Record<string, unknown> = {
    server_url: serverUrl.value,
    timeout: timeout.value,
    poll_interval: pollInterval.value,
  };

  if (workflowJson.value.trim()) {
    try {
      result.workflow = JSON.parse(workflowJson.value);
      workflowError.value = "";
    } catch {
      workflowError.value = "Invalid JSON";
    }
  }

  return result;
});

const updateValue = () => {
  emit("update:modelValue", inputs.value);
};

// Example workflow template
const exampleWorkflow = `{
  "1": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "2": {
    "inputs": {
      "text": "a beautiful sunset over mountains",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "3": {
    "inputs": {
      "text": "low quality, blurry",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "4": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "5": {
    "inputs": {
      "seed": 42,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["1", 0],
      "positive": ["2", 0],
      "negative": ["3", 0],
      "latent_image": ["4", 0]
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "samples": ["5", 0],
      "vae": ["1", 2]
    },
    "class_type": "VAEDecode"
  },
  "7": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["6", 0]
    },
    "class_type": "SaveImage"
  }
}`;

const loadExampleWorkflow = () => {
  workflowJson.value = exampleWorkflow;
  updateValue();
};
</script>

<template>
  <div class="comfyui-form">
    <div class="form-group">
      <label for="server-url">ComfyUI Server URL</label>
      <input
        id="server-url"
        v-model="serverUrl"
        type="url"
        placeholder="http://127.0.0.1:8188"
        @input="updateValue"
      />
      <span class="hint">URL of your ComfyUI server</span>
    </div>

    <div class="form-group">
      <label for="workflow">
        Workflow Definition (JSON) <span class="required">*</span>
      </label>
      <div class="workflow-actions">
        <button
          type="button"
          class="template-btn"
          @click="loadExampleWorkflow"
        >
          Load Example Workflow
        </button>
      </div>
      <textarea
        id="workflow"
        v-model="workflowJson"
        rows="16"
        placeholder="Paste your ComfyUI workflow JSON here..."
        @input="updateValue"
        :class="{ error: workflowError }"
      ></textarea>
      <span v-if="workflowError" class="error-text">{{ workflowError }}</span>
      <span v-else class="hint"
        >Paste the workflow JSON exported from ComfyUI. You can export this
        from the ComfyUI interface using the "Save (API Format)" option.</span
      >
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="timeout">Timeout (seconds)</label>
        <input
          id="timeout"
          v-model.number="timeout"
          type="number"
          min="10"
          max="3600"
          @input="updateValue"
        />
        <span class="hint">Maximum execution time</span>
      </div>

      <div class="form-group">
        <label for="poll-interval">Poll Interval (seconds)</label>
        <input
          id="poll-interval"
          v-model.number="pollInterval"
          type="number"
          min="0.1"
          max="10"
          step="0.1"
          @input="updateValue"
        />
        <span class="hint">Status check frequency</span>
      </div>
    </div>

    <div class="info-box">
      <span class="info-icon">💡</span>
      <div>
        <strong>How to get your workflow JSON:</strong>
        <ol>
          <li>Create your workflow in ComfyUI</li>
          <li>Click "Save (API Format)" in the menu</li>
          <li>Copy the JSON and paste it above</li>
        </ol>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comfyui-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.required {
  color: #dc2626;
}

.form-group input,
.form-group textarea {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: inherit;
  background: white;
}

.form-group textarea {
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 0.875rem;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-group input.error,
.form-group textarea.error {
  border-color: #dc2626;
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.error-text {
  font-size: 0.75rem;
  color: #dc2626;
}

.workflow-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.template-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
}

.template-btn:hover {
  background: var(--color-border);
  color: var(--color-text);
}

.info-box {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: #1e40af;
}

.info-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.info-box ol {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
}

.info-box li {
  margin: 0.25rem 0;
}
</style>
