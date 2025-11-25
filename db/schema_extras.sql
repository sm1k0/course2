-- ============================
-- ВЬЮШКИ ДЛЯ ОТЧЁТОВ / АНАЛИТИКИ
-- ============================
-- Включаем pgcrypto (если ещё не включено)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Товары + категория + остаток
CREATE OR REPLACE VIEW vw_products_full AS
SELECT
    p.id              AS product_id,
    p.name            AS product_name,
    p.sku             AS sku,
    p.price           AS price,
    p.discount_percent AS discount_percent,
    p.is_active       AS is_active,
    c.id              AS category_id,
    c.name            AS category_name,
    COALESCE(s.quantity, 0) AS stock_quantity
FROM products p
JOIN categories c ON p.category_id = c.id
LEFT JOIN stock s ON s.product_id = p.id;


-- Заказы + клиент + позиции
CREATE OR REPLACE VIEW vw_orders_full AS
SELECT
    o.id                    AS order_id,
    o.created_at            AS order_created_at,
    o.status                AS order_status,
    o.total_amount          AS order_total_amount,
    cp.id                   AS customer_id,
    cp.full_name            AS customer_name,
    cp.phone                AS customer_phone,
    o.delivery_address      AS delivery_address,
    oi.id                   AS order_item_id,
    oi.product_id           AS product_id,
    p.name                  AS product_name,
    oi.quantity             AS quantity,
    oi.unit_price           AS unit_price,
    (oi.quantity * oi.unit_price) AS line_total
FROM orders o
JOIN customers cp ON o.customer_id = cp.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id;


-- Сводка продаж (по дням: сумма и количество заказов)
CREATE OR REPLACE VIEW vw_sales_summary AS
SELECT
    o.created_at::date      AS sale_date,
    COUNT(DISTINCT o.id)    AS orders_count,
    SUM(o.total_amount)     AS total_amount
FROM orders o
WHERE o.status = 'COMPLETED'
GROUP BY o.created_at::date
ORDER BY o.created_at::date;


-- ============================
-- ХРАНИМЫЕ ПРОЦЕДУРЫ / ФУНКЦИИ
-- ============================

-- 1) sp_create_order: создаёт заказ из JSON-массива позиций
-- JSON формат:
-- [
--   { "product_id": 1, "quantity": 2 },
--   { "product_id": 5, "quantity": 1 }
-- ]
CREATE OR REPLACE FUNCTION sp_create_order(
    p_customer_id      INTEGER,
    p_payment_method   VARCHAR,
    p_delivery_method  VARCHAR,
    p_delivery_address TEXT,
    p_comment          TEXT,
    p_items            JSONB
) RETURNS INTEGER AS
$$
DECLARE
    v_order_id   INTEGER;
    v_item       JSONB;
    v_product_id INTEGER;
    v_qty        INTEGER;
    v_price      NUMERIC(10,2);
    v_stock_qty  INTEGER;
    v_total      NUMERIC(12,2) := 0;
BEGIN
    -- создаём заказ
    INSERT INTO orders (
        customer_id,
        status,
        payment_method,
        delivery_method,
        delivery_address,
        comment,
        total_amount,
        created_at,
        updated_at
    )
    VALUES (
        p_customer_id,
        'NEW',
        p_payment_method,
        p_delivery_method,
        p_delivery_address,
        COALESCE(p_comment, ''),
        0,
        NOW(),
        NOW()
    )
    RETURNING id INTO v_order_id;

    -- обрабатываем позиции
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        v_product_id := (v_item->>'product_id')::INT;
        v_qty        := (v_item->>'quantity')::INT;

        IF v_qty IS NULL OR v_qty <= 0 THEN
            RAISE EXCEPTION 'Некорректное количество в позиции: %', v_item;
        END IF;

        -- блокируем строку склада на время операции
        SELECT p.price, s.quantity
        INTO v_price, v_stock_qty
        FROM products p
        JOIN stock s ON s.product_id = p.id
        WHERE p.id = v_product_id
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Товар id=% не найден или нет записи на складе', v_product_id;
        END IF;

        IF v_stock_qty < v_qty THEN
            RAISE EXCEPTION 'Недостаточно товара id=% на складе (есть %, нужно %)', v_product_id, v_stock_qty, v_qty;
        END IF;

        -- создаём позицию заказа
        INSERT INTO order_items (
            order_id,
            product_id,
            quantity,
            unit_price,
            created_at
        )
        VALUES (
            v_order_id,
            v_product_id,
            v_qty,
            v_price,
            NOW()
        );

        -- уменьшаем остаток
        UPDATE stock
        SET quantity = quantity - v_qty,
            updated_at = NOW()
        WHERE product_id = v_product_id;

        -- считаем итоговую сумму
        v_total := v_total + v_price * v_qty;
    END LOOP;

    -- пишем итоговую сумму в заказ
    UPDATE orders
    SET total_amount = v_total,
        updated_at = NOW()
    WHERE id = v_order_id;

    RETURN v_order_id;
END;
$$ LANGUAGE plpgsql;


-- 2) sp_update_stock_bulk: массовое обновление остатков
-- JSON формат:
-- [
--   { "product_id": 1, "quantity": 100 },
--   { "product_id": 2, "quantity": 50 }
-- ]
CREATE OR REPLACE FUNCTION sp_update_stock_bulk(
    p_changes JSONB
) RETURNS VOID AS
$$
DECLARE
    v_item       JSONB;
    v_product_id INTEGER;
    v_qty        INTEGER;
BEGIN
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_changes)
    LOOP
        v_product_id := (v_item->>'product_id')::INT;
        v_qty        := (v_item->>'quantity')::INT;

        IF v_product_id IS NULL OR v_qty IS NULL OR v_qty < 0 THEN
            RAISE EXCEPTION 'Некорректные данные в изменениях склада: %', v_item;
        END IF;

        -- если запись в stock есть — обновляем, иначе создаём
        INSERT INTO stock (product_id, quantity, updated_at)
        VALUES (v_product_id, v_qty, NOW())
        ON CONFLICT (product_id)
        DO UPDATE SET quantity = EXCLUDED.quantity,
                      updated_at = NOW();
    END LOOP;
END;
$$ LANGUAGE plpgsql;
-- Добавляем зашифрованные колонки для персональных данных клиентов
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS phone_enc BYTEA,
    ADD COLUMN IF NOT EXISTS default_address_enc BYTEA;

-- Функция-триггер для шифрования перед вставкой/обновлением
CREATE OR REPLACE FUNCTION trg_encrypt_customer_data()
RETURNS TRIGGER AS
$$
DECLARE
    v_key TEXT := 'very_secret_key_for_demo_only'; -- в реале хранится отдельно!
BEGIN
    IF NEW.phone IS NOT NULL THEN
        NEW.phone_enc := pgp_sym_encrypt(NEW.phone::text, v_key);
    END IF;

    IF NEW.default_address IS NOT NULL THEN
        NEW.default_address_enc := pgp_sym_encrypt(NEW.default_address::text, v_key);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер на customers
DROP TRIGGER IF EXISTS tg_customers_encrypt ON customers;

CREATE TRIGGER tg_customers_encrypt
BEFORE INSERT OR UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION trg_encrypt_customer_data();


-- 3) sp_sales_report: агрегированные продажи по периоду
-- p_period: 'day', 'month', 'week' и т.п. для date_trunc
CREATE OR REPLACE FUNCTION sp_sales_report(
    p_period TEXT
)
RETURNS TABLE (
    period_start TIMESTAMP,
    total_amount NUMERIC(12,2),
    orders_count INTEGER
) AS
$$
BEGIN
    RETURN QUERY
    SELECT
        date_trunc(p_period, created_at) AS period_start,
        SUM(total_amount)                AS total_amount,
        COUNT(*)                         AS orders_count
    FROM orders
    WHERE status = 'COMPLETED'
    GROUP BY date_trunc(p_period, created_at)
    ORDER BY period_start;
END;
$$ LANGUAGE plpgsql;
