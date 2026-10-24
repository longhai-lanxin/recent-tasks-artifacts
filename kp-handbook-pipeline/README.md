# kp-handbook-pipeline

多格式文档 → 结构化知识点手册（docx/CSV/md）流水线。

把散落的 docx / pdf / pptx / xlsx 教学素材，经过**提取 → 去重 → 批次通读 → 结构化编纂 → 渲染 → 校验**六个阶段，
产出仿《高中数学知识点背诵手册》版式的结构化手册：每条知识点独立成行、编号连续，附 CSV 清单可溯源。

## 流水线

```
src/<学科>/*.{docx,pdf,pptx,xlsx}
   │  scripts/extract.py    多格式文本提取（docx zip 直读容错 / LibreOffice 兜底 / tesseract OCR / OCR 孪生检测）
   ▼
work/extracted/<学科>/*.txt + manifest.json
   │  scripts/dedupe.py     规范化文本 SHA1 折叠重复副本
   ▼
work/clean/<学科>/*.txt + index.json
   │  scripts/mkbatch.py    按来源子串合并批次文本（供人或 LLM 通读）
   ▼
work/batches/*.txt
   │  （人工/LLM 通读数料，编纂为 plan JSON）
   ▼
work/plan/<学科>.json       「卷—册—章—节—条目」结构
   │  scripts/render.py     渲染 docx/CSV/md（A4、0.5in 边距、标题 20/15/12.5/11pt）
   ▼
work/out/<学科>/*.{docx,csv,md}
   │  scripts/verify.py     编号连续/条目格式/OCR 乱码/版式参数/CSV 一致性
   ▼
   交付
```

## 安装

```bash
pip install -r requirements.txt
# OCR 功能另需: tesseract + chi_sim 语言包; LibreOffice 用于 .doc 与 docx 兜底
```

## 用法

```bash
# 1) 提取（src 下每个子目录视为一个学科）
python3 scripts/extract.py --src /path/to/src --work /path/to/work [--ocr]

# 2) 去重
python3 scripts/dedupe.py --work /path/to/work

# 3) 合并批次（供通读；子串匹配 clean/index.json 的 source）
python3 scripts/mkbatch.py --work /path/to/work 02_数学 work/batches/m_b1.txt 必修二 答案

# 4) 编纂 plan JSON 后渲染（可只渲染指定学科）
python3 scripts/render.py --work /path/to/work [--config config.example.json] [02_数学 ...]

# 5) 校验
python3 scripts/verify.py --work /path/to/work [--ref 参考手册.docx]
```

所有路径均可用 `--src/--work` 参数或 `KP_SRC/KP_WORK` 环境变量指定，默认 `./src` 与当前目录。

## plan JSON 结构

```json
{
  "subject": "02_数学",
  "unit": "高中数学知识点手册",
  "volumes": [{
    "name": "卷一　平面向量及其应用",
    "books": [{
      "name": "第1册　必修第二册 第六章",
      "src": "答案解析/必修二第六章教材解析.pdf",
      "chapters": [{
        "name": "6.1 平面向量的概念",
        "sections": [{
          "name": "6.1.1 向量的实际背景与概念",
          "entries": [
            {"t": "定义", "n": "向量", "c": "既有大小又有方向的量叫做向量。", "s": "必修二第六章教材解析"}
          ]
        }]
      }]
    }]
  }]
}
```

条目字段：`t` 类型、`n` 名称、`c` 内容、`s` 来源（可选）。渲染格式：`N. 【类型】名称 —— 内容`。

## 冒烟测试

```bash
mkdir -p /tmp/kp_demo/plan && cp demo/plan_demo.json /tmp/kp_demo/plan/99_demo.json
python3 scripts/render.py --work /tmp/kp_demo
python3 scripts/verify.py --work /tmp/kp_demo
```

## 说明

- 字体（`--font-latin/--font-ea`）与各学科的使用说明（`config.example.json`）均为可配置项；
- `extract.py` 的 `--ocr` 依赖本机 tesseract；PDF 无文本层且存在同名 `(OCR)` 文件时会自动优先采用；
- 教材衍生内容（plan JSON、手册输出）不含在本仓库中，请自行编纂并注意版权。
