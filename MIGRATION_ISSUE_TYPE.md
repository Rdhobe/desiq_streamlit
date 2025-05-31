# Migration for SupportIssue Model

## Update: Migration Applied

**Status: ✅ Migration has been successfully applied on May 14, 2025.**

The `issue_type` field has been added to the `SupportIssue` model and is now available in the database schema. The support page should now work correctly without errors.

## Original Issue

There was a pending migration to add the `issue_type` field to the `SupportIssue` model. This migration had been created but not yet applied due to database connectivity issues.

### The Error

The error occurred when accessing the support page because the `SupportIssue` model in the code included an `issue_type` field that didn't exist in the database schema.

### Temporary Fix

A temporary fix was implemented that:
1. Made the `support_view` handle database errors gracefully
2. Removed `issue_type` from the form and templates

## How the Migration Was Applied

The migration was applied using the SQLite database with the following command:

```bash
# Set the environment variable to use SQLite (Windows PowerShell)
$env:DISABLE_DOTENV="True"
$env:USE_SQLITE="True"

# Run the specific migration
python manage.py migrate core 0022_add_issue_type_to_supportissue
```

## Next Steps

Now that the migration has been applied, you can:

1. Update the `IssueForm` in `forms.py` to include the issue_type field:
   ```python
   class IssueForm(forms.ModelForm):
       class Meta:
           model = SupportIssue
           fields = ['title', 'description', 'priority', 'issue_type']
           widgets = {
               'description': forms.Textarea(attrs={'rows': 5}),
           }
   ```

2. Update the templates to display and collect the issue_type field:
   - `create_issue.html`: Add a field for selecting issue type
   - `issue_detail.html`: Display the issue type
   - `all_issues.html`: Add issue type column to the table (already has conditional code)

## Migration Details

The migration file `core/migrations/0022_add_issue_type_to_supportissue.py` added the following field:

```python
models.CharField(
    choices=[
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('question', 'Question'),
        ('feedback', 'Feedback'),
        ('contact', 'Contact Form'),
        ('other', 'Other'),
    ],
    default='other',
    max_length=20,
)
```

If you need to recreate this migration, you can run:

```bash
python manage.py makemigrations core --name add_issue_type_to_supportissue
``` 