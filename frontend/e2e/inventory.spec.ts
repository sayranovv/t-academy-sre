import { test, expect, type Page } from "@playwright/test";

test("switching resources replaces the previous table rows", async ({
  page,
}) => {
  await page.goto("/equipment");
  await expect(page.getByRole("row", { name: /DEMO-EQ-001/ })).toBeVisible();

  await page.getByRole("link", { name: "Сотрудники", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Сотрудники", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("row", { name: /DEMO-EQ-001/ })).toHaveCount(0);
  await expect(
    page.getByRole("row", { name: /Анна Демонстрационная DEMO-001 Активен/ }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Справочники", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Категории", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("row", { name: /Анна Демонстрационная/ }),
  ).toHaveCount(0);
  await expect(page.getByRole("row", { name: /Ноутбуки/ })).toBeVisible();

  await page.getByRole("link", { name: "Оборудование", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Оборудование", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("row", { name: /DEMO-EQ-001/ })).toBeVisible();
  await expect(
    page.getByRole("row", { name: /Анна Демонстрационная/ }),
  ).toHaveCount(0);
});

async function add(page: Page) {
  await page.getByRole("button", { name: "Добавить", exact: true }).click();
}
async function save(page: Page) {
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: /Новая запись|Редактировать запись/ }),
  ).toBeHidden();
}
async function pick(page: Page, label: string, search: string, option: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  const dialog = page.getByRole("dialog", { name: label, exact: true });
  await dialog
    .getByRole("textbox", { name: "Поиск в справочнике" })
    .fill(search);
  await dialog.getByRole("button", { name: "Найти", exact: true }).click();
  await dialog.getByRole("button", { name: option, exact: true }).click();
}

test("CRUD, issue, return, repeated issue, history and deletion rules", async ({
  page,
}) => {
  const suffix = Date.now().toString();
  const name = `Тест ${suffix}`,
    number = `E2E-${suffix}`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/categories");
  await add(page);
  await page.getByLabel("Название категории *", { exact: true }).fill(name);
  await save(page);
  await page.getByRole("link", { name: "Модели", exact: true }).click();
  await add(page);
  await page.getByLabel("Производитель *", { exact: true }).fill("Учебный");
  await page.getByLabel("Название модели *", { exact: true }).fill(name);
  await pick(page, "Выберите категорию", name, name);
  await save(page);
  await page.getByRole("link", { name: "Сотрудники", exact: true }).click();
  await add(page);
  await page.getByLabel("ФИО *", { exact: true }).fill(name);
  await page.getByLabel("Табельный номер *", { exact: true }).fill(number);
  await save(page);
  await page.getByRole("link", { name: "Оборудование", exact: true }).click();
  await add(page);
  await page.getByLabel("Инвентарный номер *", { exact: true }).fill(number);
  await pick(page, "Выберите модель", name, `Учебный ${name}`);
  await save(page);
  await expect(page).toHaveURL(/\/equipment\/\d+/);
  const equipmentUrl = page.url();
  await page
    .getByRole("button", { name: "Выдать сотруднику", exact: true })
    .click();
  await pick(page, "Выберите сотрудника", number, `${name} · ${number}`);
  await page.getByRole("button", { name: "Выдать", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Вернуть оборудование" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Вернуть оборудование" }).click();
  await page.getByLabel("Примечание", { exact: true }).fill("Возврат e2e");
  await page
    .getByRole("button", { name: "Оформить возврат", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Выдать сотруднику" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Выдать сотруднику" }).click();
  await pick(page, "Выберите сотрудника", number, `${name} · ${number}`);
  await page.getByRole("button", { name: "Выдать", exact: true }).click();
  await expect(
    page.locator(".history").getByText("Возвращено", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".history").getByText("Не возвращено", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Удалить оборудование", exact: true })
    .click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Удалить", exact: true })
    .click();
  await expect(
    page.getByText("Запись связана с другими данными.", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Вернуть оборудование" }),
  ).toBeVisible();

  // Direct card URL and small-screen layout retain navigation and actions.
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(page.locator(".list-pane")).toBeHidden();
  await expect(
    page.getByRole("link", { name: "Карточка оборудования" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Карточка оборудования" }).click();
  await expect(page.locator(".list-pane")).toBeVisible();
  await page.goto(equipmentUrl);
  await expect(
    page.getByRole("button", { name: "Вернуть оборудование" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("validation conflict retains form input; unreferenced category can be deleted", async ({
  page,
  request,
}) => {
  const name = `Удаляемая ${Date.now()}`;
  const category = await request.post("/api/v1/categories", { data: { name } });
  expect(category.status()).toBe(201);
  await page.goto("/categories");
  await add(page);
  await page.getByLabel("Название категории *").fill(name);
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByText(/Категория уже существует/)).toBeVisible();
  await expect(page.getByLabel("Название категории *")).toHaveValue(name);
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await page.getByRole("textbox", { name: "Поиск", exact: true }).fill(name);
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: name });
  await expect(row).toHaveCount(1);
  await row
    .getByRole("button", { name: "Удалить запись", exact: true })
    .click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Удалить", exact: true })
    .click();
  await expect(
    page.getByText("По заданным условиям ничего не найдено."),
  ).toBeVisible();
});

for (const mode of ["conflict", "network"] as const) {
  test(`issue ${mode}: retain input, refresh card, never auto retry`, async ({
    page,
    request,
  }) => {
    const suffix = Date.now().toString();
    const post = async (resource: string, data: object) => {
      const response = await request.post(`/api/v1/${resource}`, { data });
      expect(response.status()).toBe(201);
      return response.json();
    };
    const category = await post("categories", { name: `Сеть ${suffix}` });
    const model = await post("equipment-models", {
      manufacturer: "Test",
      name: suffix,
      category_id: category.id,
    });
    const employee = await post("employees", {
      full_name: "Сотрудник сети",
      personnel_number: suffix,
    });
    const eq = await post("equipment", {
      inventory_number: suffix,
      model_id: model.id,
    });
    let attempts = 0;
    await page.route("**/api/v1/assignments", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      attempts++;
      if (mode === "network") await route.abort("failed");
      else
        await route.fulfill({
          status: 409,
          json: {
            error: {
              code: "equipment_already_assigned",
              message: "Оборудование уже выдано",
              details: [],
            },
            request_id: "e2e",
          },
        });
    });
    await page.goto(`/equipment/${eq.id}`);
    await page.getByRole("button", { name: "Выдать сотруднику" }).click();
    await pick(
      page,
      "Выберите сотрудника",
      suffix,
      `${employee.full_name} · ${suffix}`,
    );
    await page.getByLabel("Примечание", { exact: true }).fill("Сохранить ввод");
    await page.getByRole("button", { name: "Выдать", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Выдать", exact: true }),
    ).toBeDisabled();
    await expect(page.getByText(/Карточка перечитана/)).toBeVisible();
    await expect(page.getByLabel("Примечание", { exact: true })).toHaveValue(
      "Сохранить ввод",
    );
    expect(attempts).toBe(1);
  });
}
