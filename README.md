# 半导体应急指挥系统

这是一个面向晶圆厂、洁净室、特气站、化学品区与厂务系统的应急指挥系统项目，围绕应变处置、事件管理、营运恢复三段逻辑构建。

## 紧急应变指挥系统

仓库内包含一个通用应急指挥系统原型，适合演示事件分级、统一指挥、资源调度、分区态势和通信日志。

启动方式：

```bash
streamlit run emergency_command_app.py
```

主要能力：

- 依据严重度、影响人数、重点点位、医疗承压和通信状态计算响应等级
- 生成符合事故现场指挥系统思路的指挥编组和任务看板
- 展示资源出动、短缺预估和现场分区风险态势
- 支持在页面内追加指挥通信日志，形成统一播报链路

## 半导体应急指挥系统

仓库内提供半导体厂专用应急指挥台，适用于晶圆厂、封测厂、特气站、化学品仓与洁净室异常场景。

启动方式：

```bash
streamlit run semiconductor_command_app.py
```

主要能力：

- 覆盖化灾、火灾、气灾、地震、电力中断或压降、异味、暴雨天气、台风天气、漏水事件
- 使用 FAB 场景指标计算厂级响应等级，联动 EHS、厂务、设备、制造和 IT/MES
- 形成批次冻结、机台保全、洁净恢复、公辅保障和事故通信日志的统一大屏
- 提供 ALOHA 快速推估、GHS 参考、GMS 读值、跨厂 CCTV、点名和 SOP 当前节点

## 半导体应急指挥系统部署

项目已经补齐容器化部署文件，默认上线入口是：

```bash
streamlit run semiconductor_command_app.py
```

### 方式一：直接部署到 Linux 服务器

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run semiconductor_command_app.py --server.address 0.0.0.0 --server.port 8501
```

如果要给局域网或反向代理访问，建议使用 `nginx` 反代到 `8501` 端口。

### 方式二：Docker 部署

```bash
docker build -t semiconductor-erc .
docker run -d --name semiconductor-erc -p 8501:8501 semiconductor-erc
```

如果平台要求读取环境变量端口，容器已支持：

```bash
docker run -d --name semiconductor-erc -e PORT=8501 -p 8501:8501 semiconductor-erc
```

### 已补齐的上线文件

- `Dockerfile`
- `.dockerignore`
- `.streamlit/config.toml`

### 上线建议

- 生产环境建议使用 `nginx` 或云平台负载均衡做入口
- 如果后续要接入真实 `CCTV`、`GMS`、`火警报警`、`广播`，建议把接口地址放进环境变量或独立配置文件
- 当前版本适合演示、内网部署和原型联调；若要正式上线，下一步建议补登录鉴权、接口鉴权、数据库持久化和操作审计

## 目录结构

```text
.
├── semiconductor_command_app.py
├── emergency_command_app.py
├── emergency_app
│   ├── core.py
│   └── semiconductor.py
├── docs
│   └── index.html
└── tests
    ├── test_emergency_core.py
    └── test_semiconductor_command.py
```

## 后续扩展建议

- 接入真实 `CCTV`、`GMS`、`火警报警`、`广播` 与 `门禁` 接口
- 增加登录鉴权、接口鉴权、数据库持久化和操作审计
- 把 `GitHub Pages` 展示页继续深化成完整的产品说明与演示入口
