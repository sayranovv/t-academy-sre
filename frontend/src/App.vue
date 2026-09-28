<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">Учёт оборудования</RouterLink>
    <nav aria-label="Основная навигация">
      <RouterLink to="/environment">Окружение</RouterLink>
    </nav>
    <span class="project-caption">Т-Академия · SRE</span>
  </header>
  <main><RouterView /></main>
</template>
