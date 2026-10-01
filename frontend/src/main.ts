import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import PrimeVue from "primevue/config";
import ConfirmationService from "primevue/confirmationservice";
import App from "./App.vue";
import EnvironmentView from "./views/EnvironmentView.vue";
import ResourceView from "./views/ResourceView.vue";
import { equipmentPreset } from "./theme";
import "primeicons/primeicons.css";
import "./style.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/equipment" },
    {
      path: "/equipment/:id?",
      component: ResourceView,
      props: { resource: "equipment" },
    },
    {
      path: "/employees/:id?",
      component: ResourceView,
      props: { resource: "employees" },
    },
    {
      path: "/categories",
      component: ResourceView,
      props: { resource: "categories" },
    },
    {
      path: "/equipment-models",
      component: ResourceView,
      props: { resource: "equipment-models" },
    },
    { path: "/environment", component: EnvironmentView },
    { path: "/:pathMatch(.*)*", redirect: "/equipment" },
  ],
});

createApp(App)
  .use(router)
  .use(ConfirmationService)
  .use(PrimeVue, {
    theme: {
      preset: equipmentPreset,
      options: {
        darkModeSelector: false,
        cssLayer: { name: "primevue", order: "primevue" },
      },
    },
    locale: {
      emptyMessage: "Нет записей",
      emptySearchMessage: "Ничего не найдено",
      selectionMessage: "Выбрано: {0}",
      emptySelectionMessage: "Не выбрано",
      aria: {
        close: "Закрыть",
        firstPageLabel: "Первая страница",
        lastPageLabel: "Последняя страница",
        nextPageLabel: "Следующая страница",
        prevPageLabel: "Предыдущая страница",
        pageLabel: "Страница {page}",
        rowsPerPageLabel: "Записей на странице",
        selectRow: "Выбрать строку",
        unselectRow: "Снять выделение",
      },
    },
  })
  .mount("#app");
