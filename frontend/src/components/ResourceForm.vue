<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import Dialog from "primevue/dialog";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import Message from "primevue/message";
import RelationPicker from "./RelationPicker.vue";
import { ApiError, errorText, request } from "../api";
import { type Item, type Resource, itemLabel } from "../domain";

const props = defineProps<{
  visible: boolean;
  resource: Resource;
  record: Item | null;
}>();
const emit = defineEmits<{
  "update:visible": [boolean];
  saved: [Item];
  conflict: [];
}>();
const busy = ref(false),
  error = ref(""),
  fields = ref<Record<string, string>>({});
const values = reactive<Record<string, string>>({});
const relation = ref<number | null>(null),
  relationLabel = ref("");
const relationResource = computed(() =>
  props.resource === "equipment" ? "equipment-models" : "categories",
);
const fieldSpecs = computed(() => {
  switch (props.resource) {
    case "equipment":
      return [
        ["inventory_number", "Инвентарный номер", 64, true],
        ["serial_number", "Серийный номер", 120, false],
        ["notes", "Примечание", 2000, false],
      ] as const;
    case "employees":
      return [
        ["full_name", "ФИО", 200, true],
        ["personnel_number", "Табельный номер", 64, true],
        ["email", "Email", 254, false],
      ] as const;
    case "equipment-models":
      return [
        ["manufacturer", "Производитель", 120, true],
        ["name", "Название модели", 200, true],
        ["description", "Описание", 2000, false],
      ] as const;
    default:
      return [
        ["name", "Название категории", 120, true],
        ["description", "Описание", 2000, false],
      ] as const;
  }
});
watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    fields.value = {};
    const record = props.record as unknown as Record<string, unknown> | null;
    for (const [key] of fieldSpecs.value)
      values[key] = String(record?.[key] ?? "");
    relation.value = Number(record?.model_id ?? record?.category_id) || null;
    relationLabel.value =
      props.record && "model" in props.record
        ? itemLabel(props.record.model)
        : props.record && "category" in props.record
          ? props.record.category.name
          : "";
  },
);
async function save() {
  if (busy.value) return;
  error.value = "";
  fields.value = {};
  const payload: Record<string, unknown> = {};
  for (const [key, , , required] of fieldSpecs.value)
    payload[key] = values[key]?.trim() || (required ? "" : null);
  if (props.resource === "equipment" || props.resource === "equipment-models") {
    if (!relation.value) {
      error.value = "Выберите связанную запись";
      return;
    }
    payload[props.resource === "equipment" ? "model_id" : "category_id"] =
      relation.value;
  }
  busy.value = true;
  try {
    const result = await request<Item>(
      `${props.resource}${props.record ? `/${props.record.id}` : ""}`,
      props.record ? "PATCH" : "POST",
      payload,
    );
    emit("saved", result);
    emit("update:visible", false);
  } catch (e) {
    error.value = errorText(e);
    if (e instanceof ApiError) {
      fields.value = e.fields;
      if (e.status === 409) emit("conflict");
    }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="!busy"
    :close-on-escape="!busy"
    :header="record ? 'Редактировать запись' : 'Новая запись'"
    :style="{ width: '520px' }"
    :breakpoints="{ '600px': '94vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form class="record-form" @submit.prevent="save">
      <p class="muted small">Поля со звёздочкой обязательны.</p>
      <Message v-if="error" severity="error" aria-live="polite">{{
        error
      }}</Message>
      <div
        v-for="[key, label, length, required] in fieldSpecs"
        :key="key"
        class="field"
      >
        <label :for="`form-${key}`"
          >{{ label }}{{ required ? " *" : "" }}</label
        >
        <Textarea
          v-if="length === 2000"
          :id="`form-${key}`"
          v-model="values[key]"
          :maxlength="length"
          rows="3"
          :invalid="!!fields[key]"
          :disabled="busy"
        />
        <InputText
          v-else
          :id="`form-${key}`"
          v-model="values[key]"
          :type="key === 'email' ? 'email' : 'text'"
          :required="required"
          :maxlength="length"
          :invalid="!!fields[key]"
          :disabled="busy"
        />
        <small v-if="fields[key]" class="field-error">{{ fields[key] }}</small>
      </div>
      <div
        v-if="resource === 'equipment' || resource === 'equipment-models'"
        class="field"
      >
        <label for="form-relation"
          >{{ resource === "equipment" ? "Модель" : "Категория" }} *</label
        >
        <RelationPicker
          v-model="relation"
          input-id="form-relation"
          :resource="relationResource"
          :label="
            resource === 'equipment' ? 'Выберите модель' : 'Выберите категорию'
          "
          :selected-label="relationLabel"
          @selected="relationLabel = $event"
        />
      </div>
      <div class="form-actions">
        <Button
          label="Отмена"
          text
          :disabled="busy"
          @click="emit('update:visible', false)"
        /><Button label="Сохранить" type="submit" :loading="busy" />
      </div>
    </form>
  </Dialog>
</template>
