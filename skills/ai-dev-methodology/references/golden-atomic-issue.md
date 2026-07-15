# Golden Atomic Issue Example

```markdown
# T012: 为 Connector Template match API 增加最终路径回归测试

> 本 issue 可直接派发。worker 只需读取本 issue 和列出的文件路径，不需要完整读取 `proposal/spec/plan`。

## 目标

证明前端可见的模板匹配接口注册为 `/api/v1/connect/templates:match`，并防止退化成 `/api/v1/connect/templates/:match`。本任务关闭 REQ-005 和 C-002 中的 API route 契约。

## 范围

| In scope | Out of scope |
|---|---|
| 为精确 match URL 增加 controller route 回归测试。 | 不修改模板匹配 service 语义。 |
| 验证未登录请求命中路由并返回鉴权错误，而不是 404。 | 不搭建完整登录态 E2E。 |

## 来源上下文

| Source | Required excerpt / meaning |
|---|---|
| REQ-005 | 用户在选择 `connectorClass + version` 后，通过 `GET /connect/templates:match?connectorClass=&version=` 获取匹配模板。 |
| C-002 | 前端 selector 在 connector class 和 version 都已选择后调用 match API；API 失败不阻塞手工配置，但路由必须存在。 |
| API route contract | 最终外部 URL 带 `/api/v1` 前缀，`templates:match` 必须在同一个 path segment 中；`/templates/:match` 是错误路径。 |

## 模块契约闭包

| Item | Content |
|---|---|
| Primary module | Connect Template API route module |
| Module responsibility | 对外提供前端可调用的 template match HTTP route，并将请求路由到后端 match handler。 |
| Owned state/data/resources touched | 仅测试 route registration；不拥有业务数据。 |
| Consumed contracts assumed true | Security/auth filter 对未登录请求返回当前项目约定的鉴权错误；template match service 语义已由其他 issue 负责。 |
| Provided contracts implemented/preserved | C-002: `/api/v1/connect/templates:match` 路由存在，且不会误注册为 `/templates/:match`。 |
| Internal invariants | route regression test 不改变 controller/service 业务逻辑；只证明 URL 命中。 |

## 锁定决策

| Decision | Exact decision | Why it matters here |
|---|---|---|
| DEC-003 | Template version matching 的 source of truth 在后端。 | 测试必须命中后端 handler，不能依赖前端 fallback。 |

## 契约摘录

| Contract | Trigger | Normal path | Failure path | Consistency | Timing | Verification excerpt |
|---|---|---|---|---|---|---|
| C-002 | 前端已有 connector class 和 version。 | exact URL 到达 template controller match handler。 | 未登录请求返回鉴权错误；如果返回 404，说明路由注册错误。 | 前端 API client 和后端 controller 必须同意 exact path。 | connector class/version 变化后重新请求。 | MockMvc/WebMvcTest 访问 `/api/v1/connect/templates:match?...`，断言不是 404。 |

## 现有代码参考

| Pattern/reference | Exact path | What to follow | What not to inherit |
|---|---|---|---|
| Controller route test | `cmp/cmp-cmp-app/src/test/java/.../*Controller*Test.java` | 使用当前应用已有 Spring MVC route-level test 风格。 | 不做 full auth E2E。 |
| Controller under test | `cmp/cmp-cmp-app/src/main/java/.../controller/ConnectorTemplateController.java` | 验证最终 route registration。 | 不修改 business method 行为。 |

## 修改文件

| Path | Required change | Ownership / notes |
|---|---|---|
| `cmp/cmp-cmp-app/src/test/java/.../controller/ConnectorTemplateControllerMappingTest.java` | 新增 exact path 测试，覆盖 `/api/v1/connect/templates:match`。 | 如果已有同类 mapping test，则扩展现有文件；否则创建该文件。 |

## 行为细节

| Item | Detail |
|---|---|
| Inputs | GET `/api/v1/connect/templates:match?connectorClass=com.example.Connector&version=1.0.0`。 |
| Outputs | 未登录场景应返回鉴权错误或被安全链路拒绝，但不能是 404。 |
| Error behavior | 404 表示 controller path 注册错误，测试必须失败。 |
| State / persistence | 不读写 DB。 |
| Compatibility | 不改变现有 `/connect/templates` 其他接口。 |
| Boundary conditions | 负向保护 `/api/v1/connect/templates/:match` 不是目标路径；如测试框架不方便断言负向路径，至少在测试名/注释中锁定原因。 |

## 实现步骤

1. 创建或更新 `ConnectorTemplateControllerMappingTest`。
2. 使用 MockMvc/WebMvcTest 发起 GET `/api/v1/connect/templates:match?connectorClass=com.example.Connector&version=1.0.0`。
3. 断言响应状态不是 404；如果 security 生效，断言为当前项目约定的 auth/403/401。
4. 增加回归断言或测试说明，防止把 route 写成 `/api/v1/connect/templates/:match`。

## 验证

| Check | Command/manual step | Expected result | Proves | Failure meaning / Not Run risk |
|---|---|---|---|---|
| Controller route regression | `./mvnw -pl cmp/cmp-app -am -Dtest=ConnectorTemplateControllerMappingTest test` | 测试通过；exact `templates:match` URL 返回鉴权/handler 响应而不是 404。 | REQ-005, C-002, API route contract | 如果返回 404，说明前后端 exact route contract 破裂；不得合并。 |

## 禁止事项

- 不修改模板匹配业务逻辑。
- 不修改前端 API path。
- 不为了让测试通过而削弱鉴权。

## 完成标准

- [ ] exact route 测试存在。
- [ ] 验证命令通过。
- [ ] 测试失败能捕获 `/templates/:match` 路由注册错误。
- [ ] 本 issue 不依赖完整全局文档即可复现实现与验证。
```
