-- Принудительное создание таблиц Django если они не существуют
-- Выполните этот скрипт если миграции не сработали

-- Проверяем, существует ли таблица auth_user
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'auth_user') THEN
        -- Создаем базовые таблицы Django auth
        CREATE TABLE auth_user (
            id SERIAL PRIMARY KEY,
            password VARCHAR(128) NOT NULL,
            last_login TIMESTAMP WITH TIME ZONE,
            is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
            username VARCHAR(150) NOT NULL UNIQUE,
            first_name VARCHAR(150) NOT NULL DEFAULT '',
            last_name VARCHAR(150) NOT NULL DEFAULT '',
            email VARCHAR(254) NOT NULL DEFAULT '',
            is_staff BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE TABLE auth_group (
            id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL UNIQUE
        );

        CREATE TABLE auth_permission (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            content_type_id INTEGER NOT NULL,
            codename VARCHAR(100) NOT NULL
        );

        CREATE TABLE django_content_type (
            id SERIAL PRIMARY KEY,
            app_label VARCHAR(100) NOT NULL,
            model VARCHAR(100) NOT NULL,
            UNIQUE(app_label, model)
        );

        CREATE TABLE auth_group_permissions (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES auth_group(id),
            permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
            UNIQUE(group_id, permission_id)
        );

        CREATE TABLE auth_user_groups (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES auth_user(id),
            group_id INTEGER NOT NULL REFERENCES auth_group(id),
            UNIQUE(user_id, group_id)
        );

        CREATE TABLE auth_user_user_permissions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES auth_user(id),
            permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
            UNIQUE(user_id, permission_id)
        );

        CREATE TABLE django_migrations (
            id SERIAL PRIMARY KEY,
            app VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE TABLE django_session (
            session_key VARCHAR(40) PRIMARY KEY,
            session_data TEXT NOT NULL,
            expire_date TIMESTAMP WITH TIME ZONE NOT NULL
        );

        -- Добавляем Foreign Key для auth_permission
        ALTER TABLE auth_permission ADD CONSTRAINT auth_permission_content_type_id_fk
            FOREIGN KEY (content_type_id) REFERENCES django_content_type(id);

        RAISE NOTICE 'Django base tables created successfully';
    ELSE
        RAISE NOTICE 'Django tables already exist';
    END IF;
END $$;