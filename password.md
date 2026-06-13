登录界面已改成公司 RBAC 演示账号：先选择身份，再输入该身份对应的账号和密码。账号不属于所选身份、密码错误、权限字段不匹配，都会拒绝登录。

## 演示账号

| 登录身份 | 账号 | 密码 | 可访问范围 |
|---------|------|------|------------|
| Executive 高管 | `ceo` | `password123` | 全公司资料、Risk Dashboard、文档验证 |
| HR 经理 | `hr_manager` | `password123` | HR 资料 + 公共资料 |
| Finance 财务 | `finance_manager` | `password123` | 财务资料 + 公共资料 |
| Engineering 工程 | `rd_director` | `password123` | 工程资料 + 公共资料 |
| Marketing 市场 | `marketing_manager` | `password123` | 市场资料 + 公共资料 |
| Employee 普通员工 | `employee_demo` | `password123` | 仅公共资料 |

## 演示方式

1. 在登录页选择一个身份，例如 `Finance 财务`。
2. 输入对应账号，例如 `finance_manager`。
3. 输入密码 `password123`。
4. 如果选择 `Finance 财务` 但输入 `employee_demo`，前端会在后端认证成功后继续校验身份并拒绝登录。
5. 如果密码输错，后端 `/api/auth/login` 会直接拒绝。
