登录界面已改好：每种成员类型需要**专属密码**才能登录。

## 成员密码对照表

| 成员类型 | 密码 | 权限 |
|---------|------|------|
| 普通员工 `employee` | `emp@2026` | 公共文档 |
| HR 经理 `hr_manager` | `hr@2026` | HR + 公共 |
| 财务 `finance` | `fin@2026` | 财务 + 公共 |
| 市场 `marketing` | `mkt@2026` | 市场 + 公共 |
| 工程 `engineering` | `eng@2026` | 工程 + 公共 |
| 高管 `c_level` | `ceo@2026` | 全部部门 |

## 登录方式

1. 填写 **用户 ID**（任意，如 `user001`）
2. 选择 **成员类型**
3. 输入该类型对应的 **专属密码**
4. 密码与成员类型不匹配会提示错误

## 改动文件

- `finbot-frontend/lib/memberCredentials.ts` — 成员密码配置
- `finbot-frontend/components/loginModal.tsx` — 登录界面与校验
- `finbot-frontend/components/LoginModal.module.css` — 样式

重启前端后生效（或重新运行 `python main.py`）。若要改密码，编辑 `memberCredentials.ts` 即可。