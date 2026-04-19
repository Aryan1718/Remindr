from __future__ import annotations

import json

import psycopg
from psycopg import sql

from app.models.user import UserModel, UserPreferencesModel

USER_COLUMNS = """
    id,
    auth_user_id,
    email,
    full_name,
    timezone,
    created_at,
    updated_at
"""

PREFERENCE_COLUMNS = """
    id,
    user_id,
    sleep_time,
    wake_time,
    work_start_time,
    work_end_time,
    work_days,
    preferred_response_style,
    decision_style_default,
    reminder_tolerance,
    fatigue_prompt_enabled,
    onboarding_completed,
    profile_json,
    created_at,
    updated_at
"""


class UserRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                create extension if not exists pgcrypto;

                create table if not exists users (
                    id uuid primary key default gen_random_uuid(),
                    auth_user_id uuid unique,
                    email text unique,
                    full_name text,
                    timezone text not null default 'America/Los_Angeles',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );

                create table if not exists user_preferences (
                    id uuid primary key default gen_random_uuid(),
                    user_id uuid not null unique references users(id) on delete cascade,
                    sleep_time time,
                    wake_time time,
                    work_start_time time,
                    work_end_time time,
                    work_days int[] default '{1,2,3,4,5}',
                    preferred_response_style text,
                    decision_style_default text,
                    reminder_tolerance text,
                    fatigue_prompt_enabled boolean not null default true,
                    onboarding_completed boolean not null default false,
                    profile_json jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                """
            )
        self.connection.commit()

    def get_by_auth_user_id(self, auth_user_id: str) -> UserModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {USER_COLUMNS}
                from users
                where auth_user_id = %s
                limit 1
                """,
                (auth_user_id,),
            )
            record = cursor.fetchone()
        return UserModel.from_record(record) if record else None

    def get_user(self, user_id: str) -> UserModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {USER_COLUMNS}
                from users
                where id = %s
                limit 1
                """,
                (user_id,),
            )
            record = cursor.fetchone()
        return UserModel.from_record(record) if record else None

    def create_user(
        self,
        *,
        auth_user_id: str,
        email: str | None,
        full_name: str | None,
        timezone: str | None,
    ) -> UserModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into users (auth_user_id, email, full_name, timezone)
                values (%s, %s, %s, %s)
                returning {USER_COLUMNS}
                """,
                (auth_user_id, email, full_name, timezone or "America/Los_Angeles"),
            )
            record = cursor.fetchone()
        self.connection.commit()
        return UserModel.from_record(record)

    def update_user(
        self,
        user_id: str,
        *,
        email: str | None,
        full_name: str | None,
        timezone: str | None,
    ) -> UserModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                update users
                set email = coalesce(%s, email),
                    full_name = coalesce(%s, full_name),
                    timezone = coalesce(%s, timezone),
                    updated_at = now()
                where id = %s
                returning {USER_COLUMNS}
                """,
                (email, full_name, timezone, user_id),
            )
            record = cursor.fetchone()
        self.connection.commit()
        return UserModel.from_record(record)

    def get_preferences(self, user_id: str) -> UserPreferencesModel | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                select {PREFERENCE_COLUMNS}
                from user_preferences
                where user_id = %s
                limit 1
                """,
                (user_id,),
            )
            record = cursor.fetchone()
        return UserPreferencesModel.from_record(record) if record else None

    def create_preferences(self, user_id: str) -> UserPreferencesModel:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into user_preferences (user_id, profile_json)
                values (%s, %s::jsonb)
                on conflict (user_id) do update set user_id = excluded.user_id
                returning {PREFERENCE_COLUMNS}
                """,
                (user_id, json.dumps({})),
            )
            record = cursor.fetchone()
        self.connection.commit()
        return UserPreferencesModel.from_record(record)

    def update_preferences(
        self,
        user_id: str,
        *,
        values: dict[str, object],
    ) -> UserPreferencesModel:
        assignments: list[sql.Composed] = []
        params: list[object] = []

        for column, value in values.items():
            if column == "profile_json":
                assignments.append(
                    sql.SQL("profile_json = coalesce(profile_json, '{}'::jsonb) || %s::jsonb")
                )
                params.append(json.dumps(value))
                continue

            assignments.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
            params.append(value)

        assignments.append(sql.SQL("updated_at = now()"))
        params.append(user_id)

        query = sql.SQL(
            """
            update user_preferences
            set {assignments}
            where user_id = %s
            returning {columns}
            """
        ).format(
            assignments=sql.SQL(", ").join(assignments),
            columns=sql.SQL(PREFERENCE_COLUMNS),
        )

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            record = cursor.fetchone()
        self.connection.commit()
        return UserPreferencesModel.from_record(record)
