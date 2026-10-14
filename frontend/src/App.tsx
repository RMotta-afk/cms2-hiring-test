import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Box, Button, CircularProgress, Container, Divider, List,
  ListItemButton, ListItemText, MenuItem, Paper, Stack, TextField,
  Typography,
} from '@mui/material'
import { getProject, listProjects, saveProject } from './api'
import {
  EditableFieldsSchema, SectorSchema, StageSchema, editableFieldNames, editableFields,
  type ConflictResponse, type EditableField, type EditableFields,
  type Project, type ProjectSummary, type UncertainResponse,
} from './contracts'

type Choice = 'current' | 'mine'
type Choices = Partial<Record<EditableField, Choice>>

const sectors = SectorSchema.options
const stages = StageSchema.options

function fieldLabel(field: EditableField): string {
  return field === 'key_dates'
    ? 'Key dates'
    : field.charAt(0).toUpperCase() + field.slice(1).replaceAll('_', ' ')
}

function displayValue(value: EditableFields[EditableField]): string {
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => `${item.label}: ${item.date}`).join('; ') : 'No dates'
  }
  return value.replaceAll('_', ' ')
}

function sameValue(a: EditableFields[EditableField], b: EditableFields[EditableField]): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

function rebaseDraft(
  base: EditableFields,
  draft: EditableFields,
  current: EditableFields,
  conflicts: readonly EditableField[],
  choices: Choices,
): EditableFields {
  const result = { ...current, key_dates: current.key_dates.map((date) => ({ ...date })) }
  for (const field of editableFieldNames) {
    if (sameValue(base[field], draft[field])) continue
    if (conflicts.includes(field) && choices[field] === 'current') continue
    if (field === 'key_dates') result.key_dates = draft.key_dates.map((date) => ({ ...date }))
    else if (field === 'name') result.name = draft.name
    else if (field === 'sector') result.sector = draft.sector
    else if (field === 'country') result.country = draft.country
    else result.stage = draft.stage
  }
  return result
}

export default function App() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [project, setProject] = useState<Project | null>(null)
  const [base, setBase] = useState<EditableFields | null>(null)
  const [draft, setDraft] = useState<EditableFields | null>(null)
  const [conflict, setConflict] = useState<ConflictResponse | null>(null)
  const [choices, setChoices] = useState<Choices>({})
  const [uncertainty, setUncertainty] = useState<UncertainResponse | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingProject, setLoadingProject] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false
    listProjects()
      .then((items) => {
        if (ignore) return
        setProjects(items)
        if (items.length) setSelectedId(items[0].id)
      })
      .catch((reason: unknown) => {
        if (!ignore) setError(reason instanceof Error ? reason.message : 'Could not load projects.')
      })
      .finally(() => { if (!ignore) setLoadingList(false) })
    return () => { ignore = true }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let ignore = false
    setLoadingProject(true)
    setProject(null)
    setBase(null)
    setDraft(null)
    setConflict(null)
    setUncertainty(null)
    setNotice(null)
    setError(null)
    getProject(selectedId)
      .then((item) => {
        if (ignore) return
        setProject(item)
        setBase(editableFields(item))
        setDraft(editableFields(item))
      })
      .catch((reason: unknown) => {
        if (!ignore) setError(reason instanceof Error ? reason.message : 'Could not load project.')
      })
      .finally(() => { if (!ignore) setLoadingProject(false) })
    return () => { ignore = true }
  }, [selectedId])

  const dirty = base !== null && draft !== null && !editableFieldNames.every(
    (field) => sameValue(base[field], draft[field]),
  )

  function selectProject(id: string) {
    if (id === selectedId || saving) return
    if (dirty && !window.confirm('Discard unsaved edits and open another project?')) return
    setSelectedId(id)
  }

  async function reloadProject() {
    if (!selectedId || saving) return
    if (dirty && !window.confirm('Discard your draft and reload the latest project?')) return
    setLoadingProject(true)
    setError(null)
    try {
      const item = await getProject(selectedId)
      setProject(item)
      setBase(editableFields(item))
      setDraft(editableFields(item))
      setConflict(null)
      setChoices({})
      setUncertainty(null)
      setNotice(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not reload project.')
    } finally {
      setLoadingProject(false)
    }
  }

  async function sendSave(saveBase: EditableFields, proposed: EditableFields) {
    if (!selectedId) return
    const valid = EditableFieldsSchema.safeParse(proposed)
    if (!valid.success) {
      setError(valid.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; '))
      return
    }
    setSaving(true)
    setError(null)
    setNotice(null)
    setUncertainty(null)
    try {
      const result = await saveProject(selectedId, saveBase, valid.data)
      if (result.kind === 'conflict') {
        setConflict(result.conflict)
        setChoices({})
      } else if (result.kind === 'uncertain') {
        setConflict(null)
        setUncertainty(result.uncertainty)
      } else {
        setProject(result.project)
        setBase(editableFields(result.project))
        setDraft(editableFields(result.project))
        setConflict(null)
        setChoices({})
        setNotice('Changes saved.')
        try {
          setProjects(await listProjects())
        } catch {
          // The saved project stays visible even if the list refresh fails.
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not process the save response.')
      setUncertainty({ code: 'write_uncertain', observed: null })
    } finally {
      setSaving(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!base || !draft || conflict) return
    void sendSave(base, draft)
  }

  function resolveConflict() {
    if (!base || !draft || !conflict) return
    if (conflict.conflicting_fields.some((field) => !choices[field])) return
    const current = editableFields(conflict.current)
    const proposed = rebaseDraft(base, draft, current, conflict.conflicting_fields, choices)
    setBase(current)
    setDraft(proposed)
    setConflict(null)
    void sendSave(current, proposed)
  }

  function changeDate(index: number, key: 'label' | 'date', value: string) {
    setDraft((previous) => previous && {
      ...previous,
      key_dates: previous.key_dates.map((item, position) =>
        position === index ? { ...item, [key]: value } : item),
    })
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>Project editor</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Select a project, edit its fields, and save. Concurrent changes are reviewed before they overwrite yours.
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '280px minmax(0, 1fr)' }, gap: 3 }}>
        <Paper variant="outlined" sx={{ alignSelf: 'start', maxHeight: { md: '75vh' }, overflow: 'auto' }}>
          <Box sx={{ p: 2 }}><Typography variant="h6">Projects</Typography></Box>
          <Divider />
          {loadingList ? <Box sx={{ p: 2 }}><CircularProgress size={24} /></Box> : null}
          {!loadingList && !projects.length ? <Box sx={{ p: 2 }}>No projects found.</Box> : null}
          <List dense disablePadding>
            {projects.map((item) => (
              <ListItemButton key={item.id} selected={selectedId === item.id} onClick={() => selectProject(item.id)}>
                <ListItemText primary={item.name} secondary={`${item.country} | ${item.stage.replaceAll('_', ' ')}`} />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, minWidth: 0 }}>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          {notice ? <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert> : null}
          {uncertainty ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              The save outcome is uncertain. A timeout or lost response may happen after a write.
              {uncertainty.observed
                ? ` The latest read shows "${uncertainty.observed.name}". This does not prove whether this save was applied.`
                : ' The latest project could not be read.'}
              {' '}Review the record before another save. <Button size="small" onClick={() => void reloadProject()}>Reload project</Button>
            </Alert>
          ) : null}
          {loadingProject ? <CircularProgress size={24} /> : null}
          {!selectedId && !loadingList ? <Typography>Select a project to begin.</Typography> : null}
          {project && draft && !loadingProject ? (
            <form onSubmit={submit}>
              <Stack spacing={2.5}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
                  <Typography variant="h5" component="h2">{project.name}</Typography>
                  <Button size="small" onClick={() => void reloadProject()} disabled={saving}>Reload</Button>
                </Box>
                <TextField fullWidth label="Name" required value={draft.name}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
                  <TextField select fullWidth label="Sector" value={draft.sector}
                    onChange={(event) => setDraft({ ...draft, sector: SectorSchema.parse(event.target.value) })}>
                    {sectors.map((sector) => <MenuItem key={sector} value={sector}>{sector.replaceAll('_', ' ')}</MenuItem>)}
                  </TextField>
                  <TextField fullWidth label="Country" required value={draft.country}
                    onChange={(event) => setDraft({ ...draft, country: event.target.value })} />
                  <TextField select fullWidth label="Stage" value={draft.stage}
                    onChange={(event) => setDraft({ ...draft, stage: StageSchema.parse(event.target.value) })}>
                    {stages.map((stage) => <MenuItem key={stage} value={stage}>{stage.replaceAll('_', ' ')}</MenuItem>)}
                  </TextField>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h6">Key dates</Typography>
                  <Button onClick={() => setDraft({ ...draft, key_dates: [...draft.key_dates, { label: '', date: '' }] })}>
                    Add date
                  </Button>
                </Box>
                {!draft.key_dates.length ? <Typography color="text.secondary">No key dates.</Typography> : null}
                {draft.key_dates.map((item, index) => (
                  <Box key={index} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 180px auto' }, gap: 1.5 }}>
                    <TextField label={`Date ${index + 1} label`} required value={item.label}
                      onChange={(event) => changeDate(index, 'label', event.target.value)} />
                    <TextField label="Date" type="date" required value={item.date}
                      slotProps={{ inputLabel: { shrink: true } }}
                      onChange={(event) => changeDate(index, 'date', event.target.value)} />
                    <Button color="error" onClick={() => setDraft({ ...draft, key_dates: draft.key_dates.filter((_, position) => position !== index) })}>
                      Remove
                    </Button>
                  </Box>
                ))}

                {conflict ? (
                  <Alert severity="warning" icon={false}>
                    <Typography variant="subtitle1" fontWeight="bold">Concurrent edits need your decision</Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      Choose a value for each overlapping field. Other fields will be merged with the latest project.
                    </Typography>
                    <Stack spacing={2}>
                      {conflict.conflicting_fields.map((field) => (
                        <Box key={field}>
                          <Typography fontWeight="bold">{fieldLabel(field)}</Typography>
                          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 0.5 }}>
                            <Button size="small" variant={choices[field] === 'current' ? 'contained' : 'outlined'}
                              onClick={() => setChoices({ ...choices, [field]: 'current' })}>
                              Current: {displayValue(conflict.current[field])}
                            </Button>
                            <Button size="small" variant={choices[field] === 'mine' ? 'contained' : 'outlined'}
                              onClick={() => setChoices({ ...choices, [field]: 'mine' })}>
                              Mine: {displayValue(draft[field])}
                            </Button>
                          </Stack>
                        </Box>
                      ))}
                    </Stack>
                    <Button sx={{ mt: 2 }} variant="contained" disabled={saving || conflict.conflicting_fields.some((field) => !choices[field])}
                      onClick={resolveConflict}>
                      {saving ? 'Saving...' : 'Save selected values'}
                    </Button>
                  </Alert>
                ) : (
                  <Box>
                    <Button type="submit" variant="contained" disabled={saving || !dirty || Boolean(uncertainty)}>
                      {saving ? 'Saving...' : 'Save changes'}
                    </Button>
                    {!dirty ? <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>No unsaved changes.</Typography> : null}
                  </Box>
                )}
              </Stack>
            </form>
          ) : null}
        </Paper>
      </Box>
    </Container>
  )
}
