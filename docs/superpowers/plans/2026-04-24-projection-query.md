# 投影查询功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 3D 资源空间中添加无限圆柱投影查询，用户选择两个资源球定义方向，指定半径，筛选圆柱内的资源球，支持多投影并集。

**Architecture:** 后端新增 `app/projection.py` 做几何计算（点到直线距离），`app/api.py` 新增查询端点，前端侧边栏新增投影面板，3D 场景中渲染半透明圆柱并高亮结果球。

**Tech Stack:** Python/FastAPI, Pydantic, Three.js (r128), pytest

---

### Task 1: Backend - 投影几何计算模块 + 测试

**Files:**
- Create: `app/projection.py`
- Create: `tests/__init__.py`
- Create: `tests/test_projection.py`

- [ ] **Step 1: 添加 pytest 依赖**

Run: `uv add --dev pytest`

- [ ] **Step 2: 创建 `app/projection.py`**

```python
import math


def normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length == 0:
        raise ValueError("zero vector cannot be normalized")
    return (v[0] / length, v[1] / length, v[2] / length)


def point_to_line_distance(point, line_point, direction):
    """点到无限直线的距离。direction 必须是单位向量。"""
    vx = point[0] - line_point[0]
    vy = point[1] - line_point[1]
    vz = point[2] - line_point[2]
    t = vx * direction[0] + vy * direction[1] + vz * direction[2]
    cx = line_point[0] + t * direction[0]
    cy = line_point[1] + t * direction[1]
    cz = line_point[2] + t * direction[2]
    dx = point[0] - cx
    dy = point[1] - cy
    dz = point[2] - cz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def query_projection(spheres, source_pos, target_pos, cylinder_radius, filter_mode):
    """查询单个投影匹配的资源球。返回 [(sphere_dict, match_type), ...]。"""
    direction = normalize((
        target_pos[0] - source_pos[0],
        target_pos[1] - source_pos[1],
        target_pos[2] - source_pos[2],
    ))

    results = []
    for sphere in spheres:
        sphere_pos = (sphere["calculated_x"], sphere["calculated_y"], sphere["calculated_z"])
        dist = point_to_line_distance(sphere_pos, source_pos, direction)
        sr = sphere["radius"]

        is_intersect = dist <= cylinder_radius + sr
        is_contain = cylinder_radius > sr and dist <= cylinder_radius - sr

        matched = False
        match_type = None
        if filter_mode == "intersect" and is_intersect:
            matched = True
            match_type = "intersect"
        elif filter_mode == "contain" and is_contain:
            matched = True
            match_type = "contain"
        elif filter_mode == "both" and (is_intersect or is_contain):
            matched = True
            match_type = "contain" if is_contain else "intersect"

        if matched:
            results.append((sphere, match_type))

    return results
```

- [ ] **Step 3: 创建 `tests/__init__.py`（空文件）**

- [ ] **Step 4: 创建 `tests/test_projection.py`**

```python
import pytest
from app.projection import normalize, point_to_line_distance, query_projection


def test_normalize_unit():
    assert normalize((3, 0, 0)) == (1.0, 0.0, 0.0)
    assert normalize((0, 4, 0)) == (0.0, 1.0, 0.0)


def test_normalize_diagonal():
    r = normalize((1, 1, 0))
    assert abs(r[0] - 0.7071) < 0.01
    assert abs(r[1] - 0.7071) < 0.01


def test_normalize_zero():
    with pytest.raises(ValueError):
        normalize((0, 0, 0))


def test_point_on_line():
    assert point_to_line_distance((5, 0, 0), (0, 0, 0), (1, 0, 0)) == 0.0


def test_point_perpendicular():
    dist = point_to_line_distance((0, 3, 0), (0, 0, 0), (1, 0, 0))
    assert abs(dist - 3.0) < 1e-9


def test_point_diagonal_line():
    dist = point_to_line_distance((1, 1, 0), (0, 0, 0), (1, 1, 0))
    assert abs(dist) < 1e-9


def test_query_intersect():
    spheres = [
        {"id": 1, "radius": 1.0, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 3, "calculated_z": 0},
        {"id": 3, "radius": 1.0, "calculated_x": 0, "calculated_y": 10, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "intersect")
    ids = [r[0]["id"] for r in results]
    assert 1 in ids  # on axis
    assert 2 in ids  # dist=3, intersect with r=3 (3 <= 3+1)
    assert 3 not in ids  # dist=10, no match


def test_query_contain():
    spheres = [
        {"id": 1, "radius": 0.5, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 2.5, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "contain")
    ids = [r[0]["id"] for r in results]
    assert 1 in ids  # on axis, contained
    assert 2 not in ids  # dist=2.5, not contained (2.5 > 3-1=2)


def test_query_both():
    spheres = [
        {"id": 1, "radius": 0.5, "calculated_x": 5, "calculated_y": 0, "calculated_z": 0},
        {"id": 2, "radius": 1.0, "calculated_x": 0, "calculated_y": 2.5, "calculated_z": 0},
    ]
    results = query_projection(spheres, (0, 0, 0), (1, 0, 0), 3.0, "both")
    ids = [r[0]["id"] for r in results]
    types = {r[0]["id"]: r[1] for r in results}
    assert 1 in ids and types[1] == "contain"
    assert 2 in ids and types[2] == "intersect"
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_projection.py -v`
Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add app/projection.py tests/
git commit -m "feat: add projection geometry calculation with tests"
```

---

### Task 2: Backend - Pydantic 模型 + API 端点

**Files:**
- Modify: `app/models.py`
- Modify: `app/api.py`

- [ ] **Step 1: 在 `app/models.py` 末尾添加投影模型**

```python
class ProjectionInput(BaseModel):
    source_id: int
    target_id: int
    radius: float
    filter_mode: str = "both"


class ProjectionQuery(BaseModel):
    projections: list[ProjectionInput]
```

- [ ] **Step 2: 在 `app/api.py` 中添加 import**

在文件顶部的 import 块添加 `ProjectionQuery`：
```python
from app.models import (
    CenterCreate, CenterResponse,
    SphereCreate, SphereUpdate, SphereResponse,
    ProjectionQuery,
)
```

添加导入 `query_projection`：
```python
from app.projection import query_projection as calc_projection
```

- [ ] **Step 3: 在 `app/api.py` 的 `delete_sphere` 函数之后、内部辅助函数之前，添加投影查询端点**

```python
# --- 投影查询 API ---

@router.post("/projections/query")
def query_projections(data: ProjectionQuery):
    conn = get_db()
    all_spheres = conn.execute("SELECT * FROM resource_spheres").fetchall()
    sphere_list = [dict(r) for r in all_spheres]

    result_map = {}

    for idx, proj in enumerate(data.projections):
        source = conn.execute(
            "SELECT * FROM resource_spheres WHERE id = ?", (proj.source_id,)
        ).fetchone()
        target = conn.execute(
            "SELECT * FROM resource_spheres WHERE id = ?", (proj.target_id,)
        ).fetchone()
        if not source or not target:
            continue

        source_pos = (source["calculated_x"], source["calculated_y"], source["calculated_z"])
        target_pos = (target["calculated_x"], target["calculated_y"], target["calculated_z"])

        candidates = [s for s in sphere_list if s["id"] != proj.source_id and s["id"] != proj.target_id]
        matches = calc_projection(candidates, source_pos, target_pos, proj.radius, proj.filter_mode)

        for sphere, match_type in matches:
            sid = sphere["id"]
            if sid not in result_map:
                result_map[sid] = {"sphere": sphere, "matched_by": [], "match_types": []}
            result_map[sid]["matched_by"].append(idx)
            result_map[sid]["match_types"].append(match_type)

    conn.close()
    return {"results": list(result_map.values())}
```

- [ ] **Step 4: 提交**

```bash
git add app/models.py app/api.py
git commit -m "feat: add projection query API endpoint"
```

---

### Task 3: Frontend - 投影面板 HTML + CSS

**Files:**
- Modify: `static/index.html`
- Modify: `static/style.css`

- [ ] **Step 1: 在 `static/index.html` 的 `<!-- 创建资源球 -->` section 结束后、`<!-- 元素列表 -->` 之前，插入投影查询面板**

在 `</div>` (创建资源球 section 结束) 之后，`<!-- 元素列表 -->` 之前插入：

```html
            <!-- 投影查询 -->
            <div class="panel-section">
                <h3 class="section-title">🔍 投影查询</h3>
                <div class="section-label">起点资源球：</div>
                <select id="proj-source" class="input-field">
                    <option value="">选择资源球...</option>
                </select>
                <div class="section-label">方向参考资源球：</div>
                <select id="proj-target" class="input-field">
                    <option value="">选择资源球...</option>
                </select>
                <div class="section-label">圆柱半径：</div>
                <input id="proj-radius" type="number" value="2" step="0.1" min="0.1" class="input-field">
                <div class="section-label">筛选模式：</div>
                <div class="filter-modes">
                    <button class="filter-btn" data-mode="intersect">相交</button>
                    <button class="filter-btn" data-mode="contain">包含</button>
                    <button class="filter-btn active" data-mode="both">两者</button>
                </div>
                <button id="btn-add-projection" class="btn btn-projection">添加投影</button>
                <div class="section-label" style="margin-top:10px;">已添加投影：</div>
                <div id="projection-list"></div>
                <div id="projection-result" class="projection-result" style="display:none;">
                    <div class="section-label">结果集（并集）：</div>
                    <div id="projection-result-list"></div>
                </div>
            </div>
```

- [ ] **Step 2: 在 `static/style.css` 末尾添加投影相关样式**

```css
/* --- 投影查询 --- */
select.input-field {
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23888'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    padding-right: 28px;
}

.filter-modes {
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
}

.filter-btn {
    flex: 1;
    padding: 5px;
    background: #555;
    color: #ccc;
    border: none;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.2s;
}

.filter-btn.active {
    background: #ffaa00;
    color: #1a1a2e;
    font-weight: bold;
}

.filter-btn:hover:not(.active) {
    background: #666;
}

.btn-projection {
    background: #ffaa00;
    color: #1a1a2e;
}

.projection-tag {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 8px;
    background: #1a1a2e;
    border-radius: 4px;
    font-size: 11px;
    color: #ffaa00;
    margin-bottom: 4px;
}

.projection-tag .tag-delete {
    color: #888;
    cursor: pointer;
    font-size: 12px;
    padding: 0 2px;
}

.projection-tag .tag-delete:hover {
    color: #ff6b6b;
}

.projection-result {
    margin-top: 8px;
}

.projection-result-item {
    padding: 4px 8px;
    background: #1a1a2e;
    border-radius: 4px;
    font-size: 11px;
    color: #4ecdc4;
    margin-bottom: 3px;
}
```

- [ ] **Step 3: 提交**

```bash
git add static/index.html static/style.css
git commit -m "feat: add projection query panel HTML and CSS"
```

---

### Task 4: Frontend - 投影查询 JS 逻辑

**Files:**
- Modify: `static/app.js`

这是最核心的任务。需要在 `app.js` 中添加：投影状态管理、3D 圆柱渲染、API 调用、UI 渲染、事件绑定、与 loadAll 集成。

- [ ] **Step 1: 在全局状态区域（第 6 行 `let highlightedId = null;` 之后）添加投影状态变量**

```js
let projections = [];
let projectionMeshes = [];
let projectionResults = [];
let currentFilterMode = "both";
```

- [ ] **Step 2: 在 `highlightElement` 函数之后（第 150 行附近），添加投影 3D 可视化函数**

```js
// ==================== 投影 3D 可视化 ====================
function addProjectionCylinder(sourcePos, targetPos, radius) {
    const direction = new THREE.Vector3().subVectors(
        new THREE.Vector3(targetPos[0], targetPos[1], targetPos[2]),
        new THREE.Vector3(sourcePos[0], sourcePos[1], sourcePos[2])
    );
    if (direction.length() === 0) return;
    direction.normalize();

    const length = 200;
    const geo = new THREE.CylinderGeometry(radius, radius, length, 32, 1, true);
    const mat = new THREE.MeshPhongMaterial({
        color: 0xffaa00, transparent: true, opacity: 0.12, side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(sourcePos[0], sourcePos[1], sourcePos[2]);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    scene.add(mesh);
    projectionMeshes.push(mesh);
}

function removeAllProjectionCylinders() {
    projectionMeshes.forEach(m => {
        scene.remove(m);
        m.geometry.dispose();
        m.material.dispose();
    });
    projectionMeshes = [];
}

function renderProjectionCylinders() {
    removeAllProjectionCylinders();
    projections.forEach(proj => {
        const srcMesh = sphereMeshes[proj.source_id];
        const tgtMesh = sphereMeshes[proj.target_id];
        if (!srcMesh || !tgtMesh) return;
        addProjectionCylinder(
            [srcMesh.position.x, srcMesh.position.y, srcMesh.position.z],
            [tgtMesh.position.x, tgtMesh.position.y, tgtMesh.position.z],
            proj.radius
        );
    });
}

function resetSphereAppearance() {
    Object.values(sphereMeshes).forEach(m => {
        m.material.color.setHex(0x4ecdc4);
        m.material.opacity = 0.35;
    });
}

function highlightProjectionResults() {
    resetSphereAppearance();
    if (projectionResults.length === 0) return;
    projectionResults.forEach(r => {
        const mesh = sphereMeshes[r.sphere.id];
        if (mesh) {
            mesh.material.opacity = 0.7;
            mesh.material.color.setHex(0xffaa00);
        }
    });
}
```

- [ ] **Step 3: 在 API 调用区域之后（`apiDelete` 之后，`loadAll` 之前），添加投影 UI 渲染和查询函数**

```js
// ==================== 投影查询 ====================
function renderProjectionOptions(spheres) {
    const sourceSelect = document.getElementById("proj-source");
    const targetSelect = document.getElementById("proj-target");
    const sourceVal = sourceSelect.value;
    const targetVal = targetSelect.value;

    const opts = '<option value="">选择资源球...</option>' +
        spheres.map(s => `<option value="${s.id}">${s.name} (${s.calculated_x.toFixed(1)}, ${s.calculated_y.toFixed(1)}, ${s.calculated_z.toFixed(1)})</option>`).join("");
    sourceSelect.innerHTML = opts;
    targetSelect.innerHTML = opts;
    sourceSelect.value = sourceVal;
    targetSelect.value = targetVal;
}

function renderProjectionList() {
    const container = document.getElementById("projection-list");
    container.innerHTML = "";
    if (projections.length === 0) {
        container.innerHTML = '<div style="color:#666;font-size:12px;">暂无投影</div>';
        document.getElementById("projection-result").style.display = "none";
        return;
    }
    projections.forEach((p, idx) => {
        const modeLabel = p.filter_mode === "intersect" ? "相交" : p.filter_mode === "contain" ? "包含" : "两者";
        const div = document.createElement("div");
        div.className = "projection-tag";
        div.innerHTML = `
            <span>${p.source_name}→${p.target_name} r=${p.radius} [${modeLabel}]</span>
            <span class="tag-delete" data-idx="${idx}">✕</span>
        `;
        container.appendChild(div);
    });
    container.querySelectorAll(".tag-delete").forEach(btn => {
        btn.addEventListener("click", async () => {
            projections.splice(parseInt(btn.dataset.idx), 1);
            renderProjectionCylinders();
            await queryProjections();
        });
    });
}

function renderProjectionResults() {
    const resultSection = document.getElementById("projection-result");
    const container = document.getElementById("projection-result-list");

    if (projections.length === 0) {
        resultSection.style.display = "none";
        return;
    }

    resultSection.style.display = "block";
    container.innerHTML = "";

    if (projectionResults.length === 0) {
        container.innerHTML = '<div style="color:#666;font-size:12px;">无匹配结果</div>';
        return;
    }

    projectionResults.forEach(r => {
        const typeLabels = r.match_types.map(t => t === "contain" ? "包含" : "相交").join(", ");
        const div = document.createElement("div");
        div.className = "projection-result-item";
        div.innerHTML = `● ${r.sphere.name} — ${typeLabels}`;
        container.appendChild(div);
    });
}

async function queryProjections() {
    if (projections.length === 0) {
        projectionResults = [];
        renderProjectionList();
        renderProjectionResults();
        resetSphereAppearance();
        return;
    }
    try {
        const data = await apiPost("/api/projections/query", {
            projections: projections.map(p => ({
                source_id: p.source_id,
                target_id: p.target_id,
                radius: p.radius,
                filter_mode: p.filter_mode,
            })),
        });
        projectionResults = data.results;
        renderProjectionList();
        renderProjectionResults();
        highlightProjectionResults();
    } catch (e) {
        alert(e.message);
    }
}

function validateProjections(spheres) {
    const validIds = new Set(spheres.map(s => s.id));
    projections = projections.filter(p => validIds.has(p.source_id) && validIds.has(p.target_id));
}
```

- [ ] **Step 4: 修改 `loadAll` 函数，在末尾添加投影刷新逻辑**

在 `loadAll` 函数体内的 `renderElementList(centers, spheres);` 之后添加：

```js
    renderProjectionOptions(spheres);
    validateProjections(spheres);
    renderProjectionCylinders();
    if (projections.length > 0) {
        await queryProjections();
    } else {
        resetSphereAppearance();
    }
```

- [ ] **Step 5: 在 `bindEvents` 函数末尾（`edit-modal` click handler 之后），添加投影事件绑定**

```js
    // 投影 - 筛选模式切换
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentFilterMode = btn.dataset.mode;
        });
    });

    // 投影 - 添加投影
    document.getElementById("btn-add-projection").addEventListener("click", async () => {
        const sourceSelect = document.getElementById("proj-source");
        const targetSelect = document.getElementById("proj-target");
        const sourceId = parseInt(sourceSelect.value);
        const targetId = parseInt(targetSelect.value);
        const radius = parseFloat(document.getElementById("proj-radius").value) || 2;

        if (!sourceId || !targetId) return alert("请选择起点和方向参考资源球");
        if (sourceId === targetId) return alert("起点和方向参考不能相同");

        const sourceName = sourceSelect.options[sourceSelect.selectedIndex].text.split(" (")[0];
        const targetName = targetSelect.options[targetSelect.selectedIndex].text.split(" (")[0];

        projections.push({
            source_id: sourceId, target_id: targetId,
            radius, filter_mode: currentFilterMode,
            source_name: sourceName, target_name: targetName,
        });
        renderProjectionCylinders();
        await queryProjections();
    });
```

- [ ] **Step 6: 提交**

```bash
git add static/app.js
git commit -m "feat: add projection query JS logic with 3D visualization"
```

---

### Task 5: 集成验证

- [ ] **Step 1: 启动服务并手动测试**

Run: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

验证流程：
1. 创建 3 个中心点 A(0,0,0), B(5,0,0), C(0,5,0)
2. 创建 3 个资源球 S1(关联 A,B), S2(关联 B,C), S3(关联 A,C)
3. 在投影面板选择 S1→S2，半径 2.0，模式"两者"
4. 点击"添加投影"，确认 3D 场景出现半透明圆柱
5. 确认结果列表显示匹配的资源球
6. 添加第二个投影 S3→S2，确认结果为并集
7. 删除一个投影，确认圆柱消失，结果更新
8. 编辑资源球关联（改变坐标），确认投影圆柱和高亮自动更新

- [ ] **Step 2: 运行测试确认无回归**

Run: `uv run pytest tests/test_projection.py -v`
Expected: 所有测试 PASS

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: complete projection query feature"
```
