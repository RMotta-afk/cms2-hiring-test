import {
  ConflictResponseSchema,
  EditableFieldsSchema,
  ProjectNotFoundResponseSchema,
  ProjectListResponseSchema,
  ProjectResponseSchema,
  UpstreamUnavailableResponseSchema,
  UncertainResponseSchema,
  type EditableFields,
} from './contracts'

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new ApiError(`The server returned an unreadable response (${response.status}).`, response.status)
  }
}

function fail(status: number): never {
  throw new ApiError(`The server request failed (${status}).`, status)
}

function failNamed(status: number, json: unknown): never {
  if (status === 404) {
    try {
      ProjectNotFoundResponseSchema.parse(json)
    } catch {
      fail(status)
    }
    throw new ApiError('This project no longer exists.', status)
  }
  if (status === 502) {
    try {
      UpstreamUnavailableResponseSchema.parse(json)
    } catch {
      fail(status)
    }
    throw new ApiError('The upstream service is unavailable. Your draft is still here; try reloading later.', status)
  }
  fail(status)
}

export async function listProjects() {
  const response = await fetch('/api/projects')
  const json = await readJson(response)
  if (!response.ok) failNamed(response.status, json)
  return ProjectListResponseSchema.parse(json).projects
}

export async function getProject(id: string) {
  const response = await fetch(`/api/projects/${encodeURIComponent(id)}`)
  const json = await readJson(response)
  if (!response.ok) failNamed(response.status, json)
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
    try {
      return { kind: 'conflict' as const, conflict: ConflictResponseSchema.parse(json) }
    } catch {
      fail(response.status)
    }
  }
  if (response.status === 504) {
    try {
      return { kind: 'uncertain' as const, uncertainty: UncertainResponseSchema.parse(json) }
    } catch {
      // A malformed 504 body still cannot establish whether the write was applied.
      throw new ApiError('The save outcome is uncertain; review the project before trying again.', 504)
    }
  }
  if (!response.ok) failNamed(response.status, json)
  return { kind: 'saved' as const, project: ProjectResponseSchema.parse(json).project }
}
