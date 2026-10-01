export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public requestId = "",
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, {
    method,
    signal: AbortSignal.timeout(10000),
    ...(body === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const fields: Record<string, string> = {};
    for (const item of data?.error?.details ?? []) {
      if (typeof item.field === "string")
        fields[item.field] = "Проверьте формат и допустимую длину поля";
    }
    throw new ApiError(
      response.status,
      data?.error?.message ?? `Ошибка HTTP ${response.status}`,
      data?.request_id ?? response.headers.get("x-request-id") ?? "",
      fields,
    );
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
}

export function errorText(error: unknown): string {
  return error instanceof ApiError
    ? `${error.message}${error.requestId ? ` · Код запроса: ${error.requestId}` : ""}`
    : "Нет ответа сервера. Проверьте подключение и обновите данные. Результат изменения может быть неизвестен.";
}
