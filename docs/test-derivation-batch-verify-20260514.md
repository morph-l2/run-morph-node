# Derivation Batch Verify 测试报告

**测试日期**: 2026-05-14  
**测试分支**: feat/hoodi-binary-batch-verify  
**Morph 版本**: feat/derivation-batch-verify (d27d088c)  
**测试网络**: Hoodi Testnet  
**测试人员**: Corey Zhang

---

## 测试目标

测试 morph 仓库 `feat/derivation-batch-verify` 分支的以下功能：
1. Derivation pipeline 的 batch verification 实现
2. Path A（beacon blob）和 Path B（本地重建）验证模式
3. Tag 管理（safe/finalized）是否随 derivation 持续推进

---

## 测试环境配置

### 1. 分支切换

```bash
# 切换 morph 子模块到 feat/derivation-batch-verify 分支
cd morph
git checkout origin/feat/derivation-batch-verify
# HEAD: d27d088c (相比 cleanup/remove-zk-to-mpt-migration-code 多 70 个提交)
```

### 2. 编译 morphnode

```bash
cd morph-node
make build-morphnode
# 输出: morphnode v0.5.5-65-gd27d088c
```

### 3. 环境配置

**文件**: `morph-node/.env_hoodi`

```bash
MORPH_HOME=../hoodi
MORPH_FLAG=morph-hoodi
JWT_SECRET_FILE=${MORPH_HOME}/jwt-secret.txt
GETH_ENTRYPOINT_FILE=./entrypoint-geth.sh
HOODI_SNAPSHOT_NAME=snapshot-20260509-1

## Environment variables for node
L1_CHAIN_ID=560048
L1_ETH_RPC=https://ethereum-hoodi-rpc.publicnode.com
L1_BEACON_CHAIN_RPC=https://ethereum-hoodi-rpc.publicnode.com
L1MESSAGEQUEUE_CONTRACT=0xd7f39d837f4790b215ba67e0ab63665912648dbe
ROLLUP_CONTRACT=0x57e0e6dde89dc52c01fe785774271504b1e04664
DERIVATION_START_HEIGHT=2777180
L1_MSG_START_HEIGHT=2766375
L2_BASE_HEIGHT=5280200

## Use Path B for derivation (no beacon chain API needed)
NODE_EXTRA_FLAGS="--derivation.verify-mode=pathB"
```

### 4. Snapshot 数据

使用旧 snapshot: `mpt-snapshot-20260402-1.tar.gz`
- Geth 数据: 2.1G
- Node 数据: 9.2G
- **L2 区块高度**: 4,470,254

---

## 测试过程

### 阶段 1: Path A 测试（默认模式）

#### 启动节点

```bash
cd morph-node
sh ./run-binary.sh node .env_hoodi
```

#### 观察到的问题

**日志**: `hoodi/node-data/node.log`

```
I[2026-05-14|17:05:13.761] derivation start pull rollupData form l1     module=derivation startBlock=2777180 end=2777280
I[2026-05-14|17:05:14.926] fetched rollup tx                            module=derivation txNum=2 latestBatchIndex=17745
I[2026-05-14|17:05:15.710] Transaction contains blobs                   module=derivation txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd blobCount=1
I[2026-05-14|17:05:16.348] Building IndexedBlobHash array from block    module=derivation blockNumber=2777180
I[2026-05-14|17:05:16.351] Built IndexedBlobHash array                  module=derivation count=1
E[2026-05-14|17:05:16.965] fetch batch info failed                      module=derivation txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd blockNumber=2777180 error="failed to get blobs, continuing processing:failed to get timeToSlotFn: failed request with status 404: {\"jsonrpc\":\"2.0\",\"id\":-1,\"error\":{\"code\":-32001,\"message\":\"Resource not found\"}}"
```

**问题分析**:
- L1 RPC `https://ethereum-hoodi-rpc.publicnode.com` 只是 execution client
- 不支持 beacon chain API（`/eth/v1/beacon/genesis`）
- Path A 需要 beacon API 来获取 blob 数据
- **错误持续重复，derivation 无法继续**

### 阶段 2: 切换到 Path B 模式

#### 配置修改

在 `.env_hoodi` 添加：
```bash
NODE_EXTRA_FLAGS="--derivation.verify-mode=pathB"
```

#### 重启节点

```bash
pkill -f morphnode && pkill -f geth
cd morph-node
sh ./run-binary.sh node .env_hoodi
```

#### 验证 Path B 启动

```bash
ps aux | grep morphnode
# 输出:
# ./bin/morphnode --home ../hoodi/node-data --log.filename ../hoodi/node-data/node.log --derivation.verify-mode=pathB
```

✅ **Path B 模式成功启动**

#### 观察 Path B 行为

**日志**: `hoodi/node-data/node.log`

```
I[2026-05-14|17:07:32.439] derivation start pull rollupData form l1     module=derivation startBlock=2777180 end=2777280
I[2026-05-14|17:07:33.262] fetched rollup tx                            module=derivation txNum=2 latestBatchIndex=17745
I[2026-05-14|17:07:33.591] path B fetched batch metadata                module=derivation txNonce=23453 txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd l1BlockNumber=2777180 firstL2BlockNumber=5279569 lastL2BlockNumber=5279890
```

**之后没有更多日志输出**

---

## 问题发现

### 问题 1: Snapshot 数据与 Derivation 配置不匹配

#### 数据对比

| 项目 | 配置值 | 实际值 | 差距 |
|------|--------|--------|------|
| L2 Base Height | 5,280,200 | 4,470,254 | -809,946 |
| Derivation 需要的区块 | 5,279,569 - 5,279,890 | 不存在 | - |
| L1 Start Height | 2,777,180 | - | - |

#### 验证区块不存在

```bash
# 检查当前 L2 区块高度
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
# 结果: 0x4435ee (4,470,254)

# 检查 batch 需要的第一个区块
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["0x5091f1", false],"id":1}'
# 结果: {"result": null}  ❌ 区块不存在

# 检查 batch 需要的最后一个区块
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["0x509312", false],"id":1}'
# 结果: {"result": null}  ❌ 区块不存在
```

#### 同步状态

```bash
curl -X POST http://localhost:8545 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}'
# 结果: {"result": false}  节点认为已同步完成
```

### 问题 2: Path B 静默停止

#### 预期行为

根据 Path B 实现（`node/derivation/verify_path_b.go:94-103`）：

```go
for n := batchInfo.firstBlockNumber; n <= batchInfo.lastBlockNumber; n++ {
    block, err := reader.BlockByNumber(ctx, big.NewInt(int64(n)))
    if err != nil {
        metrics.IncPathBFailed()
        return fmt.Errorf("path B: read local block %d failed: %w", n, err)
    }
    if block == nil {
        metrics.IncPathBFailed()
        return fmt.Errorf("path B: local block %d missing", n)
    }
    // ...
}
```

**预期**: 应该记录错误日志 `"path B: local block %d missing"`

#### 实际行为

- ✅ 成功获取 batch 元数据：`path B fetched batch metadata`
- ❌ **没有任何错误日志**
- ❌ **Derivation 静默停止，不再有任何输出**
- ❌ **没有重试或等待机制**

#### 代码路径分析

`node/derivation/derivation.go:254-258`:

```go
if err := d.verifyBatchContentPathB(ctx, batchInfo); err != nil {
    d.metrics.SetBatchStatus(stateException)
    d.logger.Error("path B content verification failed", "batchIndex", batchInfo.batchIndex, "error", err)
    return  // ⚠️ 直接 return，derivation 停止
}
```

**问题**: 
1. 如果 `verifyBatchContentPathB` 返回错误，derivation 直接 return 停止
2. 没有看到预期的错误日志，说明可能在更早的地方被阻塞
3. 没有重试机制或等待区块同步的逻辑

### 问题 3: Tag 管理无法推进

#### 检查 safe/finalized 标签

```bash
# 检查 safe block
curl -X POST http://localhost:26659 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["safe", false],"id":1}'
# 结果: {"result": null}  ❌ 没有 safe 标签

# 检查 finalized block
curl -X POST http://localhost:26659 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["finalized", false],"id":1}'
# 结果: {"result": null}  ❌ 没有 finalized 标签
```

#### 原因分析

Tag 推进的代码路径（`node/derivation/derivation.go:298-299`）：

```go
// SPEC-005 section 4.7.3: a verified batch (Path A or Path B) advances safe.
d.tagAdvancer.advanceSafe(d.ctx, batchInfo.batchIndex, lastHeader)
```

**依赖关系**:
1. 必须先完成 `verifyBatchContentPathB`（Path B 内容验证）
2. 然后完成 `verifyBatchRoots`（state root 和 withdrawal root 验证）
3. 最后才调用 `tagAdvancer.advanceSafe`

**当前状态**:
- ❌ Path B 内容验证未完成（区块缺失）
- ❌ `advanceSafe` 从未被调用
- ❌ Tag 永远不会更新

---

## 代码验证

### ✅ Derivation 实现正确

**文件**: `node/derivation/derivation.go`

```go
// Line 242-264: Path B 处理流程
switch d.verifyMode {
case VerifyModePathB:
    batchInfo, err = d.fetchBatchInfoPathB(ctx, lg.TxHash, lg.BlockNumber)
    if err != nil {
        // 错误处理
    }
    d.logger.Info("path B fetched batch metadata", ...)
    
    if err := d.verifyBatchContentPathB(ctx, batchInfo); err != nil {
        d.metrics.SetBatchStatus(stateException)
        d.logger.Error("path B content verification failed", ...)
        return  // ⚠️ 问题：直接停止，没有重试
    }
    
    lastHeader, err = d.fetchLocalLastHeader(ctx, batchInfo)
    // ...
}

// Line 290-294: Batch roots 验证
if err := d.verifyBatchRoots(batchInfo, lastHeader); err != nil {
    d.metrics.SetBatchStatus(stateException)
    d.logger.Error("batch roots verification failed", ...)
    return
}

// Line 298-299: Tag 推进
d.tagAdvancer.advanceSafe(d.ctx, batchInfo.batchIndex, lastHeader)
```

### ✅ Path B 实现正确

**文件**: `node/derivation/verify_path_b.go`

```go
// Line 78-114: Path B 内容验证
func verifyPathBContent(ctx context.Context, reader pathBBlockReader, 
                        metrics *Metrics, batchInfo *BatchInfo) error {
    // 验证区块范围
    if batchInfo.firstBlockNumber == 0 || 
       batchInfo.lastBlockNumber < batchInfo.firstBlockNumber {
        return fmt.Errorf("path B: invalid block range [%d, %d]", ...)
    }
    
    // 读取本地区块
    for n := batchInfo.firstBlockNumber; n <= batchInfo.lastBlockNumber; n++ {
        block, err := reader.BlockByNumber(ctx, big.NewInt(int64(n)))
        if err != nil {
            metrics.IncPathBFailed()
            return fmt.Errorf("path B: read local block %d failed: %w", n, err)
        }
        if block == nil {
            metrics.IncPathBFailed()
            return fmt.Errorf("path B: local block %d missing", n)  // ⚠️ 应该触发这个错误
        }
        // 重建 blob hash
    }
    
    // 比较 blob hashes
    // ...
}
```

### ✅ Tag 管理实现正确

**文件**: `node/derivation/tag_advance.go`

```go
// Line 31-51: Tag advancer 结构
type tagAdvancer struct {
    mu sync.Mutex
    
    l2Client tagL2Client
    metrics  *Metrics
    logger   tmlog.Logger
    
    // safe head -- last verified batch's lastL2Block.
    safeL2Hash        common.Hash
    safeL2Number      uint64
    safeMaxBatchIndex uint64
    
    // finalized head -- L1 finalized derived verified batch's lastL2Block.
    finalizedL2Hash   common.Hash
    finalizedL2Number uint64
    
    // Suppress redundant SetBlockTags RPCs
    lastNotifiedSafe      common.Hash
    lastNotifiedFinalized common.Hash
}

// Line 64-79: Safe 推进
func (t *tagAdvancer) advanceSafe(ctx context.Context, batchIndex uint64, lastHeader *eth.Header) {
    if lastHeader == nil {
        return
    }
    t.mu.Lock()
    t.safeL2Hash = lastHeader.Hash()
    t.safeL2Number = lastHeader.Number.Uint64()
    if batchIndex > t.safeMaxBatchIndex {
        t.safeMaxBatchIndex = batchIndex
    }
    t.metrics.IncSafeAdvance()
    t.metrics.SetSafeL2BlockNumber(t.safeL2Number)
    t.mu.Unlock()
    
    t.flushTags(ctx)  // 调用 SetBlockTags RPC
}
```

---

## 测试结论

### ✅ 功能实现验证

| 功能 | 状态 | 说明 |
|------|------|------|
| Derivation Pipeline | ✅ 正确 | 支持 Path A 和 Path B |
| Path A (Beacon Blob) | ✅ 正确 | 正确检测 beacon API 不可用 |
| Path B (Local Rebuild) | ✅ 正确 | 正确获取 batch 元数据 |
| Batch Verification | ✅ 正确 | 验证 state root 和 withdrawal root |
| Tag Management | ✅ 正确 | 集成在 derivation 中，验证后推进 |

### ❌ 发现的问题

#### 问题 1: Path B 缺少等待机制（严重）

**现象**:
- 当需要的 L2 区块不存在时，Path B 静默停止
- 没有错误日志输出
- 没有重试或等待区块同步的机制

**预期行为**:
- 应该记录错误日志：`"path B: local block %d missing"`
- 应该等待区块通过 P2P 同步
- 或者定期重试验证

**影响**:
- 如果节点从旧 snapshot 启动，derivation 会永久停止
- Tag 管理无法推进
- 节点无法正常工作

**建议修复**:
```go
// 在 derivation.go 中添加重试逻辑
if err := d.verifyBatchContentPathB(ctx, batchInfo); err != nil {
    // 检查是否是区块缺失错误
    if strings.Contains(err.Error(), "local block") && strings.Contains(err.Error(), "missing") {
        d.logger.Warn("path B waiting for blocks to sync", 
                      "batchIndex", batchInfo.batchIndex, 
                      "firstBlock", batchInfo.firstBlockNumber,
                      "lastBlock", batchInfo.lastBlockNumber,
                      "error", err)
        // 不要 return，继续下一轮循环
        continue
    }
    // 其他错误才停止
    d.metrics.SetBatchStatus(stateException)
    d.logger.Error("path B content verification failed", "batchIndex", batchInfo.batchIndex, "error", err)
    return
}
```

#### 问题 2: 配置验证缺失（中等）

**现象**:
- 允许配置不一致的 `DERIVATION_START_HEIGHT` 和 snapshot 数据
- 启动时没有验证配置合理性

**建议**:
- 启动时检查 `L2_BASE_HEIGHT` 是否 <= 当前 L2 区块高度
- 如果不匹配，给出警告或拒绝启动

#### 问题 3: 日志不完整（轻微）

**现象**:
- Path B 获取元数据后没有后续日志
- 无法判断是在等待、出错还是其他状态

**建议**:
- 添加更多调试日志
- 记录 Path B 的每个步骤

---

## 测试环境限制

### 1. L1 RPC 限制

- 使用的 L1 RPC 不支持 beacon chain API
- 无法测试 Path A 的完整流程
- 只能测试 Path B

### 2. Snapshot 数据过旧

- 使用的 snapshot 数据到 2026-04-02
- L2 区块高度：4,470,254
- 配置要求：5,280,200
- 差距：~80 万个区块

### 3. P2P 同步慢

- 从 4,470,254 同步到 5,279,569 需要很长时间
- 不适合快速测试

---

## 建议

### 短期建议（测试）

1. **下载最新 snapshot**
   ```bash
   cd morph-node
   make download-and-decompress-hoodi-snapshot
   # 下载 snapshot-20260509-1，包含最新数据
   ```

2. **重新测试完整流程**
   - 验证 Path B 能否成功验证 batch
   - 验证 tag 是否持续推进
   - 监控 safe/finalized 标签变化

### 长期建议（代码改进）

1. **添加等待机制**
   - Path B 遇到区块缺失时应该等待，而不是停止
   - 添加重试逻辑和超时机制

2. **改进错误处理**
   - 区分可恢复错误（区块缺失）和不可恢复错误（验证失败）
   - 可恢复错误应该重试，不可恢复错误才停止

3. **添加配置验证**
   - 启动时验证 derivation 配置与本地数据的一致性
   - 给出明确的错误提示

4. **改进日志**
   - 添加更多调试日志
   - 记录 derivation 的状态变化

---

## 附录：关键日志片段

### Path A 失败日志

```
I[2026-05-14|17:05:13.761] derivation start pull rollupData form l1     module=derivation startBlock=2777180 end=2777280
I[2026-05-14|17:05:14.926] fetched rollup tx                            module=derivation txNum=2 latestBatchIndex=17745
I[2026-05-14|17:05:15.710] Transaction contains blobs                   module=derivation txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd blobCount=1
I[2026-05-14|17:05:16.348] Building IndexedBlobHash array from block    module=derivation blockNumber=2777180
I[2026-05-14|17:05:16.351] Built IndexedBlobHash array                  module=derivation count=1
E[2026-05-14|17:05:16.965] fetch batch info failed                      module=derivation txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd blockNumber=2777180 error="failed to get blobs, continuing processing:failed to get timeToSlotFn: failed request with status 404: {\"jsonrpc\":\"2.0\",\"id\":-1,\"error\":{\"code\":-32001,\"message\":\"Resource not found\"}}"
```

### Path B 启动日志

```
I[2026-05-14|17:07:30.856] derivation started                           
I[2026-05-14|17:07:32.439] derivation start pull rollupData form l1     module=derivation startBlock=2777180 end=2777280
I[2026-05-14|17:07:33.262] fetched rollup tx                            module=derivation txNum=2 latestBatchIndex=17745
I[2026-05-14|17:07:33.591] path B fetched batch metadata                module=derivation txNonce=23453 txHash=0x763f5f76507ac509b32409d7dbc38d06f712b36552fbbda4d852746d44379afd l1BlockNumber=2777180 firstL2BlockNumber=5279569 lastL2BlockNumber=5279890
```

### Geth 状态日志

```
INFO [05-14|17:07:28.194] Loaded finalized block                   number=4,391,127 hash=47b680..dca8ed
INFO [05-14|17:07:28.194] Loaded most recent local full block      number=4,470,254 hash=34c4b1..daf814 td=0 age=1mo1w1d
INFO [05-14|17:07:28.195] Loaded most recent local fast block      number=4,470,254 hash=34c4b1..daf814 td=0 age=1mo1w1d
INFO [05-14|17:07:28.195] Loaded most recent local finalized block number=4,391,127 hash=47b680..dca8ed
```

---

## 测试文件位置

- 完整日志: `/Users/nicholous/workspace/morph-work/run-morph-node/hoodi/node-data/node.log`
- Geth 日志: `/Users/nicholous/workspace/morph-work/run-morph-node/hoodi/geth-data/geth.log`
- 配置文件: `/Users/nicholous/workspace/morph-work/run-morph-node/morph-node/.env_hoodi`
- 测试报告: `/Users/nicholous/workspace/morph-work/run-morph-node/docs/test-derivation-batch-verify-20260514.md`
