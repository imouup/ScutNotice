# ScutNotice 项目文档

## 1. 项目简介

ScutNotice 是一个针对华南理工大学（SCUT）各类通知信息的抓取与聚合系统。它能够自动抓取教务处、统一门户（MyScut）以及校团委的通知公告，对数据进行去重和持久化存储，并自动生成标准的 RSS 订阅源文件，方便用户通过 RSS 阅读器通过订阅及时获取校园资讯。

## 2. 系统架构

本项目采用微服务架构思想，包含两个运行在不同端口的 Flask Web 服务：

1.  **抓取与接口服务 (Data Getter)**
    *   **文件**: `dataGet.py`
    *   **端口**: `5000`
    *   **职责**: 提供外部访问 API，负责执行具体的爬虫逻辑，维护数据存储，并在检测到新数据时请求 RSS 服务进行更新。
2.  **RSS 生成服务 (RSS Generator)**
    *   **文件**: `rss.py`
    *   **端口**: `5001`
    *   **职责**: 接收抓取服务的更新指令，读取本地存储的通知数据，生成 XML 格式的 RSS 文件。

### 目录结构说明

```
ScutNotice/
├── data/                   # 数据存储目录
│   ├── *_q.json            # Quick Storage: 缓存最近一次抓取的数据，用于增量比对
│   ├── *_long.json         # Long Storage: 持久化存储的历史全量数据
│   └── lastUpdated.txt     # 记录最后一次更新的时间戳
├── headers/                # 请求头配置目录 (Cookie 等)
│   ├── jw_headers.json
│   ├── myscut_headers.json
│   └── youth_headers.json
├── rsspublic/              # 生成的 RSS 文件存放目录 (对外发布)
│   ├── jw/, myscut_*/, ...
├── public/                 # 静态资源目录 (前端页面等)
├── scrabbler.py            # 核心爬虫类与逻辑实现
├── dataGet.py              # 抓取服务入口
├── rss.py                  # RSS 服务入口
├── requirements.txt        # 项目依赖
└── README.md               # 项目说明
```

## 3. 核心功能与逻辑

### 3.1 数据抓取逻辑 (`scrabbler.py`)

系统使用 `Scrabbler` 类封装了所有平台的抓取逻辑。核心流程如下：

1.  **请求 (Request)**: 使用 `requests` 库发送 HTTP 请求。针对统一门户使用了自定义 SSL Context (`Low_secure_HttpAdapter`) 以兼容老旧服务器加密算法。支持 SOCKS5 代理（硬编码配置）。
2.  **解析 (Parse)**: 
    *   **教务/统一门户**: 解析 JSON 响应。
    *   **校团委**: 使用 `re` 正则表达式解析 HTML 页面。
3.  **比对 (Compare)**: 将新抓取的数据 ID 与 `*_q.json` (内存中也有缓存) 进行比对，识别新增通知。
4.  **存储 (Storage)**:
    *   更新 `*_q.json` 为最新状态。
    *   将新增数据追加合并到 `*_long.json` 中。
5.  **反馈**: 返回抓取结果及 `WhetherNew` 标志（1表示有更新，0表示无）。

### 3.2 RSS 生成逻辑 (`rss.py`)

RSS 服务监听 `5001` 端口。当 `dataGet` 检测到新数据时，会 POST 请求 `http://127.0.0.1:5001/update`。

*   **读取**: 从 `data/*_long.json` 读取全量数据。
*   **排序**: 按 `createTime` 倒序排列。
*   **生成**: 使用 `feedgen` 库生成 RSS 2.0 XML 文件。
*   **输出**: 文件保存在 `rsspublic/{name}/` 目录下。

## 4. API 接口文档

### 4.1 抓取服务 API (Host: `127.0.0.1:5000`)

#### 4.1.1 获取教务处通知
*   **Endpoint**: `/scut/jwnotice`
*   **Method**: `GET`
*   **描述**: 抓取教务处或学院通知。
*   **参数**:

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| `name` | string | 是 | - | `jw` (教务处) 或 `xy` (学院) |
| `tag` | int | 否 | 0 | 分类标签 (见下文附录) |
| `pageNum` | int | 否 | 1 | 页码 |
| `pageSize`| int | 否 | 15 | 每页数量 |

*   **响应示例**:
    ```json
    {
      "getre": [
        {"message": "Scrabble successful", "WhetherNew": 1, "NewData": {...}},
        200
      ],
      "update_re": {...} // RSS更新结果
    }
    ```

#### 4.1.2 获取统一门户通知
*   **Endpoint**: `/scut/myscut_notice`
*   **Method**: `GET`
*   **描述**: 抓取 MyScut 门户各类公文通知。
*   **参数**:

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| `name` | string | 是 | - | 可选值: `myscut_gw` (公务), `myscut_sw` (事务), `myscut_xz` (行政), `myscut_dw` (党务), `myscut_xs` (学术), `myscut_news` (新闻) |
| `pageNum` | int | 否 | 1 | 页码 |

#### 4.1.3 获取校团委通知
*   **Endpoint**: `/scut/youth_notice`
*   **Method**: `GET`
*   **描述**: 抓取华南理工大学校团委网站通知公告。
*   **参数**:

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| `name` | string | 否 | `youth` | 固定为 youth |
| `pageNum` | int | 否 | 1 | 页码 (对应 list.htm, list2.htm...) |

#### 4.1.4 修改 Headers 配置
*   **Endpoint**: `/scut/edit_headers`
*   **Method**: `POST`
*   **Content-Type**: `application/json`
*   **描述**: 动态更新保存在 `headers/` 目录下的 JSON 配置文件（通常用于更新 Cookie）。
*   **Body**:
    ```json
    {
      "platform": "jw", // 或 "myscut", "youth"
      "headers": {
        "Cookie": "new_cookie_value...",
        "User-Agent": "..."
      }
    }
    ```

### 4.2 RSS 服务 API (Host: `127.0.0.1:5001`)

#### 4.2.1 触发 RSS 更新
*   **Endpoint**: `/update`
*   **Method**: `POST`
*   **Content-Type**: `application/json`
*   **描述**: 这是一个内部接口，通常由 `dataGet.py` 调用，用于触发特定频道的 RSS 文件重新生成。
*   **Body**:
    ```json
    {
      "name": "jw",    // 频道名称
      "multi": 1,      // 是否包含多个 tags (0/1)
      "tag_num": 6     // tag 最大索引值
    }
    ```

#### 4.2.2 获取系统最后更新时间
*   **Endpoint**: `/lastUpdated`
*   **Method**: `GET`
*   **描述**: 获取任何频道最后一次触发更新的时间。

## 5. 附录：数据字典

### 5.1 教务通知 (`jw`) Tags 定义
| Tag ID |含义 |
| :--- | :--- |
| 0 | 全部教务通知 |
| 1 | 选课 |
| 2 | 考试 |
| 3 | 实践 |
| 4 | 交流 |
| 5 | 教师 |
| 6 | 信息 |

### 5.2 学院通知 (`xy`) Tags 定义
| Tag ID | 含义 |
| :--- | :--- |
| 0 | 全部学院通知 |
| 1 | 选课 |
| 2 | 考试 |
| 6 | 信息 |

## 6. 部署与运行

**环境依赖**:
Python 3.8+
安装依赖包: `pip install -r requirements.txt`

**启动步骤**:
需要同时启动两个服务进程：

1.  启动 RSS 服务:
    ```bash
    python rss.py
    ```
2.  启动 抓取主服务:
    ```bash
    python dataGet.py
    ```

**注意**: 若部署在内网环境抓取公网/校内网数据，请检查 `scrabbler.py` 中的 `_load_proxy` 方法，确保 SOCKS5 代理配置正确，或在不需要代理的环境下将其移除。
