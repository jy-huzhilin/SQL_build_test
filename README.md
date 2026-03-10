# SQL 配置文件参考手册

本项目展示如何通过 JSON 配置文件生成 ClickHouse SQL 查询，供编写配置文件时参考。

## 基础概念

**时间字段**：系统根据表的 schema 自动判断时间字段类型：
- 日期型（`date`）：过滤条件为 `CAST(date AS DATE) > '...' AND CAST(date AS DATE) <= '...'`
- 日期时间型（`time`）：过滤条件为 `time > '...' AND time <= '...'`
- 静态表（无时间字段）：不添加时间过滤

**时间偏移**：`start_time` / `end_time` 支持相对偏移（秒），`schedule_now` 表示调度触发时刻。偏移量基于触发时间计算，并自动跳过非交易日（以下示例基准时间为 `2026-03-02 15:30:00`）：
| 偏移量 | 含义 | 示例日期 |
|--------|------|---------|
| `-3600` | 1小时前 | `2026-03-02 14:30:00` |
| `-604800` | 约7个交易日前 | `2026-02-11` |
| `-2592000` | 约30个交易日前 | `2026-01-09` |

**SELECT 列自动补全**：不指定 `columns` 时生成 `SELECT *`；指定 `columns` 但未指定 `group_by` 时，系统会自动将表的主键字段（时间字段 + 标的代码字段）合并入 `columns`。指定 `group_by` 后，主键不会自动补全。

---

## basic.json — 静态表基础查询

静态表（无时间字段）不添加时间过滤条件。

**Item 1**

```json
{
  "sources": ["cbond.cbond_basic_info"]
}
```

```sql
SELECT * FROM cbond.cbond_basic_info
```

---

## time_range.json — 时间范围

展示不同时间偏移量及不同时间字段类型的效果。

**Item 1**：日期型字段，30个交易日范围

```json
{
  "sources": ["cbond.cbond_terms"],
  "start_time": "-2592000",
  "end_time": "schedule_now"
}
```

```sql
SELECT * FROM cbond.cbond_terms
WHERE CAST(date AS DATE) > '2026-01-09' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 2**：日期型字段，约7个交易日范围

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now"
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 3**：datetime 型字段，1小时范围

```json
{
  "sources": ["cbond.cbond_hf_1min_market"],
  "start_time": "-3600",
  "end_time": "schedule_now"
}
```

```sql
SELECT * FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 14:30:00' AND time <= '2026-03-02 15:30:00'
```

**Item 4**：日期型字段，30个交易日范围

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-2592000",
  "end_time": "schedule_now"
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-01-09' AND CAST(date AS DATE) <= '2026-03-02'
```

---

## table_types.json — 多种表类型

展示不同 schema 类型的表（静态表、日期型、datetime 型）的查询方式。系统根据表的时间字段类型自动选择过滤形式，无需在配置中手动指定。

---

## filters.json — 过滤条件

展示各种过滤条件的写法。

**Item 1**：原始字符串（直接嵌入 WHERE）

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "filters": ["issue_credit_rating = 'AAA' AND ths_code LIKE '11%'"]
}
```

```sql
SELECT * FROM cbond.cbond_basic_info
WHERE issue_credit_rating = 'AAA' AND ths_code LIKE '11%'
```

**Item 2**：等值条件

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
}
```

```sql
SELECT * FROM cbond.cbond_basic_info
WHERE issue_credit_rating = 'AAA'
```

> **注**：字符串值需在配置中手动加引号，写作 `"'AAA'"` 而非 `"AAA"`，否则生成的 SQL 中缺少引号。数值型直接写数字即可。

**Item 3**：大于

```json
{"column": "close", "op": ">", "value": 100}
```

```sql
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02') AND close > 100
```

**Item 4**：大于等于

```json
{"column": "close", "op": ">=", "value": 100}
```

```sql
WHERE ... AND close >= 100
```

**Item 5**：LIKE

```json
{"column": "ths_code", "op": "LIKE", "value": "11%"}
```

```sql
WHERE ths_code LIKE 11%
```

**Item 6**：IN 列表

```json
{"column": "ths_code", "op": "IN", "value": ["110001.SH", "110002.SH", "110003.SH"]}
```

```sql
WHERE ths_code IN ('110001.SH', '110002.SH', '110003.SH')
```

**Item 7**：NOT IN 列表

```json
{"column": "issue_credit_rating", "op": "NOT IN", "value": ["AA-", "A+"]}
```

```sql
WHERE NOT (issue_credit_rating IN ('AA-', 'A+'))
```

**Item 8**：BETWEEN 区间

```json
{"column": "close", "op": "BETWEEN", "value": [50, 200]}
```

```sql
WHERE ... AND close BETWEEN 50 AND 200
```

**Item 9**：OR 条件（内层列表表示 OR，外层列表表示 AND）

```json
"filters": [
  [
    {"column": "close", "op": ">", "value": 200},
    {"column": "close", "op": "<", "value": 50}
  ]
]
```

```sql
WHERE ... AND (close > 200 OR close < 50)
```

**Item 10**：AND + OR 混合

```json
"filters": [
  {"column": "ths_code", "op": "IN", "value": ["110001.SH", "110002.SH"]},
  {"column": "close", "op": ">", "value": 100},
  [
    {"column": "volume", "op": ">", "value": 10000},
    {"column": "pe", "op": "<", "value": 30}
  ]
]
```

```sql
WHERE ... AND ths_code IN ('110001.SH', '110002.SH')
       AND close > 100
       AND (volume > 10000 OR pe < 30)
```

---

## select_options.json — 查询选项

展示列选择、DISTINCT、QUALIFY、ORDER BY、LIMIT 等选项。

**Item 1**：指定列（静态表）

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "columns": ["ths_code", "issue_credit_rating", "issue_total_amt"]
}
```

```sql
SELECT issue_credit_rating, issue_total_amt, ths_code FROM cbond.cbond_basic_info
```

> 列按字母顺序排列。未指定 `group_by` 时，系统自动将主键字段合并入指定列（此处 `ths_code` 已在配置中）。

**Item 2**：DISTINCT

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "columns": ["issue_credit_rating"],
  "distinct": true
}
```

```sql
SELECT DISTINCT issue_credit_rating, ths_code FROM cbond.cbond_basic_info
```

**Item 3**：自定义 QUALIFY（去重保留最新记录）

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "qualify": "row_number() OVER (PARTITION BY ths_code, date ORDER BY create_time DESC) = 1"
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY ths_code, date ORDER BY create_time DESC) = 1
```

**Item 4**：ORDER BY

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "order_by": [
    {"column": "date", "direction": "DESC"},
    {"column": "ths_code", "direction": "ASC"}
  ]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
ORDER BY date DESC, ths_code ASC
```

**Item 5**：LIMIT

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "limit": 100
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
LIMIT 100
```

**Item 6**：ORDER BY + LIMIT

```json
{
  "order_by": [{"column": "date", "direction": "DESC"}],
  "limit": 50
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
ORDER BY date DESC
LIMIT 50
```

---

## group_by_having.json — 分组与聚合过滤

**Item 1**：GROUP BY + HAVING（dict 格式）

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "columns": ["issue_credit_rating", "COUNT(*) AS cnt"],
  "group_by": ["issue_credit_rating"],
  "having": [{"column": "cnt", "op": ">", "value": 10}]
}
```

```sql
SELECT COUNT(*) AS cnt, issue_credit_rating FROM cbond.cbond_basic_info
GROUP BY issue_credit_rating
HAVING cnt > 10
```

**Item 2**：HAVING 原始字符串

```json
"having": ["cnt > 10 AND cnt < 1000"]
```

```sql
GROUP BY issue_credit_rating
HAVING cnt > 10 AND cnt < 1000
```

**Item 3**：HAVING OR 条件（内层列表表示 OR）

```json
"having": [
  [
    {"column": "cnt", "op": ">", "value": 3},
    {"column": "avg_close", "op": ">", "value": 100}
  ]
]
```

```sql
SELECT AVG(close) AS avg_close, COUNT(*) AS cnt, ths_code
FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
GROUP BY ths_code
HAVING cnt > 3 OR avg_close > 100
```

**Item 4**：多列 GROUP BY + 多条件 HAVING（AND）

```json
{
  "columns": ["ths_code", "date", "SUM(volume) AS total_volume", "AVG(close) AS avg_close"],
  "group_by": ["ths_code", "date"],
  "having": [
    {"column": "total_volume", "op": ">", "value": 1000},
    {"column": "avg_close", "op": ">", "value": 50}
  ]
}
```

```sql
SELECT AVG(close) AS avg_close, SUM(volume) AS total_volume, date, ths_code
FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
GROUP BY ths_code, date
HAVING total_volume > 1000 AND avg_close > 50
```

---

## subquery.json — 子查询作为主表

将聚合子查询作为 FROM 的数据来源，外层再做过滤。子查询必须指定 `group_by`（避免系统自动补全时间/标的主键）并指定 `name` 作为别名。

**Item 1**：子查询过滤 max_price > 100

```json
{
  "sources": [
    {
      "name": "quotes_agg",
      "table": {
        "name": "sub",
        "table": "cbond.stock_daily_quotes_non_ror",
        "columns": ["ths_code", "MAX(close) AS max_price"],
        "group_by": ["ths_code"],
        "start_time": "-604800",
        "end_time": "schedule_now"
      },
      "filters": [{"column": "max_price", "op": ">", "value": 100}]
    }
  ]
}
```

```sql
SELECT * FROM (
  SELECT MAX(close) AS max_price, ths_code
  FROM cbond.stock_daily_quotes_non_ror
  WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
  GROUP BY ths_code
) AS quotes_agg
WHERE max_price > 100
```

**Item 2**：子查询过滤区间

```json
{
  "sources": [
    {
      "name": "avg_prices",
      "table": {
        "name": "sub",
        "table": "cbond.stock_daily_quotes_non_ror",
        "columns": ["ths_code", "AVG(close) AS avg_price", "COUNT(*) AS trade_cnt"],
        "group_by": ["ths_code"],
        "start_time": "-604800",
        "end_time": "schedule_now"
      },
      "filters": [
        {"column": "avg_price", "op": ">=", "value": 50},
        {"column": "avg_price", "op": "<=", "value": 200}
      ]
    }
  ]
}
```

```sql
SELECT * FROM (
  SELECT AVG(close) AS avg_price, COUNT(*) AS trade_cnt, ths_code
  FROM cbond.stock_daily_quotes_non_ror
  WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
  GROUP BY ths_code
) AS avg_prices
WHERE avg_price >= 50 AND avg_price <= 200
```

---

## join.json — 表关联

**Item 1**：LEFT JOIN 真实表

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "join": [
    {
      "table": "cbond.cbond_basic_info",
      "type": "LEFT",
      "on": "stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code"
    }
  ]
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
LEFT JOIN cbond.cbond_basic_info
  ON stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code
WHERE CAST(stock_daily_quotes_non_ror.date AS DATE) > '2026-02-11'
  AND CAST(stock_daily_quotes_non_ror.date AS DATE) <= '2026-03-02'
```

> JOIN 场景下，时间过滤字段自动加上主表别名前缀，避免多表字段歧义。

**Item 2**：INNER JOIN

```json
{
  "join": [{"table": "cbond.cbond_basic_info", "type": "INNER", "on": "..."}]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
INNER JOIN cbond.cbond_basic_info
  ON cbond_daily_quote_market.ths_code = cbond_basic_info.ths_code
WHERE CAST(cbond_daily_quote_market.date AS DATE) > '2026-02-11'
  AND CAST(cbond_daily_quote_market.date AS DATE) <= '2026-03-02'
```

**Item 3**：多表 LEFT JOIN

```json
{
  "join": [
    {"table": "cbond.cbond_basic_info", "type": "LEFT", "on": "..."},
    {"table": "cbond.cbond_daily_terms", "type": "LEFT", "on": "cbond_daily_quote_market.ths_code = cbond_daily_terms.ths_code AND cbond_daily_quote_market.date = cbond_daily_terms.date"}
  ]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
LEFT JOIN cbond.cbond_basic_info ON cbond_daily_quote_market.ths_code = cbond_basic_info.ths_code
LEFT JOIN cbond.cbond_daily_terms ON cbond_daily_quote_market.ths_code = cbond_daily_terms.ths_code
  AND cbond_daily_quote_market.date = cbond_daily_terms.date
WHERE CAST(cbond_daily_quote_market.date AS DATE) > '2026-02-11'
  AND CAST(cbond_daily_quote_market.date AS DATE) <= '2026-03-02'
```

**Item 4**：JOIN 子查询

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "join": [
    {
      "table": {
        "name": "latest_price",
        "table": "cbond.stock_daily_quotes_non_ror",
        "columns": ["ths_code", "MAX(close) AS max_price"],
        "group_by": ["ths_code"],
        "start_time": "-604800",
        "end_time": "schedule_now"
      },
      "type": "LEFT",
      "on": "cbond_basic_info.ths_code = latest_price.ths_code"
    }
  ]
}
```

```sql
SELECT * FROM cbond.cbond_basic_info
LEFT JOIN (
  SELECT MAX(close) AS max_price, ths_code
  FROM cbond.stock_daily_quotes_non_ror
  WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
  GROUP BY ths_code
) AS latest_price ON cbond_basic_info.ths_code = latest_price.ths_code
```

---

## cte.json — 公共表表达式（WITH）

**Item 1**：简单 CTE

```json
{
  "with": [
    {"name": "cte_info", "table": "cbond.cbond_basic_info", "columns": ["ths_code", "issue_credit_rating"]}
  ],
  "sources": ["cte_info"]
}
```

```sql
WITH cte_info AS (
  SELECT issue_credit_rating, ths_code FROM cbond.cbond_basic_info
)
SELECT * FROM cte_info
```

**Item 2**：多 CTE + JOIN

```json
{
  "with": [
    {"name": "bond_info", "table": "cbond.cbond_basic_info", "columns": ["ths_code", "issue_credit_rating"]},
    {"name": "latest_quote", "table": "cbond.stock_daily_quotes_non_ror", "columns": ["ths_code", "close"], "start_time": "-604800", "end_time": "schedule_now"}
  ],
  "sources": ["bond_info"],
  "join": [{"table": "latest_quote", "type": "LEFT", "on": "bond_info.ths_code = latest_quote.ths_code"}]
}
```

```sql
WITH bond_info AS (
  SELECT issue_credit_rating, ths_code FROM cbond.cbond_basic_info
),
latest_quote AS (
  SELECT close, ths_code FROM cbond.stock_daily_quotes_non_ror
  WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
)
SELECT * FROM bond_info
LEFT JOIN latest_quote ON bond_info.ths_code = latest_quote.ths_code
```

**Item 3**：CTE + 过滤

```json
{
  "with": [
    {"name": "cte_cbond", "table": "cbond.cbond_basic_info", "columns": ["ths_code", "issue_credit_rating", "issue_total_amt"]}
  ],
  "sources": ["cte_cbond"],
  "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
}
```

```sql
WITH cte_cbond AS (
  SELECT issue_credit_rating, issue_total_amt, ths_code FROM cbond.cbond_basic_info
)
SELECT * FROM cte_cbond
WHERE issue_credit_rating = 'AAA'
```

**Item 4**：CTE 子查询 — 内层过滤，外层加 ORDER BY + LIMIT

当 CTE 的 `table` 为 dict（子查询）时，外层可在子查询结果之上再加 `order_by`、`limit`、`filters` 等条件。

```json
{
  "with": [
    {
      "name": "aaa_bonds",
      "table": {
        "table": "cbond.cbond_basic_info",
        "columns": ["ths_code", "listed_date"],
        "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
      },
      "order_by": [{"column": "listed_date", "direction": "ASC"}],
      "limit": 50
    }
  ],
  "sources": ["aaa_bonds"]
}
```

```sql
WITH aaa_bonds AS (
  SELECT * FROM (
    SELECT listed_date, ths_code FROM cbond.cbond_basic_info WHERE issue_credit_rating = 'AAA'
  )
  ORDER BY listed_date ASC
  LIMIT 50
)
SELECT * FROM aaa_bonds
```

**Item 5**：CTE 子查询 — 内层聚合，外层对聚合列过滤

```json
{
  "with": [
    {
      "name": "avg_close_cte",
      "table": {
        "table": "cbond.stock_daily_quotes_non_ror",
        "columns": ["ths_code", "AVG(close) AS avg_close", "COUNT(*) AS trade_days"],
        "group_by": ["ths_code"],
        "start_time": "-604800",
        "end_time": "schedule_now"
      },
      "filters": [{"column": "trade_days", "op": ">=", "value": 3}]
    }
  ],
  "sources": ["avg_close_cte"]
}
```

```sql
WITH avg_close_cte AS (
  SELECT * FROM (
    SELECT AVG(close) AS avg_close, COUNT(*) AS trade_days, ths_code
    FROM cbond.stock_daily_quotes_non_ror
    WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
    GROUP BY ths_code
  )
  WHERE trade_days >= 3
)
SELECT * FROM avg_close_cte
```

**Item 6**：两个 CTE 子查询互相联结（各自内层预处理 + 外层再过滤）

```json
{
  "with": [
    {
      "name": "cbond_aaa",
      "table": {
        "table": "cbond.cbond_basic_info",
        "columns": ["ths_code", "issue_total_amt"],
        "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
      },
      "filters": [{"column": "ths_code", "op": "LIKE", "value": "11%"}]
    },
    {
      "name": "recent_quote",
      "table": {
        "table": "cbond.cbond_daily_quote_market",
        "columns": ["ths_code", "date", "close"],
        "start_time": "-604800",
        "end_time": "schedule_now"
      },
      "filters": [{"column": "close", "op": ">", "value": 0}]
    }
  ],
  "sources": ["cbond_aaa"],
  "join": [{"table": "recent_quote", "type": "INNER", "on": "cbond_aaa.ths_code = recent_quote.ths_code"}]
}
```

```sql
WITH cbond_aaa AS (
  SELECT * FROM (
    SELECT issue_total_amt, ths_code FROM cbond.cbond_basic_info WHERE issue_credit_rating = 'AAA'
  )
  WHERE ths_code LIKE '11%'
),
recent_quote AS (
  SELECT * FROM (
    SELECT close, date, ths_code FROM cbond.cbond_daily_quote_market
    WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
  )
  WHERE (CAST(date AS DATE) > '1969-12-31' AND CAST(date AS DATE) <= '2026-03-02') AND close > 0
)
SELECT * FROM cbond_aaa
INNER JOIN recent_quote ON cbond_aaa.ths_code = recent_quote.ths_code
```

> **注**：当 CTE 的 `table` 为 dict 且外层 CTE 定义中未显式设置 `start_time`/`end_time` 时，系统会对外层包装注入默认时间范围（`start_time` 默认 `earliest` → `1969-12-31`，`end_time` 默认 `schedule_now`）。这是框架的既定行为。

---

## sampling.json — 时序采样

对高频数据按固定时间间隔采样，每个窗口取第一条（正向）或最后一条（反向）记录。

**Item 1**：正向采样，每 5 分钟取第一条

```json
{
  "sources": ["cbond.stock_hf_1min_ror"],
  "start_time": "-3600",
  "end_time": "schedule_now",
  "sampling": {"interval": "5m"}
}
```

```sql
SELECT * FROM cbond.stock_hf_1min_ror
WHERE time > '2026-03-02 14:30:00' AND time <= '2026-03-02 15:30:00'
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '5' MINUTE)
  ORDER BY time ASC
) = 1
ORDER BY time ASC
```

**Item 2**：反向采样，每 5 分钟取最后一条（`interval` 以 `-` 开头）

```json
{"sampling": {"interval": "-5m"}}
```

```sql
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '5' MINUTE)
  ORDER BY time DESC
) = 1
ORDER BY time ASC
```

**Item 3**：每 1 小时采样，2小时范围

```json
{
  "sources": ["cbond.cbond_hf_1min_market"],
  "start_time": "-7200",
  "end_time": "schedule_now",
  "sampling": {"interval": "1h"}
}
```

```sql
SELECT * FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 13:30:00' AND time <= '2026-03-02 15:30:00'
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '1' HOUR)
  ORDER BY time ASC
) = 1
ORDER BY time ASC
```

**Item 4**：每 30 秒采样，30分钟范围

```json
{
  "start_time": "-1800",
  "sampling": {"interval": "30s"}
}
```

```sql
SELECT * FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 15:00:00' AND time <= '2026-03-02 15:30:00'
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '30' SECOND)
  ORDER BY time ASC
) = 1
ORDER BY time ASC
```

> 采样间隔支持：`s`（秒）、`m`（分钟）、`h`（小时）。

---

## drop_duplicate.json — 去重

基于主键（时间字段 + 标的代码）去重，保留 `create_time` 最新的一条记录。

**Item 1**：SELECT * 去重

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "drop_duplicate": true
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

**Item 2**：更长时间范围去重

```json
{
  "start_time": "-2592000",
  "end_time": "schedule_now",
  "drop_duplicate": true
}
```

```sql
WHERE CAST(date AS DATE) > '2026-01-09' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

**Item 3**：指定列 + 去重

```json
{
  "columns": ["ths_code", "date", "close"],
  "drop_duplicate": true
}
```

```sql
SELECT close, date, ths_code FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

---

## filters_subquery.json — 子查询过滤（IN / NOT IN）

在 `filters` 中使用子查询作为 `value`，实现基于另一张表的条件过滤。

> **注意**：若子查询的表有时间字段，子查询会自动补全主键（时间 + 标的代码）。为确保 IN 子查询只输出一列，需在子查询配置中加 `"group_by"` 来抑制主键自动补全。

**Item 1**：IN 子查询（静态表，无主键自动补全问题）

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "filters": [
    {
      "column": "ths_code",
      "op": "IN",
      "value": {
        "table": "cbond.cbond_basic_info",
        "columns": ["ths_code"],
        "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
      }
    }
  ]
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
  AND ths_code IN (
    SELECT ths_code FROM cbond.cbond_basic_info WHERE issue_credit_rating = 'AAA'
  )
```

**Item 2**：NOT IN 子查询（时序表，需加 `group_by` 抑制主键补全）

```json
{
  "sources": ["cbond.cbond_basic_info"],
  "filters": [
    {
      "column": "ths_code",
      "op": "NOT IN",
      "value": {
        "table": "cbond.stock_daily_quotes_non_ror",
        "columns": ["ths_code"],
        "group_by": ["ths_code"],
        "start_time": "-604800",
        "end_time": "schedule_now",
        "filters": [{"column": "close", "op": ">", "value": 200}]
      }
    }
  ]
}
```

```sql
SELECT * FROM cbond.cbond_basic_info
WHERE NOT (ths_code IN (
  SELECT ths_code FROM cbond.stock_daily_quotes_non_ror
  WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
    AND close > 200
  GROUP BY ths_code
))
```

**Item 3**：带时间过滤的主表 + IN 子查询

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "filters": [
    {
      "column": "ths_code",
      "op": "IN",
      "value": {
        "table": "cbond.cbond_basic_info",
        "columns": ["ths_code"],
        "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
      }
    }
  ]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
  AND ths_code IN (
    SELECT ths_code FROM cbond.cbond_basic_info WHERE issue_credit_rating = 'AAA'
  )
```

**Item 4**：NOT IN 子查询（静态表）

```json
{
  "column": "ths_code",
  "op": "NOT IN",
  "value": {
    "table": "cbond.cbond_basic_info",
    "columns": ["ths_code"],
    "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AA-'"}]
  }
}
```

```sql
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
  AND NOT (ths_code IN (
    SELECT ths_code FROM cbond.cbond_basic_info WHERE issue_credit_rating = 'AA-'
  ))
```

> **ClickHouse 限制**：ClickHouse 25.3 不支持关联子查询（EXISTS 中引用外层表），请使用等价的 IN / NOT IN 替代。

---

## combinations.json — 综合示例

综合展示多种特性组合使用的场景。

**Item 1**：多条件过滤（IN 列表 + 数值过滤）

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-2592000",
  "end_time": "schedule_now",
  "filters": [
    {"column": "ths_code", "op": "IN", "value": ["110001.SH", "110002.SH"]},
    {"column": "close", "op": ">", "value": 100}
  ]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE ((CAST(date AS DATE) > '2026-01-09' AND CAST(date AS DATE) <= '2026-03-02')
  AND ths_code IN ('110001.SH', '110002.SH'))
  AND close > 100
```

**Item 2**：GROUP BY + HAVING

```json
{
  "columns": ["ths_code", "AVG(close) AS avg_close", "COUNT(*) AS trade_days"],
  "group_by": ["ths_code"],
  "having": [{"column": "trade_days", "op": ">=", "value": 5}]
}
```

```sql
SELECT AVG(close) AS avg_close, COUNT(*) AS trade_days, ths_code
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-01-09' AND CAST(date AS DATE) <= '2026-03-02'
GROUP BY ths_code
HAVING trade_days >= 5
```

**Item 3**：LEFT JOIN + WHERE 过滤

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "join": [{"table": "cbond.cbond_basic_info", "type": "LEFT", "on": "stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code"}],
  "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
LEFT JOIN cbond.cbond_basic_info
  ON stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code
WHERE (CAST(stock_daily_quotes_non_ror.date AS DATE) > '2026-02-11'
  AND CAST(stock_daily_quotes_non_ror.date AS DATE) <= '2026-03-02')
  AND issue_credit_rating = 'AAA'
```

**Item 4**：JOIN + GROUP BY + HAVING

```json
{
  "columns": ["cbond_basic_info.issue_credit_rating", "COUNT(*) AS cnt", "AVG(close) AS avg_price"],
  "join": [{"table": "cbond.cbond_basic_info", "type": "LEFT", "on": "..."}],
  "group_by": ["cbond_basic_info.issue_credit_rating"],
  "having": [{"column": "cnt", "op": ">", "value": 100}]
}
```

```sql
SELECT AVG(close) AS avg_price, COUNT(*) AS cnt, cbond_basic_info.issue_credit_rating
FROM cbond.stock_daily_quotes_non_ror
LEFT JOIN cbond.cbond_basic_info ON stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code
WHERE CAST(stock_daily_quotes_non_ror.date AS DATE) > '2026-02-11'
  AND CAST(stock_daily_quotes_non_ror.date AS DATE) <= '2026-03-02'
GROUP BY cbond_basic_info.issue_credit_rating
HAVING cnt > 100
```

**Item 5**：CTE + WHERE 过滤

```json
{
  "with": [{"name": "bond_info", "table": "cbond.cbond_basic_info", "columns": ["ths_code", "issue_credit_rating", "issue_total_amt"]}],
  "sources": ["bond_info"],
  "filters": [{"column": "issue_credit_rating", "op": "=", "value": "'AAA'"}]
}
```

```sql
WITH bond_info AS (
  SELECT issue_credit_rating, issue_total_amt, ths_code FROM cbond.cbond_basic_info
)
SELECT * FROM bond_info WHERE issue_credit_rating = 'AAA'
```

**Item 6**：CTE + 主表 + JOIN CTE

```json
{
  "with": [{"name": "bond_info", "table": "cbond.cbond_basic_info", "columns": ["ths_code", "issue_credit_rating"]}],
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "join": [{"table": "bond_info", "type": "LEFT", "on": "stock_daily_quotes_non_ror.ths_code = bond_info.ths_code"}]
}
```

```sql
WITH bond_info AS (
  SELECT issue_credit_rating, ths_code FROM cbond.cbond_basic_info
)
SELECT * FROM cbond.stock_daily_quotes_non_ror
LEFT JOIN bond_info ON stock_daily_quotes_non_ror.ths_code = bond_info.ths_code
WHERE CAST(stock_daily_quotes_non_ror.date AS DATE) > '2026-02-11'
  AND CAST(stock_daily_quotes_non_ror.date AS DATE) <= '2026-03-02'
```

**Item 7**：采样 + IN 过滤

```json
{
  "sources": ["cbond.stock_hf_1min_ror"],
  "start_time": "-3600",
  "end_time": "schedule_now",
  "sampling": {"interval": "5m"},
  "filters": [{"column": "ths_code", "op": "IN", "value": ["110001.SH", "110002.SH"]}]
}
```

```sql
SELECT * FROM cbond.stock_hf_1min_ror
WHERE (time > '2026-03-02 14:30:00' AND time <= '2026-03-02 15:30:00')
  AND ths_code IN ('110001.SH', '110002.SH')
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '5' MINUTE)
  ORDER BY time ASC
) = 1
ORDER BY time ASC
```

**Item 8**：指定列 + 去重

```json
{
  "columns": ["ths_code", "date", "close"],
  "drop_duplicate": true
}
```

```sql
SELECT close, date, ths_code FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

**Item 9**：JOIN + GROUP BY + HAVING + LIMIT 全组合

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-2592000",
  "end_time": "schedule_now",
  "columns": ["cbond_daily_quote_market.ths_code", "cbond_basic_info.issue_credit_rating", "AVG(close) AS avg_close", "COUNT(*) AS trade_days"],
  "join": [{"table": "cbond.cbond_basic_info", "type": "LEFT", "on": "cbond_daily_quote_market.ths_code = cbond_basic_info.ths_code"}],
  "filters": [{"column": "cbond_basic_info.issue_credit_rating", "op": "=", "value": "'AAA'"}],
  "group_by": ["cbond_daily_quote_market.ths_code", "cbond_basic_info.issue_credit_rating"],
  "having": [
    {"column": "trade_days", "op": ">=", "value": 5},
    {"column": "avg_close", "op": ">", "value": 100}
  ],
  "limit": 50
}
```

```sql
SELECT AVG(close) AS avg_close, COUNT(*) AS trade_days,
       cbond_basic_info.issue_credit_rating, cbond_daily_quote_market.ths_code
FROM cbond.cbond_daily_quote_market
LEFT JOIN cbond.cbond_basic_info
  ON cbond_daily_quote_market.ths_code = cbond_basic_info.ths_code
WHERE (CAST(cbond_daily_quote_market.date AS DATE) > '2026-01-09'
  AND CAST(cbond_daily_quote_market.date AS DATE) <= '2026-03-02')
  AND cbond_basic_info.issue_credit_rating = 'AAA'
GROUP BY cbond_daily_quote_market.ths_code, cbond_basic_info.issue_credit_rating
HAVING trade_days >= 5 AND avg_close > 100
LIMIT 50
```

**Item 10**：`drop_duplicate` + `filters`

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "drop_duplicate": true,
  "filters": [{"column": "close", "op": ">", "value": 100}]
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
  AND close > 100
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

**Item 11**：`drop_duplicate` + JOIN 静态表

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "drop_duplicate": true,
  "join": [{"table": "cbond.cbond_basic_info", "type": "LEFT", "on": "stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code"}]
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
LEFT JOIN cbond.cbond_basic_info
  ON stock_daily_quotes_non_ror.ths_code = cbond_basic_info.ths_code
WHERE CAST(stock_daily_quotes_non_ror.date AS DATE) > '2026-02-11'
  AND CAST(stock_daily_quotes_non_ror.date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

**Item 12**：`drop_duplicate` + JOIN 时序表（两张表均有 `date` 字段）

```json
{
  "sources": ["cbond.cbond_daily_quote_market"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "drop_duplicate": true,
  "join": [{"table": "cbond.cbond_daily_terms", "type": "LEFT", "on": "cbond_daily_quote_market.ths_code = cbond_daily_terms.ths_code AND cbond_daily_quote_market.date = cbond_daily_terms.date"}]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
LEFT JOIN cbond.cbond_daily_terms
  ON cbond_daily_quote_market.ths_code = cbond_daily_terms.ths_code
  AND cbond_daily_quote_market.date = cbond_daily_terms.date
WHERE CAST(cbond_daily_quote_market.date AS DATE) > '2026-02-11'
  AND CAST(cbond_daily_quote_market.date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

> QUALIFY 中的裸列名 `date`、`ths_code` 在 JOIN 场景下 ClickHouse 会优先解析为左表（主表）字段，无需手动加表前缀。

**Item 13**：`drop_duplicate` + 指定列 + `order_by` + `limit`

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "columns": ["ths_code", "date", "close"],
  "drop_duplicate": true,
  "order_by": [{"column": "close", "direction": "DESC"}],
  "limit": 100
}
```

```sql
SELECT close, date, ths_code FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
ORDER BY close DESC
LIMIT 100
```

**Item 14**：`drop_duplicate` + `sampling`（内层去重、外层采样）

```json
{
  "sources": ["cbond.stock_hf_1min_ror"],
  "start_time": "-3600",
  "end_time": "schedule_now",
  "drop_duplicate": true,
  "sampling": {"interval": "5m"}
}
```

```sql
SELECT * FROM (
  SELECT * FROM cbond.stock_hf_1min_ror
  WHERE time > '2026-03-02 14:30:00' AND time <= '2026-03-02 15:30:00'
  QUALIFY row_number() OVER (PARTITION BY time, ths_code ORDER BY create_time DESC) = 1
)
QUALIFY row_number() OVER (
  PARTITION BY toStartOfInterval(time, INTERVAL '5' MINUTE)
  ORDER BY time ASC
) = 1
ORDER BY time ASC
```

> 系统自动将去重查询包装为子查询，外层再应用采样 QUALIFY，两者完全兼容。

**Item 15**：`drop_duplicate` + `qualify`（两个 QUALIFY 条件 AND 合并）

```json
{
  "sources": ["cbond.stock_daily_quotes_non_ror"],
  "start_time": "-604800",
  "end_time": "schedule_now",
  "drop_duplicate": true,
  "qualify": "row_number() OVER (PARTITION BY ths_code ORDER BY close DESC) <= 3"
}
```

```sql
SELECT * FROM cbond.stock_daily_quotes_non_ror
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
QUALIFY row_number() OVER (PARTITION BY ths_code ORDER BY close DESC) <= 3
    AND row_number() OVER (PARTITION BY date, ths_code ORDER BY create_time DESC) = 1
```

> `qualify` 与 `drop_duplicate` 的条件以 `AND` 合并为单个 QUALIFY 子句，两个条件同时生效。

---

## expressions.json — 列表达式与嵌套函数

展示 `columns`、`filters`、`group_by`、`order_by`、`having` 中使用函数、算术运算符和嵌套表达式的各种写法。

**Item 1**：列别名（`column` + `name`）

```json
{
  "columns": [
    "ths_code",
    "date",
    {"column": "close",     "name": "closing_price"},
    {"column": "volume",    "name": "vol"},
    {"column": "avg_price", "name": "vwap"}
  ]
}
```

```sql
SELECT date, ths_code, close AS closing_price, volume AS vol, avg_price AS vwap
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 2**：单参数函数（`toFloat64`、`abs`）

```json
{
  "columns": [
    "ths_code",
    "date",
    {"func": "toFloat64", "column": "close", "name": "close_f"},
    {"func": "abs",       "column": "close", "name": "abs_close"}
  ]
}
```

```sql
SELECT date, ths_code, toFloat64(close) AS close_f, abs(close) AS abs_close
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 3**：二元算术运算符（`-` / `+` / `*`）

```json
{
  "columns": [
    "ths_code", "date", "close",
    {"func": "-", "column": ["close", "pre_close"], "name": "price_change"},
    {"func": "+", "column": ["high", "low"],         "name": "hl_sum"},
    {"func": "*", "column": ["close", "volume"],     "name": "close_vol"}
  ]
}
```

```sql
SELECT close, date, ths_code,
       close - pre_close AS price_change,
       high + low AS hl_sum,
       close * volume AS close_vol
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 4**：嵌套表达式（`round(amount / volume)`、`toFloat64(close - pre_close)`）

```json
{
  "columns": [
    "ths_code", "date",
    {"func": "round",     "column": {"func": "/", "column": ["amount", "volume"]}, "name": "vwap"},
    {"func": "toFloat64", "column": {"func": "-", "column": ["close", "pre_close"]}, "name": "chg_f"}
  ]
}
```

```sql
SELECT date, ths_code, round(amount / volume) AS vwap, toFloat64(close - pre_close) AS chg_f
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

**Item 5**：三层嵌套 `round((close - pre_close) / pre_close * 100, 4)`

```json
{
  "func": "round",
  "column": [
    {"func": "*", "column": [
      {"func": "/", "column": [
        {"func": "-", "column": ["close", "pre_close"]},
        "pre_close"
      ]},
      100
    ]},
    4
  ],
  "name": "pct_chg"
}
```

```sql
SELECT close, date, pre_close, ths_code,
       round(close - pre_close / pre_close * 100, 4) AS pct_chg
FROM cbond.cbond_daily_quote_market
WHERE CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02'
```

> **注意**：sqlglot 渲染嵌套算术时依赖 SQL 运算符优先级，不会自动为低优先级的子表达式补全括号。上例中配置意图是 `((close - pre_close) / pre_close) * 100`，但渲染输出为 `close - pre_close / pre_close * 100`（按 SQL 优先级解析为 `close - (pre_close / pre_close * 100)`）。当表达式中存在减法/加法与乘法/除法混合嵌套时，建议改用字符串列名直接写完整 SQL 表达式（如 `"(close - pre_close) / pre_close * 100"`）以确保运算顺序正确。

**Item 6**：`filters` 中使用函数表达式列（`toDate(time) = toDate(now())`）

```json
{
  "filters": [
    {"column": {"func": "toDate", "column": "time"}, "op": "=", "value": "toDate(now())"},
    {"column": "close", "op": ">", "value": 0}
  ]
}
```

```sql
SELECT * FROM cbond.cbond_hf_1min_market
WHERE ((time > '2026-03-02 13:30:00' AND time <= '2026-03-02 15:30:00')
  AND toDate(time) = toDate(now())) AND close > 0
```

**Item 7**：多列元组 IN `(ths_code, date) IN (...)`

```json
{
  "filters": [
    {"column": ["ths_code", "date"], "op": "IN",
     "value": [["110001.SH", "2026-03-03"], ["110002.SH", "2026-03-03"]]}
  ]
}
```

```sql
SELECT * FROM cbond.cbond_daily_quote_market
WHERE (CAST(date AS DATE) > '2026-02-11' AND CAST(date AS DATE) <= '2026-03-02')
  AND (ths_code, date) IN (('110001.SH', '2026-03-03'), ('110002.SH', '2026-03-03'))
```

**Item 8**：`group_by` 中使用表达式 dict（`toDate(time)`）

```json
{
  "columns": [
    {"func": "toDate", "column": "time", "name": "dt"},
    "ths_code",
    {"func": "avg", "column": {"func": "toFloat64", "column": "close"}, "name": "avg_close"},
    {"func": "max", "column": {"func": "toFloat64", "column": "high"},  "name": "max_high"}
  ],
  "group_by": [
    {"func": "toDate", "column": "time"},
    "ths_code"
  ]
}
```

```sql
SELECT ths_code, toDate(time) AS dt, avg(toFloat64(close)) AS avg_close, max(toFloat64(high)) AS max_high
FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 13:30:00' AND time <= '2026-03-02 15:30:00'
GROUP BY toDate(time), ths_code
```

**Item 9**：`order_by` 中使用表达式 dict（`toDate(time) DESC`）

```json
{
  "columns": ["ths_code", "time", "close"],
  "order_by": [
    {"column": {"func": "toDate", "column": "time"}, "direction": "DESC"},
    {"column": "ths_code", "direction": "ASC"},
    {"column": "close",    "direction": "DESC"}
  ],
  "limit": 100
}
```

```sql
SELECT close, ths_code, time FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 14:30:00' AND time <= '2026-03-02 15:30:00'
ORDER BY toDate(time) DESC, ths_code ASC, close DESC
LIMIT 100
```

**Item 10**：`having` 中使用聚合列过滤

```json
{
  "columns": [
    {"func": "toDate", "column": "time", "name": "dt"},
    "ths_code",
    {"func": "avg",   "column": {"func": "toFloat64", "column": "close"}, "name": "avg_close"},
    {"func": "count", "column": "*", "name": "bar_count"}
  ],
  "group_by": [{"func": "toDate", "column": "time"}, "ths_code"],
  "having": [{"column": "bar_count", "op": ">", "value": 2}]
}
```

```sql
SELECT ths_code, toDate(time) AS dt, avg(toFloat64(close)) AS avg_close, count(*) AS bar_count
FROM cbond.cbond_hf_1min_market
WHERE time > '2026-03-02 13:30:00' AND time <= '2026-03-02 15:30:00'
GROUP BY toDate(time), ths_code
HAVING bar_count > 2
```

---

## 常见注意事项

1. **字符串值需含引号**：过滤条件中字符串标量值需写成 `"'AAA'"` 形式（外层双引号是 JSON，内层单引号是 SQL）。
2. **IN 子查询需控制列数**：IN 子查询的 `columns` 应只包含一列。若子查询来自时序表，必须加 `"group_by"` 防止系统自动补全时间主键导致多列输出。
3. **JOIN 场景下的显式列**：有 JOIN 时若需指定 `columns`，建议同时指定 `group_by`，避免系统自动补全的裸列名与 JOIN 表产生歧义。
4. **GROUP BY 抑制主键补全**：指定 `group_by` 后，系统不会自动将时间/标的主键补入 SELECT，`columns` 即为最终 SELECT 列。
5. **多列 IN**：`column` 字段支持列表格式，如 `"column": ["ths_code", "date"]`，生成 `(ths_code, date) IN (...)`。
6. **`drop_duplicate` 与其他 QUALIFY 类功能的组合行为**：
   - 与 `sampling` 同时使用：系统自动将去重查询包装为子查询，外层再应用采样 QUALIFY，两者完全兼容。
   - 与 `qualify` 同时使用：sqlglot 将两个 QUALIFY 条件以 `AND` 合并为单个 QUALIFY 子句，两个条件同时生效。
   - 与 `group_by` 同时使用：语义矛盾（聚合 vs 行级去重），不应组合。
