<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useConfirm } from "primevue/useconfirm";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Paginator from "primevue/paginator";
import Message from "primevue/message";
import Tag from "primevue/tag";
import Dialog from "primevue/dialog";
import ResourceForm from "../components/ResourceForm.vue";
import EquipmentDetail from "../components/EquipmentDetail.vue";
import EmployeeDetail from "../components/EmployeeDetail.vue";
import RelationPicker from "../components/RelationPicker.vue";
import { request, errorText } from "../api";
import {
  availability,
  titles,
  type Resource,
  type Item,
  type Page,
} from "../domain";

const props = defineProps<{ resource: Resource }>();
const route = useRoute(),
  router = useRouter(),
  confirm = useConfirm();
const rows = ref<Item[]>([]),
  total = ref(0),
  loading = ref(false),
  error = ref("");
const search = ref(""),
  formVisible = ref(false),
  editing = ref<Item | null>(null),
  revision = ref(0);
const selectedId = computed(() => Number(route.params.id) || null);
const offset = computed(() => Math.max(0, Number(route.query.offset) || 0));
const limit = computed(() =>
  Math.min(100, Math.max(1, Number(route.query.limit) || 10)),
);
const split = computed(
  () => props.resource === "equipment" || props.resource === "employees",
);
const categoryLabel = ref("");
const advancedVisible = ref(false),
  modelLabel = ref(""),
  employeeLabel = ref("");
let generation = 0;
function setQuery(values: Record<string, string | number | null>) {
  const query = { ...route.query, offset: undefined } as Record<
    string,
    string | string[] | null | undefined
  >;
  for (const [key, value] of Object.entries(values))
    query[key] = value === null || value === "" ? undefined : String(value);
  void router.replace({ query });
}
async function load() {
  const token = ++generation;
  const resourceAtStart = props.resource;
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({
      limit: String(limit.value),
      offset: String(offset.value),
    });
    for (const key of [
      "q",
      "category_id",
      "available",
      "operational_state",
      "is_active",
      "employee_id",
      "model_id",
      "sort",
      "desc",
    ]) {
      if (route.query[key] != null) params.set(key, String(route.query[key]));
    }
    const page = await request<Page>(`${props.resource}?${params}`);
    if (token === generation && resourceAtStart === props.resource) {
      rows.value = page.items;
      total.value = page.total;
      if (page.total > 0 && offset.value >= page.total) {
        setQuery({
          offset: Math.floor((page.total - 1) / limit.value) * limit.value,
        });
      }
    }
  } catch (e) {
    if (token === generation && resourceAtStart === props.resource) {
      rows.value = [];
      error.value = errorText(e);
    }
  } finally {
    if (token === generation && resourceAtStart === props.resource)
      loading.value = false;
  }
}
watch(
  () => [props.resource, route.fullPath],
  () => {
    rows.value = [];
    total.value = 0;
    search.value = String(route.query.q ?? "");
    void load();
  },
  { immediate: true },
);
watch(
  () => props.resource,
  () => {
    editing.value = null;
    formVisible.value = false;
    categoryLabel.value = "";
  },
);
function edit(item: Item) {
  editing.value = item;
  formVisible.value = true;
}
function add() {
  editing.value = null;
  formVisible.value = true;
}
async function saved(item: Item) {
  revision.value++;
  if (split.value)
    await router.push({
      path: `/${props.resource}/${item.id}`,
      query: route.query,
    });
  await load();
}
async function deleted() {
  await router.push({ path: `/${props.resource}`, query: route.query });
  await load();
}
function remove(item: Item) {
  confirm.require({
    header: "Удалить запись?",
    message:
      "Связанные записи должны быть удалены или перенесены прежде, чем удалять справочник.",
    acceptLabel: "Удалить",
    rejectLabel: "Отмена",
    accept: async () => {
      try {
        await request(`${props.resource}/${item.id}`, "DELETE");
        await load();
      } catch (e) {
        error.value = errorText(e);
      }
    },
  });
}
const availabilityFilter = computed(
  () =>
    route.query.operational_state ??
    (route.query.available === "true"
      ? "available"
      : route.query.available === "false"
        ? "not_available"
        : null),
);
function filterAvailability(value: string | null) {
  setQuery({
    available:
      value === "available"
        ? "true"
        : value === "not_available"
          ? "false"
          : null,
    operational_state:
      value && !["available", "not_available"].includes(value) ? value : null,
  });
}
</script>

<template>
  <div class="resource-layout" :class="{ split, 'has-selection': selectedId }">
    <section class="list-pane">
      <div v-if="!split" class="catalog-tabs">
        <RouterLink to="/categories">Категории</RouterLink
        ><RouterLink to="/equipment-models">Модели</RouterLink>
      </div>
      <div class="page-heading">
        <div class="title-line">
          <h1>{{ titles[resource] }}</h1>
          <span class="muted count">{{ total }} записей</span>
        </div>
        <Button label="Добавить" icon="pi pi-plus" outlined @click="add" />
      </div>
      <form class="filters" @submit.prevent="setQuery({ q: search })">
        <span class="search-control"
          ><i class="pi pi-search" aria-hidden="true" /><InputText
            v-model="search"
            :placeholder="
              resource === 'equipment'
                ? 'Номер или модель'
                : 'Поиск по названию или номеру'
            "
            aria-label="Поиск" /><Button
            type="submit"
            icon="pi pi-arrow-right"
            text
            aria-label="Найти"
        /></span>
        <RelationPicker
          v-if="resource === 'equipment' || resource === 'equipment-models'"
          :model-value="Number(route.query.category_id) || null"
          resource="categories"
          input-id="category-filter"
          label="Все категории"
          :selected-label="categoryLabel"
          @update:model-value="setQuery({ category_id: $event })"
          @selected="categoryLabel = $event"
        />
        <Select
          v-if="resource === 'employees'"
          :model-value="route.query.is_active ?? null"
          :options="[
            { label: 'Все сотрудники', value: null },
            { label: 'Активные', value: 'true' },
            { label: 'Неактивные', value: 'false' },
          ]"
          option-label="label"
          option-value="value"
          placeholder="Все сотрудники"
          aria-label="Статус сотрудника"
          @update:model-value="setQuery({ is_active: $event })"
        />
      </form>
      <div class="filter-extra">
        <Select
          v-if="resource === 'equipment'"
          :model-value="availabilityFilter"
          :options="[
            { label: 'Все состояния', value: null },
            { label: 'Доступно к выдаче', value: 'available' },
            { label: 'В эксплуатации', value: 'usable' },
            { label: 'Недоступно', value: 'unavailable' },
            { label: 'Списано', value: 'retired' },
          ]"
          option-label="label"
          option-value="value"
          placeholder="Все состояния"
          aria-label="Состояние и доступность"
          @update:model-value="filterAvailability"
        />
        <Button
          v-if="resource === 'equipment'"
          label="Фильтры"
          icon="pi pi-sliders-h"
          text
          @click="advancedVisible = true"
        />
        <Button
          v-if="Object.keys(route.query).length"
          label="Сбросить фильтры"
          text
          @click="
            router.replace({ query: {} });
            categoryLabel = '';
            modelLabel = '';
            employeeLabel = '';
          "
        />
      </div>
      <Message v-if="error" severity="error"
        >{{ error }} <Button label="Повторить загрузку" text @click="load"
      /></Message>
      <DataTable
        :key="`${resource}:${route.fullPath}`"
        :value="rows"
        :loading="loading"
        data-key="id"
        lazy
        :sort-field="String(route.query.sort || '')"
        :sort-order="route.query.desc === 'true' ? -1 : 1"
        :row-class="
          (item: Item) => (item.id === selectedId ? 'selected-row' : '')
        "
        class="inventory-table"
        @sort="
          setQuery({
            sort: String($event.sortField),
            desc: $event.sortOrder === -1 ? 'true' : 'false',
          })
        "
        @row-click="
          split &&
          router.push({
            path: `/${resource}/${$event.data.id}`,
            query: route.query,
          })
        "
      >
        <template #empty
          ><div class="empty-state">
            <p>
              {{
                route.query.q || Object.keys(route.query).length
                  ? "По заданным условиям ничего не найдено."
                  : "Записей пока нет. Добавьте первую."
              }}
            </p>
            <Button
              v-if="!Object.keys(route.query).length"
              label="Добавить запись"
              outlined
              @click="add"
            /></div
        ></template>
        <template v-if="resource === 'equipment'">
          <Column header="Инв. номер" field="inventory_number" sortable
            ><template #body="{ data }"
              ><RouterLink
                :to="{ path: `/equipment/${data.id}`, query: route.query }"
                >{{ data.inventory_number }}</RouterLink
              ></template
            ></Column
          >
          <Column header="Модель"
            ><template #body="{ data }">{{ data.model.name }}</template></Column
          >
          <Column header="Доступность"
            ><template #body="{ data }"
              ><Tag
                :value="availability(data).label"
                :severity="availability(data).severity" /></template
          ></Column>
        </template>
        <template v-else-if="resource === 'employees'">
          <Column header="Сотрудник" field="full_name" sortable
            ><template #body="{ data }"
              ><RouterLink
                :to="{ path: `/employees/${data.id}`, query: route.query }"
                >{{ data.full_name }}</RouterLink
              ></template
            ></Column
          >
          <Column field="personnel_number" header="Таб. номер" />
          <Column header="Статус"
            ><template #body="{ data }"
              ><Tag
                :value="data.is_active ? 'Активен' : 'Неактивен'"
                :severity="
                  data.is_active ? 'success' : 'secondary'
                " /></template
          ></Column>
        </template>
        <template v-else>
          <Column
            v-if="resource === 'equipment-models'"
            field="manufacturer"
            header="Производитель"
          />
          <Column field="name" header="Название" sortable />
          <Column v-if="resource === 'equipment-models'" header="Категория"
            ><template #body="{ data }">{{
              data.category.name
            }}</template></Column
          >
          <Column field="description" header="Описание" />
          <Column header="Действия"
            ><template #body="{ data }"
              ><div class="row-actions">
                <Button
                  icon="pi pi-pencil"
                  text
                  aria-label="Редактировать запись"
                  @click="edit(data)"
                /><Button
                  icon="pi pi-trash"
                  text
                  severity="danger"
                  aria-label="Удалить запись"
                  @click="remove(data)"
                /></div></template
          ></Column>
        </template>
      </DataTable>
      <div class="list-footer">
        <Paginator
          :first="offset"
          :rows="limit"
          :total-records="total"
          :rows-per-page-options="[10, 20, 50]"
          template="PrevPageLink PageLinks NextPageLink RowsPerPageDropdown"
          @page="setQuery({ offset: $event.first, limit: $event.rows })"
        /><span class="muted small"
          >{{ total ? offset + 1 : 0 }}–{{ Math.min(offset + limit, total) }} из
          {{ total }}</span
        >
      </div>
    </section>
    <aside v-if="split" class="detail-pane" aria-label="Карточка записи">
      <EquipmentDetail
        v-if="resource === 'equipment' && selectedId"
        :id="selectedId"
        :key="`equipment-${selectedId}`"
        :revision="revision"
        @edit="edit"
        @changed="load"
        @deleted="deleted"
      />
      <EmployeeDetail
        v-else-if="resource === 'employees' && selectedId"
        :id="selectedId"
        :key="`employee-${selectedId}`"
        :revision="revision"
        @edit="edit"
        @changed="load"
        @deleted="deleted"
      />
      <div v-else class="selection-placeholder">
        <i class="pi pi-arrow-left" aria-hidden="true" />
        <h2>Выберите запись</h2>
        <p>Карточка и история появятся здесь.</p>
      </div>
    </aside>
    <ResourceForm
      v-model:visible="formVisible"
      :resource="resource"
      :record="editing"
      @saved="saved"
      @conflict="
        revision++;
        load();
      "
    />
    <Dialog
      v-model:visible="advancedVisible"
      modal
      header="Фильтры оборудования"
      :style="{ width: '520px' }"
      :breakpoints="{ '600px': '94vw' }"
    >
      <div class="record-form">
        <div class="field">
          <label for="model-filter">Модель</label
          ><RelationPicker
            :model-value="Number(route.query.model_id) || null"
            resource="equipment-models"
            input-id="model-filter"
            label="Все модели"
            :selected-label="modelLabel"
            @update:model-value="setQuery({ model_id: $event })"
            @selected="modelLabel = $event"
          />
        </div>
        <div class="field">
          <label for="employee-filter">Текущий получатель</label
          ><RelationPicker
            :model-value="Number(route.query.employee_id) || null"
            resource="employees"
            input-id="employee-filter"
            label="Все сотрудники"
            :selected-label="employeeLabel"
            @update:model-value="setQuery({ employee_id: $event })"
            @selected="employeeLabel = $event"
          />
        </div>
        <Button label="Готово" @click="advancedVisible = false" />
      </div>
    </Dialog>
  </div>
</template>
