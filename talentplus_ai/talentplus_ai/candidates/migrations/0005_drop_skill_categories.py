from django.db import migrations


class Migration(migrations.Migration):
    """
    Drops the orphaned 'skill_categories' column from the candidates table.

    This column was created as a side effect of a previous migration that
    restructured the Candidate model. It was never an intentional model field,
    and the Candidate model has no corresponding definition for it.

    The correct column for skills data is 'skills' (JSONField), which already
    exists and is correctly defined in the model. This migration removes the
    mismatch so the DB schema matches the Django model exactly.
    """

    dependencies = [
        ("candidates", "0004_alter_candidate_skills"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE candidates DROP COLUMN IF EXISTS skill_categories;",
            reverse_sql=(
                "ALTER TABLE candidates "
                "ADD COLUMN skill_categories jsonb NOT NULL DEFAULT '[]'::jsonb;"
            ),
        ),
    ]