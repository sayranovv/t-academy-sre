<script setup lang="ts">
import { ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Paginator from "primevue/paginator";
import Message from "primevue/message";
import { request, errorText } from "../api";
import { itemLabel, type Item, type Page, type Resource } from "../domain";

const props = defineProps<{
  modelValue: number | null;
  resource: Resource;
  label: string;
  selectedLabel?: string;
  activeOnly?: boolean;
  inputId: string;
}>();
const emit = defineEmits<{
  "update:modelValue": [number | null];
  selected: [string];
}>();
const visible = ref(false),
  search = ref(""),
  offset = ref(0),
  rows = ref<Item[]>([]);
const total = ref(0),
  busy = ref(false),
  error = ref("");
let generation = 0;
async function load() {
  const token = ++generation;
  busy.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({
      q: search.value,
      limit: "10",
      offset: String(offset.value),
    });
    if (props.activeOnly) params.set("is_active", "true");
    const page = await request<Page>(`${props.resource}?${params}`);
    if (token === generation) {
      rows.value = page.items;
      total.value = page.total;
    }
  } catch (e) {
    if (token === generation) error.value = errorText(e);
  } finally {
    if (token === generation) busy.value = false;
  }
}
watch(visible, (open) => {
  if (open) {
    search.value = "";
    offset.value = 0;
    void load();
  }
});
function choose(item: Item) {
  emit("update:modelValue", item.id);
  emit("selected", itemLabel(item));
  visible.value = false;
}
</script>

<template>
  <Button
    :id="inputId"
    class="relation-button"
    outlined
    :label="selectedLabel || (modelValue ? `Запись №${modelValue}` : label)"
    icon="pi pi-search"
    @click="visible = true"
  />
  <Dialog
    v-model:visible="visible"
    modal
    :header="label"
    :style="{ width: '640px' }"
    :breakpoints="{ '700px': '94vw' }"
  >
    <form
      class="picker-search"
      @submit.prevent="
        offset = 0;
        load();
      "
    >
      <InputText
        v-model="search"
        aria-label="Поиск в справочнике"
        placeholder="Введите имя, номер или название"
        autofocus
      />
      <Button type="submit" label="Найти" :loading="busy" />
    </form>
    <Message v-if="error" severity="error">{{ error }}</Message>
    <DataTable :value="rows" :loading="busy" data-key="id">
      <Column header="Запись"
        ><template #body="{ data }"
          ><Button
            :label="itemLabel(data)"
            link
            @click="choose(data)" /></template
      ></Column>
      <template #empty
        >Ничего не найдено. Измените запрос или добавьте запись в
        справочник.</template
      >
    </DataTable>
    <Paginator
      :rows="10"
      :total-records="total"
      :first="offset"
      @page="
        offset = $event.first;
        load();
      "
    />
    <Button
      v-if="modelValue"
      label="Сбросить выбор"
      text
      @click="
        emit('update:modelValue', null);
        emit('selected', '');
        visible = false;
      "
    />
  </Dialog>
</template>
