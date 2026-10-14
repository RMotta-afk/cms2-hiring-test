import * as z from 'zod'

export const SectorSchema = z.enum([
  'energy', 'mining', 'water', 'transport', 'oil_and_gas', 'ict',
])
export const StageSchema = z.enum([
  'idea', 'feasibility', 'tender', 'financing', 'construction', 'operation', 'cancelled',
])
export const KeyDateSchema = z.strictObject({
  label: z.string().min(1, 'A date label is required').refine((value) => value.trim().length > 0, 'A date label is required'),
  date: z.iso.date(),
})
export const EditableFieldsSchema = z.strictObject({
  name: z.string().min(1, 'Name is required').refine((value) => value.trim().length > 0, 'Name is required'),
  sector: SectorSchema,
  country: z.string().min(1, 'Country is required').refine((value) => value.trim().length > 0, 'Country is required'),
  stage: StageSchema,
  key_dates: z.array(KeyDateSchema),
})
export const ProjectSchema = EditableFieldsSchema.extend({ id: z.string() })
export const ProjectSummarySchema = ProjectSchema.omit({ key_dates: true })
export const ProjectListResponseSchema = z.strictObject({ projects: z.array(ProjectSummarySchema) })
export const ProjectResponseSchema = z.strictObject({ project: ProjectSchema })
export const ProjectNotFoundResponseSchema = z.strictObject({
  code: z.literal('project_not_found'),
})
export const UpstreamUnavailableResponseSchema = z.strictObject({
  code: z.literal('upstream_unavailable'),
})
export const ConflictResponseSchema = z.strictObject({
  code: z.literal('edit_conflict'),
  current: ProjectSchema,
  conflicting_fields: z.array(EditableFieldsSchema.keyof()),
})
export const UncertainResponseSchema = z.strictObject({
  code: z.literal('write_uncertain'),
  observed: ProjectSchema.nullable(),
})

export type EditableFields = z.infer<typeof EditableFieldsSchema>
export type EditableField = keyof EditableFields
export type ProjectDetail = z.infer<typeof ProjectSchema>
export type Project = ProjectDetail
export type ProjectSummary = z.infer<typeof ProjectSummarySchema>
export type ConflictResponse = z.infer<typeof ConflictResponseSchema>
export type UncertainResponse = z.infer<typeof UncertainResponseSchema>

export const editableFieldNames = [
  'name', 'sector', 'country', 'stage', 'key_dates',
] as const satisfies readonly EditableField[]

export function editableFields(project: Project): EditableFields {
  return {
    name: project.name,
    sector: project.sector,
    country: project.country,
    stage: project.stage,
    key_dates: project.key_dates.map((date) => ({ ...date })),
  }
}
