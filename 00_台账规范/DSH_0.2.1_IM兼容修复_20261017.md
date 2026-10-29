# DSH 0.2.1 与 dsh-im 兼容修复

> 时间：2026-10-17 21:06  
> 症状：微信发普通消息（含“你好”）返回 `INTERNAL_UNKNOWN`，提示“消息在提交前处理失败，尚未提交执行”；`/new`、`/help` 等本地命令正常。`/session` 绑定已有会话也返回“暂时无法绑定会话”。

## 原因

DSH 0.2.1 的 Typert 网关要求每个 Remote 请求携带调用方 Peer；`@xmanrui/dsh-im 4.39.0` 的 `remoteRequest()` 没有发送 `peer`，所以 `workspace.list`、`session.create`、`session.prompt` 等 Host API 调用在约 1ms 内被拒绝，插件将其归类为 `INTERNAL_UNKNOWN`。

上游修复：dsh-im PR #364
`fix: send the Host in-process Peer with every Remote request (DSH 0.2.1 compatibility)`

## 本地补丁内容

修改了已安装插件：

```text
~/.dsh/profiles/desktop/node_modules/@xmanrui/dsh-im/
├── lib/index.js
└── plugin-src/host/modern-harness-api.mjs
```

补丁逻辑：

1. 对每个 Host root 用 `ctx.connection.createPeer({ principal: { kind: 'owner' }, interactions: 'none' })` 创建进程内 Peer；
2. 在 `remoteRequest()` 中附带 `peer`；
3. `invoke` 与 `stream` 两条调用路径都带 peer；
4. 老 Host 没有 `createPeer` 时保持原请求形状。

备份：

```text
lib/index.js.bak-before-peer-fix
plugin-src/host/modern-harness-api.mjs.bak-before-peer-fix
```

## 生效方式

**需要完全重启 DSH 桌面应用**，Host 才会重新加载 `lib/index.js`。重启后在微信发送 `/session` 测试。

## 注意

- 上游 PR 尚未发布到 npm；如果以后升级 `@xmanrui/dsh-im`，先检查该修复是否已包含，否则补丁可能被覆盖。
- 若新版插件发布，优先使用官方版本，并重新验证微信普通消息、`/new`、`/session`、附件上传与文件回传。
