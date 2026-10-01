import type { components } from "./generated/api";

type Schemas = components["schemas"];
export type Equipment = Schemas["EquipmentOut"];
export type Employee = Schemas["EmployeeOut"];
export type Category = Schemas["CategoryOut"];
export type Model = Schemas["ModelOut"];
export type Assignment = Schemas["AssignmentOut"];
export type Resource =
  | "equipment"
  | "employees"
  | "categories"
  | "equipment-models";
export type Item = Equipment | Employee | Category | Model;
export type Page =
  | Schemas["Page_EquipmentOut_"]
  | Schemas["Page_EmployeeOut_"]
  | Schemas["Page_CategoryOut_"]
  | Schemas["Page_ModelOut_"];
export type HistoryPage = Schemas["Page_AssignmentOut_"];

export const titles: Record<Resource, string> = {
  equipment: "Оборудование",
  employees: "Сотрудники",
  categories: "Категории",
  "equipment-models": "Модели",
};
export const stateOptions = [
  { label: "В эксплуатации", value: "usable" },
  { label: "Недоступно", value: "unavailable" },
  { label: "Списано", value: "retired" },
];
export function stateLabel(state: string) {
  return stateOptions.find((x) => x.value === state)?.label ?? state;
}
export function availability(item: Equipment) {
  if (item.current_assignment)
    return { label: "Выдано", severity: "secondary" as const };
  if (item.available)
    return { label: "Доступно", severity: "success" as const };
  return {
    label: stateLabel(item.operational_state),
    severity:
      item.operational_state === "unavailable"
        ? ("warn" as const)
        : ("secondary" as const),
  };
}
export function itemLabel(item: Item): string {
  if ("inventory_number" in item) return item.inventory_number;
  if ("full_name" in item)
    return `${item.full_name} · ${item.personnel_number}`;
  if ("manufacturer" in item) return `${item.manufacturer} ${item.name}`;
  return item.name;
}
export function date(value: string | null) {
  return value
    ? new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      }).format(new Date(value))
    : "—";
}
