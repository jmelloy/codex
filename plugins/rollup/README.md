# Rollup Views Plugin

Time-based rollup views for activity tracking and reporting.

## Features

- **Date Grouping**: Group files by hour, day, week, or month
- **Statistics**: Show counts and metrics for each group
- **Categorized Sections**: Organize items into filtered sections
- **Time Ranges**: Query by creation or modification time

## View Type

### Rollup

Activity report grouped by date with statistics.

**View Type**: `rollup`

**Configuration Options**:
- `group_by`: Field to group by (created_at, modified_at)
- `group_format`: Grouping granularity (hour, day, week, month)
- `show_stats`: Show statistics for each group (default: true)
- `sections`: Array of categorized sections with filters

**Example**:
```yaml
---
type: view
view_type: rollup
title: Weekly Activity Report
query:
  created_after: "{{ startOfWeek }}"
  created_before: "{{ endOfWeek }}"
config:
  group_by: created_at
  group_format: day
  show_stats: true
  sections:
    - title: New Tasks
      filter:
        tags: [task]
    - title: Journal Entries
      filter:
        tags: [journal]
---
```

## Templates

### Weekly Rollup

Create a weekly activity rollup view.

**Template ID**: `weekly-rollup`  
**Default Name**: `weekly-rollup.cdx`  
**Icon**: 📈

## Examples

The plugin includes a weekly activity report that shows all files created this week, grouped by day and categorized by type.

## Usage

### Creating a Rollup

1. Use the "Weekly Rollup" template to create a new rollup view
2. Configure the time range using query filters (created_after, created_before)
3. Set the grouping granularity (day, week, month)
4. Add categorized sections with filters
5. View activity statistics for each time period

### Template Variables

Use template variables for dynamic date queries:
- `{{ today }}` - Current date/time
- `{{ todayStart }}` - Start of today (00:00)
- `{{ startOfWeek }}` - Start of current week
- `{{ endOfWeek }}` - End of current week
- `{{ startOfMonth }}` - Start of current month

## Permissions

This plugin requires the following permissions:
- `read_files`: Read files for rollup

## License

MIT License - See LICENSE file for details
