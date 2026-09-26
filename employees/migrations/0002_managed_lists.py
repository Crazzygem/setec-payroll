"""Convert position/department from free text to managed lists.

Order matters: create the new tables, add nullable FK columns, backfill every
existing row from its text value, then swap the columns, so data survives the
conversion on any database.
"""
from django.db import migrations, models
import django.db.models.deletion


def backfill_lists(apps, schema_editor):
    Employee = apps.get_model('employees', 'Employee')
    Department = apps.get_model('employees', 'Department')
    Position = apps.get_model('employees', 'Position')
    departments, positions = {}, {}
    for employee in Employee.objects.all().order_by('pk'):
        department_name = (employee.department or '').strip() or 'Unassigned'
        position_name = (employee.position or '').strip() or 'Unspecified'
        if department_name not in departments:
            departments[department_name], _ = Department.objects.get_or_create(
                name=department_name
            )
        if position_name not in positions:
            positions[position_name], _ = Position.objects.get_or_create(
                name=position_name
            )
        Employee.objects.filter(pk=employee.pk).update(
            department_new=departments[department_name],
            position_new=positions[position_name],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='employee',
            name='department_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.department'),
        ),
        migrations.AddField(
            model_name='employee',
            name='position_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.position'),
        ),
        migrations.RunPython(backfill_lists, migrations.RunPython.noop),
        migrations.RemoveField(model_name='employee', name='department'),
        migrations.RemoveField(model_name='employee', name='position'),
        migrations.RenameField(model_name='employee', old_name='department_new', new_name='department'),
        migrations.RenameField(model_name='employee', old_name='position_new', new_name='position'),
        migrations.AlterField(
            model_name='employee',
            name='department',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.department'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='position',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.position'),
        ),
    ]
