import {
  ConflictResponseSchema,
  EditableFieldsSchema,
  ProjectListResponseSchema,
  ProjectResponseSchema,
  UncertainResponseSchema,
  type EditableFields,
} from './contracts'

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new Error(`The server returned an unreadable response (${response.status}).`)
  }
}

function fail(status: number): never {
  throw new Error(`The server request failed (${status}).`)
}

export async function listProjects() {
  const response = await fetch('/api/projects')
  const json = await readJson(response)
  if (!response.ok) fail(response.status)
  return ProjectListResponseSchema.parse(json).projects
}

export async function getProject(id: string) {
  const response = await fetch(`/api/projects/${encodeURIComponent(id)}`)
  const json = await readJson(response)
  if (!response.ok) fail(response.status)
  return ProjectResponseSchema.parse(json).project
}

export async function saveProject(id: string, base: EditableFields, proposed: EditableFields) {
  const body = {
    base: EditableFieldsSchema.parse(base),
    proposed: EditableFieldsSchema.parse(proposed),
  }
  const response = await fetch(`/api/projects/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const json = await readJson(response)
  if (response.status === 409) {
    return { kind: 'conflict' as const, conflict: ConflictResponseSchema.parse(json) }
  }
  if (response.status === 504) {
    return { kind: 'uncertain' as const, uncertainty: UncertainResponseSchema.parse(json) }
  }
  if (!response.ok) fail(response.status)
  return { kind: 'saved' as const, project: ProjectResponseSchema.parse(json).project }
}
