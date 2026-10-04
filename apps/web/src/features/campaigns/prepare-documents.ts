import { api } from "../../lib/api";
import type { components } from "../../lib/api.generated";
import type { QuestionAnswer } from "./question-renderer";
type Form = components["schemas"]["PublicForm"];
type Session = components["schemas"]["UploadSessionCreated"];
type Document = components["schemas"]["Upload"];
export class DocumentPreparationError extends Error {
  constructor(
    public code: string,
    public questionId?: string,
  ) {
    super(code);
  }
}
export type DocumentCache = {
  session?: Session;
  snapshotId?: string;
  ready: Map<string, Map<File, Document>>;
};
export async function prepareDocuments(
  form: Form,
  answers: Record<string, QuestionAnswer>,
  cache: DocumentCache,
  test: boolean,
  publicToken?: string,
  csrf?: string,
) {
  const selected = form.questions
    .filter((q) => q.type === "file")
    .flatMap((q) =>
      ((answers[q.id] ?? []) as File[]).map((file) => ({ q, file })),
    );
  if (!selected.length)
    return { answers: [], upload_session_id: null, upload_token: null };
  if (
    selected.length > 5 ||
    selected.reduce((sum, { file }) => sum + file.size, 0) > 31457280
  )
    throw new DocumentPreparationError("payload_too_large");
  for (const { q, file } of selected) {
    if (file.size > (q.constraints.max_bytes ?? 10485760))
      throw new DocumentPreparationError("payload_too_large", q.id);
    if ((answers[q.id] as File[]).length > (q.constraints.max_files ?? 5))
      throw new DocumentPreparationError("invalid_upload", q.id);
  }
  if (cache.snapshotId !== form.snapshot_id) {
    cache.session = undefined;
    cache.ready.clear();
    cache.snapshotId = form.snapshot_id;
  }
  if (!cache.session) {
    const result = test
      ? await api.POST("/api/v1/test-snapshots/{snapshot_id}/upload-sessions", {
          params: { path: { snapshot_id: form.snapshot_id } },
          headers: { "X-CSRF-Token": csrf! },
          body: { snapshot_id: form.snapshot_id },
        })
      : await api.POST(
          "/api/v1/public/campaigns/{public_token}/upload-sessions",
          {
            params: { path: { public_token: publicToken! } },
            body: { snapshot_id: form.snapshot_id },
          },
        );
    if (!result.data)
      throw new DocumentPreparationError(result.error?.error.code ?? "network");
    cache.session = result.data;
  }
  const session = cache.session;
  for (const { q, file } of selected) {
    const ready = cache.ready.get(q.id) ?? new Map<File, Document>();
    cache.ready.set(q.id, ready);
    if (ready.has(file)) continue;
    const body = new FormData();
    body.append("question_id", q.id);
    body.append("file", file);
    const options = {
      params: { path: { session_id: session.id } },
      headers: {
        "X-Upload-Token": session.upload_token,
        ...(test ? { "X-CSRF-Token": csrf! } : {}),
      },
      body: { question_id: q.id, file: "" },
      bodySerializer: () => body,
    };
    const result = test
      ? await api.POST(
          "/api/v1/test-upload-sessions/{session_id}/files",
          options,
        )
      : await api.POST("/api/v1/upload-sessions/{session_id}/files", options);
    if (!result.data) {
      const code = result.error?.error.code ?? "network";
      if (code === "upload_expired") {
        cache.session = undefined;
        cache.ready.clear();
      }
      throw new DocumentPreparationError(code, q.id);
    }
    ready.set(file, result.data);
  }
  return {
    answers: form.questions
      .filter((q) => q.type === "file" && Array.isArray(answers[q.id]))
      .map((q) => ({
        question_id: q.id,
        kind: "file" as const,
        value: (answers[q.id] as File[]).map(
          (file) => cache.ready.get(q.id)!.get(file)!.id,
        ),
      })),
    upload_session_id: session.id,
    upload_token: session.upload_token,
  };
}
