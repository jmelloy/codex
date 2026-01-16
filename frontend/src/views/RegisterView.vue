<template>
  <div class="flex justify-center items-center min-h-screen bg-gray-100 p-5 w-full">
    <div class="bg-white p-10 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="mb-8 text-center text-gray-800 text-2xl font-semibold">Register</h1>
      <form @submit.prevent="handleRegister">
        <div class="mb-5">
          <label for="username" class="block mb-1.5 text-gray-700 font-medium">Username</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            required
            minlength="3"
            maxlength="50"
            placeholder="Enter username"
            :disabled="loading"
            class="w-full px-2.5 py-2.5 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed focus:outline-none focus:border-primary"
          />
        </div>

        <div class="mb-5">
          <label for="email" class="block mb-1.5 text-gray-700 font-medium">Email</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            required
            placeholder="Enter email"
            :disabled="loading"
            class="w-full px-2.5 py-2.5 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed focus:outline-none focus:border-primary"
          />
        </div>

        <div class="mb-5">
          <label for="password" class="block mb-1.5 text-gray-700 font-medium">Password</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            required
            minlength="8"
            placeholder="Enter password (min 8 characters)"
            :disabled="loading"
            class="w-full px-2.5 py-2.5 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed focus:outline-none focus:border-primary"
          />
        </div>

        <div class="mb-5">
          <label for="confirmPassword" class="block mb-1.5 text-gray-700 font-medium">Confirm Password</label>
          <input
            id="confirmPassword"
            v-model="form.confirmPassword"
            type="password"
            required
            placeholder="Confirm password"
            :disabled="loading"
            class="w-full px-2.5 py-2.5 border border-gray-300 rounded text-sm disabled:bg-gray-100 disabled:cursor-not-allowed focus:outline-none focus:border-primary"
          />
        </div>

        <div v-if="error" class="text-red-700 bg-red-50 p-2.5 rounded mb-5 text-sm">
          {{ error }}
        </div>

        <button type="submit" :disabled="loading" class="w-full px-3 py-3 bg-primary text-white border-none rounded text-base cursor-pointer transition hover:bg-primary-hover disabled:bg-gray-400 disabled:cursor-not-allowed">
          {{ loading ? 'Registering...' : 'Register' }}
        </button>
      </form>

      <div class="text-center mt-5 text-gray-600">
        Already have an account? 
        <router-link to="/login" class="text-primary no-underline hover:underline">Login here</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/auth';
import { useAuthStore } from '../stores/auth';
import { validatePassword, validateUsername, validatePasswordsMatch } from '../utils/validation';

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
/* Tailwind classes used, minimal custom styles needed */
</style>
