# pdfplumber（中文文档）

[![版本](https://img.shields.io/pypi/v/pdfplumber.svg)](https://pypi.python.org/pypi/pdfplumber) ![测试](https://github.com/jsvine/pdfplumber/workflows/Tests/badge.svg) [![代码覆盖率](https://codecov.io/gh/jsvine/pdfplumber/branch/stable/graph/badge.svg)](https://codecov.io/gh/jsvine/pdfplumber/branch/stable) [![支持的 Python 版本](https://img.shields.io/pypi/pyversions/pdfplumber.svg)](https://pypi.python.org/pypi/pdfplumber)

对 PDF 进行“管道式”抽取，获取每个文本字符、矩形与直线的详细信息；并提供表格抽取与可视化调试功能。

本项目更适用于机器生成的 PDF，而非扫描类 PDF。基于 [`pdfminer.six`](https://github.com/goulu/pdfminer) 构建。

当前在这些版本上进行[测试](tests/)： [Python 3.8, 3.9, 3.10, 3.11](.github/workflows/tests.yml)。

本文件已有翻译版本： [中文（由 @hbh112233abc 提供）](https://github.com/hbh112233abc/pdfplumber/blob/stable/README-CN.md)。

报告缺陷或请求新功能请[创建 issue](https://github.com/jsvine/pdfplumber/issues/new/choose)。如需就特定 PDF 提问或寻求帮助，请使用[讨论区](https://github.com/jsvine/pdfplumber/discussions)。

## 目录

- [安装](#installation)
- [命令行接口](#command-line-interface)
- [Python 库](#python-library)
- [可视化调试](#visual-debugging)
- [提取文本](#extracting-text)
- [提取表格](#extracting-tables)
- [提取表单值](#extracting-form-values)
- [演示](#demonstrations)
- [与其他库的对比](#comparison-to-other-libraries)
- [致谢 / 贡献者](#acknowledgments--contributors)
- [参与贡献](#contributing)

> 注：为保持目录内链接可用，本文在各章节标题前加入了与英文 README 一致的锚点。

<a id="installation"></a>

## 安装

```sh
pip install pdfplumber
```

<a id="command-line-interface"></a>

## 命令行接口（CLI）

### 基本示例

```sh
curl "https://raw.githubusercontent.com/jsvine/pdfplumber/stable/examples/pdfs/background-checks.pdf" > background-checks.pdf
pdfplumber background-checks.pdf > background-checks.csv
```

输出将是一个 CSV，包含 PDF 中每个字符、直线与矩形的相关信息。

### 选项

| 参数 | 说明 |
|------|------|
|`--format [format]`| 可选 `csv`、`json` 或 `text`。`csv` 与 `json` 返回每个对象的信息；二者中 `json` 更详细，包含 PDF 级与页面级元数据，以及字典嵌套属性。`text` 返回 PDF 的纯文本表示，使用 `Page.extract_text(layout=True)`。|
|`--pages [list of pages]`| 空格分隔、从 1 开始的页码列表或连字符范围。例如 `1, 11-15` 返回第 1、11、12、13、14、15 页的数据。|
|`--types [list of object types to extract]`| 要抽取的对象类型：`char`、`rect`、`line`、`curve`、`image`、`annot` 等。默认抽取全部可用类型。|
|`--laparams`| 传递给 `pdfplumber.open(..., laparams=...)` 的 JSON 字符串（如 `'{"detect_vertical": true}'`）。|
|`--precision [integer]`| 浮点数保留的小数位数。默认为不四舍五入。|

<a id="python-library"></a>

## Python 库

### 基本示例

```python
import pdfplumber

with pdfplumber.open("path/to/file.pdf") as pdf:
    first_page = pdf.pages[0]
    print(first_page.chars[0])
```

### 加载 PDF

开始处理 PDF 时，调用 `pdfplumber.open(x)`，其中 `x` 可以是：

- PDF 文件路径
- 以字节方式加载的文件对象
- 以字节方式加载的类文件对象（file-like）

`open` 返回一个 `pdfplumber.PDF` 实例。

加载受密码保护的 PDF：传入 `password` 关键字参数，例如 `pdfplumber.open("file.pdf", password="test")`。

设置传给 `pdfminer.six` 布局引擎的参数：传入 `laparams`，例如 `pdfplumber.open("file.pdf", laparams={"line_overlap": 0.7})`。

若需对 Unicode 文本进行[预标准化](https://unicode.org/reports/tr15/)，传入 `unicode_norm=...`，其中 `...` 为[四种 Unicode 规范化形式](https://unicode.org/reports/tr15/#Normalization_Forms_Table)之一：`"NFC"`、`"NFD"`、`"NFKC"` 或 `"NFKD"`。

无效元数据值默认视为警告。如希望在无法解析元数据时直接抛出异常，请传入 `strict_metadata=True`。

### `pdfplumber.PDF` 类

顶层 `pdfplumber.PDF` 表示一个 PDF，主要包含两个属性：

| 属性 | 说明 |
|------|------|
|`.metadata`| 元数据字典，来自 PDF 的 `Info` 节。常见键包括 "CreationDate"、"ModDate"、"Producer" 等。|
|`.pages`| 包含所加载页面的 `pdfplumber.Page` 实例列表。|

以及如下方法：

| 方法 | 说明 |
|------|------|
|`.close()`| 调用该方法会对每个页面调用 `Page.close()`，并关闭文件流（若文件流为外部提供，即已打开并直接传入 `pdfplumber` 的情况除外）。|

### `pdfplumber.Page` 类

`pdfplumber.Page` 是 `pdfplumber` 的核心。大部分操作都会围绕该类展开。其主要属性：

| 属性 | 说明 |
|------|------|
|`.page_number`| 顺序页码，从 `1` 开始。|
|`.width`| 页面宽度。|
|`.height`| 页面高度。|
|`.objects` / `.chars` / `.lines` / `.rects` / `.curves` / `.images`| 各为列表，包含页面内每类对象的字典。详见下文[“对象”](#objects)。|

其主要方法：

| 方法 | 说明 |
|------|------|
|`.crop(bounding_box, relative=False, strict=True)`| 将页面裁剪为给定边界框并返回新页面。边界框以四元组 `(x0, top, x1, bottom)` 表示。若对象仅部分落入边界框，其尺寸会被截断以适配。`relative=True` 时，边界框基于页面左上角的相对偏移。`strict=True`（默认）时，裁剪框必须完全位于页面边界内。|
|`.within_bbox(bounding_box, relative=False, strict=True)`| 类似 `.crop`，但仅保留完全位于边界框内的对象。|
|`.outside_bbox(bounding_box, relative=False, strict=True)`| 类似 `.crop` 与 `.within_bbox`，但仅保留完全位于边界框外的对象。|
|`.filter(test_function)`| 返回仅包含满足 `test_function(obj) == True` 的对象的新页面。|
|`.close()`| 默认 `Page` 会缓存布局与对象信息，便于重复使用；解析大型 PDF 时该缓存可能占用大量内存。可调用此方法清理缓存并释放内存。|

更多方法见以下章节：

- [可视化调试](#visual-debugging)
- [提取文本](#extracting-text)
- [提取表格](#extracting-tables)

<a id="objects"></a>

### 对象（Objects）

`pdfplumber.PDF` 与 `pdfplumber.Page` 提供多种 PDF 对象的访问，这些对象均源自 [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six/) 的解析。以下属性各自返回匹配对象的 Python 列表：

- `.chars`：单个文本字符。
- `.lines`：单条一维直线。
- `.rects`：单个二维矩形。
- `.curves`：连接点序列（非直线/矩形）。
- `.images`：图像。
- `.annots`：单条 PDF 批注（参见 [PDF 规范 8.4 节](https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/pdf_reference_1-7.pdf)）。
- `.hyperlinks`：子类型为 `Link`、且具有 `URI` 动作属性的批注。

每个对象以 Python `dict` 表示，常见属性如下。

#### `char` 属性

| 属性 | 说明 |
|------|------|
|`page_number`| 所在页码。|
|`text`| 字符内容，如 "z"、"Z" 或空格 " "。|
|`fontname`| 字体名。|
|`size`| 字号。|
|`adv`| 等于 文本宽度 × 字号 × 缩放因子。|
|`upright`| 字符是否正立。|
|`height`| 字符高度。|
|`width`| 字符宽度。|
|`x0`| 字符左侧到页面左侧的距离。|
|`x1`| 字符右侧到页面左侧的距离。|
|`y0`| 字符底部到页面底部的距离。|
|`y1`| 字符顶部到页面底部的距离。|
|`top`| 字符顶部到页面顶部的距离。|
|`bottom`| 字符底部到页面顶部的距离。|
|`doctop`| 字符顶部到文档顶部的距离。|
|`matrix`| 此字符的“当前变换矩阵”（CTM）。|
|`mcid`| 该字符所属[标记内容](https://ghostscript.com/~robin/pdf_reference17.pdf#page=850)的 ID，若无则为 `None`。实验属性。|
|`tag`| 标记内容的标签，若无则为 `None`。实验属性。|
|`ncs`|TKTK|
|`stroking_pattern`|TKTK|
|`non_stroking_pattern`|TKTK|
|`stroking_color`| 描边颜色。详见 [docs/colors.md](docs/colors.md)。|
|`non_stroking_color`| 填充颜色。详见 [docs/colors.md](docs/colors.md)。|
|`object_type`| 固定为 "char"。|

注：字符的 `matrix` 为 PDF 规范（第 6 版）第 4.2.2 节所述“当前变换矩阵”。它决定缩放、倾斜与平移。旋转通常可视作 x 轴倾斜。`pdfplumber.ctm` 子模块提供 `CTM` 类辅助计算，例如：

```python
from pdfplumber.ctm import CTM
my_char = pdf.pages[0].chars[3]
my_char_ctm = CTM(*my_char["matrix"])
my_char_rotation = my_char_ctm.skew_x
```

#### `line` 属性

| 属性 | 说明 |
|------|------|
|`page_number`| 所在页码。|
|`height`| 直线的“高度”。|
|`width`| 直线的“宽度”。|
|`x0`| 左端到页面左侧的距离。|
|`x1`| 右端到页面左侧的距离。|
|`y0`| 下端到页面底部的距离。|
|`y1`| 上端到页面底部的距离。|
|`top`| 上端到页面顶部的距离。|
|`bottom`| 下端到页面顶部的距离。|
|`doctop`| 上端到文档顶部的距离。|
|`linewidth`| 线宽。|
|`stroking_color`| 线条颜色。详见 [docs/colors.md](docs/colors.md)。|
|`non_stroking_color`| 为该路径指定的非描边色。详见 [docs/colors.md](docs/colors.md)。|
|`mcid`| 标记内容 ID（若无则 `None`）。实验属性。|
|`tag`| 标记内容标签（若无则 `None`）。实验属性。|
|`object_type`| 固定为 "line"。|

#### `rect` 属性

| 属性 | 说明 |
|------|------|
|`page_number`| 所在页码。|
|`height`| 高度。|
|`width`| 宽度。|
|`x0`| 左侧到页面左侧的距离。|
|`x1`| 右侧到页面左侧的距离。|
|`y0`| 底部到页面底部的距离。|
|`y1`| 顶部到页面底部的距离。|
|`top`| 顶部到页面顶部的距离。|
|`bottom`| 底部到页面顶部的距离。|
|`doctop`| 顶部到文档顶部的距离。|
|`linewidth`| 线宽。|
|`stroking_color`| 描边颜色。详见 [docs/colors.md](docs/colors.md)。|
|`non_stroking_color`| 填充颜色。详见 [docs/colors.md](docs/colors.md)。|
|`mcid`| 标记内容 ID（若无则 `None`）。实验属性。|
|`tag`| 标记内容标签（若无则 `None`）。实验属性。|
|`object_type`| 固定为 "rect"。|

#### `curve` 属性

| 属性 | 说明 |
|------|------|
|`page_number`| 所在页码。|
|`pts`| `(x, top)` 点列表，表示曲线上的点。|
|`path`| `(cmd, *(x, top))` 元组列表，描述完整路径（包含贝塞尔曲线控制点等）。|
|`height`| 外接矩形高度。|
|`width`| 外接矩形宽度。|
|`x0`| 左侧最左点到页面左侧的距离。|
|`x1`| 右侧最右点到页面左侧的距离。|
|`y0`| 最低点到页面底部的距离。|
|`y1`| 最高点到页面底部的距离。|
|`top`| 最高点到页面顶部的距离。|
|`bottom`| 最低点到页面顶部的距离。|
|`doctop`| 最高点到文档顶部的距离。|
|`linewidth`| 线宽。|
|`fill`| 路径围成的形状是否填充。|
|`stroking_color`| 描边颜色。详见 [docs/colors.md](docs/colors.md)。|
|`non_stroking_color`| 填充颜色。详见 [docs/colors.md](docs/colors.md)。|
|`dash`| `([dash_array], dash_phase)` 描述的虚线样式。参见 [PDF 规范表 4.6](https://ghostscript.com/~robin/pdf_reference17.pdf#page=218)。|
|`mcid`| 标记内容 ID（若无则 `None`）。实验属性。|
|`tag`| 标记内容标签（若无则 `None`）。实验属性。|
|`object_type`| 固定为 "curve"。|

#### 派生属性

此外，`pdfplumber.PDF` 与 `pdfplumber.Page` 还提供一些派生对象列表：`.rect_edges`（将矩形分解成四条边）、`.curve_edges`（将曲线分解为边）、以及 `.edges`（合并 `.rect_edges`、`.curve_edges` 与 `.lines`）。

#### `image` 属性

注意：尽管能获取 `image` 对象的位置和特征，`pdfplumber` 并不直接提供重建图像像素内容的功能。参见[此建议](https://github.com/jsvine/pdfplumber/discussions/496#discussioncomment-1259772)。

| 属性 | 说明 |
|------|------|
|`page_number`| 所在页码。|
|`height`| 图像高度。|
|`width`| 图像宽度。|
|`x0`| 左侧到页面左侧距离。|
|`x1`| 右侧到页面左侧距离。|
|`y0`| 底部到页面底部距离。|
|`y1`| 顶部到页面底部距离。|
|`top`| 顶部到页面顶部距离。|
|`bottom`| 底部到页面顶部距离。|
|`doctop`| 顶部到文档顶部距离。|
|`srcsize`| 原始尺寸 `(width, height)`。|
|`colorspace`| 颜色空间（如 RGB）。|
|`bits`| 每个颜色分量的位数，例如 8 表示 0-255。|
|`stream`| 图像像素流（`pdfminer.pdftypes.PDFStream`）。|
|`imagemask`| 可空布尔值；若为 `True`，表示该图像数据作为模板遮罩使用。|
|`name`| 在当前资源字典 XObject 子字典中引用该图像 XObject 的名称。详见[规范](https://ghostscript.com/~robin/pdf_reference17.pdf#page=340)。|
|`mcid`| 标记内容 ID（若无则 `None`）。实验属性。|
|`tag`| 标记内容标签（若无则 `None`）。实验属性。|
|`object_type`| 固定为 "image"。|

### 通过 `pdfminer.six` 获取更高层次的布局对象

若向 `pdfplumber.open(...)` 传入 `laparams`，则每个页面的 `.objects` 字典还会包含 `pdfminer.six` 的高层布局对象，如 `"textboxhorizontal"`。

<a id="visual-debugging"></a>

## 可视化调试

`pdfplumber` 的可视化调试工具有助于理解 PDF 的结构以及抽取到的对象。

### 使用 `.to_image()` 创建 `PageImage`

将任意页面（包括裁剪后的页面）转换为 `PageImage`：调用 `my_page.to_image()`。可选传入以下参数（最多选一类尺寸参数）：

- `resolution`：每英寸像素数，默认 `72`，类型 `int`。
- `width`：目标图像宽度（像素）。默认未设置，由 `resolution` 决定，类型 `int`。
- `height`：目标图像高度（像素）。默认未设置，由 `resolution` 决定，类型 `int`。
- `antialias`：是否抗锯齿。为 `True` 时文字与图形更平滑但文件更大。默认 `False`，类型 `bool`。
- `force_mediabox`：使用页面的 `.mediabox` 尺寸，而非 `.cropbox`。默认 `False`，类型 `bool`。

示例：

```python
im = my_pdf.pages[0].to_image(resolution=150)
```

在脚本或 REPL 中，调用 `im.show()` 会在本地图像查看器打开图像。`PageImage` 在 Jupyter 笔记本中也可直接渲染为单元输出。例如：

![Jupyter 中的可视化调试](examples/screenshots/visual-debugging-in-jupyter.png "Visual debugging in Jupyter")

注意：`.to_image(...)` 能与 `Page.crop(...)`/`CroppedPage` 正常配合，但无法体现 `Page.filter(...)`/`FilteredPage` 的更改。

### 基本 `PageImage` 方法

| 方法 | 说明 |
|------|------|
|`im.reset()`| 清空已绘制内容。|
|`im.copy()`| 复制为新的 `PageImage`。|
|`im.show()`| 在本地查看器中打开图像。|
|`im.save(path_or_fileobject, format="PNG", quantize=True, colors=256, bits=8)`| 保存带注释的图像为 PNG。默认会量化至 256 色并使用 8-bit 色深；可通过 `quantize=False` 关闭量化，或通过 `colors=N` 调整调色板大小。|

### 绘制方法

这些方法既可接收显式坐标，也可接收任意 `pdfplumber` 对象（如 char、line、rect）。

| 单对象方法 | 批量方法 | 说明 |
|------------|----------|------|
|`im.draw_line(line, stroke={color}, stroke_width=1)`|`im.draw_lines(list_of_lines, **kwargs)`| 根据 `line`、`curve` 或两个点坐标 `((x, y), (x, y))` 绘制线段。|
|`im.draw_vline(location, stroke={color}, stroke_width=1)`|`im.draw_vlines(list_of_locations, **kwargs)`| 在 x=location 处绘制竖线。|
|`im.draw_hline(location, stroke={color}, stroke_width=1)`|`im.draw_hlines(list_of_locations, **kwargs)`| 在 y=location 处绘制横线。|
|`im.draw_rect(bbox_or_obj, fill={color}, stroke={color}, stroke_width=1)`|`im.draw_rects(list_of_rects, **kwargs)`| 根据 `rect`、`char` 等对象或 4 元组边界框绘制矩形。|
|`im.draw_circle(center_or_obj, radius=5, fill={color}, stroke={color})`|`im.draw_circles(list_of_circles, **kwargs)`| 在 `(x, y)` 或对象中心绘制圆。|

注：上述方法基于 Pillow 的 [`ImageDraw` 方法](http://pillow.readthedocs.io/en/latest/reference/ImageDraw.html)，但参数命名调整为更接近 SVG 的 `fill`/`stroke`/`stroke_width` 约定。

### 表格检测的可视化调试

`im.debug_tablefinder(table_settings={})` 将返回覆盖了已检测线（红色）、交点（圆点）与表格（浅蓝）的 `PageImage`。

<a id="extracting-text"></a>

## 提取文本

`pdfplumber` 可从任意页面（含裁剪/派生页面）抽取文本；也可尽量保留文本的版式布局，并能识别单词与搜索结果的坐标。`Page` 对象提供以下文本抽取方法：

| 方法 | 说明 |
|------|------|
|`.extract_text(x_tolerance=3, x_tolerance_ratio=None, y_tolerance=3, layout=False, x_density=7.25, y_density=13, line_dir_render=None, char_dir_render=None, **kwargs)`| 将页面字符对象整理为一个字符串。<ul><li>当 `layout=False`：若前后字符之间 `x1 -> 下个 x0` 的差值大于 `x_tolerance`，插入空格；若相邻字符 `doctop` 差值大于 `y_tolerance`，插入换行。（若设置了 `x_tolerance_ratio`，则动态容差=`x_tolerance_ratio * 前一字符 size`。）</li><li>当 `layout=True`（实验特性）：尝试模拟页面结构布局，`x_density`/`y_density` 决定每“点”（PDF 度量单位）的最小字符/换行数。传入 `line_dir_render="ttb"/"btt"/"ltr"/"rtl"` 与/或 `char_dir_render=...` 可改变输出方向。其余 `**kwargs` 会传给 `.extract_words(...)`，这是计算布局的第一步。</li></ul>|
|`.extract_text_simple(x_tolerance=3, y_tolerance=3)`| 更快但更不灵活的简化版本。|
|`.extract_words(x_tolerance=3, x_tolerance_ratio=None, y_tolerance=3, keep_blank_chars=False, use_text_flow=False, line_dir="ttb", char_dir="ltr", line_dir_rotated="ttb", char_dir_rotated="ltr", extra_attrs=[], split_at_punctuation=False, expand_ligatures=True, return_chars=False)`| 返回页面上所有“像单词的东西”及其边界框的列表。对于“正立”字符，若前后字符间横向间隔 ≤ `x_tolerance` 且 `doctop` 差 ≤ `y_tolerance`，则认为同属一词。（若设置 `x_tolerance_ratio`，则动态容差=上一字符字号×该比值。）对非正立字符使用纵向距离判断。`keep_blank_chars=True` 时空白字符也视为词的一部分。`use_text_flow=True` 则按 PDF 原始字符流顺序进行分组与排序（类似 PDF 中鼠标拖拽选择文字的顺序）。`line_dir`/`char_dir` 表示期望的行/字符阅读方向：`ttb`（上到下）、`btt`（下到上）、`ltr`（左到右）、`rtl`（右到左）；`line_dir_rotated`/`char_dir_rotated` 类似，但用于旋转文本。传入 `extra_attrs`（如 `["fontname", "size"]`）会限制组成单词的字符在这些属性上完全一致，并将这些属性包含在返回的词字典中。`split_at_punctuation=True` 会在指定标点处分词；也可传入标点字符串自定义。默认 `expand_ligatures=True` 会将连字（如 `ﬁ`）展开为 `fi`。`return_chars=True` 会在每个词字典中附带其组成字符列表（字段名为 `"chars"`）。|
|`.extract_text_lines(layout=False, strip=True, return_chars=True, **kwargs)`|（实验特性）返回表示页面文本行的字典列表。`strip` 类似 `str.strip()`，返回去除首尾空白后的 `text`（仅当 `layout=True` 时相关）。`return_chars=False` 将不包含字符对象。其余 `**kwargs` 同 `.extract_text(layout=True, ...)`。|
|`.search(pattern, regex=True, case=True, main_group=0, return_groups=True, return_chars=True, layout=False, **kwargs)`|（实验特性）在页面文本中搜索，返回所有匹配项列表。每项包含匹配文本、正则分组、边界框坐标与字符对象。`pattern` 可为编译/未编译正则或非正则字符串。`regex=False` 时按普通字符串匹配；`case=False` 时忽略大小写。`main_group` 可限制为特定分组（默认 `0` 表示整体匹配）。`return_groups`/`return_chars` 为 `False` 时将不返回对应列表。`layout` 参数与 `.extract_text(...)` 相同；其余 `**kwargs` 同 `.extract_text(layout=True, ...)`。注：零宽或全空白匹配会被丢弃。|
|`.dedupe_chars(tolerance=1, extra_attrs=("fontname", "size"))`| 去重与其他字符在 `text`、位置（x/y 容差内）及 `extra_attrs` 完全一致的重复字符（参见 [Issue #71](https://github.com/jsvine/pdfplumber/issues/71)）。|

<a id="extracting-tables"></a>

## 提取表格

`pdfplumber` 的表格检测方法大量借鉴了 [Anssi Nurminen 的硕士论文](https://trepo.tuni.fi/bitstream/handle/123456789/21520/Nurminen.pdf?sequence=3)，并受 [Tabula](https://github.com/tabulapdf/tabula-extractor/issues/16) 启发。基本流程：

1. 对页面，寻找（a）显式绘制的线条 和/或（b）由单词对齐“隐含”的线条。
2. 合并重叠或近似重叠的线段。
3. 查找所有这些线的交点。
4. 使用这些交点作为顶点，找出最细粒度的矩形（单元格）。
5. 将相邻单元格聚合为表格。

### 表格抽取方法

`pdfplumber.Page` 提供如下表格相关方法：

| 方法 | 说明 |
|------|------|
|`.find_tables(table_settings={})`| 返回 `Table` 对象列表。`Table` 提供 `.cells`、`.rows`、`.columns`、`.bbox` 属性，以及 `.extract(x_tolerance=3, y_tolerance=3)` 方法。|
|`.find_table(table_settings={})`| 返回页面上“最大”的表（按单元格数量比较）。若有并列，返回靠近页面顶部者。|
|`.extract_tables(table_settings={})`| 返回页面上“所有表”的文本，结构为 `table -> row -> cell` 的三层列表。|
|`.extract_table(table_settings={})`| 返回页面上“最大表”的文本，结构为 `row -> cell` 的二层列表。|
|`.debug_tablefinder(table_settings={})`| 返回 `TableFinder` 实例，并可访问 `.edges`、`.intersections`、`.cells`、`.tables`。|

示例：

```python
pdf = pdfplumber.open("path/to/my.pdf")
page = pdf.pages[0]
page.extract_table()
```

[点此查看更详细的示例](examples/notebooks/extract-table-ca-warn-report.ipynb)。

### 表格抽取设置

默认情况下，`extract_tables` 使用页面的垂直/水平线（或矩形边）作为单元格分隔线。但可通过 `table_settings` 高度定制。可选设置及默认值：

```python
{
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": [],
    "snap_tolerance": 3,
    "snap_x_tolerance": 3,
    "snap_y_tolerance": 3,
    "join_tolerance": 3,
    "join_x_tolerance": 3,
    "join_y_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 3,
    "min_words_horizontal": 1,
    "intersection_tolerance": 3,
    "intersection_x_tolerance": 3,
    "intersection_y_tolerance": 3,
    "text_tolerance": 3,
    "text_x_tolerance": 3,
    "text_y_tolerance": 3,
    "text_*": …,
}
```

| 设置 | 说明 |
|------|------|
|`"vertical_strategy"`| 可为 `"lines"`、`"lines_strict"`、`"text"` 或 `"explicit"`。详见下文。|
|`"horizontal_strategy"`| 同上。|
|`"explicit_vertical_lines"`| 明确指定用于分隔单元格的垂直线列表。可与任一策略组合。列表项可为数值（表示贯穿整页高度、x 为该数值的直线）或 `line`/`rect`/`curve` 对象。|
|`"explicit_horizontal_lines"`| 明确指定水平分隔线列表。用法同上。|
|`"snap_tolerance"`/`"snap_x_tolerance"`/`"snap_y_tolerance"`| 平行且相距小于该容差的线会“吸附”到相同位置。|
|`"join_tolerance"`/`"join_x_tolerance"`/`"join_y_tolerance"`| 同一直线上的线段，若端点之间距离小于该容差，将被“拼接”为一条更长的线段。|
|`"edge_min_length"`| 过短的边在构表前会被丢弃。|
|`"min_words_vertical"`| 当使用 `"vertical_strategy": "text"` 时，至少需要有 `min_words_vertical` 个词具有相同对齐。|
|`"min_words_horizontal"`| 当使用 `"horizontal_strategy": "text"` 时，至少需要有 `min_words_horizontal` 个词具有相同对齐。|
|`"intersection_tolerance"`/`"intersection_x_tolerance"`/`"intersection_y_tolerance"`| 组合边为单元格时，要求正交边之间的距离在该容差范围内，才视为“相交”。|
|`"text_*"`| 所有以 `text_` 打头的设置在从已发现表格中抽取文本时生效；传递给 `Page.extract_text(...)` 的参数也都可用于此处。|
|`"text_x_tolerance"`/`"text_y_tolerance"`| 当使用 `text` 策略识别表格时，这两个 `text_` 设置也用于“找词”的阶段，即假设同一单词中的字符横/纵向最大间隔。|

### 抽取策略

`vertical_strategy` 与 `horizontal_strategy` 均可取：

| 策略 | 说明 |
|------|------|
|`"lines"`| 使用页面的图形线条（包含矩形边）作为潜在单元格边界。|
|`"lines_strict"`| 使用页面的“直线”，但不包含矩形边。|
|`"text"`| 对垂直策略：根据页面上单词的左/右/中对齐位置推断“虚拟”线，作为单元格边界；水平策略类似，但参考单词的“上边”。|
|`"explicit"`| 仅使用 `explicit_vertical_lines` 与 `explicit_horizontal_lines` 中明确给出的线。|

#### 备注

- 抽取表格前，先对页面进行裁剪（`Page.crop(bounding_box)`）通常会更有效。
- 自 `v0.5.0` 起，`pdfplumber` 的表格抽取经历了较大重构，并引入了不兼容变更。

<a id="extracting-form-values"></a>

## 提取表单值

某些 PDF 含有可填写并保存的表单。表单字段中的“显示文本”看起来与 PDF 其他文字类似，但其数据处理方式不同。详情可参见这份[规范第 671 页](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf)。

`pdfplumber` 没有专门的表单接口，但可以通过 `pdfplumber` 对 `pdfminer` 的封装来访问表单数据。示例脚本如下（抽取字段名与值并存入字典）：

```python
import pdfplumber
from pdfplumber.utils.pdfinternals import resolve_and_decode, resolve

pdf = pdfplumber.open("document_with_form.pdf")

def parse_field_helper(form_data, field, prefix=None):
    """ 将 PDF AcroForm 中的字段/值对追加到 form_data 列表中

        若 `field` 包含子字段，将递归解析。
    """
    resolved_field = field.resolve()
    field_name = '.'.join(filter(lambda x: x, [
        prefix,
        resolve_and_decode(resolved_field.get("T"))
    ]))
    if "Kids" in resolved_field:
        for kid_field in resolved_field["Kids"]:
            parse_field_helper(form_data, kid_field, prefix=field_name)
    if "T" in resolved_field or "TU" in resolved_field:
        # "T" 是字段名，可能缺失；
        # "TU" 为“备用字段名”，通常更易读；
        # 你的 PDF 可能只有其一或两者兼有。
        alternate_field_name  = (
            resolve_and_decode(resolved_field.get("TU"))
            if resolved_field.get("TU") else None
        )
        field_value = (
            resolve_and_decode(resolved_field["V"]) if 'V' in resolved_field else None
        )
        form_data.append([field_name, alternate_field_name, field_value])


form_data = []
fields = resolve(resolve(pdf.doc.catalog["AcroForm"])['Fields'])
for field in fields:
    parse_field_helper(form_data, field)
```

执行后，`form_data` 为包含三元组的列表，例如一个含“城市”和“州”字段的 PDF：

```
[
 ['STATE.0', 'enter STATE', 'CA'],
 ['section 2  accident infoRmation.1.0',
  'enter city of accident',
  'SAN FRANCISCO']
]
```

感谢 [@jeremybmerrill](https://github.com/jeremybmerrill) 对以上表单解析代码的维护。

<a id="demonstrations"></a>

## 演示

- 使用 `extract_table` 解析加州 WARN 报告：[examples/notebooks/extract-table-ca-warn-report.ipynb](examples/notebooks/extract-table-ca-warn-report.ipynb)。演示可视化调试与表格抽取基础。
- 解析 FBI NICS 报表：[examples/notebooks/extract-table-nics.ipynb](examples/notebooks/extract-table-nics.ipynb)。演示如何用可视化调试寻找最佳表格抽取设置，并展示 `Page.crop(...)` 与 `Page.extract_text(...)`。
- 检视与可视化 `curve` 对象：[examples/notebooks/ag-energy-roundup-curves.ipynb](examples/notebooks/ag-energy-roundup-curves.ipynb)。
- 从圣何塞警方的枪械报告中抽取定宽数据：[examples/notebooks/san-jose-pd-firearm-report.ipynb](examples/notebooks/san-jose-pd-firearm-report.ipynb)，演示 `Page.extract_text(...)` 的使用。

<a id="comparison-to-other-libraries"></a>

## 与其他库的对比

许多 Python 库能从 PDF 中抽取信息。相较之下，`pdfplumber` 的特点在于：

- 易于获取每个 PDF 对象的详细信息；
- 提供更高层、可定制的文本/表格抽取方法；
- 与可视化调试紧密结合；
- 实用的工具函数，如通过裁剪框过滤对象等。

同样需要了解的是 `pdfplumber` 并不提供：

- PDF 的“生成”；
- PDF 的“修改”；
- 光学字符识别（OCR）；
- 对 OCR 文档表格抽取的强支持。

### 具体对比

- [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six) 是 `pdfplumber` 的基础，专注解析 PDF、布局分析与文本抽取；不提供表格抽取或可视化调试。许可证： [MIT](https://github.com/pdfminer/pdfminer.six?tab=MIT-1-ov-file)。

- [`PyPDF2`](https://github.com/mstamy2/PyPDF2) 是纯 Python 的 PDF 处理库，支持页面拆分/合并/裁剪/变换，设置自定义数据、查看选项与密码等；能抽取页面文本，但不提供形状对象（矩形、直线等）、表格抽取或可视化调试。许可证： [BSD](https://github.com/py-pdf/pypdf?tab=License-1-ov-file#readme)。

- [`pymupdf`](https://pymupdf.readthedocs.io/) 比 `pdfminer.six`（进而也比 `pdfplumber`）快得多，且能生成与修改 PDF，但需要安装 MuPDF（非纯 Python 依赖）。同时不便于获取形状对象，也不提供表格抽取或可视化调试。许可证： [AGPL](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)。

- [`camelot`](https://github.com/camelot-dev/camelot)、[`tabula-py`](https://github.com/chezou/tabula-py) 与 [`pdftables`](https://github.com/drj11/pdftables) 主要聚焦表格抽取，在某些场景可能更适合你的表格。许可证： [MIT](https://github.com/camelot-dev/camelot?tab=MIT-1-ov-file#readme)（camelot）、[MIT](https://github.com/chezou/tabula-py?tab=MIT-1-ov-file#readme)（tabula-py）、[BSD](https://github.com/drj11/pdftables?tab=BSD-2-Clause-1-ov-file#readme)（pdftables）。

<a id="acknowledgments--contributors"></a>

## 致谢 / 贡献者

衷心感谢以下用户的点子、功能与修复（按英文 README 顺序）：

- [Jacob Fenton](https://github.com/jsfenfen)
- [Dan Nguyen](https://github.com/dannguyen)
- [Jeff Barrera](https://github.com/jeffbarrera)
- [Bob Lannon](https://github.com/boblannon)
- [Dustin Tindall](https://github.com/dustindall)
- [@yevgnen](https://github.com/Yevgnen)
- [@meldonization](https://github.com/meldonization)
- [Oisín Moran](https://github.com/OisinMoran)
- [Samkit Jain](https://github.com/samkit-jain)
- [Francisco Aranda](https://github.com/frascuchon)
- [Kwok-kuen Cheung](https://github.com/cheungpat)
- [Marco](https://github.com/ubmarco)
- [Idan David](https://github.com/idan-david)
- [@xv44586](https://github.com/xv44586)
- [Alexander Regueiro](https://github.com/alexreg)
- [Daniel Peña](https://github.com/trifling)
- [@bobluda](https://github.com/bobluda)
- [@ramcdona](https://github.com/ramcdona)
- [@johnhuge](https://github.com/johnhuge)
- [Jhonatan Lopes](https://github.com/jhonatan-lopes)
- [Ethan Corey](https://github.com/ethanscorey)
- [Shannon Shen](https://github.com/lolipopshock)
- [Matsumoto Toshi](https://github.com/toshi1127)
- [John West](https://github.com/jwestwsj)
- [David Huggins-Daines](https://github.com/dhdaines)
- [Jeremy B. Merrill](https://github.com/jeremybmerrill)
- [Echedey Luis](https://github.com/echedey-ls)
- [Andy Friedman](https://github.com/afriedman412)
- [Aron Weiler](https://github.com/aronweiler)
- [Quentin André](https://github.com/QuentinAndre11)
- [Léo Roux](https://github.com/leorouxx)
- [@wodny](https://github.com/wodny)
- [Michal Stolarczyk](https://github.com/stolarczyk)
- [Brandon Roberts](https://github.com/brandonrobertz)
- [@ennamarie19](https://github.com/ennamarie19)

<a id="contributing"></a>

## 参与贡献

欢迎提交 Pull Request，但由于库处于活跃开发阶段，请先提交 Proposal issue 进行讨论。

当前维护者：

- [Jeremy Singer-Vine](https://github.com/jsvine)
- [Samkit Jain](https://github.com/samkit-jain)
