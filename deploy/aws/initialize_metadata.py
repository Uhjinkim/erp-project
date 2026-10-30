#!/usr/bin/env python3
"""One-time initialization after a reviewed schema-only restore; never used by CI/CD."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SEEDS = {
    ("workforce", "0002_required_roles"),
    ("workforce", "0003_payroll_manager_role"),
    ("payroll", "0003_seed_components"),
    ("payroll", "0004_seed_bonus_component"),
    ("payroll", "0005_seed_income_tax_component"),
    ("board", "0003_seed_notice_categories"),
}


def normalize_constraint(definition):
    """PostgreSQL minors deparse varchar-array-to-text casts in two equivalent forms."""
    literal = r"'(?:[^']|'')*'::character varying"
    pattern = r"\(ARRAY\[((?:" + literal + r")(?:,\s*" + literal + r")*)\]\)::text\[\]"

    def expand(match):
        values = re.findall(literal, match.group(1))
        return "ARRAY[" + ", ".join("(" + value + ")::text" for value in values) + "]"

    return re.sub(pattern, expand, definition)


def capture_schema(cursor, tables):
    """Compare structure by column names rather than nonportable PostgreSQL attribute IDs."""
    result = {}
    cursor.execute("SET LOCAL search_path=public,pg_catalog")
    for table in sorted(tables):
        relation = "public." + table
        cursor.execute(
            "SELECT a.attnum,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,"
            "a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid) "
            "FROM pg_attribute a LEFT JOIN pg_attrdef d "
            "ON d.adrelid=a.attrelid AND d.adnum=a.attnum "
            "WHERE a.attrelid=to_regclass(%s) AND a.attnum>0 AND NOT a.attisdropped "
            "ORDER BY a.attnum",
            [relation],
        )
        columns = cursor.fetchall()
        column_names = {row[0]: row[1] for row in columns}
        cursor.execute(
            "SELECT conname,contype,pg_get_constraintdef(oid,false),conkey "
            "FROM pg_constraint WHERE conrelid=to_regclass(%s) ORDER BY conname",
            [relation],
        )
        constraints = [
            (
                name,
                kind,
                normalize_constraint(definition),
                [column_names.get(n, "<expression>") for n in keys or []],
            )
            for name, kind, definition, keys in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT pg_get_indexdef(i.indexrelid),i.indkey::text "
            "FROM pg_index i JOIN pg_class ix ON ix.oid=i.indexrelid "
            "WHERE i.indrelid=to_regclass(%s) ORDER BY ix.relname",
            [relation],
        )
        indexes = [
            (definition, [column_names.get(int(n), "<expression>") for n in keys.split()])
            for definition, keys in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT a.attname,ns.nspname,s.relname,ps.seqstart,ps.seqincrement,ps.seqmin,"
            "ps.seqmax,ps.seqcache,ps.seqcycle FROM pg_attribute a "
            "JOIN pg_class s ON s.oid=pg_get_serial_sequence(%s,a.attname)::regclass "
            "JOIN pg_namespace ns ON ns.oid=s.relnamespace "
            "JOIN pg_sequence ps ON ps.seqrelid=s.oid "
            "WHERE a.attrelid=to_regclass(%s) AND a.attnum>0 AND NOT a.attisdropped "
            "ORDER BY a.attname",
            [relation, relation],
        )
        result[table] = {
            "columns": [row[1:] for row in columns],
            "constraints": constraints,
            "indexes": indexes,
            "sequences": cursor.fetchall(),
        }
    return json.loads(json.dumps(result))


def initialize(plan, database):
    import django

    django.setup()
    from django.apps import apps
    from django.contrib.auth.management import create_permissions
    from django.db import connection, transaction
    from django.db.migrations.loader import MigrationLoader
    from django.db.migrations.recorder import MigrationRecorder

    if database != "erp-db":
        raise ValueError("This reviewed bootstrap only targets erp-db")
    loader = MigrationLoader(None)
    expected_migrations = {tuple(item) for item in plan["repository_migrations"]}
    if expected_migrations != set(loader.disk_migrations):
        raise ValueError("Plan does not match this release's migration files")
    tables = set(plan["schema"])
    model_tables = {
        model._meta.db_table
        for model in apps.get_models(include_auto_created=True)
        if model._meta.managed and not model._meta.proxy and not model._meta.swapped
    } | {"django_migrations"}
    if tables != model_tables:
        raise ValueError("Plan does not match this release's model tables")
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_user")
        if cursor.fetchone() != (database, "erp"):
            raise ValueError("Expected erp owner connection to erp-db")
        cursor.execute("SELECT pg_advisory_xact_lock(20261030, 1)")
        if capture_schema(cursor, tables) != plan["schema"]:
            raise ValueError("Restored schema differs from the reviewed source projection")
        for table in sorted(tables):
            cursor.execute(
                f"SELECT EXISTS(SELECT 1 FROM {connection.ops.quote_name(table)} LIMIT 1)"
            )
            if cursor.fetchone()[0]:
                raise ValueError("Initialization requires every target table to be empty")
        ordered = []
        for leaf in loader.graph.leaf_nodes():
            for node in loader.graph.forwards_plan(leaf):
                if node not in ordered:
                    ordered.append(node)
        recorder = MigrationRecorder(connection)
        for app, name in ordered:
            recorder.record_applied(app, name)
        historical_apps = loader.project_state().apps
        with connection.schema_editor(atomic=False) as editor:
            for key in ordered:
                if key in SEEDS:
                    migration = loader.disk_migrations[key]
                    for operation in migration.operations:
                        operation.code(historical_apps, editor)
        for app_config in apps.get_app_configs():
            create_permissions(
                app_config, verbosity=0, interactive=False, using="default", apps=apps
            )
    print("Verified schema; initialized migration records, permissions and six code-defined seeds")
    print("No employee, login account, payroll or evaluation records were copied or created")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--confirm-empty-database", required=True)
    args = parser.parse_args()
    # Mounted scripts live outside /app/backend; import the configured project from its WORKDIR.
    sys.path.insert(0, str(Path.cwd()))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    initialize(json.loads(args.plan.read_text()), args.confirm_empty_database)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Django/driver exceptions can contain connection details; never emit their raw values.
        print("Metadata initialization failed: " + type(error).__name__, file=sys.stderr)
        sys.exit(1)
