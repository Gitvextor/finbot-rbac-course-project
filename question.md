**推荐登录角色：`c_level`**（能访问所有部门文档，最容易答对）

下面按部门给你可直接复制的问题。用 **英文** 问更稳（路由和文档都是英文）。

---

## 工程 Engineering  
**角色：`c_level` 或 `engineering`**

| 你可以问 | 文档里有的内容 |
|---------|----------------|
| `What tech stack are we using for the backend?` | 微服务、React、PostgreSQL 等 |
| `Explain the CI/CD pipeline for the project` | SDLC、部署流程 |
| `How does the microservices setup work?` | 系统架构 |
| `What is the SLA for our API uptime?` | SLA 报告（如 Payment 99.989%） |
| `What is the software development lifecycle?` | SDLC 章节 |
| `What are the engineering sprint metrics for 2024?` | sprint 文档 |

---

## 财务 Finance  
**角色：`c_level` 或 `finance`**

| 你可以问 |
|---------|
| `What is the company's total revenue this quarter?` |
| `Show me the profit and loss statement` |
| `What is the operating budget for this year?` |
| `What are the key financial KPIs like profit margin and EBITDA?` |
| `What are the total expenses by department?` |

数据来源：`data/finance/` 下的 docx 报告。

---

## 市场 Marketing  
**角色：`c_level` 或 `marketing`**

| 你可以问 |
|---------|
| `What is marketing campaign performance?` |
| `How many leads were generated?` |
| `What is cost per lead?` |
| `What is campaign ROI?` |
| `Show social media engagement metrics` |

---

## 人力资源 HR  
**角色：`c_level` 或 `hr_manager`**

| 你可以问 |
|---------|
| `How many employees are in the Finance department?` |
| `How many employees are in Lucknow?` |
| `How many female employees are in HR?` |
| `What is the average salary for Senior HR Executives?` |
| `How many employees have performance rating above 4?` |

数据来源：`data/hr/hr_data.csv`（这类统计题效果最好）。

---

## 不建议这样问

| 问题类型 | 原因 |
|---------|------|
| `这是什么`、`你好` | 太模糊，容易路由失败或 off_topic |
| 天气、笑话、做饭 | 会被 off_topic 拦截 |
| 用 **`employee`** 角色 | 只能访问 `general`，而 general 里 PDF 被跳过，**几乎没有文档** |
| `What is the company vision and mission?`（general 类） | 目前 general 知识库基本为空，可能仍答不上 |

---

## 最快验证（复制即用）

1. 登录：**User ID** 随便填，**Role 选 `c_level`**
2. 先发：
   ```
   What is the SLA for our API uptime?
   ```
3. 再发：
   ```
   How many employees are in the Finance department?
   ```

第一次可能要等 1–2 分钟（建知识库），之后会变快。  
正常回答末尾会有 **Citations:** 和 `[Source 1 | 文件名 | ...]`。

---

**一句话：选 `c_level`，用英文问具体业务问题（SLA、财务、营销、HR 统计），不要选 `employee`，也不要问太模糊的中文。**