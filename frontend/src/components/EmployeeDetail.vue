<script setup lang="ts">
import { ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import Button from "primevue/button";
import Tag from "primevue/tag";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import AssignmentHistory from "./AssignmentHistory.vue";
import { request, errorText } from "../api";
import type { Employee, Equipment, Page } from "../domain";

const props = defineProps<{ id: number; revision: number }>();
const emit = defineEmits<{ edit: [Employee]; changed: []; deleted: [] }>();
const record = ref<Employee | null>(null),
  equipment = ref<Equipment[]>([]),
  total = ref(0);
const error = ref(""),
  loading = ref(false),
  busy = ref(false),
  confirm = useConfirm();
let generation = 0;
async function load() {
  const token = ++generation;
  loading.value = true;
  error.value = "";
  try {
    const [employee, page] = await Promise.all([
      request<Employee>(`employees/${props.id}`),
      request<Page>(`equipment?employee_id=${props.id}&limit=5`),
    ]);
    if (token === generation) {
      record.value = employee;
      equipment.value = page.items as Equipment[];
      total.value = page.total;
    }
  } catch (e) {
    if (token === generation) error.value = errorText(e);
  } finally {
    if (token === generation) loading.value = false;
  }
}
watch(
  () => [props.id, props.revision],
  () => {
    record.value = null;
    void load();
  },
  { immediate: true },
);
async function toggleActive() {
  if (!record.value || busy.value) return;
  busy.value = true;
  try {
    await request(`employees/${props.id}`, "PATCH", {
      is_active: !record.value.is_active,
    });
    await load();
    emit("changed");
  } catch (e) {
    const message = errorText(e);
    await load();
    error.value = message;
  } finally {
    busy.value = false;
  }
}
function remove() {
  confirm.require({
    header: "Удалить сотрудника?",
    message: "Удаление возможно, только если у сотрудника нет истории выдач.",
    acceptLabel: "Удалить",
    rejectLabel: "Отмена",
    accept: async () => {
      busy.value = true;
      try {
        await request(`employees/${props.id}`, "DELETE");
        emit("deleted");
      } catch (e) {
        error.value = errorText(e);
      } finally {
        busy.value = false;
      }
    },
  });
}
</script>

<template>
  <div class="detail-content">
    <RouterLink
      class="back-link"
      :to="{ path: '/employees', query: $route.query }"
      ><i class="pi pi-angle-left" aria-hidden="true" /> Карточка
      сотрудника</RouterLink
    >
    <Message v-if="error" severity="error"
      >{{ error }} <Button label="Обновить карточку" text @click="load"
    /></Message>
    <Skeleton v-if="loading && !record" height="15rem" />
    <template v-if="record">
      <h1>{{ record.full_name }}</h1>
      <p class="detail-subtitle">
        Табельный номер <strong>{{ record.personnel_number }}</strong>
      </p>
      <dl class="details">
        <dt>Email</dt>
        <dd>{{ record.email || "—" }}</dd>
        <dt>Статус</dt>
        <dd>
          <Tag
            :value="record.is_active ? 'Активен' : 'Неактивен'"
            :severity="record.is_active ? 'success' : 'secondary'"
          />
        </dd>
      </dl>
      <div class="detail-actions">
        <Button
          label="Редактировать"
          outlined
          @click="emit('edit', record)"
        /><Button
          :label="record.is_active ? 'Деактивировать' : 'Активировать'"
          outlined
          :loading="busy"
          @click="toggleActive"
        />
      </div>
      <section class="assignment-section">
        <h2>На руках · {{ total }}</h2>
        <p v-if="!total" class="muted">Оборудование не выдано.</p>
        <ul class="equipment-links">
          <li v-for="item in equipment" :key="item.id">
            <RouterLink :to="`/equipment/${item.id}`"
              >{{ item.inventory_number }} · {{ item.model.name }}</RouterLink
            >
          </li>
        </ul>
        <RouterLink v-if="total > 5" :to="`/equipment?employee_id=${id}`"
          >Показать всё оборудование</RouterLink
        >
      </section>
      <AssignmentHistory :employee-id="id" :revision="revision" />
      <Button
        label="Удалить сотрудника"
        text
        severity="danger"
        :disabled="busy"
        @click="remove"
      />
    </template>
  </div>
</template>
