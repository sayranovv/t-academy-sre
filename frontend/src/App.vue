<script setup lang="ts">
import ConfirmDialog from "primevue/confirmdialog";
const today = new Date().toLocaleDateString("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
</script>
<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">Учёт оборудования</RouterLink>
    <nav aria-label="Основная навигация">
      <RouterLink
        to="/equipment"
        :class="{
          'router-link-active':
            $route.path.startsWith('/equipment') &&
            !$route.path.startsWith('/equipment-models'),
        }"
        >Оборудование</RouterLink
      >
      <RouterLink
        to="/employees"
        :class="{ 'router-link-active': $route.path.startsWith('/employees') }"
        >Сотрудники</RouterLink
      >
      <RouterLink
        to="/categories"
        :class="{ 'router-link-active': $route.path === '/equipment-models' }"
        >Справочники</RouterLink
      >
    </nav>
    <RouterLink
      class="project-caption"
      to="/environment"
      title="Состояние окружения"
      >{{ today }}</RouterLink
    >
  </header>
  <main><RouterView /></main>
  <ConfirmDialog />
</template>
