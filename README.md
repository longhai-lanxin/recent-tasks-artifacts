# recent-tasks-artifacts

近期开发任务中沉淀的**可复用工具产物**（已脱敏：无个人路径、无个人数据、无教材衍生内容）。

## 子项目

| 子项目 | 说明 |
|---|---|
| [`kp-handbook-pipeline/`](kp-handbook-pipeline/) | 多格式文档（docx/pdf/pptx/xlsx）→ 结构化知识点手册（docx/CSV/md）六阶段流水线：提取 → SHA1 去重 → 批次合并 → plan JSON 编纂 → 版式渲染 → 质量校验 |
| [`latex-omml/`](latex-omml/) | 单文件零依赖 LaTeX → OMML 公式转换器，生成可插入 `.docx` 的 `<m:oMath>` 原生公式 XML |

## 本地快速验证

```bash
cd latex-omml && python3 test_omml.py
cd ../kp-handbook-pipeline && python3 scripts/render.py --work /tmp/kp_demo
```

## 未纳入本仓库的内容及原因

| 内容 | 原因 |
|---|---|
| PuppetMDM（Android 管控 App 源码） | 对商用管控软件 `net.forclass.guard`（ForClass）的 1:1 UI/逻辑复刻，含其包名与商标引用，公开分发有侵权与冒充风险，不适合公开仓库 |
| 六科知识点手册 docx/CSV/plan JSON | 教材衍生内容，存在版权风险 |
| AUTO_WEATHER 工作记忆文件 | 纯个人记忆，无可复用代码 |

## 提交建议

```bash
git remote add origin https://github.com/<your-name>/<repo>.git
git push -u origin main
```
