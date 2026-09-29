<script setup lang="ts">
import { ref, watch } from "vue";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Tag from "primevue/tag";
import Paginator from "primevue/paginator";
import Message from "primevue/message";
import Button from "primevue/button";
import { request, errorText } from "../api";
import { date, type Assignment, type HistoryPage } from "../domain";

const props = defineProps<{
  equipmentId?: number;
  employeeId?: number;
  revision: number;
}>();
const rows = ref<Assignment[]>([]),
  total = ref(0),
  offset = ref(0),
  loading = ref(false),
  error = ref("");
let generation = 0;
async function load() {
  const token = ++generation;
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({
      limit: "5",
      offset: String(offset.value),
    });
    if (props.equipmentId)
      params.set("equipment_id", String(props.equipmentId));
    if (props.employeeId) params.set("employee_id", String(props.employeeId));
    const page = await request<HistoryPage>(`assignments?${params}`);
    if (token === generation) {
      rows.value = page.items;
      total.value = page.total;
    }
  } catch (e) {
    if (token === generation) error.value = errorText(e);
  } finally {
    if (token === generation) loading.value = false;
  }
}
watch(
  () => [props.equipmentId, props.employeeId, props.revision],
  () => {
    offset.value = 0;
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <section class="history">
    <h2>История выдач</h2>
    <Message v-if="error" severity="error"
      >{{ error }} <Button label="Обновить историю" text @click="load"
    /></Message>
    <DataTable
      :value="rows"
      :loading="loading"
      data-key="id"
      class="history-table"
    >
      <Column header="Период"
        ><template #body="{ data }"
          ><span
            >{{ date(data.issued_at)
            }}<template v-if="data.returned_at"
              ><br />— {{ date(data.returned_at) }}</template
            ></span
          ></template
        ></Column
      >
      <Column :header="employeeId ? 'Оборудование' : 'Сотрудник'"
        ><template #body="{ data }">
          <RouterLink
            :to="
              employeeId
                ? `/equipment/${data.equipment_id}`
                : `/employees/${data.employee_id}`
            "
            >{{
              employeeId
                ? data.equipment.inventory_number
                : data.employee.full_name
            }}</RouterLink
          >
          <small v-if="data.issue_note" class="history-note"
            >Выдача: {{ data.issue_note }}</small
          >
          <small v-if="data.return_note" class="history-note"
            >Возврат: {{ data.return_note }}</small
          >
        </template></Column
      >
      <Column header="Статус"
        ><template #body="{ data }"
          ><Tag
            :value="data.returned_at ? 'Возвращено' : 'Не возвращено'"
            :severity="data.returned_at ? 'success' : 'secondary'" /></template
      ></Column>
      <template #empty>Выдач пока нет.</template>
    </DataTable>
    <Paginator
      v-if="total > 5"
      :first="offset"
      :rows="5"
      :total-records="total"
      @page="
        offset = $event.first;
        load();
      "
    />
  </section>
</template>
