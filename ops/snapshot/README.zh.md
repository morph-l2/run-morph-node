# Snapshot 自动化

> English version: [README.md](./README.md)

每两周自动制作一次节点 snapshot，并将相关参数同步到 README.md 供用户下载使用。

## 背景

手动制作 snapshot 流程繁琐且容易遗漏，本方案通过服务器 cron 定时任务和 GitHub REST API 将全流程自动化，无需 GitHub Actions 或 git CLI。

## 目录结构

```
run-morph-node/
├── README.md                         # snapshot 表格在此更新
└── ops/snapshot/
    ├── README.md                     # 英文文档
    ├── README.zh.md                  # 本文档
    ├── snapshot.env.example          # 环境变量模板（每个环境复制一份填写）
    ├── snapshot_make.py              # 入口：停服 → 制作 → 上传 → 重启 → 更新 README
    ├── update_metadata.py            # 查询 indexer API 并编排完整更新流程
    ├── update_readme.py              # 纯表格更新逻辑（由 update_metadata.py 调用）
    └── metrics_server.py             # 常驻 HTTP server，在 :6060/metrics 暴露 metrics
```

## 完整流程

```
服务器 cron 定时任务（每月 1 日 / 15 日）
        │
        ▼
  ops/snapshot/snapshot_make.py
    [1] 停止 morph-node、morph-geth
    [2] 制作快照（tar geth + node 数据）
    [3] 上传至 S3
    [4] 重启 morph-geth → 等待 RPC 就绪 → 采集 base_height
    [5] 重启 morph-node
    [6] 调用 update_metadata.py
        │  BASE_HEIGHT, SNAPSHOT_NAME
        ▼
  python3 update_metadata.py
  ┌─────────────────────────────────────────────────────┐
  │ 1. 调用内网 explorer-indexer API：                  │
  │    GET /v1/batch/l1_msg_start_height/<base_height>  │
  │    GET /v1/batch/derivation_start_height/<base_height>│
  │ 2. 通过 GitHub API 获取 README.md 当前内容          │
  │ 3. 在内存中插入新快照记录到表格顶部                  │
  │ 4. 通过 GitHub API 建新分支并推送更新后的文件        │
  │ 5. 通过 GitHub API 开启 PR                          │
  └─────────────────────────────────────────────────────┘
```

## 触发方式

| 方式 | 说明 |
|---|---|
| 定时 | 服务器 cron，每月 1 日和 15 日自动执行 |
| 手动 | SSH 登录服务器，直接执行 `snapshot_make.py` |

## 多环境支持

| 环境 | Indexer API（内网） |
|---|---|
| mainnet | `explorer-indexer.morphl2.io` |
| hoodi | `explorer-indexer-hoodi.morphl2.io` |
| holesky | `explorer-indexer-holesky.morphl2.io` |

每个环境 / 快照类型有独立的 env 文件，通过 `ENV_FILE` 环境变量指定。S3 路径和 README 表格自动按环境区分。

## 部署步骤

### 1. 在节点服务器上克隆仓库

```bash
git clone https://github.com/morph-l2/run-morph-node.git /data/run-morph-node
```

### 2. 创建环境变量文件

在脚本同级目录复制模板并填写对应值：

```bash
cd /data/run-morph-node/ops/snapshot
cp snapshot.env.example snapshot.env
# 编辑 snapshot.env，填写 GH_TOKEN、S3_BUCKET、ENVIRONMENT 等
```

多个环境或快照类型各自使用独立的 env 文件：

```bash
cp snapshot.env.example snapshot-hoodi.env
cp snapshot.env.example snapshot-mainnet-mpt.env
```

所有可配置变量及其说明见 [`snapshot.env.example`](./snapshot.env.example)。这些文件**不可提交到 git**（在 `.gitignore` 中添加 `*.env`）。

同时建议在 repo Settings → General 中开启 **"Automatically delete head branches"**，PR merge 后分支自动删除，无需手动维护。

### 3. 配置定时任务（PM2）

复制 ecosystem 模板，修改 `ENV_FILE` 和 `script` 路径后启动：

```bash
cp /data/run-morph-node/ops/snapshot/ecosystem.config.js.example /data/morph-hoodi/ecosystem.config.js
# 编辑 ecosystem.config.js
```

启动并持久化：

```bash
pm2 start /data/morph-hoodi/ecosystem.config.js
pm2 save
```

手动触发测试：

```bash
pm2 restart snapshot-hoodi
pm2 logs snapshot-hoodi
```

### 4. 启动 metrics server

在节点服务器上用 pm2 托管 `metrics_server.py`，使其随机器重启自动恢复：

```bash
pm2 startup          # 将 pm2 自身注册为系统开机服务（仅需执行一次）
pm2 start python3 --name morph-snapshot-metrics -- /data/run-morph-node/ops/snapshot/metrics_server.py
pm2 save
```

启动后采集侧即可通过 `http://<server-ip>:6060/metrics` 拉取指标。

暴露的 metrics：

| Metric | 类型 | 说明 |
|---|---|---|
| `morph_snapshot_readme_update_status` | gauge | 1 = 成功，0 = 失败 |
| `morph_snapshot_readme_update_timestamp_seconds` | gauge | 最后一次执行的 Unix 时间戳 |

Labels：`environment`（mainnet / hoodi / holesky）、`snapshot`（快照名称）

> 默认 metrics 文件路径：`/tmp/morph_snapshot_metrics.prom`
> 如需修改，通过环境变量 `METRICS_FILE` 统一传入（对 `update_readme.py` 和 `metrics_server.py` 同时生效）。

## 关键设计决策

- **base_height 在 geth 重启后采集**：snapshot 制作完成、geth 单独启动后再查询 RPC，读取的是 snapshot 实际对应的区块状态，比停止前采集更准确。morph-node 在确认高度后再启动。
- **失败时兜底恢复**：`snapshot_make.py` 在异常时尝试拉起两个进程，避免服务持续中断。
- **不依赖 GitHub Actions 和 git CLI**：`update_metadata.py` 直接调用 GitHub REST API，服务器只需要 Python 3，`GH_TOKEN` 是唯一需要的凭证。
- **新记录插入表格顶部**：最新 snapshot 始终出现在表格第一行，便于用户快速找到。
- **通过 PR 而非直接 push 合并变更**：创建新分支并开启 PR，保留 review 机会，避免自动化脚本直接写入 main 分支。
- **每个环境 / 类型独立 env 文件**：通过 `ENV_FILE` 环境变量指定，各配置互不干扰，同一台机器可以跑多种 snapshot 类型。
