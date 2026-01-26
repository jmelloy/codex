<template>
  <BaseAuthLayout
    title="Register"
    link-text="Already have an account?"
    link-to="/login"
    link-label="Login here"
  >
    <form @submit.prevent="handleRegister">
      <BaseInput
        id="username"
        v-model="form.username"
        type="text"
        label="Username"
        placeholder="Enter username"
        required
        :minlength="3"
        :maxlength="50"
        :disabled="loading"
      />
      <BaseInput
        id="email"
        v-model="form.email"
        type="email"
        label="Email"
        placeholder="Enter email"
        required
        :disabled="loading"
      />
      <BaseInput
        id="password"
        v-model="form.password"
        type="password"
        label="Password"
        placeholder="Enter password (min 8 characters)"
        required
        :minlength="8"
        :disabled="loading"
      />
      <BaseInput
        id="confirmPassword"
        v-model="form.confirmPassword"
        type="password"
        label="Confirm Password"
        placeholder="Confirm password"
        required
        :disabled="loading"
      />
      
      <div v-if="error" class="p-2.5 rounded mb-5 text-sm" style="color: var(--pen-red); background: color-mix(in srgb, var(--pen-red) 10%, transparent)">
        {{ error }}
      </div>

      <BaseButton
        type="submit"
        variant="primary"
        :disabled="loading"
        full-width
      >
        {{ loading ? 'Registering...' : 'Register' }}
      </BaseButton>
    </form>
  </BaseAuthLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/auth';
import { useAuthStore } from '../stores/auth';
import { validatePassword, validateUsername, validatePasswordsMatch } from '../utils/validation';
import BaseAuthLayout from '../components/base/BaseAuthLayout.vue';
import BaseInput from '../components/base/BaseInput.vue';
import BaseButton from '../components/base/BaseButton.vue';

const router = useRouter();
const authStore = useAuthStore();

const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const loading = ref(false);
const error = ref('');

const handleRegister = async () => {
  error.value = '';

  // Validate username
  const usernameValidation = validateUsername(form.value.username);
  if (!usernameValidation.valid) {
    error.value = usernameValidation.error || 'Invalid username';
    return;
  }

  // Validate password
  const passwordValidation = validatePassword(form.value.password);
  if (!passwordValidation.valid) {
    error.value = passwordValidation.error || 'Invalid password';
    return;
  }

  // Validate passwords match
  const passwordsMatchValidation = validatePasswordsMatch(form.value.password, form.value.confirmPassword);
  if (!passwordsMatchValidation.valid) {
    error.value = passwordsMatchValidation.error || 'Passwords do not match';
    return;
  }

  loading.value = true;

  try {
    // Register the user
    await authService.register({
      username: form.value.username,
      email: form.value.email,
      password: form.value.password
    });

    // Automatically log in after successful registration
    const tokenResponse = await authService.login({
      username: form.value.username,
      password: form.value.password
    });

    localStorage.setItem('access_token', tokenResponse.access_token);
    await authStore.fetchCurrentUser();

    // Redirect to home
    router.push('/');
  } catch (err: any) {
    console.error('Registration error:', err);
    error.value = err.response?.data?.detail || 'Registration failed. Please try again.';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Additional styles if needed */
</style>
