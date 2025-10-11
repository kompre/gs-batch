# Todo Workflow System

## Directory Structure

- `proposal/` - Task proposals awaiting user approval
- `pending/` - Active development tasks with progress updates
- `completed/YYYY-MM-DD/` - Archived completed tasks by completion date

## Workflow

1. **User**: Add task to `todo.md` with clear objectives
2. **Claude**: Create detailed proposal in `proposal/[task-name].md`
3. **User**: Review, comment, approve proposal
4. **Claude**: Move to `pending/`, implement with progress updates
5. **Claude**: Complete and archive to `completed/YYYY-MM-DD/` with summary

## Task File Format

Each task file should include:
- Original objective from todo.md
- Detailed implementation plan (proposal phase)
- Progress updates (pending phase)
- Final summary and insights (completed phase)
