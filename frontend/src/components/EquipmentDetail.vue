<script setup lang="ts">
import { ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import Button from "primevue/button";
import Tag from "primevue/tag";
import Select from "primevue/select";
import Dialog from "primevue/dialog";
import Textarea from "primevue/textarea";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import RelationPicker from "./RelationPicker.vue";
import AssignmentHistory from "./AssignmentHistory.vue";
import { request, errorText, ApiError } from "../api";
import { date, stateLabel, stateOptions, type Equipment } from "../domain";
import type { components } from "../generated/api";

const props = defineProps<{ id: number; revision: number }>();
const emit = defineEmits<{ edit: [Equipment]; changed: []; deleted: [] }>();
const record = ref<Equipment | null>(null),
  loading = ref(false),
  error = ref(""),
  busy = ref(false);
const dialog = ref<"issue" | "return" | null>(null),
  formError = ref(""),
  uncertain = ref(false);
const employeeId = ref<number | null>(null),
  employeeLabel = ref(""),
  note = ref("");
const nextState = ref("usable"),
  localRevision = ref(0),
  confirm = useConfirm();
let generation = 0;
async function load() {
  const token = ++generation;
  loading.value = true;
  error.value = "";
  try {
    const row = await request<Equipment>(`equipment/${props.id}`);
    if (token === generation) {
      record.value = row;
      nextState.value = row.operational_state;
    }
  } catch (e) {
    if (token === generation) {
      record.value = null;
      error.value = errorText(e);
    }
  } finally {
    if (token === generation) loading.value = false;
  }
}
watch(
  () => [props.id, props.revision],
  () => {
    record.value = null;
    dialog.value = null;
    void load();
  },
  { immediate: true },
);
function open(mode: "issue" | "return") {
  dialog.value = mode;
  formError.value = "";
  uncertain.value = false;
  note.value = "";
  employeeId.value = null;
  employeeLabel.value = "";
}
async function changed() {
  await load();
  localRevision.value++;
  emit("changed");
}
async function submitAssignment() {
  if (busy.value || uncertain.value || !record.value) return;
  if (dialog.value === "issue" && !employeeId.value) {
    formError.value = "Выберите сотрудника";
    return;
  }
  busy.value = true;
  formError.value = "";
  try {
    if (dialog.value === "issue") {
      const body: components["schemas"]["AssignmentCreate"] = {
        equipment_id: record.value.id,
        employee_id: employeeId.value!,
        issue_note: note.value || null,
      };
      await request("assignments", "POST", body);
    } else {
      await request(
        `assignments/${record.value.current_assignment!.id}/return`,
        "PUT",
        {
          return_note: note.value || null,
        } satisfies components["schemas"]["ReturnInput"],
      );
    }
    dialog.value = null;
    await changed();
  } catch (e) {
    formError.value = errorText(e);
    // Never blindly repeat a possibly committed issue, even after a 5xx response.
    uncertain.value =
      !(e instanceof ApiError) || e.status >= 500 || e.status === 409;
    await load();
    localRevision.value++;
    emit("changed");
  } finally {
    busy.value = false;
  }
}
async function changeState() {
  if (
    !record.value ||
    busy.value ||
    nextState.value === record.value.operational_state
  )
    return;
  if (nextState.value === "retired") {
    confirm.require({
      header: "Списать оборудование?",
      message: "Вернуть списанный экземпляр в оборот будет нельзя.",
      acceptLabel: "Списать",
      rejectLabel: "Отмена",
      accept: () => void saveState(),
    });
  } else await saveState();
}
async function saveState() {
  busy.value = true;
  error.value = "";
  try {
    await request(`equipment/${props.id}`, "PATCH", {
      operational_state: nextState.value,
    });
    await changed();
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
    header: "Удалить оборудование?",
    message: "Физическое удаление возможно, только если выдач ещё не было.",
    acceptLabel: "Удалить",
    rejectLabel: "Отмена",
    accept: async () => {
      busy.value = true;
      try {
        await request(`equipment/${props.id}`, "DELETE");
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
      :to="{ path: '/equipment', query: $route.query }"
      ><i class="pi pi-angle-left" aria-hidden="true" /> Карточка
      оборудования</RouterLink
    >
    <Message v-if="error" severity="error"
      >{{ error }} <Button label="Обновить карточку" text @click="load"
    /></Message>
    <div v-if="loading && !record" class="skeleton-stack">
      <Skeleton height="3rem" /><Skeleton height="12rem" />
    </div>
    <template v-if="record">
      <h1>{{ record.model.name }}</h1>
      <p class="detail-subtitle">
        Инв. номер <strong>{{ record.inventory_number }}</strong>
      </p>
      <dl class="details">
        <dt>Категория</dt>
        <dd>{{ record.model.category.name }}</dd>
        <dt>Производитель</dt>
        <dd>{{ record.model.manufacturer }}</dd>
        <dt>Серийный номер</dt>
        <dd>{{ record.serial_number || "—" }}</dd>
        <dt>Состояние</dt>
        <dd>
          <Tag
            :value="stateLabel(record.operational_state)"
            :severity="
              record.operational_state === 'usable'
                ? 'success'
                : record.operational_state === 'unavailable'
                  ? 'warn'
                  : 'secondary'
            "
          />
        </dd>
      </dl>
      <section class="assignment-section">
        <h2>Текущая выдача</h2>
        <template v-if="record.current_assignment">
          <dl class="details compact">
            <dt>Сотрудник</dt>
            <dd>
              <RouterLink
                :to="`/employees/${record.current_assignment.employee.id}`"
                >{{ record.current_assignment.employee.full_name }}</RouterLink
              >
            </dd>
            <dt>Табельный номер</dt>
            <dd>{{ record.current_assignment.employee.personnel_number }}</dd>
          </dl>
          <p class="muted">С {{ date(record.current_assignment.issued_at) }}</p>
        </template>
        <p v-else class="muted">
          {{
            record.available
              ? "Оборудование свободно и готово к выдаче."
              : "Открытой выдачи нет. Оборудование недоступно."
          }}
        </p>
        <div class="detail-actions">
          <Button
            v-if="record.current_assignment"
            label="Вернуть оборудование"
            :disabled="busy || loading"
            @click="open('return')"
          />
          <Button
            v-else
            label="Выдать сотруднику"
            :disabled="!record.available || busy || loading"
            @click="open('issue')"
          />
          <Button
            label="Редактировать"
            outlined
            :disabled="busy"
            @click="emit('edit', record)"
          />
        </div>
      </section>
      <AssignmentHistory
        :equipment-id="id"
        :revision="revision + localRevision"
      />
      <section class="additional-details">
        <h2>Дополнительно</h2>
        <p class="note-text">{{ record.notes || "Примечаний нет." }}</p>
        <div class="field">
          <label for="equipment-state">Состояние оборудования</label>
          <div class="state-controls">
            <Select
              v-model="nextState"
              input-id="equipment-state"
              :options="stateOptions"
              option-label="label"
              option-value="value"
              :disabled="
                busy ||
                !!record.current_assignment ||
                record.operational_state === 'retired'
              "
            /><Button
              label="Применить"
              outlined
              :disabled="busy || nextState === record.operational_state"
              @click="changeState"
            />
          </div>
        </div>
        <Button
          label="Удалить оборудование"
          severity="danger"
          text
          :disabled="busy"
          @click="remove"
        />
      </section>
    </template>
    <Dialog
      :visible="dialog !== null"
      modal
      :header="
        dialog === 'issue' ? 'Выдача оборудования' : 'Возврат оборудования'
      "
      :closable="!busy"
      :close-on-escape="!busy"
      :style="{ width: '520px' }"
      :breakpoints="{ '600px': '94vw' }"
      @update:visible="dialog = $event ? dialog : null"
    >
      <form class="record-form" @submit.prevent="submitAssignment">
        <p>{{ record?.inventory_number }} · {{ record?.model.name }}</p>
        <Message v-if="formError" severity="error"
          >{{ formError }}
          <p v-if="uncertain">
            Карточка перечитана. Закройте окно и проверьте текущую выдачу перед
            новым действием.
          </p></Message
        >
        <div v-if="dialog === 'issue'" class="field">
          <label for="assignment-employee">Сотрудник *</label
          ><RelationPicker
            v-model="employeeId"
            resource="employees"
            input-id="assignment-employee"
            label="Выберите сотрудника"
            :selected-label="employeeLabel"
            active-only
            @selected="employeeLabel = $event"
          />
        </div>
        <div class="field">
          <label for="assignment-note">Примечание</label
          ><Textarea
            id="assignment-note"
            v-model="note"
            rows="3"
            :maxlength="2000"
            :disabled="busy"
          />
        </div>
        <div class="form-actions">
          <Button
            label="Закрыть"
            text
            :disabled="busy"
            @click="dialog = null"
          /><Button
            :label="dialog === 'issue' ? 'Выдать' : 'Оформить возврат'"
            type="submit"
            :loading="busy"
            :disabled="uncertain"
          />
        </div>
      </form>
    </Dialog>
  </div>
</template>
