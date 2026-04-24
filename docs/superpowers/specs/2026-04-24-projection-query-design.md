---
name: Projection Query Feature
type: feature
created: 2026-04-24
status: approved
---

# 投影查询功能设计

## 概述

在 3D 资源空间中添加投影查询功能。用户选择两个资源球 A 和 B，沿 A→B 方向创建一个无限延伸的圆柱区域（给定半径 r），筛选出与该圆柱区域有特定关系的其他资源球。支持多个投影的并集查询。

## 几何定义

**无限延伸圆柱：**
- 轴线：从资源球 A 位置出发，沿 normalize(B.pos - A.pos) 方向无限延伸（两个方向都延伸）
- 半径：用户指定 r
- 投影圆柱在 3D 场景中以半透明方式可视化

**筛选模式：**
- **相交**：资源球与圆柱有重叠区域（球心到轴线距离 ≤ r + sphere.radius）
- **包含**：资源球完全在圆柱内部（球心到轴线距离 ≤ r - sphere.radius，要求 r > sphere.radius）
- **两者**：满足相交或包含任意一个条件

**多投影组合：** 并集关系 — 资源球只需满足任意一个投影的条件即出现在结果中。

## 后端

### 新增 API 端点

**POST /api/projections/query**

请求体：
```json
{
  "projections": [
    {
      "source_id": 1,
      "target_id": 2,
      "radius": 2.0,
      "filter_mode": "both"
    }
  ]
}
```

`filter_mode` 取值：`"intersect"` / `"contain"` / `"both"`

响应体：
```json
{
  "results": [
    {
      "sphere": { "id": 3, "name": "S3", "radius": 1.0, "calculated_x": 1.0, ... },
      "matched_by": [0],
      "match_types": ["intersect"]
    }
  ]
}
```

`matched_by` 是匹配到的投影索引列表，`match_types` 是对应的匹配类型。

### 计算逻辑

点到线段距离（点到无限直线距离）：

1. 方向向量 d = normalize(B.pos - A.pos)
2. 投影向量 v = sphere.pos - A.pos
3. 投影长度 t = dot(v, d)
4. 最近点 closest = A.pos + t * d
5. 距离 dist = length(sphere.pos - closest)

筛选判定：
- 相交：dist ≤ r + sphere.radius
- 包含：dist ≤ r - sphere.radius（当 r > sphere.radius 时）或 dist = 0（当 r ≤ sphere.radius 时不包含，除非球心在轴线上且半径为0）

## 前端

### UI 组件

在右侧控制面板中新增 "投影查询" 面板（panel-section），位于"创建资源球"面板之后、"元素列表"之前。

**面板内容：**

1. **配置区：**
   - 起点资源球下拉框（列出所有已有资源球）
   - 方向参考资源球下拉框（列出所有已有资源球，不能与起点相同）
   - 圆柱半径输入框（默认 2.0）
   - 筛选模式按钮组：相交 / 包含 / 两者（默认选中"两者"）
   - "添加投影"按钮

2. **投影列表：**
   - 每个投影显示为标签：`S1→S2 r=2.0 [两者]`
   - 标签右侧有 ✕ 删除按钮
   - 无投影时显示空状态提示

3. **结果集：**
   - 列出所有命中的资源球，标注匹配类型（相交/包含）
   - 高亮命中的资源球（3D 场景中变色）

### 3D 场景可视化

- 每个投影渲染为一个半透明圆柱（Three.js CylinderGeometry）
- 圆柱颜色：#ffaa00（橙黄色），透明度 0.15
- 圆柱沿 A→B 方向放置，长度足够覆盖整个场景（例如 100 单位）
- 结果集中的资源球高亮显示（改变颜色/透明度）

### 交互流程

1. 用户选择起点、方向参考、半径、筛选模式
2. 点击"添加投影"
3. 前端将当前所有投影发送到 POST /api/projections/query
4. 3D 场景中渲染投影圆柱，更新结果列表
5. 添加/删除投影时自动重新查询并更新
6. 场景刷新（loadAll）后保留投影状态，重新渲染圆柱

### 状态管理

- `projections` 数组：存储当前所有投影配置
- `projectionMeshes` 数组：存储圆柱 3D 对象
- `projectionResults` 数组：存储查询结果
